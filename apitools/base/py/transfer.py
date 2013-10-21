#!/usr/bin/env python
"""Upload and download support for apitools."""

import collections
import httplib
import io
import json
import mimetypes
import os
import threading

from apitools.base.py import exceptions

__all__ = [
    'Download',
    'Upload',
    ]

# pylint: disable=slots-on-old-class


# Note: currently the order of fields here is important, since we want
# to be able to pass in the result from httplib2.request.
class _HttpResponse(collections.namedtuple(
    '_HttpResponse', ['info', 'content'])):
  __slots__ = ()

  def __len__(self):
    return int(self.info.get('content-length', len(self.content)))

  @property
  def status_code(self):
    return int(self.info['status'])


class _TransferSerializationData(collections.namedtuple(
    '_TransferSerializationData', ['progress', 'total_size', 'url'])):
  __slots__ = ()

  def ToJson(self):
    return json.dumps(self._asdict())

  @classmethod
  def FromJson(cls, json_data):
    data = json.loads(json_data)
    data_keys = set(('progress', 'url'))
    if data_keys > set(cls._fields):
      raise exceptions.InvalidDataError(
          'Invalid keys for Transfer: %s' % data_keys)
    return cls._make(data[field] for field in cls._fields)


class _Transfer(object):
  """Generic bits common to Uploads and Downloads."""

  def __init__(self, stream, close_stream=False, chunksize=None):
    self.__close_stream = close_stream
    self.__http = None
    self.__stream = stream
    self.__total_size = None
    self.__url = None

    self._progress = 0

    self.chunksize = chunksize or 1048576L

  def __repr__(self):
    return str(self)

  @property
  def _type_name(self):
    return type(self).__name__

  @property
  def url(self):
    return self.__url

  @url.setter
  def url(self, value):
    if self.url is not None:
      raise exceptions.ConfigurationValueError(
          'Cannot set download url on initialized %s', self._type_name)
    self.__url = value

  @property
  def http(self):
    return self.__http

  @http.setter
  def http(self, value):
    if self.http is not None:
      raise exceptions.ConfigurationValueError(
          'Cannot set http on initialized %s', self._type_name)
    self.__http = value

  @property
  def total_size(self):
    return self.__total_size

  @total_size.setter
  def total_size(self, value):
    if self.total_size is not None:
      raise exceptions.ConfigurationValueError(
          'Cannot set total_size on initialized %s', self._type_name)
    self.__total_size = value

  @property
  def initialized(self):
    return self.url is not None and self.http is not None

  def EnsureInitialized(self):
    if not self.initialized:
      raise exceptions.TransferInvalidError(
          'Cannot use uninitialized %s', self._type_name)

  @property
  def close_stream(self):
    return self.__close_stream

  @property
  def stream(self):
    return self.__stream

  @property
  def serialization_data(self):
    self.EnsureInitialized()
    return {
        'progress': self._progress,
        'total_size': self.total_size,
        'url': self.url,
        }

  def __del__(self):
    if self.__close_stream:
      self.__stream.close()


class Download(_Transfer):
  """Data for a single download.

  Public attributes:
    chunksize: default chunksize to use for transfers.
  """

  def __str__(self):
    return 'Download for url %s' % self.url

  @classmethod
  def FromFile(cls, filename, overwrite=False):
    """Create a new download object from a filename."""
    path = os.path.expanduser(filename)
    if os.path.exists(path) and not overwrite:
      raise exceptions.InvalidUserInputError(
          'File %s exists and overwrite not specified' % path)
    return cls(open(path, 'wb'), close_stream=True)

  @classmethod
  def FromStream(cls, stream):
    """Create a new Download object from a stream."""
    return cls(stream)

  @classmethod
  def FromData(cls, stream, json_data, http=None):
    """Create a new Download object from a stream and serialized data."""
    download = cls.FromStream(stream)
    info = _TransferSerializationData.FromJson(json_data)
    download._progress = info.progress  # pylint: disable=protected-access
    download.http = http
    download.total_size = info.total_size
    download.url = info.url
    return download

  def __SetTotal(self, info):
    if self.total_size is None and 'content-range' in info:
      _, _, total = info['content-range'].rpartition('/')
      if total != '*':
        self.total_size = int(total)

  def __GetChunk(self, start, end=None, chunksize=None):
    """Retrieve a chunk, and return the full response."""
    self.EnsureInitialized()
    start = max(start, 0)
    chunksize = chunksize or self.chunksize
    if end and end < 0:
      # Requesting range from end
      start = ''
      end = abs(end)
    else:
      max_end = start + chunksize - 1
      end = min(end or max_end, max_end)
      if end < start:
        raise exceptions.TransferInvalidError(
            'Range requested with end[%s] < start[%s]' % (end, start))
    headers = {'Range': 'bytes=%s-%d' % (start, end)}
    # TODO(craigcitro): Add support for retries.
    response = _HttpResponse(*self.http.request(self.url, headers=headers))
    self.__SetTotal(response.info)
    if response.status_code not in (httplib.PARTIAL_CONTENT,
                                    httplib.REQUESTED_RANGE_NOT_SATISFIABLE):
      raise exceptions.TransferInvalidError(response.content)
    if response.status_code == httplib.PARTIAL_CONTENT:
      self.stream.write(response.content)
    return response

  def GetRange(self, start, end, chunksize=None, exact_range=True):
    """Retrieve a given byte range from this download."""
    progress = start
    chunksize = chunksize or self.chunksize
    while progress < end:
      response = self.__GetChunk(progress, end=end)
      if (response.status_code == httplib.REQUESTED_RANGE_NOT_SATISFIABLE and
          exact_range):
        raise exceptions.TransferInvalidError(
            'Could not fetch all requested bytes: ended at %d' % progress)
      progress += len(response)

  def __ExecuteCallback(self, callback, response):
    # TODO(craigcitro): Push these into a queue.
    if callback is not None:
      threading.Thread(target=callback, args=(response, self)).start()

  def StreamInChunks(self, callback=None, finish_callback=None, chunksize=None,
                     end=None):
    """Stream the entire download."""

    def ArgPrinter(response, unused_download):
      print 'Received bytes %s' % response.info['content-range']

    def CompletePrinter(*unused_args):
      print 'Download complete'

    callback = callback or ArgPrinter
    finish_callback = finish_callback or CompletePrinter

    self.EnsureInitialized()
    while True:
      response = self.__GetChunk(self._progress, chunksize=chunksize, end=end)
      # TODO(craigcitro): Consider whether this update and writing
      # the response to self.stream need to happen as a transaction.
      self._progress += len(response)
      if response.status_code == httplib.REQUESTED_RANGE_NOT_SATISFIABLE:
        break
      # Callback with the new chunk.
      self.__ExecuteCallback(callback, response)
      # Handle range requests
      # TODO(craigcitro): Exert python mastery over the known universe by
      # cleaning up this hackish implementation.
      if end:
        if end < 0:
          if(self._progress) >= abs(end):
            break
        elif self._progress >= end:
          break
    self.__ExecuteCallback(finish_callback, response)


class Upload(_Transfer):
  """Data for a single Upload.

  Fields:
    stream: The stream to upload.
    mime_type: MIME type of the upload.
    mime_encoding: (optional) Encoding for the upload. Currently unused.
    size_hint: (optional) Total upload size for the stream.
    close_stream: (default: False) Whether or not we should close the
        stream when finished with the upload.
  """

  def __init__(self, stream, mime_type, mime_encoding=None, size_hint=None,
               close_stream=False, chunksize=None):
    super(Upload, self).__init__(stream, close_stream=close_stream,
                                 chunksize=chunksize)
    self.__mime_type = mime_type
    self.__mime_encoding = mime_encoding

    self.total_size = size_hint

  @property
  def mime_type(self):
    return self.__mime_type

  @property
  def mime_encoding(self):
    return self.__mime_encoding

  def __str__(self):
    size = self.total_size or '<unknown>'
    return 'Upload of size %s and mime type %s' % (size, self.mime_type)

  @classmethod
  def FromFile(cls, filename, mime_type=None, mime_encoding=None):
    """Create a new Upload object from a filename."""
    path = os.path.expanduser(filename)
    if not os.path.exists(path):
      raise exceptions.NotFoundError('Could not find file %s' % path)
    if not mime_type:
      mime_type, mime_encoding = mimetypes.guess_type(path)
      if mime_type is None:
        raise exceptions.InvalidUserInputError(
            'Could not guess mime type for %s' % path)
    size = os.stat(path).st_size
    return cls(open(path, 'rb'), mime_type, mime_encoding=mime_encoding,
               size_hint=size, close_stream=True)

  @classmethod
  def FromStream(cls, stream, mime_type, mime_encoding=None):
    """Create a new Upload object from a seekable stream."""
    if isinstance(stream, io.IOBase) and not stream.seekable():
      raise exceptions.InvalidUserInputError('Stream not seekable')
    # TODO(craigcitro): Consider checking the full interface we need
    # for a stream here.
    if mime_type is None:
      raise exceptions.InvalidUserInputError(
          'No mime_type specified for stream')
    stream.seek(0, io.SEEK_END)
    size = stream.tell()
    return cls(stream, mime_type, mime_encoding=mime_encoding,
               size_hint=size, close_stream=False)
