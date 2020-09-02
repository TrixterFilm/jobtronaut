# ######################################################################################################################
#  Copyright 2020 TRIXTER GmbH                                                                                         #
#                                                                                                                      #
#  Redistribution and use in source and binary forms, with or without modification, are permitted provided             #
#  that the following conditions are met:                                                                              #
#                                                                                                                      #
#  1. Redistributions of source code must retain the above copyright notice, this list of conditions and the following #
#  disclaimer.                                                                                                         #
#                                                                                                                      #
#  2. Redistributions in binary form must reproduce the above copyright notice, this list of conditions and the        #
#  following disclaimer in the documentation and/or other materials provided with the distribution.                    #
#                                                                                                                      #
#  3. Neither the name of the copyright holder nor the names of its contributors may be used to endorse or promote     #
#  products derived from this software without specific prior written permission.                                      #
#                                                                                                                      #
#  THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES,  #
#  INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE   #
#  DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,  #
#  SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS        #
#  OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF           #
#  LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY    #
#  OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.                                 #
# ######################################################################################################################

"""BaseProcessors and Processor Schemas to implement custom processors """

from collections import (
    Iterable,
    namedtuple
)
import hashlib
import logging
import re
import os
from schema import Schema, SchemaError, And, Or, Use
import uuid

from .argument import (
    Arguments,
    ArgumentValue
)
from ..constants import (
    BASH_STYLES,
    LOGGING_NAMESPACE
)
from .plugins import Plugins

_LOG = logging.getLogger("{}.processor".format(LOGGING_NAMESPACE))
_ProcessorDefinition = namedtuple("Processor", ["name", "scope", "parameters"])


def ProcessorDefinition(name, scope=[], parameters={}):
    """ Processor Factory Function that "looks" like a class (due to its CamelCase naming on purpose """
    return _ProcessorDefinition(name, scope, parameters)


MethodStore = namedtuple("MethodStore", ["method", "schema"])


class ProcessorSchemas(object):
    """ Simple container that holds preset schemas to be used by the processors """
    # some preconfigured schemas for easy access
    FRAMERANGE = Schema(And([int], lambda x: len(x) == 2, lambda x: x[0] <= x[1]))  # only allow increasing/equal range
    FRAMERANGES = Schema([FRAMERANGE])


class Overload(type):

    methods = dict()

    def __new__(cls, name, bases, attrs):
        # we add the temp methods from the class attribute to the class
        # we are constructing. The original method call will then end up
        # in the wrapper which will forward the request to the correct
        # method.
        for methodname, method in Overload.methods.iteritems():
            attrs[methodname] = method
        cls.methods = dict()
        return super(Overload, cls).__new__(cls, name, bases, attrs)


def schema_to_hex(*args):
    """ Converts an arbitrary amount of schemas into a unique hash.

    Args:
        *args (Schema): Variable number of Schemas

    Returns:
        str: a unique hash given the input Schemas

    """
    hashobj = hashlib.md5()
    hashobj.update(str(sum([hash(_) for _ in args])))
    return hashobj.hexdigest()


def supported_schemas(*argument):  # contains the actual supported schemas
    # @todo prefer more specialised schemas over broader schemas so FRAMERANGE will be chosen over [int]
    def inner(func):  # func is the overloaded method
        """ Will be run when the processors are initialized.
        """
        def wrapper(*args, **kwargs): # the arguments that we pass to the process method upon calling
            """ Will be run when the actual process method is called.
            """
            assert issubclass(args[0].__class__, BaseProcessor) and func.__name__ == "process", \
                   "Decorator is only supposed to work on process method of BaseProcessor subclasses"

            value = args[2]
            field = None

            # as valid will be our input we are checking against we want to store a unique identifier
            # if our initial value got overriden
            # which means that we didn't raise a SchemaError, so our schema is valid
            _valid = valid = uuid.uuid4()
            processor_name = args[0].__class__.__name__

            for fieldname in dir(args[0]):
                field = getattr(args[0], fieldname)

                if fieldname.startswith(func.__name__) and isinstance(field, MethodStore):
                    _LOG.info("{0}: Validating argument {1} against schema {2}\nValue: {3}"
                              .format(processor_name, args[1], field.schema, value))
                    # We try to validate it directly first. If validation failes an exception is thrown
                    # this has to be wrapped as schema.validate raises an exception if the schema can't be matched
                    try:
                        valid = field.schema.validate(value)
                        _LOG.info("{0}: Found matching processor implementation for argument \"{1}\" with value \"{2}\""
                                  .format(processor_name, args[1], valid))
                        break
                    except SchemaError:
                        # this exception is separate as we always want to try the automatic conversion ESPECIALLY
                        # if this raises
                        _LOG.debug("{0}: Purposefully ignoring SchemaError.".format(processor_name))

                    try:
                        # If direct validation fails we try and to a conversion for single element lists and simple
                        # types because those are safe to do. int -> [int], [str] -> str ...
                        if isinstance(value, list) and len(value) == 1:
                            valid = field.schema.validate(value[0])
                            _LOG.info("{0}: Automatically converted argument \"{1}\" from \"{2}\" to \"{3}\""
                                      .format(processor_name, args[1], args[2], valid))
                        elif not isinstance(value, Iterable) or isinstance(value, str):
                            valid = field.schema.validate([value])
                            _LOG.info("{0}: Automatically converted argument \"{1}\" from \"{2}\" to \"{3}\""
                                      .format(processor_name, args[1], args[2], valid))
                    except SchemaError:
                        # we ignore the exceptions here but raise them again later
                        _LOG.debug("{0}: Purposefully ignoring SchemaError.".format(processor_name))

            if valid != _valid:
                new_args = list(args)
                new_args[2] = valid

                return field.method(*new_args, **kwargs)

            else:
                raise SchemaError("No matching processor has been implemented on {0} for the argument value {1}"
                                  .format(processor_name, value))

        schemas = Schema(Or(*argument))
        set_methodname = "{0}_{1}".format(func.__name__, schema_to_hex(schemas))
        Overload.methods[set_methodname] = MethodStore(method=func, schema=schemas)

        return wrapper
    return inner


class BaseProcessor(object):
    """ a basic arguments processor that will direct all required arguments towards task arguments
    """
    __metaclass__ = Overload
    description = "No description has been set."
    parameters = {}

    def __init__(self):
        self.task = None
        self._argument_re = re.compile(r"(?P<to_replace>\<\s*arg:\s*(?P<name>[a-zA-Z0-9_\-]*)\.(?P<state>(initial|processed))\s*\>)")
        self._expression_re = re.compile(r"(?P<to_replace>\<\s*expr:\s*(?P<expression>[^\<\>]*)\s*\>)")

    def __call__(self, task, scope, parameters):
        # store the task in the object primarily for access to the task arguments
        self.task = task
        task_arguments = Arguments(self.task.arguments)
        resolved_parameters = {key: self._resolve(task, value) for key, value in parameters.iteritems()}

        # call the processors process() only for arguments in scope
        for arg_to_process in scope:
            argnametokens = arg_to_process.split(".")
            argument = self.task.arguments.__getattribute__(argnametokens[0])
            argument = ArgumentValue(argument.initial,
                                     self.process(argnametokens[0],
                                                  argument.__getattribute__(argnametokens[1]),
                                                  resolved_parameters)
                                     )
            task_arguments.set(argnametokens[0], argument)

        self.task.arguments = task_arguments
        # task = self.task  # task es passed by reference seems to be not necessary

    def process(self, argument_name, argument_value, parameters):
        return argument_value

    def _resolve(self, task, value):
        """ resolves argument values and python expressions

        Args:
            task (:obj: `Task`):
            value (str): value that will get resolved

        Notes:
            supported syntax examples: "<arg: foobar.initial>",
                                       "<arg: foobar.initial>_test_<arg: foobar.processed>",
                                       "<expr: len(\"test\")>,
                                       "<expr:<arg:foobar.initial>[0]>,
                                       "<expr: x=1;2*x>_<expr:x=5;x-3>


        Returns:
            undefined type or str: whenever it can be resolved it will be the intended type
            am argument value or python expression holds, otherwise it will be the unresolved string

        """
        _base_exception_msg = "Unable to resolve expression in processor `{}` on task `{}`: "

        try:
            result = self._resolve_arguments(task, value)
        except:
            _LOG.critical(
                (
                    _base_exception_msg +
                    "\nKnown Attributes are: {}"
                ).format(
                        self.__class__.__name__,
                        task.__class__.__name__,
                        [_ for _ in task.arguments.keys() if _ != "elements_id"]
                ), exc_info=True)
            raise

        try:
            result = self._resolve_expression(result)
        except:
            _LOG.critical(
                (
                    _base_exception_msg +
                    "\nIt properly resolved any argument value in '{}' to '{}' though.."
                ).format(
                    self.__class__.__name__,
                    task.__class__.__name__,
                    value,
                    result
                ),
                exc_info=True
            )
            raise

        return result

    @staticmethod
    def _post_resolve(match_object, original_value, preresolved_value):
        """ decides weather to keep resolved value type or convert to a string

        Args:
            match_object (:obj: `re.MatchObject`): regex match object
            original_value (str): original, unresolved value
            preresolved_value (undefined): a previously resolved value

        Returns:
            undefined type or str: the resolved value which can be of any type as long
            as the original string value represents exactly one resolved value, whereas
            multiple values will be expected to be of type string.

        """
        if match_object.groupdict()["to_replace"] == original_value:  # always use native type when expression identically
            return preresolved_value
        else:
            # support multiple replacements when resolved type can be converted to a string
            try:
                str(preresolved_value)
            except TypeError:
                _LOG.error("Can't resolve '{0}' successfully within {1}.".format(str(preresolved_value),
                                                                                 original_value),
                           exc_info=True)

            original_value = original_value.replace(match_object.groupdict()["to_replace"], str(preresolved_value))

        return original_value

    def _resolve_arguments(self, task, value):
        """ resolve all `<arg: >` matches

        Args:
            task (:obj: `Task`): task instance that keeps the arguments that shall be resolved
            value (str): string value to resolve

        Returns:
            undefined type: resolved value
        """
        if not isinstance(value, str):
            return value

        matches = self._argument_re.finditer(value)

        for match in matches:
            _LOG.debug("Resolving {0} state of argument '{1}' on processor '{2}'".format(
                match.groupdict()["state"],
                match.groupdict()["name"],
                self.__class__.__name__
                )
            )
            try:
                argument_value = getattr(task.arguments, match.groupdict()["name"])
                resolved = getattr(argument_value, match.groupdict()["state"])
                _LOG.debug("Resolve ArgumentValue '{0}' to {1}".format(match.groupdict()["name"], resolved))

                value = self._post_resolve(match, value, resolved)

            except AttributeError:
                raise

        return value

    def _resolve_expression(self, value):
        """ resolve all `<expr: >` matches

        Args:
            value (str): a preresolved string that must not have <arg: > expression anymore

        Returns:
            undefined type: resolved value
        """
        if not isinstance(value, str):
            return value

        matches = self._expression_re.finditer(value)

        for match in matches:
            _LOG.debug("Evaluating expression '{0}' on processor '{1}'".format(match.groupdict()["expression"],
                                                                               self.__class__.__name__))
            try:
                # try if we can evaluate directly without getting any errors, otherwise expect we have a statement
                resolved = eval(match.groupdict()["expression"])
            except:
                # lets cover a the statement case
                # going through statements and consider rightmost statement as the one to return
                # declaring *_result* smells a bit fishy, but works for our usecases
                statements = [statement for statement in match.groupdict()["expression"].rsplit(";") if statement]
                statements[-1] = "resolved=" + statements[-1]
                exec (";".join(statements))

            value = self._post_resolve(match, value, resolved)

        return value

    @classmethod
    def info(cls, short=True):
        """ Provides a nicely formatted representation to be used as a terminal
        output.

        Arguments:
            cls (class): The class which should be formatted
        """

        if short:
            infostr = "{BOLD}{BG_PURPLE}{FG_WHITE}" + cls.__name__ + "{END}"
        else:
            infostr = "\n{BOLD}{BG_PURPLE}{FG_WHITE}\n" + cls.__name__ + "\n{END}\n\n"
            infostr += "{BOLD}Description:" + "{END}\n"
            infostr += cls.description + "{END}\n\n"
            infostr += "{BOLD}Parameters:" + "{END}\n\n"
            for parameter, parameter_default in cls.parameters.items():
                parameter_default_type = type(parameter_default)
                parameter_default = Plugins.format_safe(parameter_default)
                infostr += "{BOLD} " + parameter + " {END}" + " (default [{}]: {})".format(
                    parameter_default_type, parameter_default
                ) + "{END}\n"

            infostr += "\n"

            infostr += "{BOLD}Module Path:" + "{END}\n"
            infostr += Plugins().get_module_path(cls.__name__) + "{END}\n\n"

            infostr += "\n"

        return infostr.format(**BASH_STYLES)

