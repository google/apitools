#!/usr/bin/env python
"""Assorted utilities shared between parts of apitools."""

import collections
import httplib
import os
import types
import urllib2

from apitools.base.py import exceptions

RETRYABLE_STATUS_CODES = (
    httplib.MOVED_PERMANENTLY,
    httplib.FOUND,
    httplib.SEE_OTHER,
    httplib.TEMPORARY_REDIRECT,
    # 308 doesn't have a name in httplib.
    308,
    )


def DetectGae():
  """Determine whether or not we're running on GAE.

  This is based on:
    https://developers.google.com/appengine/docs/python/#The_Environment

  Returns:
    True iff we're running on GAE.
  """
  server_software = os.environ.get('SERVER_SOFTWARE', '')
  return (server_software.startswith('Development/') or
          server_software.startswith('Google App Engine/'))


def DetectGce():
  """Determine whether or not we're running on GCE.

  This is based on:
    https://developers.google.com/compute/docs/instances#dmi

  Returns:
    True iff we're running on a GCE instance.
  """
  try:
    o = urllib2.urlopen('http://metadata.google.internal')
  except urllib2.URLError:
    return False
  return o.getcode() == httplib.OK


def NormalizeScopes(scope_spec):
  """Normalize scope_spec to a set of strings."""
  if isinstance(scope_spec, types.StringTypes):
    return set(scope_spec.split(' '))
  elif isinstance(scope_spec, collections.Iterable):
    return set(scope_spec)
  raise exceptions.TypecheckError(
      'NormalizeScopes expected string or iterable, found %s' % (
          type(scope_spec),))
