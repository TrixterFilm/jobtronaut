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

import tractor.api.query as tractor_query

from tractor.api.author.base import ModuleEngineClient


def initialize_engine():
    """ Initialize Tractor Engine Client

    Returns:

    """

    def _do_test():
        try:
            tractor_query.jobs("jid=0")
            return True
        except (tractor_query.PasswordRequired, tractor_query.TractorQueryError):
            return False

    def _set_engine_params():
        from ..constants import (
            TRACTOR_ENGINE_CREDENTIALS_RESOLVER,
            TRACTOR_ENGINE
        )

        if TRACTOR_ENGINE:
            hostname, port = TRACTOR_ENGINE.split(":")

            tractor_query.setEngineClientParam(
                hostname=hostname,
                port=int(port),
                user=TRACTOR_ENGINE_CREDENTIALS_RESOLVER()[0],
                password=TRACTOR_ENGINE_CREDENTIALS_RESOLVER()[1]
            )
        else:
            tractor_query.setEngineClientParam(
                user=TRACTOR_ENGINE_CREDENTIALS_RESOLVER()[0],
                password=TRACTOR_ENGINE_CREDENTIALS_RESOLVER()[1]
            )

    # an initial test is likely to fail because no user/password was set
    if not _do_test():
        # just set the credentials
        _set_engine_params()

        # if this still won't work we have to clear the session entirely
        if not _do_test():
            ModuleEngineClient.tsid = None
            _set_engine_params()

        # something else don't work as expacted
        assert _do_test(), "Unsuccessful engine client initialization attempt."