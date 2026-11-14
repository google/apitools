# Copyright 2026 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Public pager limit boundary regressions."""

import unittest

from apitools.base.protorpclite import messages
from apitools.base.py import list_pager


class PageRequest(messages.Message):
    pageToken = messages.StringField(1)
    maxResults = messages.IntegerField(2)


class PageResponse(messages.Message):
    items = messages.StringField(1, repeated=True)
    nextPageToken = messages.StringField(2)


class ListService(object):
    def __init__(self):
        self.calls = []

    def List(self, request, global_params=None):
        self.calls.append(request.maxResults)
        return PageResponse(items=['a', 'b', 'c'])


class PagerLimitTest(unittest.TestCase):
    def _AssertNoFetch(self, limit):
        service = ListService()
        request = PageRequest(pageToken='original', maxResults=37)
        result = list(list_pager.YieldFromList(
            service, request, limit=limit))
        self.assertEqual([], result)
        self.assertEqual([], service.calls)
        self.assertEqual('original', request.pageToken)
        self.assertEqual(37, request.maxResults)

    def testNegativeLimitDoesNotFetch(self):
        self._AssertNoFetch(-1)

    def testLargerNegativeLimitDoesNotFetch(self):
        self._AssertNoFetch(-100)

    def testZeroLimitDoesNotFetch(self):
        service = ListService()
        result = list(list_pager.YieldFromList(
            service, PageRequest(), limit=0))
        self.assertEqual([], result)
        self.assertEqual([], service.calls)

    def testPositiveLimitRemainsBounded(self):
        service = ListService()
        result = list(list_pager.YieldFromList(
            service, PageRequest(), limit=2))
        self.assertEqual(['a', 'b'], result)
        self.assertEqual([2], service.calls)

    def testUnlimitedStillYieldsAllItems(self):
        service = ListService()
        result = list(list_pager.YieldFromList(
            service, PageRequest(), limit=None))
        self.assertEqual(['a', 'b', 'c'], result)
        self.assertEqual([100], service.calls)


if __name__ == '__main__':
    unittest.main()
