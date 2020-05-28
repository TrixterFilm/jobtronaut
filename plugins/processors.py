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

import base64
import copy
import logging
import os
import re

from schema import Schema, And, Or

from jobtronaut.constants import LOGGING_NAMESPACE
from jobtronaut.author import (
    BaseProcessor,
    ProcessorSchemas,
    supported_schemas
)

_LOG = logging.getLogger("{}.processor".format(LOGGING_NAMESPACE))


class FilePatternProcessor(BaseProcessor):

    description = \
    """ 
    Given an input directory it parses the filesystem for all files
    matching the pattern. Returns a list of all files that have
    been found.
    """
    parameters = {
        "pattern": ".*",
        "recursive": True
    }

    @staticmethod
    def _find_files(root, pattern=r".*", recursive=True):
        """ help to find files recursively matching a regex pattern

        Args:
            root (str): path to root directory
            pattern (str): regex pattern
            recursive (bool): if True perform a recursive search

        Returns:
            list: found files

        """
        matches = []

        for _ in os.listdir(root):
            path = os.path.join(root, _)
            if os.path.isfile(path):
                if re.search(pattern, _):
                    matches.append(path)
            elif recursive:
                matches.extend(FilePatternProcessor._find_files(path, pattern))
        return matches

    @supported_schemas(str)
    def process(self, argument_name, argument_value, parameters):
        return self._find_files(
            argument_value,
            parameters.get("pattern", self.parameters["pattern"]),
            parameters.get("recursive", self.parameters["recursive"])
        )


class ChunkProcessor(BaseProcessor):

    description = \
    """ 
    Only keeps each Nth element from an input list
    """
    parameters = {
        "chunkhandles": [0, 0]
    }

    @supported_schemas(ProcessorSchemas.FRAMERANGE)
    def process(self, argument_name, argument_value, parameters):
        chunksize = self.task.arguments.chunksize.processed
        handles = parameters.get("chunkhandles") or self.parameters["chunkhandles"]
        new_elements = []
        for i in xrange(argument_value[0], argument_value[1] + 1, chunksize):
            new_elements.append([i - handles[0], min(argument_value[1], i + chunksize - 1) + handles[1]])
        return new_elements

    @supported_schemas(ProcessorSchemas.FRAMERANGES)
    def process(self, argument_name, argument_value, parameters):
        chunksize = self.task.arguments.chunksize.processed
        handles = parameters.get("chunkhandles") or self.parameters["chunkhandles"]
        new_elements = []
        for _range in argument_value:
            for i in xrange(_range[0], _range[1] + 1, chunksize):
                new_elements.append([i - handles[0], min(_range[1], i + chunksize - 1) + handles[1]])
        return new_elements


class ExpressionToElementsProcessor(BaseProcessor):

    description = \
    """ 
    Converts a frame expression into a list of individual frames

    The following expression are all considered valid
    1001-1002,1005,1010-1100
    900-1002,800, 0040
    800-900, 1001-1010

    Output:
    [1001, 1002, 1005, 1010, ...]
    """

    @supported_schemas(str)
    def process(self, argument_name, argument_value, parameters):
        import re
        frames = []
        pattern = re.compile(r"(?P<range>\d+-\d+)|(?P<frame>-*\d*)")
        for match in re.finditer(pattern, argument_value):
            if match.group("frame"):
                frames.append(int(match.group("frame")))
                continue
            elif match.group("range"):
                _range = match.group("range").replace(" ", "").split("-")
                stride = 1 if int(_range[0]) < int(_range[1]) else -1
                frames += range(int(_range[0]), int(_range[1]) + stride, stride)
        return sorted(list(set(frames)))


class RangeToExpressionProcessor(BaseProcessor):

    description = \
    """ Convers a single range [start, end] to a frame expression
    'start-end'
    We assume that a range will always be ascending.
    """

    @supported_schemas(ProcessorSchemas.FRAMERANGE)
    def process(self, argument_name, argument_value, parameters):
        return "{0}-{1}".format(argument_value[0], argument_value[-1])


class ElementsToRangesProcessor(BaseProcessor):

    description = \
    """ 
    Converts a list of individual elements into as few ranges as 
    possible. The amount of resulting ranges depends on the continuity
    of the input elements.
    """
    parameters = {
        "sort": True
    }

    # @todo implement chunksize into this processor
    @supported_schemas([int])
    def process(self, argument_name, argument_value, parameters):
        if parameters.get("sort", self.parameters["sort"]):
            argument_value.sort()
        previous_value = argument_value[0]
        del argument_value[0]
        ranges = []
        _range = [previous_value, previous_value]
        for frame in argument_value:
            if frame - previous_value == 1:
                _range[1] = frame
            else:
                ranges.append(copy.deepcopy(_range))
                _range = [frame, frame]
            previous_value = frame
        ranges.append(_range)
        return ranges


class ElementsToEnclosingRangeProcessor(BaseProcessor):

    description = \
    """ 
    Converts a list of elements into a single range, considering
    the lowest number as start and highest number as end of a range.
    """

    @supported_schemas(Schema([int]))
    def process(self, argument_name, argument_value, parameters):
        argument_value.sort()
        return [argument_value[0], argument_value[-1]]


class ValueFromKeyProcessor(BaseProcessor):

    description = \
    """ Extracts a value from a dictionary based on a given element as key. """

    parameters = {
        "default": None
    }

    @supported_schemas(dict)
    def process(self, argument_name, argument_value, parameters):
        default = parameters.get("default", self.parameters["default"])
        return argument_value.get(parameters.get("key", ""), default)


class RangesToElementsProcessor(BaseProcessor):

    description = \
    """ 
    Converts a list of ranges [start, end] into a list of all expanded
    ranges [start, ..., end]
    """

    @supported_schemas(ProcessorSchemas.FRAMERANGES)
    def process(self, argument_name, argument_value, parameters):
        frames = []
        for _range in argument_value:
            frames += range(_range[0], _range[1] + 1)
        return sorted(list(set(frames)))


class RangeToElementsProcessor(BaseProcessor):

    description = \
    """ 
    Expands a single range [start, end] into a flat list of
    all elements [start, ..., end]
    """

    @supported_schemas(ProcessorSchemas.FRAMERANGE)
    def process(self, argument_name, argument_value, parameters):
        return range(argument_value[0], argument_value[1] + 1)


class InputToOutputProcessor(BaseProcessor):

    description = \
    """
    Generates a new input based on a given output directory
    """

    parameters = {
        "prefix": "",
        "input_name": "",
        "suffix": "",
        "extension":  ""
    }

    @supported_schemas(str)
    def process(self, argument_name, argument_value, parameters):
        input_name, input_extension = os.path.splitext(os.path.basename(argument_value))
        prefix = parameters.get("prefix", "")
        input_name = parameters.get("input_name", self.parameters["input_name"]) or input_name
        suffix = parameters.get("suffix", self.parameters["suffix"])
        extension = parameters.get("extension", self.parameters["extension"]) or input_extension

        output = os.path.join(
            self.task.arguments.output_directory.processed, "{0}{1}{2}{3}".format(
                prefix,
                input_name,
                suffix,
                extension
            )
        )

        return output


class CopyValueProcessor(BaseProcessor):

    description = \
    """
    Copies a value
    """

    parameters = {
        "value": ""
    }

    @supported_schemas(object)
    def process(self, argument_name, argument_value, parameters):
        value = parameters.get("value", self.parameters["value"]) or argument_value
        return copy.deepcopy(value)


class SubstitutionProcessor(BaseProcessor):

    description = \
    """
    Find an replace within a given input using a regex pattern
    """

    parameters = {
        "pattern": "",
        "replacement": ""
    }

    @supported_schemas(str)
    def process(self, argument_name, argument_value, parameters):
        pattern = parameters.get("pattern", self.parameters["pattern"])
        replacement = parameters.get("replacement", self.parameters["replacement"])

        if pattern:
            return re.sub(pattern, replacement, argument_value)
        else:
            return argument_value

    @supported_schemas([str])
    def process(self, argument_name, argument_value, parameters):
        pattern = parameters.get("pattern", self.parameters["pattern"])
        replacement = parameters.get("replacement", self.parameters["replacement"])

        if pattern:
            return [re.sub(pattern, replacement, _) for _ in argument_value]
        else:
            return argument_value


class Base64EncodeProcessor(BaseProcessor):

    description = \
    """
    Encodes to urlsafe base64 string.
    """

    @supported_schemas(str)
    def process(self, argument_name, argument_value, parameters):
        return base64.urlsafe_b64encode(argument_value)


class Base64DecodeProcessor(BaseProcessor):

    description = \
    """
    Decodes from an urlsafe base64 string.
    """

    @supported_schemas(str)
    def process(self, argument_name, argument_value, parameters):
        return base64.urlsafe_b64decode(argument_value)


class ElementsPreviewReorderProcessor(BaseProcessor):

    description = \
    """
    Will reorder the input elements to provide a sensible order for preview purposes. 
    We assume we always want the first and last frames rendered first to establish a valid
    framerange in Nuke. The user can additionally define how many frames from the sequence
    he wants for a preview. We will split the sequence accordingly.
    """

    parameters = {
        "stride": 0,
        "discard_rest": False
    }

    @supported_schemas(Schema(And([int], lambda x: len(x) > 1)))
    def process(self, argument_name, argument_value, parameters):
        stride = parameters.get("stride", self.parameters["stride"]) or len(argument_value)
        discard_rest = parameters.get("discard_rest", self.parameters["discard_rest"])

        indices = [0, len(argument_value)-1] + range(stride, len(argument_value)-2, stride)
        reordered = [argument_value[idx] for idx in indices]
        rest = [value for idx, value in enumerate(argument_value) if idx not in indices]

        if not discard_rest:
            return reordered + rest
        elif stride == 1:  # with a stride of 1 we don't have a rest
            return reordered + rest
        else:
            return reordered

    @supported_schemas(Schema(And([int], lambda x: len(x) == 1)))
    def process(self, arugment_name, argument_value, parameters):
        return argument_value


class LambdaProcessor(BaseProcessor):

    description = \
    """
    Enables arbitrary argument processing from within a Task.

    This is useful for very specific processors that do not have a generic
    usecase.

    Expects a lambda expression as the 'predicate' parameter.
    """

    parameters = {
        "required_modules": {},
        "predicate": lambda value, modules, arguments: value
    }

    @supported_schemas(object)
    def process(self, argument_name, argument_value, parameters):
        required_modules = parameters.get("required_modules", self.parameters["required_modules"])
        predicate = parameters.get("predicate", self.parameters["predicate"])

        modules = {}
        for name, module in required_modules.items():
           modules[name] = getattr(__import__(module, globals(), locals(), [name], -1), name)

        return predicate(argument_value, modules, self.task.arguments)
