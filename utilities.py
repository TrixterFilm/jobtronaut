# ######################################################################################################################
#  Copyright 2020-2021 TRIXTER GmbH                                                                                         #
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
import time

from .constants import LOGGING_NAMESPACE

_LOG = logging.getLogger("{}.author.job".format(LOGGING_NAMESPACE))


class CallIntervalLimiter(object):
    """ allow to limit function calls based on a given time interval

    """
    def __init__(self, func, default=None, interval=0, run_initial_call=True):
        self._func = func
        self._interval = interval
        self._default = default

        if run_initial_call:
            self._attempt = None
        else:
            self._attempt = time.time()

    def __call__(self, *args, **kwargs):
        if not self._attempt:
            _LOG.debug(
                "Run initial call of given function {}. Start enforcing interval from now....".format(self._func)
            )
            result = self._func(*args, **kwargs)
            self._attempt = time.time()
        elif time.time() - self._attempt > self._interval:
            _LOG.debug(
                "Call given function {} as we passed the given interval of {} seconds.".format(
                    self._func,
                    self._interval
                )
            )
            result = self._func(*args, **kwargs)
            self._attempt = time.time()
        else:
            _LOG.debug(
                (
                    "We don't passed the given interval since last call or initialization. "
                    "Prevent call of given function {}.".format(self._func)
                )
            )
            result = self._default

        return result