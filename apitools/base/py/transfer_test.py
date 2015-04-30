#!/usr/bin/env python


import six

import unittest2

from apitools.base.py import base_api
from apitools.base.py import http_wrapper
from apitools.base.py import transfer


class TransferTest(unittest2.TestCase):

    def testFromEncoding(self):
        # Test a specific corner case in multipart encoding.

        # Python's mime module by default encodes lines that start with
        # "From " as ">From ", which we need to make sure we don't run afoul
        # of when sending content that isn't intended to be so encoded. This
        # test calls out that we get this right. We test for both the
        # multipart and non-multipart case.
        multipart_body = '{"body_field_one": 7}'
        upload_contents = 'line one\nFrom \nline two'
        upload_config = base_api.ApiUploadInfo(
            accept=['*/*'],
            max_size=None,
            resumable_multipart=True,
            resumable_path=u'/resumable/upload',
            simple_multipart=True,
            simple_path=u'/upload',
        )
        url_builder = base_api._UrlBuilder('http://www.uploads.com')

        # Test multipart: having a body argument in http_request forces
        # multipart here.
        upload = transfer.Upload.FromStream(
            six.StringIO(upload_contents),
            'text/plain',
            total_size=len(upload_contents))
        http_request = http_wrapper.Request(
            'http://www.uploads.com',
            headers={'content-type': 'text/plain'},
            body=multipart_body)
        upload.ConfigureRequest(upload_config, http_request, url_builder)
        self.assertEqual(url_builder.query_params['uploadType'], 'multipart')
        rewritten_upload_contents = '\n'.join(
            http_request.body.split('--')[2].splitlines()[1:])
        self.assertTrue(rewritten_upload_contents.endswith(upload_contents))

        # Test non-multipart (aka media): no body argument means this is
        # sent as media.
        upload = transfer.Upload.FromStream(
            six.StringIO(upload_contents),
            'text/plain',
            total_size=len(upload_contents))
        http_request = http_wrapper.Request(
            'http://www.uploads.com',
            headers={'content-type': 'text/plain'})
        upload.ConfigureRequest(upload_config, http_request, url_builder)
        self.assertEqual(url_builder.query_params['uploadType'], 'media')
        rewritten_upload_contents = http_request.body
        self.assertTrue(rewritten_upload_contents.endswith(upload_contents))


if __name__ == '__main__':
    unittest2.main()
