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

import copy

from schema import Schema

from .. import TestCase

from jobtronaut.author.task import Task
from jobtronaut.author.processor import (
    BaseProcessor,
    ProcessorDefinition,
    ProcessorSchemas
)


class TestBaseProcessor(TestCase):

    @classmethod
    def setUp(cls):
        cls._Task = Task
        cls._Task.elements_id = "testrange"
        cls._Task.is_handle_task = False  # handle tasks will process on initialization
        cls._arg_one_name = "test_range"
        cls._arg_two_name = "test_dir"
        cls._arg_one_value = [0, 1, 2, 3, 4]
        cls._arg_two_value = "/tmp"
        cls._task = cls._Task(arguments={cls._arg_one_name: cls._arg_one_value,
                                         cls._arg_two_name: cls._arg_two_value}
                             )
        cls._processor = BaseProcessor()

    # @todo: move into more specific test methods
    def test_call(self):
        """ check if BaseProcessor call processes task arguments and scope correctly """

        def _get_parameters(argument_name, argument_value, parameters):
            """ Intended to inspect our parameters we are passing and resolving """
            return parameters

        before_process = copy.deepcopy(self._task.arguments)

        self.assertIsNone(self._processor.task)
        self._processor(
            self._task,
            scope=[_ + ".initial" for _ in self._task.arguments.iterkeys()],
            parameters={}
        )
        self.assertIsNotNone(self._processor.task)
        self.assertDictEqual(before_process, self._task.arguments)

        self._processor.task = None
        self._processor.process = _get_parameters

        # test single arguments resolution
        self._processor(
            self._task,
            scope=["{}.initial".format(self._arg_two_name)],
            parameters={"steps": "<arg:{}.initial>".format(self._arg_two_name)}
        )
        self.assertEqual(
            {"steps": self._arg_two_value},
            self._processor.task.arguments.get(self._arg_two_name).processed
        )

        # test multiple arguments resolution
        self._processor(
            self._task,
            scope=["{}.initial".format(self._arg_two_name)],
            parameters={"steps": "<arg:{0}.initial>_<arg:{1}.processed>".format(
                self._arg_two_name,
                self._arg_one_name)
            }
        )
        self.assertEqual(
            {"steps": "{0}_{1}".format(
                self._arg_two_value,
                str(self._arg_one_value)
                )
            },
            self._processor.task.arguments.get(self._arg_two_name).processed
        )

        # test python expression/statements resolution
        self._processor(
            self._task,
            scope=["{}.initial".format(self._arg_one_name)],
            parameters={"steps": "<expr: \"hello_world\".encode(\"hex\") >"}
        )
        self.assertEqual(
            {"steps": "68656c6c6f5f776f726c64"},
            self._processor.task.arguments.get(self._arg_one_name).processed
        )

        self._processor(
            self._task,
            scope=["{}.initial".format(self._arg_one_name)],
            parameters={"steps": "<expr: x=5;5+x>"}
        )
        self.assertEqual(
            {"steps": 10},
            self._processor.task.arguments.get(self._arg_one_name).processed
        )

        self._processor(
            self._task,
            scope=["{}.initial".format(self._arg_one_name)],
            parameters={"steps": "<expr: x=5;5+x>_<expr: x=1;1+x>"}
        )
        self.assertEqual(
            {"steps": "10_2"},
            self._processor.task.arguments.get(self._arg_one_name).processed
        )

        self._processor(
            self._task,
            scope=["{}.initial".format(self._arg_one_name)],
            parameters={"steps": "<expr: <arg:{0}.initial>[:2]>".format(self._arg_one_name)}
        )
        self.assertEqual(
            {"steps": [0, 1]},
            self._processor.task.arguments.get(self._arg_one_name).processed
        )

        # TODO: check if this can be handled smarter using unittet.Mock
        #  reinitialize task and reset processor, patch process method
        #  otherwise we have to keep this the last part in the test to not run into
        #  issues related to our monkey-patched process method
        def _process(argument_name, argument_value, parameters):
            return argument_value + argument_value

        self._task = self._Task(
            arguments={
                self._arg_one_name: self._arg_one_value,
                self._arg_two_name: self._arg_two_value
            }
        )

        self._processor.process = _process  # lets change the process method for test purpose
        self._processor(
            self._task,
            scope=["{}.initial".format(self._arg_one_name)],
            parameters={}
        )
        self.assertNotDictEqual(self._processor.task.arguments, before_process)
        self.assertNotEqual(
            self._processor.task.arguments.get(self._arg_one_name).initial,
            self._processor.task.arguments.get(self._arg_one_name).processed
        )
        self.assertEqual(
            self._processor.task.arguments.get(self._arg_two_name).initial,
            self._processor.task.arguments.get(self._arg_two_name).processed
        )

    def test_process(self):
        """ test if processor returns the defined argument value (second positional arg) """
        args = self._task, ["foobar"], {}
        processed = self._processor.process(*args)
        self.assertEqual(processed, args[1])


class TestProcessorDefinition(TestCase):

    @classmethod
    def setUpClass(cls):
        cls._empty_definition = ProcessorDefinition(name="Empty")

    def test_has_name(self):
        """ check if ProcessorDefinition holds a field for 'name' """
        self.assertIn("name", self._empty_definition._fields)

    def test_has_scope(self):
        """ check if ProcessorDefinition holds a field for 'scope' """
        self.assertIn("scope", self._empty_definition._fields)

    def test_has_parameters(self):
        """ check if ProcessorDefinition holds a field for 'parameters' """
        self.assertIn("parameters", self._empty_definition._fields)

    def test_initial_values(self):
        """ check if our initial values types are the expected ones"""
        self.assertIsInstance(getattr(self._empty_definition, "name"), str)
        self.assertIsInstance(getattr(self._empty_definition, "scope"), list)
        self.assertIsInstance(getattr(self._empty_definition, "parameters"), dict)


class TestProcessorSchemas(TestCase):

    @classmethod
    def setUpClass(cls):
        cls._schemas_obj = ProcessorSchemas()

    def _get_member_names(self):
        return [
            attr for attr in dir(self._schemas_obj)
            if not callable(getattr(self._schemas_obj, attr))
            and not attr.startswith("__")
        ]

    def test_members_types(self):
        """ check if all of our members are using Schema objects"""
        members = self._get_member_names()
        self.assertNotEqual(members, [], msg="We expect the schema class should hold schemas.")
        for member in members:
            self.assertIsInstance(getattr(self._schemas_obj, member), Schema)

    def test_member_formatting(self):
        """ check if all of our members have the proper formatting """
        members = self._get_member_names()
        for member in members:
            self.assertTrue(
                member.isupper(),
                msg="Schemas should be constant and we expect them using capital letters"
            )