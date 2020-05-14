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

""" Job class and submission utilities

The Job class extends the base tractor.author.Job class and acts as
the starting point for generating a job with a task hierarchy.
"""

import getpass
import json
import logging
import os
import uuid

from datetime import date

from tractor.api import author

from ..constants import (
    ARGUMENTS_STORAGE_PATH,
    JOB_STORAGE_PATH_TEMPLATE,
    LOGGING_NAMESPACE,
    INHERIT_ENVIRONMENT,
    ENVIRONMENT_RESOLVER
)
from .plugins import Plugins
from ..query.command import get_local_state


_LOG = logging.getLogger("{}.author.job".format(LOGGING_NAMESPACE))


# DEPRECATION: obsolete with Python 3.2, because os.makedirs offers the exist_ok keyword argument
def make_dirs(path, mode=0777):
    """ convenience function around os.make_dirs

    Avoids the need to check if the path that will be created already exists.

    Args:
        path (str): directory path
        mode (octal, optional): file mode

    Returns:
        bool - True if file exists or could be created. False if not.
    """
    try:
        if not os.path.exists(path):
            os.makedirs(path)
            os.chmod(path, mode)
        return True
    except (OSError, AttributeError, TypeError):
        _LOG.error("Failed to create directory '%s'" % path, exc_info=True)
    return False


class Job(author.Job):
    """ extends tractors Job class """

    title = "untitled"

    MEMBERS = author.Job.MEMBERS + [
        "arguments",
        "arguments_cache",
        "arguments_file",
        "job_attributes",
        "requires_arguments_cache",
        "task",
        "_flat_hierarchy",
        "local"
    ]

    def __init__(self, task, arguments={}, append_instances=True, compact_hierarchy=True, local=None, **kwargs):
        """

        Args:
            task (:obj: `Task`): the root task(hierarchy) the job will resolve
            arguments (:obj: `dict` or `Arguments` or `str`): task arguments
            append_instances (bool): if True it will append an instance to each
            command that refers to a specific parent task when this task has
            a serial relationship to an upstream task.
            Only set this to True when the task hierarchy will be expanded within
            an activily running task.
            This normally is not required, as our `serial` task ensures a serial
            relationship by nature, but due to a Tractor bug this will not work
            if the hierarchy was expanded via `TR_EXPAND_CHUNK`.
            local (bool): if True commands won't be created as RemoteCommand instances,
            but as regular Command instances that will only run on the spoolhost; if None
            the job initialization handles the command type inheritance automatically when
            running as active command
            **kwargs ():
        """
        super(Job, self).__init__()

        # a title is always required, lets use our default
        self.title = getattr(self.__class__, "title", "")

        self.envkey = []

        # define the commands type
        job_id = os.getenv("TR_ENV_JID")
        command_id = os.getenv("TR_ENV_CID")

        if local is not None:
            # explicitly set local value
            self.local = local
        # check if the job is initialized inside a running command on tractor
        elif job_id and command_id:
            # inherit the current local attribute when running on tractor
            # otherwise use the passed value
            self.local = get_local_state(job_id=job_id, command_id=command_id)
        else:
            self.local = False

        # unfortunately attributes is reserved so we have to name it differently
        self.job_attributes = kwargs.get("job_attributes", {})
        self.arguments_cache = {}
        self.arguments_file = os.path.join(ARGUMENTS_STORAGE_PATH, "{}.json".format(uuid.uuid4()))
        self.requires_arguments_cache = False
        self._prepare_attributes(self.job_attributes)

        if isinstance(task, str):
            _task_cls = Plugins().task(task)
            _task_cls.job = self
            _task = _task_cls(arguments)
            self.addChild(_task)
        elif isinstance(task, author.Task):
            _task = task
            self.addChild(task)
        else:
            raise NotImplementedError("Only Task names and author.Tasks instances allowed.")

        self.task = _task

        if compact_hierarchy:
            self._compact_hierarchy()
        if append_instances:
            self._append_instances()

        self._flat_hierarchy = None

    @property
    def flat_hierarchy(self):
        """ flatten the hierarchy when accessed the first time, otherwise
        return cached result

        Returns:
            dict: "tasks": [], "cmds": []

        """
        if not self._flat_hierarchy:
            self._flat_hierarchy = self._flatten(self.task)
        return self._flat_hierarchy

    def _prepare_attributes(self, kwargs):
        """ correction and validation of job attributes

        Returns:

        """
        for name, value in kwargs.iteritems():
            # tractor does not like unicode; we automatically convert to ASCII
            if isinstance(value, unicode):
                value = str(value)
            assert self.attributeByName.get(name, None), \
                   "Invalid keyword argument for job submission: \"{}\"".format(name)
            self.__setattr__(name, value)

    @staticmethod
    def _resolve_job_file(job_id):
        """ resolve our job file template path"""
        return JOB_STORAGE_PATH_TEMPLATE.format(
            user=getpass.getuser(),
            date=date.today().strftime("%y%m%d"),
            job_id=job_id
        )

    def dump_job(self, filepath):
        """ stores tractor job TCL represention

        The generated TCL script can be used by Tractor's job parser.
        This format was first introduced for the Alfred system, and Tractor
        remains compatible with nearly all Alfred constructs. Previously this
        format used the `.alf`  extension, so lets stick to this.

        Later on this file can be used for debugging/inspection or simple
        resubmission via `tractor-spool` command.

        Args:
            filepath (str): path to the script file

        Returns:

        """
        try:
            make_dirs(os.path.dirname(filepath))
            with open(filepath, "w") as f:
                f.write(self.asTcl())
                _LOG.info("Dumping job to file: '{}'".format(filepath))
        except IOError:
            _LOG.error("Unable to dump job file.", exc_info=True)

    def submit(self, dump_job=True, **kwargs):
        """ convenience wrapper for the spool method that enables setting
        job attributes as keyword arguments at submission time and more

        Args:
            dump_job (bool): If True it will store the job as alf file.
            The storage place is defined in the JOB_STORAGE_PATH_TEMPLATE.
            **kwargs: arguments that should be set as job attributes

        Returns:
        """
        self._prepare_attributes(kwargs)

        # we don't know exactly which of our tasks require our dumped arguments
        # so lets always dump it when submitting
        self.dump_arguments_cache(self.arguments_file)

        # TODO: find a way to ignore the envkey in the tractor search
        if INHERIT_ENVIRONMENT:
            _LOG.info("Option to inherit environment was enabled. Passing the environment to the job.")
            self.envkey = [self._get_env_as_tractor_envkey()]

        job_id = self.spool(owner=getpass.getuser())

        if dump_job:
            if JOB_STORAGE_PATH_TEMPLATE:
                # lets store our job as file for later reusage
                alf_file = self._resolve_job_file(job_id)
                self.dump_job(alf_file)
            else:
                _LOG.warning(
                    "Option `dump_job` was set to True, but no `JOB_STORAGE_PATH_TEMPLATE` was configured. " +
                    "Skipped job dumping."
                )

        return job_id

    @staticmethod
    def _get_env_as_tractor_envkey():
        """ extracts the whole environment and formats it as a tractor envkey

        Args:
            exclude (:obj:`list` of :obj:`str`): list of environment variables that will be not included

        Returns:
             str: formatted envkey for tractor
        """
        return "setenv " + " ".join(["{0}={1}".format(key, value) for key, value in ENVIRONMENT_RESOLVER().items()])

    def dump_arguments_cache(self, filepath, force=False):
        """ dumps a json that includes all serialized arguments

        Args:
            filepath (str): path to the arguments we will store as file
            force (bool): if True it will dump the arguments cache even if its not
            a requirement for a task of the given job that consumes the arguments cache
        """
        if not self.requires_arguments_cache and not force:
            _LOG.info("Job does not to require dumped arguments. Skipped...")
        else:
            try:
                make_dirs(ARGUMENTS_STORAGE_PATH)
                with open(filepath, "w") as f:
                    json.dump(self.arguments_cache, f)
                    _LOG.info("Dumping arguments cache to file: '{}'".format(filepath))
            except IOError:
                _LOG.error("Unable to dump serialized object.")
                raise

    def _flatten(self, task):
        """ walks the task and cmd hierarchy in a depth first manner and returns
        a dictionary with both as a flattened lists

        Args:
            task: the root level task to start the walk

        Returns:
            dict: a dict with "cmds" and "tasks"

        """
        subtasks = {"tasks": [], "cmds": []}

        for cmd in task.attributeByName.get("cmds", []):
            subtasks["cmds"].append(cmd)

        subtasks["tasks"].append(task)

        # whenever we hit an instance we get None via task.subtasks
        if task.subtasks:
            for subtask in task.subtasks:
                _temp = self._flatten(subtask)
                subtasks["tasks"].extend(_temp["tasks"])
                subtasks["cmds"].extend(_temp["cmds"])

        return subtasks

    def _compact_hierarchy(self, task=None):
        if not task:
            task = self

        new_task = task
        while new_task.subtasks:
            if len(new_task.subtasks) == 1:
                # we have to handle this in case the job has been processed
                # before and is reused in a jobs_as_task situation
                if isinstance(new_task.subtasks[0], author.Instance):
                    break
                new_task = new_task.subtasks[0]
            elif len(new_task.subtasks) > 1:
                for subtask in new_task.subtasks:
                    self._compact_hierarchy(subtask)
                break

        if new_task is not task:
            task.attributeByName["subtasks"].value = [new_task]
            # If task is self we don't want to optimize that away.
            # In case of an expanded task we don't have any possibility to
            # change the existing parent to serial so we have to keep the
            # intermediate "serial" task to handle the hierarchy
            # correctly.
            if task is not self and new_task.title in ("serial", "parallel"):
                if new_task.title == "serial" or new_task.serial:
                    task.serialsubtasks = 1
                task.attributeByName["subtasks"].value = new_task.subtasks

    def _append_instances(self, task=None, dependent_id=""):
        if not task:
            task = self.task

        if task.__class__ == author.Instance:
            return

        if task.subtasks:
            for idx, subtask in enumerate(task.subtasks):
                self._append_instances(subtask, dependent_id)
                if task.serialsubtasks:
                    dependent_id = subtask.id
        elif dependent_id:
            instance = author.Instance(title=dependent_id)
            task.addChild(instance)

    def _modify(self, predicate, attribute, value, scope):
        """ modifies task or command attributes if the predicate returns true

        Args:
            predicate: a callable that returns True or False
            attribute: the attribute to modify
            value: the new value for the attribute
            scope: "cmds" or "tasks"

        Returns:

        """
        for child in self.flat_hierarchy[scope]:
            if predicate(child):
                if child.attributeByName.get(attribute):
                    child.attributeByName.get(attribute).value = value
                elif getattr(child, attribute):
                    setattr(child, attribute, value)

    def modify_tasks(self, predicate=lambda task: False, attribute="", value=""):
        """ calls modify with a "tasks" scope

        Args:
            predicate: a callable that returns True or False
            attribute: the attribute to modify
            value: the new value for the attribute

        Returns:

        """
        self._modify(predicate, attribute, value, "tasks")

    def modify_cmds(self, predicate=lambda cmd: False, attribute="", value=""):
        """ calls modify with a "cmds" scope

        Args:
            predicate: a callable that returns True or False
            attribute: the attribute to modify
            value: the new value for the attribute

        Returns:

        """
        self._modify(predicate, attribute, value, "cmds")


# @todo: maybe find a good way to abstract this and make it resuable inside the task implementation and elsewhere
def jobs_to_task(jobs, parent_task=None, wait_for_task=None):
    """ converts a job dependency representation to a single task dependency

    Recursively adds a Job's main task to a given parent task. This allows you
    to use the usual tuple vs list syntax to describe a dependency.

    Args:
        jobs (:obj:`list` or `tuple` :obj:`Job`): serial/parallel job
                                                  dependency representation

                Example:
                    [Job1, Job2] - Job1's root task runs parallel to Job2's
                                   root task
                    (Job1, Job2) - Job2's root task runs after Job1's root
                                     task
                    [Job1, [Job2, Job3]] - Job1's root task runs parallel to
                                           Job2's root task & Job3's root
                                           task, but Job3's root task starts
                                           when Job2's root task finishes
                    [Job1, (Job2, Job3)] - Job3's root task runs after Job2's
                                           root task, Job2's root task runs
                                           parallel to Job1's root task
        parent_task (:obj: `Task`): the parent task that will change recursively
        root_task (:obj: `Task`): the root task that will represent the
                                  main handle for the created dependency

    Returns:
        Task: the root path holding the generated dependency

    """
    if not parent_task:
        root_task = author.Task({}, title="root", id=str(uuid.uuid4()))
        jobs_to_task(jobs, parent_task=root_task)
        return root_task

    if isinstance(jobs, tuple):
        _serialtask = author.Task({}, serialsubtasks=True, title="serial", id=str(uuid.uuid4()))
        parent_task.addChild(_serialtask)
        parent_task = _serialtask
    elif isinstance(jobs, list):
        _paralleltask = author.Task({}, title="parallel", id=str(uuid.uuid4()))
        parent_task.addChild(_paralleltask)
        parent_task = _paralleltask

    for job_or_jobs in jobs:
        if isinstance(job_or_jobs, (tuple, list)):
            jobs_to_task(job_or_jobs, parent_task=parent_task)
        else:
            parent_task.subtasks.append(job_or_jobs.task)


def _dump_arguments_cache(jobs, force=False):
    """ dumps the arguments cache for a given job dependency recursively

    Args:
        jobs (:obj:`list` or `tuple` :obj:`Job`): job dependency representation
        force (bool): if True it will dump the arguments cache even if its not
        a requirement for a task of the given job that consumes the arguments cache
    """
    if isinstance(jobs, Job):
        jobs.dump_arguments_cache(jobs.arguments_file, force=force)
    elif isinstance(jobs, (list, tuple)):
        for job_or_jobs in jobs:
            _dump_arguments_cache(job_or_jobs, force=force)


def submit_as_tasks(jobs, job_attributes=None, dump_job=True):
    """ lets you submit multiple jobs as a single job converting them to tasks

    Args:
        jobs (:obj:`list` or `tuple` :obj:`Job`): : serial/parallel job
                                                    dependency representation

                Example:
                    [Job1, Job2] - Job1's root task runs parallel to Job2's
                                   root task
                    (Job1, Job2) - Job2's root task runs after Job1's root
                                     task
                    [Job1, [Job2, Job3]] - Job1's root task runs parallel to
                                           Job2's root task & Job3's root
                                           task, but Job3's root task starts
                                           when Job2's root task finishes
                    [Job1, (Job2, Job3)] - Job3's root task runs after Job2's
                                           root task, Job2's root task runs
                                           parallel to Job1's root task
        job_attributes (dict, optional): job attributes
        dump_job (bool): if True it will store the job as alf file

    Returns:

    """

    # convert multiple jobs into a single root task
    task = jobs_to_task(jobs)
    # ensure that we dump the arguments cache file reqursively
    _dump_arguments_cache(jobs)
    job_attributes = job_attributes or jobs[0].job_attributes
    return Job(task, job_attributes=job_attributes).submit(dump_job=dump_job)


def submit(jobs, job_attributes={}, serial=False, dump_job=True):
    """ lets you submit multiple jobs serial to each other or in parallel

    Args:
        jobs (:obj:`list` or `tuple` :obj:`Job`): jobs to submit
        job_attributes (dict): effective overrides to all job attributes
        serial (bool): if True jobs will be serial to each other
        dump_job (bool): if True it will store the job as alf file.

    Returns:
        list: job ids

    """
    ids = []
    parent_id = None
    for job in jobs:
        job.job_attributes.update(job_attributes)
        if serial and parent_id:
            # setting serial relationship
            job.job_attributes["afterjids"] = [parent_id]

        parent_id = job.submit(dump_job=dump_job, **job.job_attributes)
        ids.append(parent_id)

    return ids
