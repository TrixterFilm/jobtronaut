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

"""Argument Storage

This module contains classes that handle job arguments.
"""

import base64
from collections import namedtuple
import json
import logging
import os
import pickle
import re

from ..constants import LOGGING_NAMESPACE

_LOG = logging.getLogger("{}.argument".format(LOGGING_NAMESPACE))

ArgumentValue = namedtuple("ArgumentValue", ["initial", "processed"])


class Arguments(dict):
    """ class to store job/task arguments

    This will serve as a simple helper class to provide a nicer syntax for accessing arguments data

    """
    def __init__(self, arguments, **defaults):
        """

        Args:
            arguments (dict or string): arguments as dict, arguments object or serialied arguments
            (which can also represented through a filepath that holds the serialized arguments itself)
            **defaults: arbitrary arguments providing a default value
            In case attributes with same name exist inside the Arguments object/dict/string that
            will get passed through the arguments parameter their default values will be overriden by them
        """
        super(Arguments, self).__init__()
        if isinstance(arguments, dict) or isinstance(arguments, Arguments):
            _arguments = arguments
        elif isinstance(arguments, str):
            # we have to differ when reinitializing from serialized data
            # if this was passes as the serialized string directly or if this
            # could be a potential file where we dumped the serialized data
            if self._pointing_to_cache_file(arguments):
                _LOG.debug("Deserialize Arguments from file '{}'".format(arguments.split(":")[0]))
                _arguments = self._deserialize_from_file(arguments)
            else:
                _arguments = self._deserialize(arguments)
        else:
            raise NotImplementedError

        # let us add default arguments first
        for key, value in defaults.iteritems():
            self.add(key, value)

        # and let override them by passed arguments
        for key, value in _arguments.iteritems():
            self.set(key, value, initialize=True)

    @staticmethod
    def _pointing_to_cache_file(value):
        """ check if the string value represents a cache file address

        Args:
            value (str): string value that could be a cache file address
        """
        match = re.search("\/.*(\.[a-z]*:[a-z0-9\-]*)$", value)
        if not match:
            return False
        return True

    def _set(self, name, value):
        """ adds/sets an attribute with value and logs debug information

        Args:
            name (str): attribute name
            value (object): attribute value of any type

        Returns:

        """
        initialize = True
        if hasattr(self, name):
            _LOG.debug("Attribute '{0}' existing with value '{1}'".format(name, self[name]))
            initialize = False

        if hasattr(value, "initial") and hasattr(value, "processed"):
            self.__setattr__(name, ArgumentValue(value.initial, value.processed))
            self.__setitem__(name, ArgumentValue(value.initial, value.processed))
        else:
            self.__setattr__(name, ArgumentValue(value, value))
            self.__setitem__(name, ArgumentValue(value, value))

        if initialize:
            _LOG.debug("Attribute '{0}' initialized with value '{1}'".format(name, self[name]))
        else:
            _LOG.debug("Attribute '{0}' set to value '{1}'".format(name, self[name]))

    def set(self, name, value, initialize=False):
        """ sets an argument value

        Args:
            name (str): attribute name
            value (object): attribute value of any type
            initialize (bool): if False it will only set and add the value if the name exists

        Returns:

        """
        if not initialize:
            assert hasattr(self, name), "Non-existing argument {}".format(name)
        self._set(name, value)

    def add(self, name, value):
        """ adds an argument

        Args:
            name (str): attribute name
            value (object): initial value of any type

        Returns:

        """
        assert not hasattr(self, name)

        self.set(name, value, initialize=True)

    def remove(self, name):
        """ removes an argument

        Args:
            name (str): attribute name

        Returns:

        """
        assert hasattr(self, name), "Non-existing argument '{}'".format(name)

        try:
            self.__delitem__(name)
            delattr(self, name)
        except KeyError:
            _LOG.error("Not able to remove argument {}".format(name), exc_info=True)

    def serialized(self):
        """ get arguments as encoded string

        Returns: base64 encoded string, pickeled object

        """
        serialized = base64.b64encode(pickle.dumps(self))
        return serialized

    def pickle_arguments(self, filepath):
        """ stores pickled arguments within file

        Args:
            filepath (str): path to file

        Returns:

        """
        try:
            with open(filepath, "w") as f:
                pickle.dump(self, f, protocol=pickle.HIGHEST_PROTOCOL)
        except OSError:
            _LOG.error("Unable to store file {}".format(filepath), exc_info=True)

    @staticmethod
    def _deserialize(serialized_arguments):
        """ decode and load the serialized arguments

        Args:
            serialized_arguments (str): encoded string arguments

        Returns: arguments as dictionary

        """
        return pickle.loads(base64.b64decode(serialized_arguments))

    def _deserialize_from_file(self, string_value):
        """ decode our serialized object from file

        Args:
            string_value (str): address to cache file that holds our base64
            encoded pickled arguments

        Returns:
            Arguments: arguments as dictionary
        """
        filepath = string_value.split(":")[0]
        key = string_value.split(":")[1]
        assert os.path.isfile(filepath), "File '{}' doesn't exist".format(filepath)

        try:
            with open(filepath, "r") as f:
                arguments_dump = json.load(f)
                return self._deserialize(arguments_dump[key])
        except (OSError, TypeError, KeyError):
            _LOG.error("Unable to deserialize data from '%s'", filepath)
            raise

    def __repr__(self):
        return "".join(["{0}: {1}\n".format(key, value) for key, value in self.iteritems()])
