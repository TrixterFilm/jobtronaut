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

import logging
import re

import tractor.api.query as tractor_query

from ..author import Arguments
from ..constants import LOGGING_NAMESPACE
from ..query import initialize_engine

initialize_engine()
_LOG = logging.getLogger("{}.query.arguments".format(LOGGING_NAMESPACE))


def get_arguments_objects(task_id):
    """ Given a Tractor Task ID it will return a list of all used Arguments objects.

    We expect that the matching Task uses a trixter.farmsubmit.Task.script() method.

    Args:
        task_id (str): `:`separated id string, example: 1701362644: 15

    Returns:
        list: Arguments objects

    """
    ARGUMENTS_RE = re.compile(r"\)\(\"(?P<arguments>.*)\"\)\.script\(\)")
    task_id = task_id.replace(" ", "")  # when copy pasting the task id from tractor it includes spaces
    argument_objects = []

    assert task_id.count(":") == 1, "Task ID is invalid."

    commands = tractor_query.commands("jid='{0}' and tid='{1}'".format(*task_id.split(":")), archive=True)

    if not commands:
        _LOG.warning("No matching commands for Task ID '%s' found", task_id)

    for command in commands:
        for arg in command["argv"]:
            match = ARGUMENTS_RE.search(arg)
            if match:
                argument_objects.append(Arguments(str(match.groupdict()["arguments"])))

    return argument_objects
