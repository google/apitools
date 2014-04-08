#!/usr/bin/env python


import base64
import json

from protorpc import messages

from google.apputils import basetest as googletest
from apitools.base.py import encoding


class SimpleMessage(messages.Message):
  field = messages.StringField(1)
  repfield = messages.StringField(2, repeated=True)


class BytesMessage(messages.Message):
  field = messages.BytesField(1)
  repfield = messages.BytesField(2, repeated=True)


@encoding.MapUnrecognizedFields('additional_properties')
class AdditionalPropertiesMessage(messages.Message):

  class AdditionalProperty(messages.Message):
    key = messages.StringField(1)
    value = messages.StringField(2)

  additional_properties = messages.MessageField(
      AdditionalProperty, 1, repeated=True)


class CompoundPropertyType(messages.Message):
  index = messages.IntegerField(1)
  name = messages.StringField(2)


@encoding.MapUnrecognizedFields('additional_properties')
class AdditionalMessagePropertiesMessage(messages.Message):
  class AdditionalProperty(messages.Message):
    key = messages.StringField(1)
    value = messages.MessageField(CompoundPropertyType, 2)

  additional_properties = messages.MessageField(
      'AdditionalProperty', 1, repeated=True)


class HasNestedMessage(messages.Message):
  nested = messages.MessageField(AdditionalPropertiesMessage, 1)


class EncodingTest(googletest.TestCase):

  def testCopyProtoMessage(self):
    msg = SimpleMessage(field='abc')
    new_msg = encoding.CopyProtoMessage(msg)
    self.assertEqual(msg.field, new_msg.field)
    msg.field = 'def'
    self.assertNotEqual(msg.field, new_msg.field)

  def testBytesEncoding(self):
    b64_str = 'AAc+'
    b64_msg = '{"field": "%s"}' % b64_str
    urlsafe_b64_str = 'AAc-'
    urlsafe_b64_msg = '{"field": "%s"}' % urlsafe_b64_str
    data = base64.b64decode(b64_str)
    msg = BytesMessage(field=data)
    self.assertEqual(msg, encoding.JsonToMessage(BytesMessage, urlsafe_b64_msg))
    self.assertEqual(msg, encoding.JsonToMessage(BytesMessage, b64_msg))
    self.assertEqual(urlsafe_b64_msg, encoding.MessageToJson(msg))

    enc_rep_msg = '{"repfield": ["%(b)s", "%(b)s"]}' % {
        'b': urlsafe_b64_str,
        }
    rep_msg = BytesMessage(repfield=[data, data])
    self.assertEqual(rep_msg, encoding.JsonToMessage(BytesMessage, enc_rep_msg))
    self.assertEqual(enc_rep_msg, encoding.MessageToJson(rep_msg))

  def testIncludeFields(self):
    msg = SimpleMessage()
    self.assertEqual('{}', encoding.MessageToJson(msg))
    self.assertEqual(
        '{"field": null}',
        encoding.MessageToJson(msg, include_fields=['field']))
    self.assertEqual(
        '{"repfield": null}',
        encoding.MessageToJson(msg, include_fields=['repfield']))

  def testAdditionalPropertyMapping(self):
    msg = AdditionalPropertiesMessage()
    msg.additional_properties = [
        AdditionalPropertiesMessage.AdditionalProperty(
            key='key_one', value='value_one'),
        AdditionalPropertiesMessage.AdditionalProperty(
            key='key_two', value='value_two'),
        ]

    encoded_msg = encoding.MessageToJson(msg)
    self.assertEqual(
        {'key_one': 'value_one', 'key_two': 'value_two'},
        json.loads(encoded_msg))

    new_msg = encoding.JsonToMessage(type(msg), encoded_msg)
    self.assertEqual(
        set(('key_one', 'key_two')),
        set([x.key for x in new_msg.additional_properties]))
    self.assertIsNot(msg, new_msg)

    new_msg.additional_properties.pop()
    self.assertEqual(1, len(new_msg.additional_properties))
    self.assertEqual(2, len(msg.additional_properties))

  def testAdditionalMessageProperties(self):
    json_msg = '{"input": {"index": 0, "name": "output"}}'
    result = encoding.JsonToMessage(
        AdditionalMessagePropertiesMessage, json_msg)
    self.assertEqual(1, len(result.additional_properties))
    self.assertEqual(0, result.additional_properties[0].value.index)

  def testNestedFieldMapping(self):
    nested_msg = AdditionalPropertiesMessage()
    nested_msg.additional_properties = [
        AdditionalPropertiesMessage.AdditionalProperty(
            key='key_one', value='value_one'),
        AdditionalPropertiesMessage.AdditionalProperty(
            key='key_two', value='value_two'),
        ]
    msg = HasNestedMessage(nested=nested_msg)

    encoded_msg = encoding.MessageToJson(msg)
    self.assertEqual(
        {'nested': {'key_one': 'value_one', 'key_two': 'value_two'}},
        json.loads(encoded_msg))

    new_msg = encoding.JsonToMessage(type(msg), encoded_msg)
    self.assertEqual(
        set(('key_one', 'key_two')),
        set([x.key for x in new_msg.nested.additional_properties]))

    new_msg.nested.additional_properties.pop()
    self.assertEqual(1, len(new_msg.nested.additional_properties))
    self.assertEqual(2, len(msg.nested.additional_properties))


if __name__ == '__main__':
  googletest.main()
