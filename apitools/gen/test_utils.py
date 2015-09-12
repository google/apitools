"""Various utilities used in tests."""

import contextlib
import os
import tempfile
import shutil
import sys

import six
import unittest2


RunOnlyOnPython27 = unittest2.skipUnless(
    sys.version_info[:2] == (2, 7), 'Only runs in Python 2.7')


@contextlib.contextmanager
def TempDir(change_to=False):
    if change_to:
        original_dir = os.getcwd()
    path = tempfile.mkdtemp()
    try:
        if change_to:
            os.chdir(path)
        yield path
    finally:
        if change_to:
            os.chdir(original_dir)
        shutil.rmtree(path)


@contextlib.contextmanager
def CaptureOutput():
    new_stdout, new_stderr = six.StringIO(), six.StringIO()
    old_stdout, old_stderr = sys.stdout, sys.stderr
    try:
        sys.stdout, sys.stderr = new_stdout, new_stderr
        yield new_stdout, new_stderr
    finally:
        sys.stdout, sys.stderr = old_stdout, old_stderr
