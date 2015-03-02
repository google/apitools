#!/usr/bin/env python
"""Test gen_client against all the APIs we use regularly."""

import contextlib
import logging
import os
import shutil
import subprocess
import sys
import tempfile


import unittest2

_API_LIST = [
    'drive.v2',
    'bigquery.v2',
    'compute.v1',
    'storage.v1',
]


@contextlib.contextmanager
def TempDir():
  original_dir = os.getcwd()
  path = tempfile.mkdtemp()
  try:
    os.chdir(path)
    yield path
  finally:
    os.chdir(original_dir)
    shutil.rmtree(path)


class ClientGenerationTest(unittest2.TestCase):

  def setUp(self):
    super(ClientGenerationTest, self).setUp()
    self.gen_client_binary = 'gen_client'

  def testGeneration(self):
    if sys.version_info < (2, 7):
      # TODO(craigcitro): Make apitools codegen support python 2.6.
      # Maybe.
      #
      # unittest in 2.6 doesn't have skipIf.
      return
    for api in _API_LIST:
      with TempDir():
        args = [
            self.gen_client_binary,
            '--client_id=12345',
            '--client_secret=67890',
            '--discovery_url=%s' % api,
            '--outdir=generated',
            '--overwrite',
            'client',
        ]
        logging.info(
            'Testing API %s with command line: %s', api, ' '.join(args))
        retcode = subprocess.call(args)
        if retcode == 128:
          logging.error('Failed to fetch discovery doc, continuing.')
          continue
        self.assertEqual(0, retcode)

        with tempfile.NamedTemporaryFile() as out:
          cmdline_args = [
              os.path.join('generated', api.replace('.', '_') + '.py'),
              'help',
          ]
          retcode = subprocess.call(cmdline_args, stdout=out)
        # appcommands returns 1 on help
        self.assertEqual(1, retcode)


if __name__ == '__main__':
  unittest2.main()
