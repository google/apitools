"""Test gen_client against all the APIs we use regularly."""

import logging
import os
import subprocess
import tempfile

from apitools.gen import test_utils

import unittest2

_API_LIST = [
    'drive.v2',
    'bigquery.v2',
    'compute.v1',
    'storage.v1',
]


class ClientGenerationTest(unittest2.TestCase):

    def setUp(self):
        super(ClientGenerationTest, self).setUp()
        self.gen_client_binary = 'gen_client'

    @test_utils.RunOnlyOnPython27
    def testGeneration(self):
        for api in _API_LIST:
            with test_utils.TempDir(change_to=True):
                args = [
                    self.gen_client_binary,
                    '--client_id=12345',
                    '--client_secret=67890',
                    '--discovery_url=%s' % api,
                    '--outdir=generated',
                    '--overwrite',
                    'client',
                ]
                logging.info('Testing API %s with command line: %s',
                             api, ' '.join(args))
                retcode = subprocess.call(args)
                if retcode == 128:
                    logging.error('Failed to fetch discovery doc, continuing.')
                    continue
                self.assertEqual(0, retcode)

                with tempfile.NamedTemporaryFile() as out:
                    cmdline_args = [
                        os.path.join(
                            'generated', api.replace('.', '_') + '.py'),
                        'help',
                    ]
                    retcode = subprocess.call(cmdline_args, stdout=out)
                # appcommands returns 1 on help
                self.assertEqual(1, retcode)
