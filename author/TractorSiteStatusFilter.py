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

import inspect
import logging

from tractor.apps.blade.TrStatusFilter import TrStatusFilter

from jobtronaut.author.plugins import Plugins
from jobtronaut.constants import (
    LOGGING_NAMESPACE,
    ENABLE_PLUGIN_CACHE
)
from jobtronaut.utilities import CallIntervalLimiter


_LOG = logging.getLogger("tractor-blade")

_LOG.info("Sourcing `TractorSiteStatusFilter.py` module from jobtronaut...")


class TractorSiteStatusFilter(TrStatusFilter):
    """ Delegate all filter methods to our plugin or fallback to default implementation """

    def __init__(self):
        self.super = super(type(self), self)  # magic proxy (like shown in the TractorSiteStatusFilter.py example)

        self._name = self.__class__.__name__

        # we need to store information per reference that we can pass to
        # individual site status filter plugins and modify from within any method
        self._persistent_data = {}

        self._plugins = Plugins()
        # site status filters are called frequently, so don't perform a rediscovery of plugins all the time
        self._plugins_initialize = CallIntervalLimiter(self._plugins.initialize, interval=60)

        _LOG.info("Trying to delegate site status filter calls to plugin `{}`".format(self._name))

        self._delegate(self.super.__init__)
        self.processes = {}

    def _delegate(self, function, function_args=(), function_kwargs={}, keep_cache=False):
        """ handle function call delegation to plugin """

        # TODO: handle delegation more dynamically via identifier handlers
        #  so we can automatically pick statusfilter plugins based on things like profile names
        #  or commands
        _LOG.info("Delegating `{}`".format(function.__name__))

        plugin = None

        # enforce bypassing the plugin cache to ensure implemented sites status filter methods
        # are always up to date
        if ENABLE_PLUGIN_CACHE and not keep_cache:
            self._plugins_initialize()

        try:
            plugin = self._plugins.sitestatusfilter(self._name)(persistent_data=self._persistent_data)
            # as the plugin inherits from TrSiteStatusFilter there should always be the actual filter function
            func = getattr(plugin, function.__name__)
        except KeyError:
            # fallback to original implementation if the plugin can't be found
            _LOG.error(
                "Unable to find site status filter `{}`.".format(self._name),
                exc_info=True
            )
            func = function

        if plugin:
            _LOG.debug(
                "Calling filter function on plugin `{}` from `{}`".format(
                    plugin.__class__.__name__,
                    inspect.getfile(func)
                )
            )

        return func(*function_args, **function_kwargs)

    def FilterBasicState(self, stateDict, now):
        return self._delegate(self.super.FilterBasicState, (stateDict, now))

    def TestBasicState(self, stateDict, now):
        return self._delegate(self.super.TestBasicState, (stateDict, now))

    def FilterDynamicState(self, stateDict, now):
        return self._delegate(self.super.FilterDynamicState, (stateDict, now))

    def TestDynamicState(self, stateDict, now):
        return self._delegate(self.super.TestDynamicState, (stateDict, now))

    def SubprocessFailedToStart(self, cmd):
        return self._delegate(self.super.SubprocessFailedToStart, (cmd, ), keep_cache=True)

    def SubprocessStarted(self, cmd):
        return self._delegate(self.super.SubprocessStarted, (cmd, ))

    def SubprocessEnded(self, cmd):
        return self._delegate(self.super.SubprocessEnded, (cmd, ), keep_cache=True)

    def FilterSubprocessOutputLine(self, cmd, textline):
        return self._delegate(self.super.FilterSubprocessOutputLine, (cmd, textline), keep_cache=True)
