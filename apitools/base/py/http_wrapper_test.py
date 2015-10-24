#
# Copyright 2015 Google Inc.
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

"""Tests for http_wrapper."""
import unittest2

from apitools.base.py import http_wrapper


class RaisesExceptionOnLen(object):

    """Supports length property but raises if __len__ is used."""

    def __len__(self):
        raise Exception('len() called unnecessarily')

    def length(self):
        return 1


class HttpWrapperTest(unittest2.TestCase):

    def testRequestBodyUsesLengthProperty(self):
        http_wrapper.Request(body=RaisesExceptionOnLen())

    def testRequestBodyWithLen(self):
        http_wrapper.Request(body='burrito')
