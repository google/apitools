#!/usr/bin/env python
"""Exceptions for generated client libraries."""

from apiclient import errors as apiclient_errors


class Error(Exception):
  """Base class for all exceptions."""


class TypecheckError(Error, TypeError):
  """An object of an incorrect type is provided."""


class NotFoundError(Error):
  """A specified resource could not be found."""


class UserError(Error):
  """Base class for errors related to user input."""


class InvalidDataError(Error):
  """Base class for any invalid data error."""


class CommunicationError(Error):
  """Any communication error talking to an API server."""


class HttpError(CommunicationError, apiclient_errors.HttpError):
  """Error making a request, with a code."""

  def __init__(self, *args, **kwds):
    CommunicationError.__init__(self)  # pylint: disable=non-parent-init-called
    apiclient_errors.HttpError.__init__(self, *args, **kwds)

  @classmethod
  def FromApiclientError(cls, e):
    if not isinstance(e, apiclient_errors.HttpError):
      raise TypecheckError('Invalid error type: %s', type(e).__name__)  # pylint: disable=nonstandard-exception
    return cls(e.resp, e.content, uri=e.uri)


class InvalidUserInputError(InvalidDataError):
  """User-provided input is invalid."""


class InvalidDataFromServerError(InvalidDataError, CommunicationError):
  """Data received from the server is malformed."""


class ConfigurationError(Error):
  """Base class for configuration errors."""


class GeneratedClientError(Error):
  """The generated client configuration is invalid."""


class ConfigurationValueError(UserError):
  """Some part of the user-specified client configuration is invalid."""


class ResourceUnavailableError(Error):
  """User requested an unavailable resource."""


class CredentialsError(Error):
  """Errors related to invalid credentials."""


class TransferError(CommunicationError):
  """Errors related to transfers."""


class TransferInvalidError(TransferError):
  """The given transfer is invalid."""
