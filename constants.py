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

""" a collection of constants """


import imp
import logging
import traceback
import os
import sys


from . import configuration

LOGGING_NAMESPACE = "jobtronaut"
_LOG = logging.getLogger(LOGGING_NAMESPACE)
logging.basicConfig(level=logging.INFO)

_custom_configuration = os.getenv("JOBTRONAUT_CONFIGURATION_PATH", False)
custom_configuration = None

# try our best to source a custom configuration
if _custom_configuration:
    if not os.path.exists(_custom_configuration):
        raise OSError("Custom configuration `{}` doesn't exist.".format(_custom_configuration))
    if not os.path.splitext(_custom_configuration)[1] in [".py"]:
        raise AssertionError("Custom configuration must `{}` be a .py file.".format(_custom_configuration))
    if os.path.exists(os.path.splitext(_custom_configuration)[0] + ".pyc") or \
        os.path.exists(os.path.splitext(_custom_configuration)[0] + ".pyo"):

        _LOG.warning(
            "Byte-compiled file exist for configuration `{}`. ".format(_custom_configuration) +
            "Please ensure this matches your current configuration. It will probably load the compiled source."
        )

    _LOG.info("Custom configuration specified in `{}`. Trying to load...".format(_custom_configuration))
    try:
        custom_configuration = imp.load_source("configuration", _custom_configuration)
    except Exception:
        raise Exception(
            "Failed to load custom configuration.\n{}".format("\n".join(traceback.format_exception(*sys.exc_info())))
        )


def _get_configuration_value(entry, validator=(lambda x: True, "")):
    """ helper to get the (custom) configuration entry with options to validate

    Args:
        entry (str): configuration module member
        validator (tuple): a tuple where the first index is a callable that performs a True/False validation
        and the second index a string representing the message that gets raised when the validation returns False

    Returns: The value of the configuration module member

    """
    if custom_configuration:
        if hasattr(custom_configuration, entry):
            value = getattr(custom_configuration, entry)
        else:
            _default = getattr(configuration, entry)
            _LOG.info(
                "Entry `{}` wasn't defined in custom configuration. ".format(entry) +
                "Use default of `{}` instead".format(_default)
            )
            return _default
    else:
        value = getattr(configuration, entry)

    if not validator[0](value):
        raise ValueError(validator[1])
    else:
        return value


LOGGING_NAMESPACE = _get_configuration_value("LOGGING_NAMESPACE")

MAYA_SCRIPT_WRAPPER = _get_configuration_value("MAYA_SCRIPT_WRAPPER")
KATANA_SCRIPT_WRAPPER = _get_configuration_value("KATANA_SCRIPT_WRAPPER")
NUKE_SCRIPT_WRAPPER = _get_configuration_value("NUKE_SCRIPT_WRAPPER")

ARGUMENTS_SERIALIZED_MAX_LENGTH = _get_configuration_value("ARGUMENTS_SERIALIZED_MAX_LENGTH")
ARGUMENTS_STORAGE_PATH = _get_configuration_value("ARGUMENTS_STORAGE_PATH")

COMMANDFLAGS_ARGUMENT_NAME = _get_configuration_value("COMMANDFLAGS_ARGUMENT_NAME")

JOB_STORAGE_PATH_TEMPLATE = _get_configuration_value(
    "JOB_STORAGE_PATH_TEMPLATE",
    validator=(
        lambda x: "{user}" in x and "{date}" in x and "{job_id}" in x if x else True,
        "Missing {user} or {date} or {job_id} placeholder in template path. Please ensure to use all of those."
    )
)

TRACTOR_ENGINE_CREDENTIALS_RESOLVER = _get_configuration_value("TRACTOR_ENGINE_CREDENTIALS_RESOLVER")

TRACTOR_ENGINE_USER_NAME = _get_configuration_value("TRACTOR_ENGINE_USER_NAME")
TRACTOR_ENGINE_USER_PASSWORD = _get_configuration_value("TRACTOR_ENGINE_USER_PASSWORD")

PLUGIN_PATH = _get_configuration_value(
    "PLUGIN_PATH",
    validator=(
        lambda x: isinstance(x, (list, tuple)),
        "PLUGIN_PATH value must be of type list or tuple."
    )
)

ENABLE_PLUGIN_CACHE = _get_configuration_value(
    "ENABLE_PLUGIN_CACHE",
    validator=(
        lambda x: isinstance(x, bool),
        "ENABLE_PLUGIN_CACHE value must be of type bool."
    )
)

EXECUTABLE_RESOLVER = _get_configuration_value(
    "EXECUTABLE_RESOLVER"
)

ENVIRONMENT_RESOLVER = _get_configuration_value(
    "ENVIRONMENT_RESOLVER",
)

INHERIT_ENVIRONMENT = _get_configuration_value(
    "INHERIT_ENVIRONMENT",
    validator=(
        lambda x: isinstance(x, bool),
        "INHERIT_ENVIRONMENT value must be of type bool."
    )
)

# Formatting options grabbed from https://misc.flogisoft.com/bash/tip_colors_and_formatting
BASH_STYLES = {
    # COLORS
    "FG_DEFAULT": "\033[39m",
    "FG_BLACK": "\033[30m",
    "FG_WHITE": "\033[97m",
    "FG_RED": "\033[91m",
    "FG_DARKRED": "\033[31m",
    "FG_GREEN": "\033[92m",
    "FG_DARKGREEN": "\033[32m",
    "FG_YELLOW": "\033[93m",
    "FG_DARKYELLOW": "\033[33m",
    "FG_BLUE": "\033[94m",
    "FG_DARKBLUE": "\033[34m",
    "FG_PURPLE": "\033[95m",
    "FG_DARKPURPLE": "\033[35m",
    "FG_CYAN": "\033[96m",
    "FG_DARKCYAN": "\033[36m",

    # BACKGROUND
    "BG_DEFAULT": "\033[49m",
    "BG_BLACK": "\033[40m",
    "BG_WHITE": "\033[107m",
    "BG_RED": "\033[101m",
    "BG_DARKRED": "\033[41m",
    "BG_GREEN": "\033[102m",
    "BG_DARKGREEN": "\033[42m",
    "BG_YELLOW": "\033[103m",
    "BG_DARKYELLOW": "\033[43m",
    "BG_BLUE": "\033[104m",
    "BG_DARKBLUE": "\033[44m",
    "BG_PURPLE": "\033[105m",
    "BG_DARKPURPLE": "\033[45m",
    "BG_CYAN": "\033[106m",
    "BG_DARKCYAN": "\033[46m",

    # STYLES
    "BOLD": "\033[1m",
    "DIM": "\033[2m",
    "UNDERLINE": "\033[4m",
    "BLINK": "\033[5m",
    "INVERT": "\033[7m",

    # TERMINATORS
    "END": "\033[0m",
    "NO_BOLD": "\033[21m",
    "NO_DIM": "\033[22m",
    "NO_UNDERLINE": "\033[24m",
    "NO_BLINK": "\033[25m",
    "NO_INVERT": "\033[27m"
    }

