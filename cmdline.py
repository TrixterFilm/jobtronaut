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

""" jobtronaut commandline parser """

import argparse
import ast
import logging

from .author.plugins import Plugins
from .author import Job

from .constants import (
    BASH_STYLES,
    LOGGING_NAMESPACE
)

_LOG = logging.getLogger("{}.cmdline".format(LOGGING_NAMESPACE))


class StoreDict(argparse.Action):
    """ Argparse action that converts incoming job/task arguments to their correct types
    and automatically stores them in a dict.
    """
    def __init__(self, option_strings, dest, nargs=None, **kwargs):
        super(StoreDict, self).__init__(option_strings, dest, nargs, **kwargs)

    def __call__(self, parser, namespace, arguments, option_string=None):
        setattr(namespace, self.dest, dict())
        for arg in arguments:
            key, value = tuple(arg.split(":", 1))
            value = self._infer_type(value)
            getattr(namespace, self.dest)[key] = value

    @staticmethod
    def _infer_type(value):
        try:
            typed_value = ast.literal_eval(value)
        except (ValueError, SyntaxError):
            # ast.literal_eval throws a ValueError in case it encounters a string
            # and a SyntaxError if the string starts with a / (essentially a path)
            typed_value = value
        return typed_value


class AssembleEnvkeys(argparse.Action):
    """ Argparse action that mangles the incoming env arguments into a format
    that tractor expects and also automatically prepend 'setenv'.
    """
    def __call__(self, parser, namespace, arguments, option_string=None):
        envkey = ["setenv {0}".format(" ".join([_.replace(":", "=") for _ in arguments]))]
        setattr(namespace, self.dest, envkey)


def parse_args():
    """ defines the argparser for the commandline submission

    Returns:
        Parsed arguments
    """
    # define the actual valid arguments here
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers()

    submit_parser = subparsers.add_parser("submit", help="Submit a job to the farm.")
    submit_parser.set_defaults(func=submit)
    submit_parser.add_argument("--paused", action="store_const", const=True, default=False,
                               help="Submit the job in a paused state.")
    submit_parser.add_argument("--local", action="store_const", const=True, default=False,
                               help="Submit the job locally. All commands will be enforced to run on the spoolhost.")
    submit_parser.add_argument("--expandchunk", action="store_const", const=True, default=False,
                               help="If set no new job will be spooled and instead the job's .alf representation will "
                                    "be invoked via Tractor's `TR_EXPAND_CHUNK` mechanism.")
    submit_parser.add_argument("--task", type=str, required=True,
                               help="Set the root task for the job.")
    submit_parser.add_argument("--title", type=str, default="",
                               help="Set a custom job title.")
    submit_parser.add_argument("--comment", type=str, default="",
                               help="Set a job comment.")
    submit_parser.add_argument("--service", "--hostmask", dest="service", type=str, default="",
                               help="Specify a hostmask to limit the blades this job can run on.")
    submit_parser.add_argument("--afterjids", dest="jids", type=str,
                               help="Only start the job when the jobs with these ids are done.")
    submit_parser.add_argument("--priority", type=int, default=100,
                               help="Set the priority of the job.")
    submit_parser.add_argument("--maxactive", type=int, default=0,
                               help="Limit simultaneous active render nodes. Default value is 0 (no limit)")
    submit_parser.add_argument("--tags", nargs='+', type=str, default=[],
                               help="Speficy custom limit tags on the job.")
    submit_parser.add_argument("--projects", nargs='+', type=str, default=[],
                               help="Specify the projects of the job.")
    submit_parser.add_argument("--args", nargs="+", dest="arguments", action=StoreDict,
                               default=dict(), metavar="ARGNAME:ARGVALUE",
                               help="Job Arguments. Supported value types are: str, int, " "float, list")
    submit_parser.add_argument("--env", nargs="+", dest="environment", action=AssembleEnvkeys,
                               metavar="ENVVAR:ENVVALUE",
                               help="Custom environment variables that will be set prior to a command's execution on the "
                                    "farm")
    list_parser = subparsers.add_parser("list", help="Can list all known plugins.")
    list_parser.add_argument("type", default="all", choices=["all", "tasks", "processors", "sitestatusfilters"],
                             help="Define which plugins you want to list.")
    list_parser.add_argument("--info", action="store_const", const=True, default=False,
                               help="Show the detailed information for every plugin.")
    list_parser.set_defaults(func=list_)

    info_parser = subparsers.add_parser("info", help="Get more info on a specific plugin.")
    info_parser.add_argument("plugin", type=str,
                             help="Specify the plugin name for which you want more information.")
    info_parser.set_defaults(func=info)

    query_parser = subparsers.add_parser("query", help="Query jobtronaut related things.")
    query_parser.add_argument("--arguments", type=str, default="")
    query_parser.set_defaults(func=query)

    args = parser.parse_args()
    args.func(args)


def submit(args):
    """ Function that simply runs the argparser and creates and submits
    a job according the the specified arguments.
    """
    # @todo Add arguments to the jobs and tasks metadata
    try:
        jid = Job(args.task, arguments=args.arguments, local=args.local).submit(
            title=args.title or args.task,
            comment=args.comment,
            service=args.service,
            paused=args.paused,
            tags=args.tags,
            priority=args.priority,
            maxactive=args.maxactive,
            projects=args.projects or [],
            envkey=args.environment or [],
            expandchunk=args.expandchunk
        )
        _LOG.info("Successfully submitted job \"{0}\" with jid: {1}".format(args.title or args.task, jid))
    except Exception as error:
        _LOG.error("Job submission was NOT successful.", exc_info=True)
        raise error


def list_(args):
    plugins = Plugins()
    if args.type in ["all", "tasks"]:
        for _ in sorted(plugins.tasks):
            print(plugins.task(_).info(short=not(args.info)))
    if args.type in ["all", "processors"]:
        for _ in sorted(plugins.processors):
            print(plugins.processor(_).info(short=not(args.info)))
    if args.type in ["all", "sitestatusfilters"]:
        for _ in sorted(plugins.sitestatusfilters):
            print(plugins.sitestatusfilter(_).info(short=not(args.info)))


def info(args):
    print(Plugins().plugin(args.plugin).info(short=False))


def query(args):
    if args.arguments:
        from .query.arguments import get_arguments_objects

        _arguments = get_arguments_objects(args.arguments)
        if not _arguments:
            print(
                (
                    "{{BG_DARKRED}}{{FG_WHITE}}No arguments objects found for given tractor task `{}`. "
                    "Be aware that we can only extract the arguments if the corresponding task implements "
                    "a script method.{{END}}"
                ).format(
                    args.arguments
                ).format(**BASH_STYLES)
            )
        else:
            for arguments in _arguments:
                print(arguments.info())