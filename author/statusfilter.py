# ######################################################################################################################
#  Copyright 2020-2021 TRIXTER GmbH                                                                                    #
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

from tractor.apps.blade.TrStatusFilter import TrStatusFilter as _TrStatusFilter

from ..constants import BASH_STYLES
from .plugins import Plugins


class TrStatusFilter(_TrStatusFilter):
    """ wrapper around TrStatusFilter to inject and store persistent data

    """

    description = "Base StatusFilter class to derive from."

    def __init__(self, persistent_data={}):
        super(TrStatusFilter, self).__init__()

        self.persistent_data = persistent_data

    @classmethod
    def info(cls, short=True):
        """ Provides a nicely formatted representation to be used as a terminal
        output.

        Arguments:
            cls (class): The class which should be formatted
        """

        if short:
            infostr = "{BOLD}{BG_PURPLE}{FG_WHITE}" + cls.__name__ + "{END}"
        else:
            infostr = "\n{BOLD}{BG_PURPLE}{FG_WHITE}\n" + cls.__name__ + "\n{END}\n\n"
            infostr += "{BOLD}Description:" + "{END}\n"
            infostr += cls.description + "{END}\n\n"

            infostr += "{BOLD}Module Path:" + "{END}\n"
            infostr += Plugins().get_module_path(cls.__name__) + "{END}\n\n"

            infostr += "\n"

        return infostr.format(**BASH_STYLES)
