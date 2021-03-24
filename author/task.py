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

""" Contains the Task class which extends tractor.author.Task

It handles hierarchy building, argument processing and most
importantly combines tractors concept of tasks and commands.

In our API the command is inherently a part of the task
and cannot be defined without a task.
"""

import copy

import difflib
import inspect
import logging
import os
import re
import tempfile
import uuid

from collections import Iterable

from tractor.api import author

from . import scripts
from .argument import (
    Arguments,
    ArgumentValue
)
from ..constants import (
    ARGUMENTS_SERIALIZED_MAX_LENGTH,
    BASH_STYLES,
    COMMANDFLAGS_ARGUMENT_NAME,
    EXECUTABLE_RESOLVER,
    LOGGING_NAMESPACE
)
from .plugins import Plugins
from .command import Command
from .job import (
    Job,
    jobs_to_task
)

_LOG = logging.getLogger("{}.author".format(LOGGING_NAMESPACE))


class Task(author.Task):
    """ extends the tractor Task class

    Here we have to define custom members that will help us to  build task dependencies with in
    an automated way.

    Attributes:
        requited_tasks (list): all child task classes that has to be specified, which will be
        needed to produce the expected result. Please not that required_tasks is supporting nested lists that
        will represent a simple syntax to add tasks in a serial or parallel way.

        Example:
            [Task1, Task2] - Task1 runs parallel to Task2
            (Task1, Task2) - Task2 runs after Task1
            [Task1, [Task2, Task3]] - Task1 runs parallel to Task2 & Task3, but Task3 starts when
            Task2 finishes
            [Task1, (Task2, Task3)] - Tas3 runs after Task2, Task2 runs parallel to Task1

        required_arguments (:obj:`list` of :obj:`str`): keyword arguments the must have for proper processing
        argument_processors (:obj:`list` of :obj:`ProcessorDefinition`): processors that will be called
        for each required argument
        name (str): name that will define the task title
        flags (): flags that will control the behavior of the task dependency

            Flags.SERIAL - If set it will add the direct childtask as serialsubtasks
            Flags.PER_ELEMENTS - If set the task will only work for a single elements, wheras if
            not set the task is capable to handle multiple elements at once, for example a list of
            numbers or strings

            Example:
            flags = Task.flags.SERIAL | Flags.PER_ELEMENTS

    """
    # additional members we have to add for the tractor assertions
    MEMBERS = author.Task.MEMBERS + [
        "arguments",
        "arguments_defaults",
        "elements_id",
        "is_handle_task",
        "required_arguments",
        "wait_for_task"
    ]

    description = "No description has been set."

    class Flags(object):
        """ represents a bitmask for additional Task options

        New flags have to have a value of 2^n to avoid ambigiuity.
        """
        SERIAL = 2**1
        PER_ELEMENT = 2**2
        NO_RETRY = 2**3
        NOOP = 2**16  # will pass all arguments through

    required_tasks = []
    required_arguments = []
    elements_id = None
    is_handle_task = False

    argument_defaults = {}

    # every defined processor will be called to process the incoming arguments
    argument_processors = []

    flags = 0

    services = ["linux64"]
    tags = []
    hostmask = ""
    retryrc = []

    # use it to bypass the job
    job = None

    title = ""

    def __init__(self, arguments, is_handle_task=True, wait_for_task=None, *args, **kwargs):
        """

        Args:
            arguments (:obj: `dict` or `Arguments` or `str`): task arguments
            is_handle_task (bool): defines if the task will be a simple null task
            that only serves as handle
            *args ():
            **kwargs ():
        """
        # generate the "null" task as self

        super(Task, self).__init__(*args, **kwargs)

        # use the class name as title if not given
        self.title = getattr(self.__class__, "title", "") or self.__class__.__name__

        # we automatically add
        self.id = str(uuid.uuid4())

        # access for instance usage
        self.wait_for_task = wait_for_task

        # run all assertions to verify if the task is valid
        self._is_valid()

        # store process state
        self.is_handle_task = is_handle_task

        # we are in "null" task and have all task properties (class attributes) available
        self.arguments = Arguments(arguments, **self.argument_defaults)

        # consider our elements mapper as required argument as well
        self._add_elements_mapper()

        # we have the original arguments so we have to process them
        if self.is_handle_task:
            self._process_arguments()

        # because we have processed all arguments now, we can set our elements
        # self.arguments.set("elements", self.arguments.get(self.elements_id, []), override=True)

        self.serialsubtasks = self.serial
        # add all subtasks to our "null" task (self)
        # the function has to handle the specific subtask addition based on the tasks properties

        # first intercept to catch potential stop conditions early
        if self.stop_traversal():
            return

        if self.is_handle_task and self._has_cmd(self.__class__):
            _LOG.debug("Handletask {}. Adding simple dependency...".format(self))
            self._add_command_tasks(*args, **kwargs)
        elif self.elements_id and self.per_element and self._is_expected_iterable(getattr(self.elements, "processed", None)):
            for element in self.elements.processed:
                element = ArgumentValue(self.elements.initial, element)
                self._add_required_tasks(self.required_tasks, self, elements=element, *args, **kwargs)
        else:
            self._add_required_tasks(self.required_tasks, self, elements=self.elements, *args, **kwargs)

    # when using the members as class attributes directly, we are having the issue
    # that the __getattr__ function of our parent task class will not be called anymore
    # for now this only was an issue when retrieving the title, but we might need to
    # extend it for other members
    def __getattribute__(self, attr):
        if attr == "title":
            return super(Task, self).__getattr__(attr)
        else:
            return super(Task, self).__getattribute__(attr)

    def _is_valid(self):
        assert not (self._has_cmd(self.__class__) and self.required_tasks), \
               "{0}: Tasks with a command cannot have required tasks. Introduce a parent task to manage your hierarchy." \
               .format(self.title)

    @property
    def elements(self):
        return self.arguments.get(self.elements_id)

    @property
    def serial(self):
        return (self.flags & self.Flags.SERIAL) > 0

    @property
    def per_element(self):
        return (self.flags & self.Flags.PER_ELEMENT) > 0

    @property
    def no_retry(self):
        return (self.flags & self.Flags.NO_RETRY) > 0

    # use our patched Command
    def addCommand(self, command):
        """Add the specified Command to command list of the Task."""
        if not isinstance(command, Command):
            raise TypeError("%s is not an instance of Command" % str(command))
        self.attributeByName["cmds"].addElement(command)

    # use our patched Command
    def newCommand(self, **kw):
        """Instantiate a new Command element, add to command list, and return
        element.
        """
        command = Command(**kw)
        self.addCommand(command)
        return command

    def stop_traversal(self):
        """Decide whether we want to add *this* task as well as all child tasks
        to the hierarchy.
        """
        return False

    @staticmethod
    def _has_cmd(cls):
        return "cmd" in dir(cls) and callable(cls.cmd)

    @staticmethod
    def _has_script(cls):
        return "script" in dir(cls) and callable(cls.script)

    @staticmethod
    def _has_view(cls):
        return "view" in dir(cls) and callable(cls.view)

    @staticmethod
    def _is_expected_iterable(obj):
        """ simply check if the object is dedicated for iteration

        We want to treat a str as not iterable here

        Args:
            obj ():

        Returns:

        """

        return isinstance(obj, Iterable) and not isinstance(obj, (str, unicode))

    # TODO: this wrapper should be removed...
    #  But for now we just keep it, as it is easier to patch within out unittests
    @staticmethod
    def _get_executable(cmd_id):
        return EXECUTABLE_RESOLVER(cmd_id)

    def _add_elements_mapper(self):
        """ add the element "mapper" as required argument

        Returns:

        """

        if not self.elements_id:
            assert "elements_id" in self.arguments, "elements_id has to be defined by an upstream task."
            self.elements_id = self.arguments.elements_id.initial
            _LOG.debug("No element mapper found. Inheriting '{0}' on {1}. ".format(self.elements_id, self))

        #_required_arguments.add(self.elements_id)
        self.arguments.set("elements_id", ArgumentValue(self.elements_id, self.elements_id), initialize=True)

    def _process_arguments(self):
        """ call all argument processors

        Returns:

        """
        if self.argument_processors:
            _LOG.debug("Processing arguments for task {} with processors ".format(self.title) +
                       ", ".join([processor.__class__.__name__ for processor in self.argument_processors]))
            for processor_definition in self.argument_processors:
                processor = Plugins().processor(processor_definition.name)()
                stats = (processor, "="*120, self.arguments, "="*120)
                _LOG.debug("Arguments before processor {0}\n{1}\n{2}{3}".format(*stats))
                processor(self, processor_definition.scope, processor_definition.parameters)
                _LOG.debug("Arguments after processor {0}\n{1}\n{2}{3}".format(*stats))

    def _add_command_tasks(self, *args, **kwargs):
        """ adds the child tasks to our "null" task

        Args:
            *args ():
            **kwargs ():

        Returns:

        """
        cls = self.__class__
        # check if the task is capable to handle multi elements or not
        # pass the process task_arguments to the class
        if not self.per_element or not self._is_expected_iterable(getattr(self.elements, "processed", None)):
            _task = cls(self.arguments, is_handle_task=False, *args, **kwargs)
            self._append_elements_to_title(_task)
            self._add_command(_task)
            self._add_view(_task)
            if self.job and getattr(self.job, "append_instances", False):
                if self.wait_for_task:
                    instance = author.Instance(title=self.wait_for_task.id)
                    _task.addChild(instance)
            self.addChild(_task)
        else:
            # add task per element
            for element in self.elements.processed:
                _task = cls(self.arguments, is_handle_task=False, *args, **kwargs)
                _task.arguments.set(self.elements_id, ArgumentValue(_task.elements.initial, element))

                # second intercept to prevent the addition of per element command tasks
                # this is important to check against iterable attributes that are
                # unwrapped in this for loop [1, 2, 3] --> Task1, Task2, Task3
                if _task.stop_traversal():
                    continue

                self._append_elements_to_title(_task)
                self._add_command(_task)
                self._add_view(_task)
                if self.job and getattr(self.job, "append_instances", False):
                    if self.wait_for_task:
                        instance = author.Instance(title=self.wait_for_task.id)
                        _task.addChild(instance)
                    if self.serial:
                        self.wait_for_task = _task
                self.addChild(_task)

    def _append_elements_to_title(self, task):
        """ extend the tasks title with used elements

        Args:
            task ():

        Returns:

        """
        assert task.elements, "Missing ArgumentValue for argument '{}'".format(self.elements_id)
        task.title += ": Elements {}".format(str(task.elements.processed))

    def _add_required_tasks(self, required, parent_task, elements, *args, **kwargs):
        """ recursive addition of required tasks

        Consider tuple and list style syntax to define a serial or parallel
        dependency behavior

        Args:
            required (:obj:`list` of/or :cls:`Task`): task class(es)
            parent_task (:obj: `Task`): task the subtask will be added to
            *args ():
            **kwargs ():

        Returns:

        """
        class Serial(Task):
            title = "serial"
            elements_id = self.elements_id
            flags = Task.Flags.SERIAL
            job = self.job

        class Parallel(Task):
            title = "parallel"
            elements_id = self.elements_id
            job = self.job

        # todo: for some reason this check does not work
        # isinstance(self, (Serial, Parallel)):
        if self.title in ("serial", "parallel"):
            return

        # store the current task to wait for in a variable so we don't override
        # it in self. When overriding it in self, we destroy the information
        # at the current hierarchy level and propagate the task to wait for
        # from a subtree into an unrelated subtree.
        # if we don't have a dependency on the current level (maybe because the
        # immediate parent is a parallel task) we could still depend on an up-
        # stream serial dependency which we have to respect (parent_task)
        current_wait_for_task = self.wait_for_task or parent_task.wait_for_task
        last_task = None

        # check if the required tasks should run serial
        # we have to exclude command tasks here because we only want to add child tasks
        # to our dedicated "handle" tasks
        if not self._has_cmd(parent_task):
            if isinstance(required, tuple) or self.serial:
                _serialtask = Serial({}, wait_for_task=current_wait_for_task)
                parent_task.addChild(_serialtask)
                parent_task = _serialtask
            elif isinstance(required, list):
                # No need to create nested parallel dependencies. They would be
                # redundant.
                if parent_task.title != "parallel":
                    _paralleltask = Parallel({}, wait_for_task=current_wait_for_task)
                    parent_task.addChild(_paralleltask)
                    parent_task = _paralleltask

        for _required in required:
            # check for nested task dependencies
            if isinstance(_required, (tuple, list)):
                # in the case of nested serial hierarchies we also need to pass
                # the current wait_for_task dependency into the next recursion
                # level.
                parent_task.wait_for_task = current_wait_for_task
                last_task = self._add_required_tasks(_required, parent_task, elements, *args, **kwargs)
                if parent_task.title == "serial":
                    current_wait_for_task = last_task.parent
            else:
                # @todo find a cleaner way to pass the arguments, maybe without deepcopy
                # check the required task if it should be a regular
                # or a Task with overrides and
                # map the actual Task object from the plugins Singleton/
                # and subclass it in case of overriding its
                # attributes
                if isinstance(_required, TaskWithOverrides):
                    _required = _required.get()
                else:
                    _required = Plugins().task(_required)
                _required.job = self.job

                _args = copy.deepcopy(self.arguments)
                _args.set(self.elements_id, elements)

                # the task to wait for has to be passed down the hierarchy so
                # we can eventually attach it to the final command task. That's
                # the only way to effectively block the immediate readiness
                # of the command task when dealing with an expanded job.
                task = _required(_args, wait_for_task=current_wait_for_task, *args, **kwargs)
                if parent_task.title == "serial":
                    current_wait_for_task = task
                parent_task.addChild(task)
                last_task = parent_task
        return last_task

    def _add_command(self, task):
        """ check for cmd and script implementation on custom task

        Args:
            task (:obj: `Task`): task the command will be added to

        Returns:

        """
        has_cmd = self._has_cmd(task.__class__)
        has_script = self._has_script(task.__class__)

        _cmd_str = "Added command '{0}' to task {1}"

        # check if either a command or script has been implemented
        # it's not supported to have both, but it's totally fine to have none
        if has_script and not has_cmd:
            raise AssertionError("{}: You must implement a command if you specify a script."
                                 .format(task.__class__.__name__))

        if has_cmd and task.cmd():
            if has_script:
                cmd = self._get_commandlist_with_script_call(task)
            else:
                cmd = self._get_commandlist_with_resolved_executable(task)

            cmd = self._get_commandlist_with_additional_command_flags(cmd)

            # during the recursive task creation we always have a valid job instance
            # but during the processing in tractor we don't
            local = False
            if task.job and task.job.local:
                local = True

            task.newCommand(
                argv=cmd,
                service=",".join(task.services),
                tags=task.tags,
                retryrc=task.retryrc,
                local=local
            )
            _LOG.debug(_cmd_str.format(" ".join(cmd), task))

    def _get_commandlist_with_resolved_executable(self, task):
        """ replaces the first item command list with the proper executable

        Args:
            task (:obj: `Task`): task that holds the command

        Returns: command list

        """
        executable = self._get_executable(task.cmd()[0])
        _cmd = task.cmd()
        _cmd[0] = executable

        return _cmd

    def _get_commandlist_with_script_call(self, task):
        """ appends script to command list

        Args:
            task (:obj: `Task`): task that holds the command

        Returns: command list

        """

        # during the recursive task creation we always have a valid job instance
        # but during the processing in tractor we don't
        # in this case it doesn't matter what to return as we are not building
        # the corresponding command
        if self.job == None:
            return []

        arguments = self.arguments.serialized()
        # to avoid running into OSError: [Errno 7] Argument list too long
        # we have to check the maximum length of our serialized data
        # and dump it to a unique file
        if len(arguments) > ARGUMENTS_SERIALIZED_MAX_LENGTH:
            # generate a unique key and associate the arguments in the cache with it
            key = self._generate_argument_key()
            self.job.arguments_cache[key] = arguments
            # lets modify the string we will pass to our command which our Arguments object
            # can understand to do the reinitialization from file
            arguments = self.job.arguments_file + ":" + key
            # we have to alter the state of the job that defines if we have to store
            # the arguments to file
            self.job.requires_arguments_cache = True

        # @todo don't require each task to query the whole pluginlist; be specific (we have the needed information)
        if hasattr(self.__class__, "_has_overrides"):
            classname = re.sub(r"Overriden$", "", self.__class__.__name__)
        else:
            classname = self.__class__.__name__

        script = "from jobtronaut.author.plugins import Plugins;" \
                 "task=Plugins().task(\"{0}\")(\"{1}\");task.script()".format(classname, arguments)

        script = script + ";task.neutralize_commands()" if task.no_retry else script

        cmd = self._get_commandlist_with_resolved_executable(task)
        cmd.append(script)

        return cmd

    @staticmethod
    def neutralize_commands():
        """ neutralize all commands of the current task

        """
        from jobtronaut.query import (
            initialize_engine,
            tractor_query
        )
        initialize_engine()

        # if a command runs he normally has access to the `TR_ENV_* vars,
        # so we know where we want to neutralise all commands
        job_id = os.getenv("TR_ENV_JID")
        task_id = os.getenv("TR_ENV_TID")

        if not (job_id and task_id):
            _LOG.error("Unable to neutralize commands, because we can't identify the current job and/or task id.")
            return

        _LOG.info("Previous commands exited successfully. We are neutralising them!")

        for command in tractor_query.commands("jid='{}' and tid='{}'".format(job_id, task_id)):
            # we don't want to lose the original command, so let us know what that was
            # but only echo it instead of letting it execute again
            new_argv = ["/bin/echo", "Command has been neutralised:", "{}".format(" ".join(command["argv"]))]
            tractor_query.cattr(command, key="argv", value=new_argv)

    def _get_commandlist_with_additional_command_flags(self, cmdlist):
        """ get a modified cmdlist of a commandtask and inserts additional commandflags

        Within the cmd method implementation we always expect the executable to be the first item in our commandlist
        followed by whatever additional items the specific implementation needs.
        We can use a reserved argument name to provide additional commandflags which we insert directly after
        the executable.
        Appending those is not what we want here, as our custom *_SCRIPT_WRAPPER helper scripts expect the
        script method call to be the last item in the commandlist.

        Returns:
            list: modified command list
        """
        cmdlist = copy.deepcopy(cmdlist)
        if hasattr(self.arguments, COMMANDFLAGS_ARGUMENT_NAME):
            flags_value = getattr(self.arguments, COMMANDFLAGS_ARGUMENT_NAME).processed
            if isinstance(flags_value, basestring):
                cmdlist[1:1] = flags_value.split(" ")
            elif isinstance(flags_value, dict):
                cmdstring = " ".join(cmdlist)
                for pattern, value in flags_value.items():
                    if re.search(pattern, cmdstring):
                        _LOG.debug(
                            "Given pattern `{}` matches command `{}`. Flags `{}` will be injected.".format(
                                pattern,
                                cmdstring,
                                value
                            )
                        )
                        cmdlist[1:1] = value.split(" ")
            else:
                raise TypeError(
                    "Unsupported type for argument `{}`. Expected basestring or dict, got `{}`".format(
                        COMMANDFLAGS_ARGUMENT_NAME,
                        type(flags_value)
                    )
                )

        return cmdlist

    @staticmethod
    def _generate_argument_key():
        """ generates a unique identifier

        The purpose for this method is to make it easier to patch within the automated
        testing.
        """
        return str(uuid.uuid4())

    def _add_view(self, task):
        """ sets chaser on a given task

        Args:
            task (:obj: `Task`): task

        Returns:

        """
        if self._has_view(task.__class__):
            task.chaser = task.view()

    @classmethod
    def info(cls, short=True):
        """ Provides a nicely formatted representation to be used as a terminal
        output.

        Arguments:
            cls (class): The class which should be formatted
        """
        if short:
            infostr = "{BOLD}{BG_BLUE}{FG_WHITE}" + cls.__name__ + "{END}"
        else:
            infostr = "\n{BOLD}{BG_BLUE}{FG_WHITE}\n" + cls.__name__ + "\n{END}\n\n"
            infostr += "{BOLD}{FG_WHITE}Title:\n{END}"
            infostr += (cls.title or "No title set") + "\n\n"

            infostr += "{BOLD}Description:" + "{END}\n"
            infostr += cls.description + "{END}\n\n"

            if cls.argument_defaults:
                infostr += "{BOLD}{FG_WHITE}Argument Defaults:" + "{END}\n"
                for argument_name, default in cls.argument_defaults.items():
                    default_type = type(default)
                    default = Plugins.format_safe(default)
                    infostr += "{BOLD} " + argument_name + " {END}" + " (default [{}]: {})".format(
                        default_type, default
                    ) + "{END}\n"
                infostr += "\n"

            if cls.required_tasks:
                infostr += "{BOLD}{FG_WHITE}Required Tasks:" + "{END}\n"
                infostr += repr(cls.required_tasks) + "\n\n"

            if cls.argument_processors:
                infostr += "{BOLD}{FG_WHITE}Processors:" + "{END}\n"
                for processor in cls.argument_processors:
                    infostr += Plugins.format_safe(processor) + "\n"
                infostr += "\n"

            infostr += "{BOLD}Module Path:" + "{END}\n"
            infostr += Plugins().get_module_path(cls.__name__) + "{END}\n\n"

            infostr += "\n"

        return infostr.format(**BASH_STYLES)

    @staticmethod
    def __EXPAND__(root_task, arguments_mapping, local=None):  # don't remove the arguments_mapping parameter!
        """ handles a task expansion

        The given rootask defines the relation between subtasks.
        Those subtasks will be treated as sub-jobs, because they expect their own arguments,
        which will not be inherited by the global arguments state.

        Args:
            root_task (str or TaskWithOverrides): the name of the root task or a TaskWithOverrides
                that defines the downstream hierarchy of subtasks
            arguments_mapping (dict): a mapping of the arguments <-> subtask relation. A valid entry mus exist
                for EVERY task that exists in root_task.required_tasks.
            local (bool): the local state of new commands that will be created; check the Job docs for more information

        Returns:

        """
        if isinstance(root_task, TaskWithOverrides):
            _root_task = root_task.get()
        else:
            _root_task = Plugins().task(root_task)

        assert _root_task.required_tasks, \
            "Expected the `required_tasks` attribute to define subtasks, but nothing was defined"

        _tmp_directory = tempfile.gettempdir()
        alf_file = os.path.join(_tmp_directory, "{}.alf".format(str(uuid.uuid4())))

        _LOG.info("Dump temporary job file as '{}'".format(alf_file))

        required_jobs = str(_root_task.required_tasks)

        all_tasks = re.findall(r"(?<=['\"])[a-zA-Z0-9_]+(?=['\"])", required_jobs)
        task_count_by_name = {}

        for task in all_tasks:
            if task not in task_count_by_name:
                task_count_by_name[task] = 1
            else:
                task_count_by_name[task] += 1

        sighted_arguments = {k: 0 for k in task_count_by_name}

        def convert(matchobj):
            task = matchobj.groupdict()["task"]
            arguments = arguments_mapping[task]

            if isinstance(arguments, dict):
                if task_count_by_name[task] > 1:
                    _LOG.warning(
                        "You require the task `{task}` several times, but only provide a single arguments dictionary. "
                        "Note that this will be applied to all `{task}` references".format(task=task)
                    )

            elif isinstance(arguments, (list, tuple)):
                if len(arguments) != task_count_by_name[task]:
                    raise AssertionError(
                        "You wanna pass {} individual arguments dictionary/dictionaries to {} `{}` task references. "
                        "Ensure you provide the same amount of argument dictionaries as you require tasks.\n"
                        "If you want to apply the same argument dictionary to all task references use it directly "
                        "instead of a list/tuple.".format(len(arguments), task_count_by_name[task], task)
                    )
                else:
                    arguments = arguments[sighted_arguments[task]]
                    sighted_arguments[task] += 1
            else:
                raise NotImplementedError("Unsupported type. Supported is dict or a list/tuple with dicts.")

            return "Job(\"{}\", {}, local={})".format(task, arguments, local)

        Job(
            jobs_to_task(
                eval(re.sub(r"['\"](?P<task>[a-zA-Z0-9_]+)['\"]", convert, required_jobs))
            )
        ).dump_job(alf_file)

        # expand the job
        print("TR_EXPAND_CHUNK \"{}\"".format(alf_file))


class TaskWithOverrides(object):
    """ An extension to existing Tasks

    Due to the nature we are loading and specifying Tasks it is not achievable to
    customize an existing Task for specific needs that are not part of the module
    scope.
    Nevertheless it often becomes useful to reuse simple hierarchy Task and only
    changing the required_task attribute for instance.

    """
    def __init__(self, basetask, **overrides):
        """ Given a base Task this class allows you to generate a subclass with
        overrides.

        Args:
            basetask (str): name of the Task that is supposed to get overridden
            class_name (str): name of the Task class that will be generated
            **overrides (dict): attribute name and value that represent intended to
            define the task behavior. Have a closer look at the Task class
            attributes intended to use for that purpose.

        Warnings: class_name argument will become deprecated as soon the Task class
        treads name and title attribute in a more obvious way
        """

        assert overrides, "No Task overrides defined."

        self.overrides = overrides
        self.basetask = basetask

    def get(self):
        """ get the Task with overrides

        Returns:
            Task: Task class that is a direct subclass overriding attributes defined in the class
            constructor
        """
        task_cls = Plugins().task(self.basetask)
        task_dict = dict(Task.__dict__)
        task_dict.update(task_cls.__dict__)

        # TODO: we should prevent overrides for protected and private members
        self._allowed_overrides = task_dict.keys()

        _LOG.debug("Designated Task to override {}".format(task_cls))

        # lets store the overrides
        overrides = {}

        for override in self.overrides:
            if override not in self._allowed_overrides:
                closest = difflib.get_close_matches(override, self._allowed_overrides)
                raise AssertionError("No attribute found for {0}, closest matches are {1}".format(override, closest))

            # we are comparing against the defaults to log proper information about
            # the effective overrides
            if self.overrides[override] != getattr(task_cls, override):
                overrides[override] = self.overrides[override]

        if overrides:
            # create the subclass based on overrides
            task_with_overrides = type(task_cls.__name__+ "Overriden", (task_cls,), overrides)
            task_with_overrides._has_overrides = True
            overrides_msg = ["'{0}' : {1}".format(key, value) for key, value in overrides.iteritems()]
            _LOG.debug("Generated Task with effective overrides: \n" + "=" * 70 + "\n" + "\n".join(overrides_msg))

            return task_with_overrides
        else:
            _LOG.warning("No effective override set. Returning original Task '{}'".format(task_cls))
            return task_cls

    def __repr__(self):
        """ Forward the request for a string representation to the actual task
        """
        return "'{} (with overrides)'".format(self.basetask)
