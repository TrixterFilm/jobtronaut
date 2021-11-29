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

import inspect
import logging

from tractor.apps.blade.TrStatusFilter import TrStatusFilter

from jobtronaut.author.plugins import Plugins
from jobtronaut.constants import (
    ENABLE_PLUGIN_CACHE,
    FILTER_SELECTOR
)
from jobtronaut.utilities import CallIntervalLimiter

# TODO: figure out what happens: If we store the logger within a variable
#  here at module level and reuse it in the filter methods at some point
#  the stored logger will result in `None`. This happens on an engine restart
#  but also under other yet unknown circumstances
logging.getLogger("tractor-blade").info("Sourcing `TractorSiteStatusFilter.py` module from jobtronaut...")


class TractorSiteStatusFilter(TrStatusFilter):
    """ Delegate all filter methods to our plugin or fallback to default implementation """

    def __init__(self):
        # TODO: use the regular way to super
        self.super = super(type(self), self)  # magic proxy (like shown in the TractorSiteStatusFilter.py example)
        self.super.__init__()

        self._filter_selector = FILTER_SELECTOR

        # we need to store information per reference that we can pass to
        # individual site status filter plugins and modify from within any method
        self._persistent_data = {}

        self._plugins = Plugins()

        def reload_selector():
            import logging  # TODO: as written above - even modules can be missing at some point
            logging.getLogger("tractor-blade").info("Reloading FILTER_SELECTOR...")

            import jobtronaut.constants
            reload(jobtronaut.constants)
            from jobtronaut.constants import FILTER_SELECTOR

            self._filter_selector = FILTER_SELECTOR

        # site status filters are called frequently, so don't perform a rediscovery of plugins and a selector
        # reload all the time
        self._plugins_initialize = CallIntervalLimiter(
            lambda: self._plugins.initialize(ignore_duplicates=True),
            interval=300
        )
        self._reload_selector = CallIntervalLimiter(reload_selector, interval=300)

    def _delegate(self, function, function_args=(), function_kwargs={}, keep_cache=False):
        """ handle function call delegation to plugin """
        import logging  # TODO: as written above - even modules can be missing at some point

        self._reload_selector()

        logging.getLogger("tractor-blade").debug("Delegating `{}`".format(function.__name__))

        if function.__name__.endswith("State"):
            selector = lambda: self._filter_selector(function_args[0], None)  # -> pass `stateDict` and no cmd
        else:
            selector = lambda: self._filter_selector({}, function_args[0])  # -> pass cmd and empty stateDict

        try:
            plugin_names = selector()
        except:
            logging.getLogger("tractor-blade").error(
                "Calling filter selector failed. Unable to delegate to any plugin.",
                exc_info=True
            )
            plugin_names = []

        plugin = None

        if plugin_names:

            if isinstance(plugin_names, basestring):
                plugin_names = [plugin_names]

            # enforce bypassing the plugin cache to ensure implemented sites status filter methods
            # are always up to date
            if ENABLE_PLUGIN_CACHE and not keep_cache:
                self._plugins_initialize()

            for plugin_name in plugin_names:

                try:
                    plugin = self._plugins.sitestatusfilter(plugin_name)(persistent_data=self._persistent_data)
                    # as the plugin inherits from TrSiteStatusFilter there should always be the actual filter function
                    func = getattr(plugin, function.__name__)

                    break

                except KeyError:
                    # fallback to original implementation if the plugin can't be found
                    logging.getLogger("tractor-blade").error(
                        "Unable to find site status filter `{}`.".format(plugin_name),
                        exc_info=True
                    )
                    func = function

            # fallback mechanism!
            # We'd like to prevent bypassing the default implementation of TrSiteStatusFilter
            if func != function:
                if plugin:
                    logging.getLogger("tractor-blade").debug(
                        "Calling filter function on plugin `{}` from `{}`".format(
                            plugin.__class__.__name__,
                            inspect.getfile(func)
                        )
                    )

                try:
                    return func(*function_args, **function_kwargs)
                except:
                    logging.getLogger("tractor-blade").error(
                        "Fallback to derived implementation, because `{}` failed.".format(func),
                        exc_info=True
                    )

        return function(*function_args, **function_kwargs)

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
