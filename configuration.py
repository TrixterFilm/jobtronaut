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

""" The default jobtronaut configuration to show what is configurable """

import os

from collections import OrderedDict

LOGGING_NAMESPACE = "jobtronaut"

# some wrapper scripts that are required to allow the given DCC to call python code directly
MAYA_SCRIPT_WRAPPER = os.path.join(os.path.dirname(__file__), "author", "scripts", "mayascript.mel")
KATANA_SCRIPT_WRAPPER = os.path.join(os.path.dirname(__file__), "author", "scripts", "katanascript.py")
NUKE_SCRIPT_WRAPPER = os.path.join(os.path.dirname(__file__), "author", "scripts", "nukescript.py")

# the maximum character limit our serialized arguments string can have
# when hitting the limit we dump the content to a file instead of passing it
# to the command directly
ARGUMENTS_SERIALIZED_MAX_LENGTH = 10000
# storage path for the dumped serialized arguments
ARGUMENTS_STORAGE_PATH = ""

# a "reserved" argument we can provide to allow additional flags to a tractor commandtask through a job
COMMANDFLAGS_ARGUMENT_NAME = "additional_command_flags"

# storage path template for our jobs as alf files
JOB_STORAGE_PATH_TEMPLATE = ""

# to keep the engine user credentials more secret a function callable can be defined
# that would return the credentials tuple (username, password)
TRACTOR_ENGINE_CREDENTIALS_RESOLVER = lambda: ("unknown_user", "unknown_password")

# The searchpaths for any kind of plugins (tasks/processors)
PLUGIN_PATH = []
# Whether the plugin path should only be resolved once and read from a cache for successive accesses.
# You can use Plugins().initialize() to force a resolve of the plugin paths at any time.
ENABLE_PLUGIN_CACHE = True

# A resolver for converting a command id like `maya` into an absolute path.
# A command id is always the first item in the list that gets returned by task.cmd()
EXECUTABLE_RESOLVER = \
    lambda x: x \
        if os.path.isfile(x) and os.path.isabs(x) and os.access(x, os.X_OK) \
        else (_ for _ in ()).throw(
            OSError("Command Id `{}` is not an executable.".format(x))
        )

# A way to resolve an environment. It will be assumed that the resolver would return a dict or OrderedDict
# where the key represents the env var name and the value a string joining all values separated through the
# required separator character
ENVIRONMENT_RESOLVER = lambda: OrderedDict(sorted(os.environ.items()))
# Only if True the resolver will be used and the environment be passed to the envkey attribute of the resulting job
INHERIT_ENVIRONMENT = True
