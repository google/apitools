#!/usr/bin/env python
"""Common code for converting proto to other formats, such as JSON."""

import base64
import json


from protorpc import messages
from protorpc import protojson

from apitools.base.py import exceptions

__all__ = [
    'CopyProtoMessage',
    'JsonToMessage',
    'MessageToJson',
    'DictToMessage',
    'MessageToDict',
    ]


# TODO(craigcitro): Delete this function with the switch to proto2.
def CopyProtoMessage(message):
  codec = protojson.ProtoJson()
  return codec.decode_message(type(message), codec.encode_message(message))


# XXX json.dumps(body_value, cls=ApiJsonEncoder)
def MessageToJson(message, include_fields=None):
  """Convert the given message to JSON."""
  result = _ProtoJsonApilib.Get().encode_message(message)
  return _IncludeFields(result, message, include_fields)


def JsonToMessage(message_type, message):
  """Convert the given JSON to a message of type message_type."""
  return _ProtoJsonApilib.Get().decode_message(message_type, message)


# TODO(craigcitro): Do this directly, instead of via JSON.
def DictToMessage(d, message_type):
  """Convert the given dictionary to a message of type message_type."""
  return JsonToMessage(message_type, json.dumps(d))


def MessageToDict(message):
  """Convert the given message to a dictionary."""
  return json.loads(MessageToJson(message))


def _IncludeFields(encoded_message, message, include_fields):
  """Add the requested fields to the encoded message."""
  if include_fields is None:
    return encoded_message
  result = json.loads(encoded_message)
  for field_name in include_fields:
    try:
      message.field_by_name(field_name)
    except KeyError:
      raise exceptions.InvalidDataError(
          'No field named %s in message of type %s' % (
              field_name, type(message)))
    result[field_name] = None
  return json.dumps(result)


class _ProtoJsonApilib(protojson.ProtoJson):
  """JSON encoder used by apitools clients."""
  _INSTANCE = None

  @classmethod
  def Get(cls):
    if cls._INSTANCE is None:
      cls._INSTANCE = cls()
    return cls._INSTANCE

  def decode_message(self, message_type, encoded_message):  # pylint: disable=invalid-name
    result = super(_ProtoJsonApilib, self).decode_message(
        message_type, encoded_message)
    return _DecodeUnknownFields(result)

  def decode_field(self, field, value):
    """Decode the given value as JSON."""
    if isinstance(field, messages.BytesField):
      try:
        return base64.urlsafe_b64decode(str(value))
      except TypeError:
        pass
    field_value = super(_ProtoJsonApilib, self).decode_field(field, value)
    if isinstance(field, messages.MessageField):
      field_value = _DecodeUnknownFields(field_value)
    return field_value

  def encode_message(self, message):  # pylint: disable=invalid-name
    message = _EncodeUnknownFields(message)
    return super(_ProtoJsonApilib, self).encode_message(message)

  def encode_field(self, field, value):
    """Encode the given value as JSON."""
    if isinstance(field, messages.BytesField):
      try:
        if isinstance(field, messages.BytesField):
          if field.repeated:
            return [base64.urlsafe_b64encode(byte) for byte in value]
          else:
            return base64.urlsafe_b64encode(value)
      except TypeError:
        pass
    if isinstance(field, messages.MessageField):
      value = _EncodeUnknownFields(value)
    return super(_ProtoJsonApilib, self).encode_field(field, value)


# TODO(craigcitro): Storing this in a global is a bad idea, for all
# the usual reasons. In particular, if we plan to make base_api a
# shared file, we need to fix this.
_UNRECOGNIZED_FIELD_MAPPINGS = {}


def _DecodeUnknownFields(message):
  """Rewrite unknown fields in message into message.destination."""
  destination = _UNRECOGNIZED_FIELD_MAPPINGS.get(type(message))
  if destination is None:
    return message
  pair_field = message.field_by_name(destination)
  if not isinstance(pair_field, messages.MessageField):
    raise exceptions.InvalidDataFromServerError(
        'Unrecognized fields must be mapped to a compound '
        'message type.')
  pair_type = pair_field.message_type
  # TODO(craigcitro): Add more error checking around the pair
  # type being exactly what we suspect (field names, etc).
  new_values = []
  for unknown_field in message.all_unrecognized_fields():
    # TODO(craigcitro): Consider validating the variant if
    # the assignment below doesn't take care of it. It may
    # also be necessary to check it in the case that the
    # type has multiple encodings.
    value, _ = message.get_unrecognized_field_info(unknown_field)
    new_pair = pair_type(key=str(unknown_field), value=value)
    new_values.append(new_pair)
  setattr(message, destination, new_values)
  # We could probably get away with not setting this, but
  # why not clear it?
  setattr(message, '_Message__unrecognized_fields', {})
  return message


def _EncodeUnknownFields(message):
  """Remap unknown fields in message out of message.source."""
  source = _UNRECOGNIZED_FIELD_MAPPINGS.get(type(message))
  if source is None:
    return message
  result = CopyProtoMessage(message)
  pairs_field = message.field_by_name(source)
  if not isinstance(pairs_field, messages.MessageField):
    raise exceptions.InvalidUserInputError(
        'Invalid pairs field %s' % pairs_field)
  pairs_type = pairs_field.message_type
  value_variant = pairs_type.field_by_name('value').variant
  pairs = getattr(message, source)
  for pair in pairs:
    result.set_unrecognized_field(pair.key, pair.value, value_variant)
  setattr(result, source, [])
  return result


def MapUnrecognizedFields(field_name):
  """Register field_name as a container for unrecognized fields in message."""
  def Register(cls):
    _UNRECOGNIZED_FIELD_MAPPINGS[cls] = field_name
    return cls
  return Register
