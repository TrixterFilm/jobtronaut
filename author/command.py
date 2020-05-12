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

from tractor.api.author.base import *


class Command(KeyValueElement):
    """Command Patch"""
    def __init__(self, local=False, **kw):
        if local:
            # this fixes the bug that `Command` would end up in the resulting Tcl
            # causing a `SEVERE tractor_spool problem (ingress rc = 1)`
            cmdtype = "Cmd"  # <- "Command"
        else:
            cmdtype = "RemoteCmd"
        attributes = [
            Constant(cmdtype),
            ArgvAttribute("argv", required=True, suppressTclKey=True),
            StringAttribute("msg"),
            StringListAttribute("tags"),
            StringAttribute("service"),
            StringAttribute("metrics"),
            StringAttribute("id"),
            StringAttribute("refersto"),
            BooleanAttribute("expand"),
            IntAttribute("atleast"),
            IntAttribute("atmost"),
            IntAttribute("minrunsecs"),
            IntAttribute("maxrunsecs"),
            BooleanAttribute("samehost"),
            StringListAttribute("envkey"),
            IntListAttribute("retryrc"),
            WhenStringAttribute("when"),
            StringListAttribute("resumewhile"),
            BooleanAttribute("resumepin"),
            StringAttribute("metadata")
            ]
        super(Command, self).__init__(attributes, **kw)
