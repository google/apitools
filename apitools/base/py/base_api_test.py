#!/usr/bin/env python


from protorpc import messages

from google.apputils import basetest as googletest
from apitools.base.py import base_api


class SimpleMessage(messages.Message):
  field = messages.StringField(1)


class FakeCredentials(object):
  def authorize(self, _):  # pylint: disable=invalid-name
    return None


class FakeClient(base_api.BaseApiClient):
  MESSAGES_MODULE = 'message_module'
  _PACKAGE = 'package'
  _SCOPES = ['scope1']
  _CLIENT_ID = 'client_id'
  _CLIENT_SECRET = 'client_secret'


class BaseApiTest(googletest.TestCase):

  def __GetFakeClient(self):
    return FakeClient('', credentials=FakeCredentials())

  def testNoCredentials(self):
    client = FakeClient('', get_credentials=False)
    self.assertIsNotNone(client)
    self.assertIsNone(client._credentials)

  def testIncludeEmptyFieldsClient(self):
    msg = SimpleMessage()
    client = self.__GetFakeClient()
    self.assertEqual('{}', client.SerializeMessage(msg))
    with client.IncludeFields(('field',)):
      self.assertEqual('{"field": null}', client.SerializeMessage(msg))


if __name__ == '__main__':
  googletest.main()
