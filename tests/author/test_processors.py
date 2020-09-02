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

from mock import patch
from schema import Schema, And, Or

import shutil
import tempfile
import time

from .. import TestCase

from jobtronaut.author.task import Task
from jobtronaut.author import processor
from jobtronaut.plugins import processors


class SupportedSchemasFixture(processors.BaseProcessor):

    @processors.supported_schemas(int)
    def process(self, *args):
        return "int"

    @processors.supported_schemas(bool)
    def process(self, *args):
        return "bool"

    @processors.supported_schemas(str)
    def process(self, *args):
        return "str"

    @processors.supported_schemas(float)
    def process(self, *args):
        return "float"

    @processors.supported_schemas(tuple)
    def process(self, *args):
        return "tuple"

    @processors.supported_schemas([str])
    def process(self, *args):
        return "list_w_str"

    @processors.supported_schemas([{str: int}])
    def process(self, *args):
        return "dict_w_str_int"

    @processors.supported_schemas(Schema(And([int], lambda x: len(x) != 2)))
    def process(self, *args):
        return "list_w_ints"

    @processors.supported_schemas(processor.ProcessorSchemas.FRAMERANGE)
    def process(self, *args):
        return "FRAMERANGE"

    @processors.supported_schemas(processor.ProcessorSchemas.FRAMERANGES)
    def process(self, *args):
        return "FRAMERANGES"

    @processors.supported_schemas(Schema(Or([float], {str: [float]}, {str: float})))
    def process(self, *args):
        return "list_w_floats_or_dict_w_str_list_floats_or_dict_w_float"


class TestFilePatternProcessor(TestCase):

    @classmethod
    def setUpClass(cls):
        cls._processor = processors.FilePatternProcessor()
        cls._tmpdir = os.path.join(tempfile.gettempdir(), str(time.time()).replace(".", ""))

        # sorted testfiles
        cls._exrs = ["1.exr", "2.exr"]
        cls._asss = ["a.1001.ass", "a.1002.ass", "a.1003.ass"]
        cls._pys = ["bar.py", "bar.py~", "foo.py"]
        cls._temps = ["1.exr.lock"]

        try:
            os.makedirs(cls._tmpdir)
        except OSError:
            raise

        cls._all_files = [os.path.join(cls._tmpdir, _) for _ in
                          sorted(cls._exrs + cls._asss + cls._pys + cls._temps)]
        for _file in cls._all_files:
            with open(_file, "a"):
                pass

    def test_process(self):
        assert_result_equal(self, self._tmpdir, self._all_files, sort=True)
        assert_result_equal(self, self._tmpdir,
                            [os.path.join(self._tmpdir, _) for _ in self._exrs],
                            input_parameters={"pattern": ".*.exr$"}, sort=True)
        assert_result_equal(self, self._tmpdir,
                            [os.path.join(self._tmpdir, _) for _ in self._pys],
                            input_parameters={"pattern": ".*.py"}, sort=True)
        assert_result_equal(self, self._tmpdir,
                            [os.path.join(self._tmpdir, _) for _ in self._asss],
                            input_parameters={"pattern": ".*.ass"}, sort=True)
        assert_result_equal(self, self._tmpdir,
                            [os.path.join(self._tmpdir, _) for _ in [self._exrs[0], self._temps[0]]],
                            input_parameters={"pattern": "^1\."}, sort=True)

    @classmethod
    def tearDownClass(cls):
        try:
            shutil.rmtree(cls._tmpdir)
        except OSError:
            raise


class TestChunkProcessor(TestCase):

    @classmethod
    def setUpClass(cls):
        cls._processor = processors.ChunkProcessor()
        _Task = Task
        _Task.elements_id = "chunksize"
        cls._processor.task = _Task({"chunksize": 1, "chunkhandles": [0, 0]})

    def test_process(self):
        assert_result_equal(self, [1, 1], [[1, 1]])
        assert_result_equal(self, [1, 2], [[1, 1], [2, 2]])
        assert_result_equal(self, [1, 5], [[1, 1], [2, 2], [3, 3], [4, 4], [5, 5]])
        assert_result_equal(self, [[1, 3], [1, 3]], [[1, 1], [2, 2], [3, 3],[1, 1], [2, 2], [3, 3]])

        self._processor.task.arguments.set("chunksize", 2)
        assert_result_equal(self, [1, 1], [[1, 1]])
        assert_result_equal(self, [1, 2], [[1, 2]])
        assert_result_equal(self, [1, 5], [[1, 2], [3, 4], [5, 5]])
        assert_result_equal(self, [[1, 6], [8, 8], [-12, -10]], [[1, 2], [3, 4], [5, 6], [8, 8], [-12, -11], [-10, -10]])

        self._processor.task.arguments.set("chunksize", 5)
        assert_result_equal(self, [1, 1], [[1, 1]])
        assert_result_equal(self, [1, 2], [[1, 2]])
        assert_result_equal(self, [-5, 5], [[-5, -1], [0, 4], [5, 5]])
        assert_result_equal(self, [[-5, 5], [10, 20]], [[-5, -1], [0, 4], [5, 5], [10, 14], [15, 19], [20, 20]])
        assert_result_equal(self, [[0, 1], [11, 13], [15, 20]], [[0, 1], [11, 13], [15, 19], [20, 20]])
        assert_result_equal(self, [[10, 12], [1, 2]], [[10, 12], [1, 2]])
        #assert_result_equal(self, [[0, 1], [2, 5]], [[0, 4], [5, 5]]) # not sure if this is needed

        assert_result_equal(self, [1001, 1010], [[996, 1010], [1001, 1015]], input_parameters={"chunkhandles": [5, 5]})
        assert_result_equal(self, [0, 10], [[-10, 24], [-5, 29], [0, 30]], input_parameters={"chunkhandles": [10, 20]})
        assert_result_equal(self, [10, 10], [[11, 9]], input_parameters={"chunkhandles": [-1, -1]})


class TestElementsPreviewReorderProcessor(TestCase):

    @classmethod
    def setUpClass(cls):
        cls._processor = processors.ElementsPreviewReorderProcessor()

    def test_processor(self):
        assert_result_equal(self, [1001], [1001])
        assert_result_equal(self, [0, 1, 2, 3, 4, 5, 6], [0, 6, 2, 4, 1, 3, 5], input_parameters={"stride": 2})
        assert_result_equal(self, [10, 20, 30, 99, 150], [10, 150, 20, 30, 99], input_parameters={})
        assert_result_equal(self, [10, 11, 12, 13, 14, 15, 16, 17, 18, 19,
                                   20, 21, 22, 23, 24, 25, 26, 27, 28, 29],
                            [10, 29,  # first, last
                             14, 18, 22, 26,  # stride
                             11, 12, 13, 15, 16, 17, 19,  # rest
                             20, 21, 23, 24, 25, 27, 28], input_parameters={"stride": 4})
        assert_result_equal(self, [1001], [1001], input_parameters={"stride": 2, "discard_rest": True})
        assert_result_equal(
            self,
            [0, 1, 2, 3, 4, 5, 6],
            [0, 6, 1, 2, 3, 4, 5],
            input_parameters={"stride": 1, "discard_rest": True}
        )
        assert_result_equal(
            self,
            [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
            [0, 10, 2, 4, 6, 8],
            input_parameters={"stride": 2, "discard_rest": True}
        )
        assert_result_equal(
            self,
            [10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29],
            [10, 29,  # first, last
             14, 18, 22, 26],  # stride,
            input_parameters={"stride": 4, "discard_rest": True}
        )


class TestExpressionToElementsProcessor(TestCase):

    @classmethod
    def setUpClass(cls):
        cls._processor = processors.ExpressionToElementsProcessor()

    def test_process(self):
        assert_result_equal(self, "1", [1])
        assert_result_equal(self, "1-2", [1, 2])
        assert_result_equal(self, "1-2, 5-6", [1, 2, 5, 6])
        assert_result_equal(self, "5, 10, 34", [5, 10, 34])


class TestRangeToExpressionProcessor(TestCase):

    @classmethod
    def setUpClass(cls):
        cls._processor = processors.RangeToExpressionProcessor()

    def test_process(self):
        assert_result_equal(self, [1, 1], "1-1")
        assert_result_equal(self, [1, 2], "1-2")
        assert_result_equal(self, [1, 10], "1-10")
        assert_result_equal(self, [-99, 99], "-99-99")


class TestElementsToRangesProcessor(TestCase):

    @classmethod
    def setUpClass(cls):
        cls._processor = processors.ElementsToRangesProcessor()

    def test_process(self):
        assert_result_equal(self, [1, 2], [[1, 2]])
        assert_result_equal(self, [1, 3], [[1, 1], [3, 3]])
        assert_result_equal(self, [1, 2, 3], [[1, 3]])
        assert_result_equal(self, [10, 5], [[5, 5], [10, 10]])
        assert_result_equal(self, [-3, -2, -1], [[-3, -1]])
        assert_result_equal(self, [10, 11, 12, 25, 26, 27], [[10, 12], [25, 27]])

        assert_result_equal(self, [5, 1], [[5, 5], [1, 1]], input_parameters={"sort": False})
        assert_result_equal(self, [1, 7, 3, 5, 2, 4, 6, 8, 9, 10, 11, 12],
                            [[1, 1], [7, 7], [3, 3], [5, 5], [2, 2], [4, 4], [6, 6], [8, 12]],
                            input_parameters={"sort": False})


class TestElementsToEnclosingRangeProcessor(TestCase):

    @classmethod
    def setUpClass(cls):
        cls._processor = processors.ElementsToEnclosingRangeProcessor()

    def test_process(self):
        assert_result_equal(self, range(1, 6), [1, 5])
        assert_result_equal(self, range(1, 5) + range(10, 16), [1, 15])
        assert_result_equal(self, [1], [1, 1])
        assert_result_equal(self, [-99, -999], [-999, -99])
        assert_result_equal(self, [-10, -5, 1, 100, 500, -20], [-20, 500])
        assert_result_equal(self, range(-9999, 9999, 3), [-9999, 9996])


class TestValueFromKeyProcessor(TestCase):

    @classmethod
    def setUpClass(cls):
        cls._processor = processors.ValueFromKeyProcessor()

    def test_process(self):
        assert_result_equal(self, {"foo": "bar"}, "bar",
                            input_parameters={"key": "foo"})
        assert_result_equal(self, {"foo": "bar"}, None,
                            input_parameters={"key": "a"})
        assert_result_equal(self, {"foo": "bar"}, "foobar",
                            input_parameters={"key": "a",
                                              "default": "foobar"})
        assert_result_equal(self, {1: "bar"}, "bar",
                            input_parameters={"key": 1})
        assert_result_equal(self, {(1, 2): 200}, 200,
                            input_parameters={"key": (1, 2)})


class TestRangesToElementsProcessor(TestCase):

    @classmethod
    def setUpClass(cls):
        cls._processor = processors.RangesToElementsProcessor()

    def test_process(self):
        # reverse input - expected_output of "ElementsToRangesProcessor"
        assert_result_equal(self, [[1, 2]], [1, 2])
        assert_result_equal(self, [[1, 1], [3, 3]], [1, 3])
        assert_result_equal(self, [[1, 3]], [1, 2, 3])
        assert_result_equal(self, [[10, 10], [5, 5]], [5, 10])
        assert_result_equal(self, [[-3, -1]], [-3, -2, -1])
        assert_result_equal(self, [[10, 12], [25, 27]], [10, 11, 12, 25, 26, 27])


class TestRangeToElementsProcessor(TestCase):

    @classmethod
    def setUpClass(cls):
        cls._processor = processors.RangeToElementsProcessor()

    def test_process(self):
        assert_result_equal(self, [1, 1], [1])
        assert_result_equal(self, [1, 2], [1, 2])
        assert_result_equal(self, [-3, -1], [-3, -2, -1])
        assert_result_equal(self, [0, 0], [0])


class TestInputToOutputProcessor(TestCase):

    @classmethod
    def setUpClass(cls):
        cls._processor = processors.InputToOutputProcessor()
        _Task = Task
        cls._processor.task = _Task({"output_directory": "/my/new/path"})

    def test_process(self):
        assert_result_equal(self, __file__, "/my/new/path/prefix_test_processors_suffix.abc",
                            input_parameters={
                                "prefix": "prefix_",
                                "suffix": "_suffix",
                                "extension": ".abc"
                                })


class TestSubstitutionProcessor(TestCase):

    @classmethod
    def setUpClass(cls):
        cls._processor = processors.SubstitutionProcessor()

    def test_process(self):
        assert_result_equal(self, "hello world", "heo word",
                            input_parameters={
                                "pattern": "l"
                                }
                            )
        assert_result_equal(self, "hello world", "help the world",
                            input_parameters={
                                "pattern": "lo\s",
                                "replacement": "p the "
                                }
                            )
        assert_result_equal(self, ["hello", "world"], ["ciao", "world"],
                            input_parameters={
                                "pattern": "hell",
                                "replacement": "cia"
                                }
                            )


class TestBase64Processors(TestCase):

    @classmethod
    def setUpClass(cls):
        cls._processor = None

    def test_encode_decode(self):
        decoded = "foobar"
        encoded = "Zm9vYmFy"

        with patch.object(self, "_processor", processors.Base64EncodeProcessor()):
            assert_result_equal(self, decoded, encoded)

        with patch.object(self, "_processor", processors.Base64DecodeProcessor()):
            assert_result_equal(self, encoded, decoded)


class TestCopyValueProcessor(TestCase):

    @classmethod
    def setUpClass(cls):
        cls._processor = processors.CopyValueProcessor()

    def test_process(self):
        assert_result_equal(self, "foobar", "foobar")
        assert_result_equal(self, "", "foobar",
                            input_parameters={
                                "value": "foobar"
                            }
                            )
        assert_result_equal(self, {}, {1: 2},
                            input_parameters={
                                "value": {1: 2}
                            }
                            )
        assert_result_equal(self, None, 5,
                            input_parameters={
                                "value": 5
                            }
                            )
        class Test():pass
        test_obj = Test()
        assert_result_equal(self, test_obj, True,
                            input_parameters={
                                "value": True
                            })


class TestSupportedTypes(TestCase):

    @classmethod
    def setUpClass(cls):
        cls._processor = SupportedSchemasFixture()

    def test_process(self):
        """ check if the per-type/schema overloading works correctly """
        # check some basic types
        assert_result_equal(self, 1, "int")
        #assert_result_equal(self, False, "bool")  # expected to not working at the moment
        assert_result_equal(self, "a", "str")
        assert_result_equal(self, 1.0, "float")
        assert_result_equal(self, (1, 2), "tuple")

        # check some simple schemas
        assert_result_equal(self, ["1"], "list_w_str")
        assert_result_equal(self, ["1", "a"], "list_w_str")
        assert_result_equal(self, [1], "list_w_ints")
        assert_result_equal(self, [1, 2, 3], "list_w_ints")  # has to work with len(input) != 2
        assert_result_equal(self, [{"1": 1}], "dict_w_str_int")

        # check some advanced schemas
        assert_result_equal(self, [1, 2], "FRAMERANGE")
        assert_result_equal(self, [[-2, 1], [0, 1]], "FRAMERANGES")
        assert_result_equal(self, [1.0], "list_w_floats_or_dict_w_str_list_floats_or_dict_w_float")
        assert_result_equal(self, {"a": 1.0}, "list_w_floats_or_dict_w_str_list_floats_or_dict_w_float")

        invalid = False
        try:
            assert_result_equal(self, set([]), "")
            invalid = True
        except:
            pass

        self.assertFalse(invalid, msg="Non matching schema should raise an error. Tested with type 'set'")


def assert_result_equal(obj, input, expected_output, input_parameters={}, sort=False):
    """  convenience function for doing Processor.process assertions

    Args:
        obj (:obj: `TestCase`): the expected TestCase subclass
        input (): input that will be called by processors process method
        expected_output (): output you would expect to match the output of the processors process method
        input_parameters (dict): additional parameters the processor will pick up
        sort (bool): if True it will sort the result of the processors process method

    Returns:

    """
    assert hasattr(obj, "_processor"), "Set up a '_processor' property first."
    result = obj._processor.process("", input, input_parameters)
    if sort:
        result = sorted(result)
    obj.assertEqual(expected_output, result)
