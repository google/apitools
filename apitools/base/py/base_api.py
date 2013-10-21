#!/usr/bin/env python
"""Base class for api services."""

import contextlib
import email.mime.multipart as mime_multipart
import email.mime.nonmultipart as mime_nonmultipart
import httplib
import logging
import types
import urllib
import urlparse


from apiclient import errors as apiclient_errors
from apiclient import http as apiclient_http
from apiclient import mimeparse
import apiclient.model
import httplib2
from protorpc import message_types
from protorpc import messages

import gflags as flags

from apitools.base.py import credentials_lib
from apitools.base.py import encoding
from apitools.base.py import exceptions

FLAGS = flags.FLAGS

# TODO(craigcitro): Remove this once we quiet the spurious logging in
# oauth2client (or drop oauth2client).
logging.getLogger('oauth2client.util').setLevel(logging.ERROR)


class ApiUploadInfo(messages.Message):
  """Media upload information for a method.

  Fields:
    accept: (repeated) MIME Media Ranges for acceptable media uploads
        to this method.
    max_size: Maximum size of a media upload, such as "1MB" or "3TB".
    resumable_path: Path to use for resumable uploads.
    resumable_multipart: (boolean) Whether or not the resumable endpoint
        supports multipart uploads.
    simple_path: Path to use for simple uploads.
    simple_multipart: (boolean) Whether or not the simple endpoint
        supports multipart uploads.
  """
  accept = messages.StringField(1, repeated=True)
  max_size = messages.IntegerField(2)
  resumable_path = messages.StringField(3)
  resumable_multipart = messages.BooleanField(4)
  simple_path = messages.StringField(5)
  simple_multipart = messages.BooleanField(6)


class ApiMethodInfo(messages.Message):
  """Configuration info for an API method.

  All fields are strings unless noted otherwise.

  Fields:
    relative_path: Relative path for this method.
    method_id: ID for this method.
    http_method: HTTP verb to use for this method.
    path_params: (repeated) path parameters for this method.
    query_params: (repeated) query parameters for this method.
    ordered_params: (repeated) ordered list of parameters for
        this method.
    description: description of this method.
    request_type_name: name of the request type.
    response_type_name: name of the response type.
    request_field: if not null, the field to pass as the body
        of this POST request. may also be the REQUEST_IS_BODY
        value below to indicate the whole message is the body.
    upload_config: (ApiUploadInfo) Information about the upload
        configuration supported by this method.
    supports_download: (boolean) If True, this method supports
        downloading the request via the `alt=media` query
        parameter.
  """

  relative_path = messages.StringField(1)
  method_id = messages.StringField(2)
  http_method = messages.StringField(3)
  path_params = messages.StringField(4, repeated=True)
  query_params = messages.StringField(5, repeated=True)
  ordered_params = messages.StringField(6, repeated=True)
  description = messages.StringField(7)
  request_type_name = messages.StringField(8)
  response_type_name = messages.StringField(9)
  request_field = messages.StringField(10, default='')
  upload_config = messages.MessageField(ApiUploadInfo, 11)
  supports_download = messages.BooleanField(12, default=False)
REQUEST_IS_BODY = '<request>'


def _LoadClass(name, messages_module):
  if name.startswith('message_types.'):
    _, _, classname = name.partition('.')
    return getattr(message_types, classname)
  elif '.' not in name:
    return getattr(messages_module, name)
  else:
    raise exceptions.GeneratedClientError('Unknown class %s' % name)


def _RequireClassAttrs(obj, attrs):
  for attr in attrs:
    attr_name = attr.upper()
    if not hasattr(obj, '%s' % attr_name) or not getattr(obj, attr_name):
      msg = 'No %s specified for object of class %s.' % (
          attr_name, type(obj).__name__)
      raise exceptions.GeneratedClientError(msg)


def _Typecheck(arg, arg_type, msg=None):
  if not isinstance(arg, arg_type):
    if msg is None:
      if isinstance(arg_type, tuple):
        msg = 'Type of arg is "%s", not one of %r' % (type(arg), arg_type)
      else:
        msg = 'Type of arg is "%s", not "%s"' % (type(arg), arg_type)
      raise exceptions.TypecheckError(msg)
  return arg


def NormalizeApiEndpoint(api_endpoint):
  if not api_endpoint.endswith('/'):
    api_endpoint += '/'
  return api_endpoint


class BaseApiModel(apiclient.model.JsonModel):
  """Base model for generated clients."""
  alt_param = None

  def __init__(self, request_type, response_type, log_request, log_response,
               *args, **kwds):
    self.__request_type = request_type
    self.__response_type = response_type
    self.__log_request = log_request
    self.__log_response = log_response
    # TODO(craigcitro): Remove this field when we switch to proto2.
    self.include_fields = None
    super(BaseApiModel, self).__init__(*args, **kwds)

  # TODO(craigcitro): Delete these methods once we don't have to
  # support both variations of apiclient.
  @staticmethod
  def _GetDumpFlag():
    if hasattr(FLAGS, 'dump_request_response'):
      return FLAGS.dump_request_response
    else:
      return apiclient.model.dump_request_response

  @staticmethod
  def _SetDumpFlag(value):
    if hasattr(FLAGS, 'dump_request_response'):
      FLAGS.dump_request_response = value
    else:
      apiclient.model.dump_request_response = value

  def _log_request(self, *args, **kwds):
    old_value = self._GetDumpFlag()
    if self.__log_request:
      self._SetDumpFlag(True)
    super(BaseApiModel, self)._log_request(*args, **kwds)
    self._SetDumpFlag(old_value)

  def _log_response(self, *args, **kwds):
    old_value = self._GetDumpFlag()
    if self.__log_response:
      self._SetDumpFlag(True)
    super(BaseApiModel, self)._log_response(*args, **kwds)
    self._SetDumpFlag(old_value)

  def serialize(self, body_value):
    """Serialize a message (which might involve ProtoRPC messages)."""
    _Typecheck(body_value, self.__request_type)
    return encoding.MessageToJson(
        body_value, include_fields=self.include_fields)

  def deserialize(self, content):
    """Deserialize a message (which might involve ProtoRPC messages)."""
    try:
      message = encoding.JsonToMessage(self.__response_type, content)
    except (exceptions.InvalidDataFromServerError,
            messages.ValidationError) as e:
      raise exceptions.InvalidDataFromServerError(
          'Error decoding response "%s" as type %s: %s' % (
              content, self.__response_type, e))
    return message


class BaseMediaDownloadModel(BaseApiModel):
  """Base class for requests that return media in the response."""
  alt_param = 'media'

  def deserialize(self, content):
    return content

  @property
  def no_content_response(self):
    return ''


class BaseApiClient(object):
  """Base class for client libraries."""
  MESSAGES_MODULE = None

  _API_KEY = ''
  _CLIENT_ID = ''
  _CLIENT_SECRET = ''
  _PACKAGE = ''
  _SCOPES = []
  _USER_AGENT = ''

  def __init__(self, url, credentials=None, get_credentials=True, http=None,
               model=None, log_request=False, log_response=False,
               default_global_params=None):
    _RequireClassAttrs(self, (
        '_package', '_scopes', '_client_id', '_client_secret',
        'messages_module'))
    if default_global_params is not None:
      _Typecheck(default_global_params, self.params_type)
    self.__default_global_params = default_global_params
    self.log_request = log_request
    self.log_response = log_response
    self._base_model_class = model or BaseApiModel
    self._url = url
    self._credentials = credentials
    if get_credentials and not credentials:
      # TODO(craigcitro): It's a bit dangerous to pass this
      # still-half-initialized self into this method, but we might need
      # to set attributes on it associated with our credentials.
      # Consider another way around this (maybe a callback?) and whether
      # or not it's worth it.
      self._credentials = credentials_lib.GetCredentials(
          self._PACKAGE, self._SCOPES, self._CLIENT_ID, self._CLIENT_SECRET,
          self._USER_AGENT, api_key=self._API_KEY, client=self)
    self._http = http or httplib2.Http()
    # Note that "no credentials" is totally possible.
    if self._credentials is not None:
      self._http = self._credentials.authorize(self._http)
    # TODO(craigcitro): Remove this field when we switch to proto2.
    self.__include_fields = None

  @property
  def base_model_class(self):
    return self._base_model_class

  @property
  def http(self):
    return self._http

  @property
  def url(self):
    return self._url

  @classmethod
  def GetScopes(cls):
    return cls._SCOPES

  @property
  def params_type(self):
    return _LoadClass('StandardQueryParameters', self.MESSAGES_MODULE)

  @property
  def _default_global_params(self):
    if self.__default_global_params is None:
      self.__default_global_params = self.params_type()
    return self.__default_global_params

  def AddGlobalParam(self, name, value):
    params = self._default_global_params
    setattr(params, name, value)

  @property
  def global_params(self):
    return encoding.CopyProtoMessage(self._default_global_params)

  def ConfigureModel(self, model):
    model.include_fields = self.__include_fields

  @contextlib.contextmanager
  def IncludeFields(self, include_fields):
    self.__include_fields = include_fields
    yield
    self.__include_fields = None


class BaseApiService(object):
  """Base class for generated API services."""

  def __init__(self, client):
    self.__client = client

  @property
  def _client(self):
    return self.__client

  def __CombineGlobalParams(self, global_params, default_params):
    _Typecheck(global_params, (types.NoneType, self.__client.params_type))
    result = self.__client.params_type()
    global_params = global_params or self.__client.params_type()
    for field in result.all_fields():
      value = (global_params.get_assigned_value(field.name) or
               default_params.get_assigned_value(field.name))
      if value not in (None, [], ()):
        setattr(result, field.name, value)
    return result

  def __ConstructQueryParams(self, query_params, request, global_params):
    query_info = dict((field.name, getattr(global_params, field.name))
                      for field in self.__client.params_type.all_fields())
    query_info.update(
        (param, getattr(request, param, None)) for param in query_params)
    query_info = dict((k, v) for k, v in query_info.iteritems()
                      if v is not None)
    return query_info

  def __ConstructPathParams(self, method_config, request):
    path = method_config.relative_path
    path_params = {}
    for param in method_config.path_params:
      param_template = '{%s}' % param
      if param_template not in path:
        raise exceptions.InvalidUserInputError(
            'Missing path parameter %s' % param)
      try:
        # TODO(craigcitro): Do we want to support some sophisticated
        # mapping here?
        value = getattr(request, param)
      except AttributeError:
        raise exceptions.InvalidUserInputError(
            'Request missing required parameter %s' % param)
      if value is None:
        raise exceptions.InvalidUserInputError(
            'Request missing required parameter %s' % param)
      try:
        path = path.replace(param_template,
                            urllib.quote(value.encode('utf_8'), ''))
      except TypeError as e:
        raise exceptions.InvalidUserInputError(
            'Error setting required parameter %s to value %s: %s' % (
                param, value, e))
      path_params[param] = value
    return path, path_params

  def __GetUploadStrategy(self, upload, upload_config):
    # Choose a protocol: We generally prefer resumable, unless the
    # server only supports simple, or if we have a small transfer.
    strategy = 'resumable'
    if upload_config.simple_path:
      if not upload_config.resumable_path:
        strategy = 'simple'
      elif (upload.total_size is not None and
            upload.total_size < 4 * 1 << 20 and
            upload_config.simple_multipart):
        strategy = 'simple'
    return strategy

  def __GetUploadParams(self, upload, upload_config, body_value):
    strategy = self.__GetUploadStrategy(upload, upload_config)
    params = {}
    if strategy == 'simple':
      params['uploadType'] = 'multipart' if body_value else 'media'
    else:
      params['uploadType'] = 'resumable'
    return params

  def __GetUploadPath(self, upload, upload_config):
    # In theory, we should use the resumable path in the case that the
    # strategy is 'resumable'. However, apiclient is designed around a
    # flow that pushes the original body in the first request, and
    # pumps the media bytes through on successive requests.
    _ = self.__GetUploadStrategy(upload, upload_config)
    return upload_config.simple_path

  def __SimpleMediaBody(self, upload, headers, body_value):
    # Rewrite the body. (This section follows apiclient.discovery.)
    upload.stream.seek(0)
    if not body_value:
      headers['content-type'] = upload.mime_type
      body_value = upload.stream.read()
    else:
      # This is a multipart/related upload.
      msg_root = mime_multipart.MIMEMultipart('related')
      # msg_root should not write out it's own headers
      setattr(msg_root, '_write_headers', lambda self: None)

      # attach the body as one part
      msg = mime_nonmultipart.MIMENonMultipart(
          *headers['content-type'].split('/'))
      msg.set_payload(body_value)
      msg_root.attach(msg)

      # attach the media as the second part
      msg = mime_nonmultipart.MIMENonMultipart(
          *upload.mime_type.split('/'))
      msg['Content-Transfer-Encoding'] = 'binary'
      msg.set_payload(upload.stream.read())
      msg_root.attach(msg)

      body_value = msg_root.as_string()
      multipart_boundary = msg_root.get_boundary()
      headers['content-type'] = ('multipart/related; '
                                 'boundary=%r') % multipart_boundary
    return headers, body_value

  def __CreateMediaUpload(self, upload, upload_config, headers, body_value):
    # Validate total_size vs. max_size
    if (upload.total_size and upload_config.max_size and
        upload.total_size > upload_config.max_size):
      raise exceptions.InvalidUserInputError(
          'Upload too big: %s larger than max size %s' % (
              upload.total_size, upload_config.max_size))
    # Validate mime type
    if not mimeparse.best_match(upload_config.accept, upload.mime_type):
      raise exceptions.InvalidUserInputError(
          'MIME type %s does not match any accepted MIME ranges %s' % (
              upload.mime_type, upload_config.accept))
    strategy = self.__GetUploadStrategy(upload, upload_config)
    # Create a MediaIoBaseUpload
    if strategy == 'simple':
      media_upload = False
      headers, body_value = self.__SimpleMediaBody(upload, headers, body_value)
    elif strategy == 'resumable':
      # Don't need to set a body value in this case, since the
      # HttpRequest is in charge of uploading it.
      media_upload = apiclient_http.MediaIoBaseUpload(
          upload.stream, upload.mime_type, resumable=True)
    return media_upload, headers, body_value

  def __IsRetryable(self, exc):
    status = int(exc.resp.get('status'))
    # 308 doesn't have a name in httplib.
    retryable_status = status in (
        httplib.MOVED_PERMANENTLY, httplib.FOUND, httplib.SEE_OTHER,
        httplib.TEMPORARY_REDIRECT, 308)
    return retryable_status and 'location' in exc.resp

  def __ExecuteRequest(self, request, url):
    try:
      return request.execute()
    except apiclient_errors.HttpError as e:
      if self.__IsRetryable(e):
        logging.info('Got redirect for %s', request.uri)
        request.uri = e.resp['location']
        logging.info('Redirecting to %s', request.uri)
        return self.__ExecuteRequest(request, request.uri)
      e.content = e.content.decode('ascii', 'replace')
      logging.error('Error making request to "%s": "%s", "%s"',
                    url, e, e.content)
      raise exceptions.HttpError.FromApiclientError(e)
    except httplib2.HttpLib2Error as e:
      raise exceptions.CommunicationError(
          'Communication error making request to "%s": "%s"' % (url, e))

  def _RunMethod(self, method_config, request, global_params=None,
                 upload=None, upload_config=None, download=None):
    """Call this method with request."""
    global_params = self.__CombineGlobalParams(
        global_params, self.__client.global_params)
    request_type = _LoadClass(
        method_config.request_type_name, self.__client.MESSAGES_MODULE)
    response_type = _LoadClass(
        method_config.response_type_name, self.__client.MESSAGES_MODULE)
    _Typecheck(request, request_type)
    if self.__client.log_request:
      logging.info('Request of type %s: %s',
                   method_config.request_type_name, request)
    body_type = None
    if method_config.request_field == REQUEST_IS_BODY:
      body_type = request_type
    elif method_config.request_field:
      body_field = request_type.field_by_name(method_config.request_field)
      _Typecheck(body_field, messages.MessageField)
      body_type = body_field.type
    # TODO(craigcitro): Make the http and model objects configurable.
    request_builder = apiclient_http.HttpRequest
    model_class = self.__client.base_model_class
    if download:
      model_class = BaseMediaDownloadModel
    api_model = model_class(
        body_type, response_type,
        self.__client.log_request, self.__client.log_response)
    self.__client.ConfigureModel(api_model)

    body_value = None
    if method_config.request_field == REQUEST_IS_BODY:
      body_value = request
    elif method_config.request_field:
      body_value = getattr(request, method_config.request_field)

    query_params = self.__ConstructQueryParams(
        method_config.query_params, request, global_params)
    if upload:
      query_params.update(self.__GetUploadParams(
          upload, upload_config, body_value))
      method_config.relative_path = self.__GetUploadPath(upload, upload_config)
    relative_path, path_params = self.__ConstructPathParams(
        method_config, request)

    # Note that api_model.request side-effects the headers, so must
    # be threaded through.
    headers = {}
    headers, path_params, query, body = api_model.request(
        headers, path_params, query_params, body_value)

    resumable = False
    if upload:
      resumable, headers, body = self.__CreateMediaUpload(
          upload, upload_config, headers, body)

    url = urlparse.urljoin(self.__client.url, ''.join((relative_path, query)))
    if self.__client.log_request:
      logging.info('%s %s', method_config.http_method, url)
    request = request_builder(
        self.__client.http,
        api_model.response,
        url,
        method=method_config.http_method,
        body=body,
        headers=headers,
        methodId=method_config.method_id,
        resumable=resumable)

    # If we're downloading media, we want to just get the new URL and
    # hand it back to the download object.
    if download:
      try:
        request.http.request(
            uri=str(request.uri), method='GET', headers=request.headers,
            body='', redirections=0)
        # TODO(craigcitro): Confirm that this is invalid.
        raise exceptions.InvalidDataFromServerError(
            'No redirect received for media download')
      except httplib2.RedirectLimit as e:
        download.url = e.response['location']
        download.http = request.http
      return

    response = self.__ExecuteRequest(request, url)
    if self.__client.log_response:
      logging.info('Response of type %s: %s',
                   method_config.response_type_name, response)
    return response
