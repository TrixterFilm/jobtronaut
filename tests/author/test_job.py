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


import json
import os
import tempfile

from collections import OrderedDict

from mock import patch

from .. import TestCase

from jobtronaut.author import Job
from jobtronaut.author.job import _dump_arguments_cache
from jobtronaut.author.plugins import Plugins


from .plugins_fixtures import some_tasks as tasks


class TestJob(TestCase):

    @classmethod
    @patch("jobtronaut.author.plugins.PLUGIN_PATH", new=[os.path.dirname(tasks.__file__)])
    def setUp(cls):
        cls._job = Job(tasks.TASKS_DICT.keys()[0], {"uno": 1, "dos": 2, "tres": 3})
        cls._arguments_cache_file_template = os.path.join(tempfile.gettempdir(), "{placeholder}.json")

    def test_init(self):
        """ check if the initialized Job fulfills the expected requirements """

        self.assertEqual(
            len(self._job.attributeByName["subtasks"].value),
            1,
            msg="Expected exactly one subtask for job."
        )

    @patch.dict("os.environ", {"A": "1", "B": "2", "PATH": "/var/tmp:/tmp/user"}, clear=True)
    @patch("jobtronaut.author.job.INHERIT_ENVIRONMENT", new=True)
    @patch("jobtronaut.author.job.ENVIRONMENT_RESOLVER", new=lambda: OrderedDict(sorted(os.environ.items())))
    @patch("jobtronaut.author.job.Job.spool", new=lambda x, owner: "")
    @patch("jobtronaut.author.job.Job.dump_job", new=lambda x, y: "")
    def test_inherit_environment_resolve(self):
        """ check if our method for retrieving the environment for tractor works correctly """
        expected = ["setenv A=1 B=2 PATH=/var/tmp:/tmp/user"]
        root_task, arguments = tasks.TASKS_DICT.keys()[0], {"uno": 1, "dos": 2, "tres": 3}

        job = Job(root_task, arguments)
        job.submit()
        self.assertEqual(expected, job.envkey)

    @patch("jobtronaut.author.plugins.PLUGIN_PATH", new=[os.path.dirname(tasks.__file__)])
    def test_dump_arguments_cache(self):

        self._job.arguments_cache = {"hello": "world"}

        with patch.object(self._job, "arguments_file", self._arguments_cache_file_template.format(placeholder="1")):
            # we shouldn't dump a cache when we didn't set this explicitly to required
            self._job.dump_arguments_cache(self._job.arguments_file)
            self.assertFalse(os.path.exists(self._job.arguments_file))

            # check with force flag
            self._job.dump_arguments_cache(self._job.arguments_file, force=True)
            self.assertTrue(os.path.exists(self._job.arguments_file))
            # cleanup
            os.remove(self._job.arguments_file)

            with patch.object(self._job, "requires_arguments_cache", True):
                # try without force flag but with requirement set
                self._job.dump_arguments_cache(self._job.arguments_file)
                self.assertPathExists(self._job.arguments_file)

                with open(self._job.arguments_file) as f:
                    self.assertEqual(self._job.arguments_cache, json.load(f))

                # cleanup mess
                os.remove(self._job.arguments_file)

    @patch("jobtronaut.constants.ARGUMENTS_STORAGE_PATH", "/tmp/dump")
    def test_dump_arguments_cache_on_job_dependency(self):
        root_task, arguments = tasks.TASKS_DICT.keys()[0], {"uno": 1, "dos": 2, "tres": 3}

        job_one = Job(root_task, arguments)
        job_two = Job(root_task, arguments)
        job_three = Job(root_task, arguments)
        job_four = Job(root_task, arguments)
        job_five = Job(root_task, arguments)
        job_six = Job(root_task, arguments)

        all_jobs = [job_one, job_two, job_three, job_four, job_five, job_six]
        requires = [job_one, job_five]

        # let all jobs require the arguments cache
        [setattr(job, "requires_arguments_cache", True) for job in all_jobs]
        [setattr(job, "arguments_file", self._arguments_cache_file_template.format(placeholder=i)) for i, job in enumerate(all_jobs)]

        hierarchy = (
            job_one, [
                job_two, (
                    job_three, [
                        job_four, job_five
                    ],
                )
            ],
            job_six
        )

        # test when all jobs require
        _dump_arguments_cache(hierarchy)
        for job in all_jobs:
            self.assertPathExists(job.arguments_file)
            os.remove(job.arguments_file)

        # change the requirements
        [setattr(job, "requires_arguments_cache", False) for job in all_jobs if not job in requires]

        # test when some jobs require
        _dump_arguments_cache(hierarchy)
        for job in all_jobs:
            if job in requires:
                self.assertPathExists(job.arguments_file)
                os.remove(job.arguments_file)
            else:
                self.assertFalse(os.path.exists(job.arguments_file))

        # test when some jobs require but with enforced dumping
        _dump_arguments_cache(hierarchy, force=True)
        for job in all_jobs:
            self.assertPathExists(job.arguments_file)
            os.remove(job.arguments_file)

    def test_stop_traversal(self):
        """ check if stop_traversal will prevent task creation """
        root_task, arguments = tasks.TASKS_DICT.keys()[0], {"uno": [1, 2, 3], "dos": 2, "tres": 3}

        for task in Plugins().tasks.values():
            task.cmd = lambda x: ["/bin/echo", "Hello World"]
            task.flags = tasks.Task.Flags.PER_ELEMENT

        job = Job(root_task, arguments)
        self.assertEqual(len(job.flat_hierarchy["tasks"]), 4)

        for task in Plugins().tasks.values():
            task.stop_traversal = lambda x: x.arguments.uno.processed == 2

        job = Job(root_task, arguments)
        self.assertEqual(len(job.flat_hierarchy["tasks"]), 3)
        self.assertTrue("Elements 2" not in " ".join([_.title for _ in job.flat_hierarchy["tasks"]]))

        for task in Plugins().tasks.values():
            task.stop_traversal = lambda x: x.arguments.uno.processed in [1, 2, 3]

        job = Job(root_task, arguments)
        self.assertEqual(len(job.flat_hierarchy["tasks"]), 1)
        self.assertTrue("Elements" not in " ".join([_.title for _ in job.flat_hierarchy["tasks"]]))

    def test_modify(self):

        root_task, arguments = tasks.TASKS_DICT.keys()[0], {"uno": [1, 2, 3], "dos": 2, "tres": 3}

        for task in Plugins().tasks.values():
            task.flags = task.Flags.PER_ELEMENT
            task.cmd = lambda x: ["/bin/echo", "Hello World"]
            task.tags = ["foo", "bar"]

        job = Job(root_task, arguments)

        def _get_attribute_listed(job, type, attribute):
            return [_.attributeByName.get(attribute).value for _ in job.flat_hierarchy[type]]

        job.modify_cmds(predicate=False, attribute="tags", value=["foobar"])
        self.assertListEqual(
            [["foo", "bar"], ["foo", "bar"], ["foo", "bar"]],
            _get_attribute_listed(job, "cmds", "tags")
        )

        job.modify_cmds(predicate=True, attribute="tags", value=["foobar"])
        self.assertListEqual(
            [["foobar"], ["foobar"], ["foobar"]],
            _get_attribute_listed(job, "cmds", "tags")
        )

        class Counter(object):
            def __init__(self):
                self.count = 0

            def __call__(self):
                self.count += 1
                return self.count

        def _skip(command, counter, number):
            if counter() == number:
                print counter.count
                return False
            else:
                return True

        counter = Counter()
        job.modify_cmds(predicate=lambda x: _skip(x, counter, 1), attribute="tags", value=["bar", "foo"])
        self.assertListEqual(
            [["foobar"], ["bar", "foo"], ["bar", "foo"]],
            _get_attribute_listed(job, "cmds", "tags")
        )

        counter = Counter()
        job.modify_cmds(predicate=lambda x: _skip(x, counter, 3), attribute="tags", value=["barfoo"])
        self.assertListEqual(
            [["barfoo"], ["barfoo"], ["bar", "foo"]],
            _get_attribute_listed(job, "cmds", "tags")
        )

        counter = Counter()
        job.modify_cmds(predicate=lambda x: _skip(x, counter, 3), attribute="tags", value=lambda x: [["one"], ["zero"]][counter.count % 2])
        self.assertListEqual(
            [["zero"], ["one"], ["bar", "foo"]],
            _get_attribute_listed(job, "cmds", "tags")
        )

