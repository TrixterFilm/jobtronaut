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


import os
import pickle
import tempfile
import time

from .. import TestCase

from jobtronaut.author import (
    ArgumentValue,
    Arguments
)

from . import arguments_fixtures


DUMPED_VALID_SERIALZED_ARGUMENTS_FIXTURE = os.path.join(
    os.path.dirname(arguments_fixtures.__file__), "valid.json"
)
DUMPED_INVALID_SERIALZED_ARGUMENTS_FIXTURE = os.path.join(
    os.path.dirname(arguments_fixtures.__file__), "invalid.json"
)


class TestArgumentValue(TestCase):

    @classmethod
    def setUpClass(cls):
        cls._empty_argument = ArgumentValue

    def test_has_initial(self):
        """ check if ArgumentsValue holds a field for 'initial' """
        self.assertIn("initial", self._empty_argument._fields)

    def test_has_processed(self):
        """ check if ArgumentsValue holds a field for 'processed' """
        self.assertIn("processed", self._empty_argument._fields)

    def test_argument_value(self):
        """ check if setting an argument value will do what we expect """
        initial_value = "initial"
        processed_value = "process"

        argument_value = ArgumentValue(initial_value, processed_value)

        self.assertEqual(initial_value, argument_value.initial)
        self.assertEqual(processed_value, argument_value.processed)


class TestArguments(TestCase):

    @classmethod
    def setUpClass(cls):

        cls._serialized = (
            "Y2NvcHlfcmVnCl9yZWNvbnN0cnVjdG9yCnAwCihjam9idHJvbmF1dC5hdXRob3IuYXJndW1lbnQKQXJndW1lbnRzCnAxCmNfX2J1aW"
            "x0aW5fXwpkaWN0CnAyCihkcDMKUyd0ZXN0X2FyZycKcDQKZzAKKGNqb2J0cm9uYXV0LmF1dGhvci5hcmd1bWVudApBcmd1bWVudFZhb"
            "HVlCnA1CmNfX2J1aWx0aW5fXwp0dXBsZQpwNgooUyd0ZXN0X3ZhbHVlJwpwNwpnNwp0cDgKdHA5ClJwMTAKc3RwMTEKUnAxMgooZHAx"
            "MwpnNApnMAooZzUKZzYKKGc3Cmc3CnRwMTQKdHAxNQpScDE2CnNiLg=="  # our serialized arguments object
        )

        cls._test_arg_name = "test_arg"
        cls._test_arg_value = "test_value"
        cls._test_argumentvalue = ArgumentValue(cls._test_arg_value, cls._test_arg_value)

    @classmethod
    def setUp(cls):
        cls._empty_arguments = Arguments({})
        cls._prefilled_arguments = Arguments({cls._test_arg_name: cls._test_arg_value})
        cls._tmp_pickle = os.path.join(tempfile.gettempdir(), str(time.time()) + "_arguments.pickle")

    def test_init_empty(self):
        """ check if initialization of Arguments works when providing no information """
        self.assertEqual(self._empty_arguments, {})

    def test_init_with_argument(self):
        """ check if initialization of Arguments works when providing information"""

        arguments = Arguments({self._test_arg_name: self._test_arg_value})

        do_arguments_basic_assertions(self, arguments)

    def test_init_with_serialized(self):
        """ check if initialization of Arguments works as expected """
        arguments = Arguments(self._serialized)

        do_arguments_basic_assertions(self, arguments)

    def test_init_from_file(self):
        """ check if initialization from dumped serialized Arguments works """
        # check invalid file
        # with self.assertRaises(AssertionError) as context:
        with self.assertRaises(AssertionError):
            Arguments("/te/test.abcdef:0")

        with self.assertRaises((KeyError, TypeError)):
            Arguments("{}:0".format(DUMPED_INVALID_SERIALZED_ARGUMENTS_FIXTURE))

        arguments = Arguments("{}:0".format(DUMPED_VALID_SERIALZED_ARGUMENTS_FIXTURE))

        do_arguments_basic_assertions(self, arguments)

    def test_init_with_arguments_instance(self):
        """ check if initialization of Arguments works when providing Arguments instance"""

        arguments = Arguments({self._test_arg_name: self._test_arg_value})
        new_arguments = Arguments(arguments)

        do_arguments_basic_assertions(self, new_arguments)

    def test_init_with_defaults(self):
        """ check if the initialization of Arguments behaves expected when declaring defaults"""
        arguments = Arguments({}, test_arg="test_value")

        do_arguments_basic_assertions(self, arguments)

        arguments = Arguments({self._test_arg_name: self._test_arg_value}, test_arg=0)
        do_arguments_basic_assertions(self, arguments)

    def test_add(self):
        """ check if adding arguments works as expected """

        arguments = self._empty_arguments
        arguments.add(self._test_arg_name, self._test_arg_value)

        self.assertHasAttribute(arguments, self._test_arg_name)
        self.assertIsInstance(arguments.get(self._test_arg_name, ""), ArgumentValue)

    def test_set(self):
        """ check if setting arguments works as expected """

        arguments = self._prefilled_arguments
        # check if the prefilled has expected arguments, values
        self.assertHasAttribute(arguments, self._test_arg_name)
        self.assertIn(self._test_arg_name, arguments)
        self.assertEqual(arguments.get(self._test_arg_name).initial, self._test_arg_value)
        new_value = "foobar"

        arguments.set(self._test_arg_name, new_value)
        self.assertEqual(arguments.get(self._test_arg_name).initial, new_value)

        # assert that setting a nonexisting attribute would fail
        try:
            self._empty_arguments.set(self._test_arg_name, new_value)
        except:
            pass

        # assert that setting a nonexisting attribute would be successful
        arguments_two = self._empty_arguments
        arguments_two.set(self._test_arg_name, self._test_arg_value, initialize=True)
        self.assertHasAttribute(arguments_two, self._test_arg_name)
        self.assertIn(self._test_arg_name, arguments_two)
        self.assertEqual(arguments_two.get(self._test_arg_name).initial, self._test_arg_value)

    def test_remove(self):
        """ check if removing arguments works as expected """

        arguments = self._prefilled_arguments
        # check if the prefilled has expected arguments, values
        self.assertHasAttribute(arguments, self._test_arg_name)
        self.assertEqual(arguments.get(self._test_arg_name).initial, self._test_arg_value)

        arguments.remove(self._test_arg_name)
        self.assertNotHasArgument(arguments, self._test_arg_name)
        self.assertNotIn(self._test_arg_name, arguments)

    def test_serialized(self):
        """ check if serialized works as expected """
        self.assertEqual(self._serialized, self._prefilled_arguments.serialized())

    def test_pickle_arguments(self):
        """ check if pickling the Arguments works as expected """
        self._prefilled_arguments.pickle_arguments(self._tmp_pickle)
        self.assertPathExists(self._tmp_pickle)

        unpickled = pickle.load(open(self._tmp_pickle, "rb" ))

        self.assertDictEqual(self._prefilled_arguments, unpickled)

        try:
            os.remove(self._tmp_pickle)
        except OSError:
            raise


def do_arguments_basic_assertions(obj, arguments_obj):
    obj.assertIsInstance(arguments_obj.__getitem__(obj._test_arg_name), ArgumentValue)

    obj.assertEqual(obj._test_arg_value, arguments_obj[obj._test_arg_name].initial)
    obj.assertEqual(obj._test_arg_value, arguments_obj[obj._test_arg_name].processed)
