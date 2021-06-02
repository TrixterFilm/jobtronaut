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

import ast
import logging
import os
import re
import sys
import inspect
import difflib
import imp

from collections import defaultdict

from ..constants import (
    LOGGING_NAMESPACE,
    PLUGIN_PATH,
    ENABLE_PLUGIN_CACHE
)

_LOG = logging.getLogger("{}.plugins".format(LOGGING_NAMESPACE))


class Singleton(object):
    _instance = None
    _initialized = False

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(Singleton, cls).__new__(cls, *args, **kwargs)
        return cls._instance


class Plugins(Singleton):

    def __init__(self):
        if not Singleton._initialized or not ENABLE_PLUGIN_CACHE:
            Singleton._initialized = True
            self.__tasks = dict()
            self.__processors = dict()
            self.__sitestatusfilters = dict()
            self.__not_loaded = dict()
            self.__module_paths_map = defaultdict(list)
            self.initialize()

    def _source_modules(self, searchpath, index):
        """ Source all modules in searchpath that match names and extensions.

        Args:
            searchpath (str): PLUGIN_PATH environment search path
            index (int): index that has to be unique to avoid name clashes

        Returns:
             list: of sourced modules

        """
        modules = []
        for name, path in [(os.path.splitext(_f)[0], os.path.join(searchpath, _f))
                                            for _f in os.listdir(searchpath)
                                            if os.path.splitext(_f)[1] == ".py"
                                            and os.path.splitext(_f)[0] != "__init__"]:
            modulename = "jobtronaut_{}_{}".format(name, index)
            try:
                modules.append(imp.load_source(modulename, path))
                _LOG.debug("Sourced {0} as module named {1}".format(path, modulename))
            except ImportError as error:
                message = "Plugins from {0} could not be sourced.\n" \
                          "ImportError: {1}\n" \
                          "The missing module needs to be available in your PYTHONPATH" \
                          .format(path, error.message)
                _LOG.warning(message)
                for cls in self._parse_and_find_classes(path):
                    self.__not_loaded[cls] = (path, message)
        return modules

    @staticmethod
    def _parse_and_find_classes(path):
        """ Parse the syntax of the given file and return the names of
        all top level classes.

        Args:
            path (str): path to python module

        Returns:
             Class Names (str): top level class names in module (path)
        """
        with open(path) as _file:
            node = ast.parse(_file.read())
        classes = [cls.name for cls in node.body if isinstance(cls, ast.ClassDef)]
        return classes

    def initialize(self, ignore_duplicates=False):
        """ Parse all the searchpaths and store the result.

        This will (re-)initialize the Plugins singleton and (re-)load all plugins
        (tasks, processors) that can be found in the PLUGIN_PATH.
        """
        if self.__tasks or self.__processors or self.__sitestatusfilters:
            self._clear()

        _PLUGIN_PATH = list(set(PLUGIN_PATH))
        _LOG.info("Current jobtronaut plugins searchpaths: {}".format("\n".join(_PLUGIN_PATH)))

        for index, path in enumerate(_PLUGIN_PATH):
            if not os.path.exists(path):
                _LOG.warning("Defined jobtronaut plugin searchpath '{}' doesn't exist. Ignore path.".format(path))
            else:
                sys.path.extend(path)
                for _module in self._source_modules(path, index):
                    for name, obj in dict(inspect.getmembers(_module, lambda cls: inspect.isclass(cls))).iteritems():
                        if self.__tasks.get(name) or self.__processors.get(name) or self.__sitestatusfilters.get(name):
                            if ignore_duplicates:
                                _LOG.warning("Plugin \"{0}\" has been found multiple times. Using original definition."
                                             .format(name))
                                continue
                            else:
                                raise AssertionError(
                                    "Plugin \"{0}\" has been found multiple times. Please make sure "
                                    "Task, Processor and SiteStatusFilter names are unique.".format(name)
                                )
                        if hasattr(_module, "Task") \
                                and issubclass(obj, _module.Task) \
                                and not obj.__name__ == "Task":  # exclude the basetask
                            self.__tasks[name] = obj
                            self.__module_paths_map[_module.__file__].append(obj)
                        elif hasattr(_module, "BaseProcessor") \
                                and issubclass(obj, _module.BaseProcessor) \
                                and not obj.__name__ == "BaseProcessor":
                            self.__processors[name] = obj
                            self.__module_paths_map[_module.__file__].append(obj)
                        elif hasattr(_module, "TrStatusFilter") \
                                and issubclass(obj, _module.TrStatusFilter) \
                                and not obj.__name__ == "TrStatusFilter":
                            self.__sitestatusfilters[name] = obj
                            self.__module_paths_map[_module.__file__].append(obj)

    def _clear(self):
        """ Initializes the tasks and processors to an empty dict.
        This effectively clears the cache.
        """
        self.__tasks = dict()
        self.__processors = dict()
        self.__sitestatusfilters = dict()
        self.__module_paths_map = defaultdict(list)

    # this is just a static helper we make use of in plugin.info(short=False)
    @staticmethod
    def format_safe(value):
        if isinstance(value, basestring):
            return "\"{}\"".format(value)
        elif value is None:
            return "None"
        else:
            return str(value).replace("{", "{{").replace("}", "}}")

    @property
    def tasks(self):
        """ Holds the available tasks.

        Returns:
             dict: all available task classes

        """
        return self.__tasks

    @property
    def processors(self):
        """ Holds the available processors.

        Returns:
             dict: all available processor classes

        """
        return self.__processors

    @property
    def sitestatusfilters(self):
        """ Holds the available sitestatusfilters.

        Returns:
             dict: all available sitestatusfilter classes

        """
        return self.__sitestatusfilters

    @property
    def plugins(self):
        """ Get all available processors AND tasks.

        Returns:
             Plugins (dict): all available plugins
        """
        all_plugins = self.__tasks.copy()
        all_plugins.update(self.__processors)
        all_plugins.update(self.__sitestatusfilters)
        return all_plugins

    def task(self, name):
        """ Get task class by given name.

        Args:
            name (str): task class name

        Returns:
             Task (class): task class

        """
        try:
            return self.__tasks[name]
        except KeyError:
            if name in self.__not_loaded:
                raise ImportError(
                        "Task {0} exists in {1}, but could not be loaded.\n"
                        "Original Message was:\n{2}"
                        .format(name, *self.__not_loaded[name])
                        )
            else:
                closest = difflib.get_close_matches(name, self.__tasks.keys())
                raise KeyError("No task found for {0}, closest matches are {1}".format(name, closest))

    def processor(self, name):
        """ Get the processor class by given name.

        Args:
            name (str): processor class name

        Returns:
             Processor (class): processor class
        """
        try:
            return self.__processors[name]
        except KeyError:
            closest = difflib.get_close_matches(name, self.__processors.keys())
            raise KeyError("No processor found for {0}, closest matches are {1}".format(name, closest))

    def sitestatusfilter(self, name):
        """ Get the sitestusfilter class by given name.

        Args:
            name (str): sitestusfilter class name

        Returns:
             SiteStatusFilter (class): sitestusfilter class
        """
        try:
            return self.__sitestatusfilters[name]
        except KeyError:
            closest = difflib.get_close_matches(name, self.__sitestatusfilters.keys())
            raise KeyError("No sitestatusfilter found for {0}, closest matches are {1}".format(name, closest))

    def plugin(self, name):
        """ Get the plugin class and type by given name.

        Args:
            name (str): plugin class name

        Returns:
             Plugin (class): plugin class
        """
        try:
            return self.plugins[name]
        except KeyError:
            closest = difflib.get_close_matches(name, self.plugins.keys())
            raise KeyError("No plugin found for {0}, closest matches are {1}".format(name, closest))

    def plugin_class(self, name):
        """ Get a plugin's type by it's name.

        Args:
            name (str): the plugin name

        Returns:
            str: The plugin's type as a string
        """
        assert name in self.plugins, "Plugin {0} could not be found.".format(name)

        if name in self.__tasks:
            return "Task"
        if name in self.__processors:
            return "Processor"
        if name in self.__sitestatusfilters:
            return "SiteStatusFilter"

    def plugin_description(self, name):
        """ Get information for a plugin and return a nicely formatted description

        Args:
            name (str): plugin name

        Returns:
            str: Nicely formatted task/processor description
        """
        pass

    def get_all_arguments(self, taskname="", arguments=None):
        """ Given a taskname this method returns all the arguments that are processed
        by the resulting task hierarchy

        Args:
            taskname (str): The name of the root task.
            arguments (list): The reference to the resulting arguments list.

        Returns:
            list: A list of unique arguments.
        """
        if arguments is None:
            arguments = list()

        if taskname:
            task = self.task(taskname)
            required = Plugins._flatten_nested_iterable(task.required_tasks)
            if required:
                for _task in required:
                    self.get_all_arguments(taskname=_task, arguments=arguments)

            for proc in task.argument_processors:
                args = proc[1]
                for arg in args:
                    arguments.append(arg.split(".")[0])

        return list(set(arguments))

    def get_module_path(self, plugin_name):
        """ Gets the module path from where the given plugin was sourced from

        Args:
            plugin_name (str): name of the Processor or Task plugin

        Returns:
            str: path to the compiled module

        """
        plugin = self.plugin(plugin_name)
        for path, plugins in self.__module_paths_map.items():
            if plugin in plugins:
                return re.sub("\.py$", ".py", path)

    @staticmethod
    def _flatten_nested_iterable(iterable, flat=None):
        """ Converts a nested list or tuple and returns a flat list of unique elements

        Args:
            iterable (any): The current (nested) list element. Usually list, tuple or str
            flat (list): The resulting flat list with unique elements.

        Returns:
            list: A list of unique elements
        """
        if flat is None:
            flat = list()

        if type(iterable) in [list, tuple]:
            for element in iterable:
                Plugins._flatten_nested_iterable(element, flat=flat)
        else:
            flat.append(iterable)

        return list(set(flat))

