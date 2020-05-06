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

""" script to neutralise/defuse existing commands on a given task

This script can be used to workaround the limitation that we can't make tasks
non-retriable. This is especially needed when using the task expansion feature
that tractor provides.
This script needs to be added as a separate (and probably the last) command on
a specific task, because it will ensure previous command will exit
cleanly after a previous successful run.
"""

import logging
import os

import tractor.api.query as tractor_query

from trixter.farmsubmit.query import initialize_engine
from trixter.farmsubmit.constants import LOGGING_NAMESPACE

LOG = logging.getLogger("{}.scripts".format(LOGGING_NAMESPACE))

initialize_engine()

# if a command runs he normally has access to the `TR_ENV_* vars,
# so we know where we want to neutralise all commands
job_id = os.getenv("TR_ENV_JID")
task_id = os.getenv("TR_ENV_TID")

assert job_id, "Not able to detect job id"
assert task_id, "Not able to detect task id"

LOG.info("Previous commands exited sucessfully. We are neutralising them!")

for command in tractor_query.commands("jid='{}' and tid='{}'".format(job_id, task_id)):
    # we don't want to lose the original command, so let us know what that was
    # but only echo it instead of letting it execute again
    new_argv = ["/bin/echo", "Command has been neutralised:", "{}".format(" ".join(command["argv"]))]
    tractor_query.cattr(command, key="argv", value=new_argv)
