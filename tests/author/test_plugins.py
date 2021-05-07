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

from mock import patch
import os

from jobtronaut.author.plugins import Plugins

from .. import TestCase
from .plugins_fixtures import some_processors as processors
from .plugins_fixtures import some_tasks as tasks
from .plugins_fixtures import some_sitestatusfilters as sitestatusfilters


class TestPlugins(TestCase):

    @classmethod
    @patch("jobtronaut.author.plugins.PLUGIN_PATH", new=[os.path.dirname(processors.__file__)])
    def setUp(cls):
        # let us use the fixtures path to test with
        Plugins().initialize()
        # in case all unittests are failing the initialize will not work, so check test_initialize

    def test_processors(self):
        """ check if available processors match the ones we provide """
        self.assertListEqual(
            sorted(processors.PROCESSORS_DICT.keys()),
            sorted(Plugins().processors)
        )

    def test_tasks(self):
        """ check if available tasks match the ones we provide """
        self.assertListEqual(
            sorted(tasks.TASKS_DICT.keys()),
            sorted(Plugins().tasks)
        )

    def test_sitestatusfilters(self):
        """ check if available sitestatusfilter match the ones we provide """
        self.assertListEqual(
            sorted(sitestatusfilters.FILTERS_DICT.keys()),
            sorted(Plugins().sitestatusfilters)
        )

    def test_plugins(self):
        """ check if available plugins match the ones we provide """
        self.assertListEqual(
            sorted(tasks.TASKS_DICT.keys() + processors.PROCESSORS_DICT.keys() + sitestatusfilters.FILTERS_DICT.keys()),
            sorted(Plugins().plugins)
        )

    def test_task(self):
        """ check if we get the task class we would expect """
        for task_name in tasks.TASKS_DICT:
            self.assertEqual(
                Plugins().task(task_name).__name__,
                tasks.TASKS_DICT[task_name].__name__
            )

        with self.assertRaises(KeyError) as context:
            Plugins().task("NonExistingTask")
        self.assertIn("No task found for", context.exception.message)

    def test_processor(self):
        """ check if we get the processor class we would expect """
        for processor_name in processors.PROCESSORS_DICT:
            self.assertEqual(
                Plugins().processor(processor_name).__name__,
                processors.PROCESSORS_DICT[processor_name].__name__
            )

        with self.assertRaises(KeyError) as context:
            Plugins().processor("NonExistingProcessor")

        self.assertIn("No processor found for", context.exception.message)

    def test_sitestatusfilter(self):
        """ check if we get the processor class we would expect """
        for filter_name in sitestatusfilters.FILTERS_DICT:
            self.assertEqual(
                Plugins().sitestatusfilter(filter_name).__name__,
                sitestatusfilters.FILTERS_DICT[filter_name].__name__
            )

        with self.assertRaises(KeyError) as context:
            Plugins().sitestatusfilter("NonExistingFilter")

        self.assertIn("No sitestatusfilter found for", context.exception.message)

    def test_plugin(self):
        """ check if we get the plugin class we expect """
        plugins = processors.PROCESSORS_DICT.copy()
        plugins.update(tasks.TASKS_DICT)

        for plugin_name in plugins:
            self.assertEqual(
                Plugins().plugin(plugin_name).__name__,
                plugins[plugin_name].__name__
            )

        with self.assertRaises(KeyError) as context:
            Plugins().plugin("NonExistingPlugin")
        self.assertIn("No plugin found for", context.exception.message)

    def test_plugin_class(self):
        for processor in processors.PROCESSORS_DICT.keys():
            self.assertEqual(
                Plugins().plugin_class(processor), "Processor"
            )

        for task in tasks.TASKS_DICT.keys():
            self.assertEqual(
                Plugins().plugin_class(task), "Task"
            )

        for sitestatusfilter in sitestatusfilters.FILTERS_DICT.keys():
            self.assertEqual(
                Plugins().plugin_class(sitestatusfilter), "SiteStatusFilter"
            )

        with self.assertRaises(AssertionError) as context:
            Plugins().plugin_class("NonExistingPlugin")

        self.assertIn("Plugin NonExistingPlugin could not", context.exception.message)

    def test_initialize(self):
        """ check if initialize clears the cache properly """
        with patch("jobtronaut.author.plugins.PLUGIN_PATH", new=[]):
            self.assertNotEqual(
                [],
                sorted(Plugins().tasks)
            )
            self.assertNotEqual([], sorted(Plugins().processors))

            Plugins().initialize()
            self.assertListEqual([], sorted(Plugins().tasks))
            self.assertListEqual([], sorted(Plugins().processors))

    def test_initialize_with_duplicates(self):
        """ check if the duplicates detection works as expected """

        with patch("jobtronaut.author.plugins.PLUGIN_PATH", new=[
            os.path.dirname(processors.__file__), os.path.join(os.path.dirname(processors.__file__), "duplicates")]):
            # ensure that we raise an error if we find duplicates
            with self.assertRaises(AssertionError) as context:
                Plugins().initialize()

            self.assertIn("names are unique", context.exception.message)

            Plugins().initialize(ignore_duplicates=True)

    def test_get_all_arguments(self):
        """ check if we will get all arguments a task will consume correctly """

        all_arguments = list(set([item for sublist in tasks.PROCESSOR_SCOPE for item in sublist]))
        for i, task_name in enumerate(sorted(tasks.TASKS_DICT.keys())):
            if i != 0:  # we expect the first task will get all other available tasks as required
                all_arguments = [_ for _ in tasks.PROCESSOR_SCOPE[i]]

            expected_arguments = list(set(all_arguments))
            self.assertListEqual(
                Plugins().get_all_arguments(task_name),
                list(set([_.split(".")[0] for _ in expected_arguments]))
            )

    def test_get_module_path(self):
        """ check if we properly get the module path from where the plugin was sourced """

        for task_name in tasks.TASKS_DICT.keys():
            self.assertEqual(tasks.__file__, Plugins().get_module_path(task_name))

        for processor_name in processors.PROCESSORS_DICT.keys():
            self.assertEqual(processors.__file__, Plugins().get_module_path(processor_name))

        for filter_name in sitestatusfilters.FILTERS_DICT.keys():
            self.assertEqual(sitestatusfilters.__file__, Plugins().get_module_path(filter_name))