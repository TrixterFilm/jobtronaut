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

from collections import namedtuple
from mock import patch, PropertyMock
import os

from .. import TestCase
from .task_fixtures import tasks
from .task_fixtures.tasks import (
    TaskFixture,
    SERIALIZED_ARGUMENTS_EXEEDED_LIMIT,
    TASK_FIXTURE_ARGUMENTS,
)
from jobtronaut.author import (
    ArgumentValue,
    scripts,
    Task,
    TaskWithOverrides
)
from jobtronaut.constants import (
    COMMANDFLAGS_ARGUMENT_NAME
)

JOB_PATCH = namedtuple('job', ["arguments_cache", "arguments_file", "append_instances", "local"])
JOB_PATCH.arguments_cache = {}
JOB_PATCH.arguments_file = "/temp/foobar/attributes.json"
JOB_PATCH.local = False


class TestTask(TestCase):

    @classmethod
    def setUp(cls):
        TaskFixture.required_tasks = []  # until we don't have a good way to mock our class attributes we have to reset
                                         # some of the attributes to the initial values
        cls._task = TaskFixture(TASK_FIXTURE_ARGUMENTS)
        cls._task.MEMBERS.append("flags")  # we have to add it to the members, otherwise we are not able to patch
        cls._task.MEMBERS.append("services")
        cls._task.MEMBERS.append("tags")

    def test_elements_property(self):
        """ check if elements property gives the expected result """
        self.assertIsInstance(self._task.elements, ArgumentValue)
        self.assertEqual(TASK_FIXTURE_ARGUMENTS["test_argument"], self._task.elements.initial)

    def test_serial_property(self):
        """ check if serial property gives the expected result """
        self.assertFalse(self._task.serial)
        self._task.flags = Task.Flags.SERIAL
        self.assertTrue(self._task.serial)
        self._task.flags = Task.Flags.NOOP | Task.Flags.PER_ELEMENT
        self.assertFalse(self._task.serial)
        self._task.flags = Task.Flags.PER_ELEMENT | Task.Flags.SERIAL

    def test_per_element_property(self):
        """ check if per_element property gives the expected result """
        # found no way to mock this easily so we have to monkey patch it
        self.assertFalse(self._task.per_element)
        self._task.flags = Task.Flags.PER_ELEMENT
        self.assertTrue(self._task.per_element)
        self._task.flags = Task.Flags.PER_ELEMENT | Task.Flags.NOOP
        self.assertTrue(self._task.per_element)
        self._task.flags = Task.Flags.PER_ELEMENT | Task.Flags.SERIAL
        self.assertTrue(self._task.per_element)

    def test_no_retry_property(self):
        """ check if no_retry property gives the expected result """
        self.assertFalse(self._task.no_retry)
        self._task.flags = Task.Flags.PER_ELEMENT
        self.assertFalse(self._task.no_retry)
        self._task.flags = Task.Flags.PER_ELEMENT | Task.Flags.SERIAL
        self.assertFalse(self._task.no_retry)
        self._task.flags = Task.Flags.NO_RETRY
        self.assertTrue(self._task.no_retry)
        self._task.flags = Task.Flags.PER_ELEMENT | Task.Flags.SERIAL | Task.Flags.NO_RETRY
        self.assertTrue(self._task.no_retry)

    def test_has_cmd(self):
        """ check if the has_cmd method works correctly """
        self.assertFalse(self._task._has_cmd(TaskFixture))
        with patch.object(TaskFixture, "cmd", create=True, return_value=None):
            self.assertTrue(self._task._has_cmd(TaskFixture))

    def test_has_script(self):
        """ check if has_scrit method works correctly """
        self.assertFalse(self._task._has_script(TaskFixture))
        with patch.object(TaskFixture, "script", create=True, return_value=None):
            self.assertTrue(self._task._has_script(TaskFixture))

    def test_is_expected_iterable(self):
        """ check if _is_expected_iterable works as expected """
        self.assertTrue(self._task._is_expected_iterable([]))
        self.assertTrue(self._task._is_expected_iterable({}))
        self.assertTrue(self._task._is_expected_iterable(set()))
        self.assertFalse(self._task._is_expected_iterable(1))
        self.assertFalse(self._task._is_expected_iterable("this has to be False"))
        self.assertFalse(self._task._is_expected_iterable(unicode("also False")))

    @patch("jobtronaut.author.task.EXECUTABLE_RESOLVER", new=lambda x: x.replace("/bin/echo", "/resolved/command"))
    def test_get_executable(self):
        """ incomplete test of getting the executable by providing a cmd_id """
        # paths should get through without any changes
        self.assertEqual("/resolved/command", self._task._get_executable("/bin/echo"))

    def test_add_elements_mapper(self):
        """ check if the _add_elements_mapper method did work correctly """
        self.assertEqual(self._task.arguments.elements_id.initial, TaskFixture.elements_id)
        self.assertEqual(self._task.arguments.elements_id.processed, TaskFixture.elements_id)

    @patch.object(TaskFixture, "cmd", create=True, new=lambda x: ["/bin/echo", "test"])
    @patch("jobtronaut.author.task.EXECUTABLE_RESOLVER", new=lambda x: x.replace("/bin/echo", "/resolved/command"))
    def test_get_commandlist_with_resolved_executable(self):
        """ check if the _add_executable_to_command works correctly """
        _task = TaskFixture(TASK_FIXTURE_ARGUMENTS)
        expected_result = ["/resolved/command", "test"]

        # check function directly
        self.assertEqual(expected_result, _task._get_commandlist_with_resolved_executable(_task))

        # check if our task holds the subtask with a correctly set argv value
        self.assertEqual(
            expected_result,
            _task.attributeByName["subtasks"].value[0].attributeByName["cmds"].value[0].attributeByName["argv"].value
        )

    @patch.object(TaskFixture, "cmd", create=True, new=lambda x: ["/bin/echo", "test"])
    @patch.object(TaskFixture, "argument_defaults", new={COMMANDFLAGS_ARGUMENT_NAME: "-hello f -world p"})
    def test_get_commandlist_with_additional_command_flags_string(self):
        _task = TaskFixture(TASK_FIXTURE_ARGUMENTS)
        expected_result = ["/bin/echo", "-hello", "f", "-world", "p", "test"]

        # check function directly
        self.assertEqual(expected_result, _task._get_commandlist_with_additional_command_flags(_task.cmd()))

        # check if our task holds the subtask with a correctly set argv value
        self.assertEqual(
            expected_result,
            _task.attributeByName["subtasks"].value[0].attributeByName["cmds"].value[0].attributeByName["argv"].value
        )

    @patch.object(TaskFixture, "cmd", create=True, new=lambda x: ["/bin/echo", "test"])
    def test_get_commandlist_with_additional_command_flags_not_matching_dict(self):
        with patch.object(TaskFixture, "argument_defaults", new={COMMANDFLAGS_ARGUMENT_NAME: {"no/match": "-hello f -world p"}}):
            _task = TaskFixture(TASK_FIXTURE_ARGUMENTS)
            expected_result = ["/bin/echo", "test"]

            # check function directly
            self.assertEqual(expected_result, _task._get_commandlist_with_additional_command_flags(_task.cmd()))

            # check if our task holds the subtask with a correctly set argv value
            self.assertEqual(
                expected_result,
                _task.attributeByName["subtasks"].value[0].attributeByName["cmds"].value[0].attributeByName["argv"].value
            )

        with patch.object(TaskFixture, "argument_defaults", new={COMMANDFLAGS_ARGUMENT_NAME: {"in/ec": "-hello f -world p"}}):
            _task = TaskFixture(TASK_FIXTURE_ARGUMENTS)
            expected_result = ["/bin/echo", "-hello", "f", "-world", "p", "test"]

            # check function directly
            self.assertEqual(expected_result, _task._get_commandlist_with_additional_command_flags(_task.cmd()))

            # check if our task holds the subtask with a correctly set argv value
            self.assertEqual(
                expected_result,
                _task.attributeByName["subtasks"].value[0].attributeByName["cmds"].value[0].attributeByName["argv"].value
            )

    @patch.object(TaskFixture, "script", create=True, new=lambda x: "print 'test'")
    @patch.object(TaskFixture, "cmd", create=True, new=lambda x: ["/some/executable", "test"])
    @patch("jobtronaut.author.task.EXECUTABLE_RESOLVER", new=lambda x: "/bin/echo")
    @patch.object(TaskFixture, "_generate_argument_key", new=lambda x: "12")
    @patch.object(TaskFixture, "job", create=True, new=JOB_PATCH)
    @patch("jobtronaut.author.task.ARGUMENTS_SERIALIZED_MAX_LENGTH", new=len(SERIALIZED_ARGUMENTS_EXEEDED_LIMIT) - 1)
    def test_get_commandlist_with_script_call(self):
        """ check if the _add_script_to_command works correctly """
        _task = TaskFixture(TASK_FIXTURE_ARGUMENTS)
        with patch.object(self._task.arguments, "serialized", return_value="AAAAA"):
            # although this is how it currently should look it is not correct
            # we expect API changes and have to adjust the testMethod
            self.assertEqual(
                ["/bin/echo",
                 "test",
                 "from jobtronaut.author.plugins import Plugins;Plugins().task(\"TaskFixture\")(\"AAAAA\").script()"
                 ],
                 self._task._get_commandlist_with_script_call(_task)
            )

        # check filedump when we hit the characters limit for the serialized objects
        with patch.object(self._task.arguments, "serialized", return_value=SERIALIZED_ARGUMENTS_EXEEDED_LIMIT):
            self.assertEqual(
                ["/bin/echo",
                 "test",
                 "from jobtronaut.author.plugins import Plugins;Plugins().task(\"TaskFixture\")(\"/temp/foobar/attributes.json:12\").script()"
                 ],
                self._task._get_commandlist_with_script_call(_task)
            )

    @patch.object(TaskFixture, "cmd", create=True, new=lambda x: ["/some/executable", "test"])
    @patch("jobtronaut.author.task.EXECUTABLE_RESOLVER", new=lambda x: "/bin/echo")
    def test_add_remote_command(self):
        """ check if the command that gets added to the task looks like we expect """
        _task = TaskFixture(TASK_FIXTURE_ARGUMENTS)
        _task.services = ["some service", "another service"]
        _task.tags = ["some tag", "another tag"]

        self._task._add_command(_task)

        cmds = _task.attributeByName["cmds"]
        self.assertEqual(1, len(cmds.value))  # we should only have a single command per task
        self.assertEqual("RemoteCmd", cmds.value[0].attributeByName["constant"].value)  # currently expect all RemoteCmd
        self.assertEqual("some service,another service", cmds.value[0].service)
        self.assertEqual(["some tag", "another tag"], cmds.value[0].tags)

    @patch.object(TaskFixture, "cmd", create=True, new=lambda x: ["/some/executable", "test"])
    @patch("jobtronaut.author.task.EXECUTABLE_RESOLVER", new=lambda x: "/bin/echo")
    def test_add_local_command(self):
        job = namedtuple("job", "local")
        job.local = True

        _task = TaskFixture(TASK_FIXTURE_ARGUMENTS)
        _task.services = ["some service", "another service"]
        _task.tags = ["some tag", "another tag"]
        _task.job = job

        self._task._add_command(_task)

        cmds = _task.attributeByName["cmds"]
        self.assertEqual(1, len(cmds.value))  # we should only have a single command per task
        self.assertEqual("Cmd", cmds.value[0].attributeByName["constant"].value)  # currently expect all RemoteCmd
        self.assertEqual("some service,another service", cmds.value[0].service)
        self.assertEqual(["some tag", "another tag"], cmds.value[0].tags)

    @patch.object(TaskFixture, "cmd", create=True, new=lambda x: ["/some/executable", "test"])
    @patch("jobtronaut.author.task.EXECUTABLE_RESOLVER", new=lambda x: "/bin/echo")
    @patch.object(TaskFixture, "no_retry", new_callable=PropertyMock, return_value=True)
    def test_add_command_with_no_retry_flag(self, mock_no_retry):
        """ check if we get the proper extra command for "command neutralisation" when no_retry is set """
        script_name = "neutralisecommands.py"

        _task = TaskFixture(TASK_FIXTURE_ARGUMENTS)
        self._task._add_command(_task)
        self.assertEqual(2, len(_task.attributeByName["cmds"].value))

        self.assertListEqual(
            [
                ["/bin/echo", "test"],
                ["/bin/echo", os.path.join(scripts.__path__[0], script_name)]
            ],
            [_.attributeByName["argv"].value for _ in _task.attributeByName["cmds"].value]
        )

    @patch("jobtronaut.author.plugins.PLUGIN_PATH", new=[os.path.dirname(tasks.__file__)])
    @patch.object(TaskFixture, "per_element", new_callable=PropertyMock, return_value=False)
    def test_add_command_tasks(self, mock_per_element):
        """ check if we get the correct amount of subtasks """
        TaskFixture.required_tasks = ["CmdTaskFixture"]

        # test without per element
        _task = TaskFixture(TASK_FIXTURE_ARGUMENTS)
        self.assertEqual(1, len(_task.subtasks))

        # test with per element
        mock_per_element.return_value = True
        _task = TaskFixture(TASK_FIXTURE_ARGUMENTS)
        self.assertEqual(len(_task.arguments[_task.elements_id].initial), len(_task.subtasks))

    @patch.object(TaskFixture, "view", create=True, new=lambda x: x.cmd()[-1])
    @patch.object(TaskFixture, "cmd", create=True, new=lambda x: ["/some/executable", "test"])
    @patch("jobtronaut.author.task.EXECUTABLE_RESOLVER", new=lambda x: "/bin/echo")
    def test_add_view(self):
        """ check if we are adding the chaser properly """
        _task = TaskFixture(TASK_FIXTURE_ARGUMENTS)
        self._task._add_view(_task)
        self.assertEqual(["test"], _task.attributeByName["chaser"].value)


class TestTaskOverrides(TestCase):

    @patch("jobtronaut.author.plugins.PLUGIN_PATH", new=[os.path.dirname(tasks.__file__)])
    def test_get(self):
        with self.assertRaises(AssertionError) as context:
            TaskWithOverrides("CmdTaskFixture").get()
        self.assertEqual("No Task overrides defined.", context.exception.message)

        with self.assertRaises(AssertionError) as context:
            TaskWithOverrides("CmdTaskFixture", required=["not_working"]).get()
        self.assertIn("No attribute found for required, closest matches are " +
                      "['required_tasks', 'required_arguments']", context.exception.message)

        _task = TaskWithOverrides("CmdTaskFixture",
                                  title="A Task based on CmdTaskFixture").get()

        # testing identity (the overridden task should be unique)
        from jobtronaut.author.plugins import Plugins
        self.assertFalse(_task is Plugins().task("CmdTaskFixture"))

        # testing the attributes
        self.assertEqual("CmdTaskFixtureOverriden", _task.__name__)
        self.assertHasAttribute(_task, "_has_overrides")
        self.assertEqual("A Task based on CmdTaskFixture", _task.title)
        self.assertEqual(["linux64"], _task.services)
