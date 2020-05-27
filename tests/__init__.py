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

import difflib
import os
import pprint
import unittest


class TestCase(unittest.TestCase):
    """ extending unittests.TestCase class
    """

    def _assert_has_attribute(self, obj, name, expectation, msg):
        if not hasattr(obj, name) == expectation:
            msg = self._formatMessage(msg, "%s has no attribute named %s" % (unittest.case.safe_repr(obj),
                                                                             unittest.case.safe_repr(name)
                                                                             )
                                      )
            raise self.failureException(msg)

    def assertHasAttribute(self, obj, name, msg=None):
        """ fail if the attribute does not exist on object """
        self._assert_has_attribute(obj, name, True, msg)

    def assertNotHasArgument(self, obj, name, msg=None):
        """ fail if attribute exists on object """
        self._assert_has_attribute(obj, name, False, msg)

    def assertPathExists(self, path, msg=None):
        """ fail if path does not exist """
        if not os.path.exists(path):
            msg = self._formatMessage(msg, "Path %s does not exist." % unittest.case.safe_repr(path))
            raise self.failureException(msg)

    def assertNotDictEqual(self, d1, d2, msg=None):
        self.assertIsInstance(d1, dict, 'First argument is not a dictionary')
        self.assertIsInstance(d2, dict, 'Second argument is not a dictionary')

        if d1 == d2:
            standardMsg = '%s == %s' % (unittest.case.safe_repr(d1, True),
                                        unittest.case.safe_repr(d2, True))
            diff = ('\n' + '\n'.join(difflib.ndiff(
                           pprint.pformat(d1).splitlines(),
                           pprint.pformat(d2).splitlines())))
            standardMsg = self._truncateMessage(standardMsg, diff)
            self.fail(self._formatMessage(msg, standardMsg))