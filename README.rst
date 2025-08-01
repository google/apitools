**DEPRECATED - Please see alternatives below**

google-apitools
===============

|pypi| |build| |coverage| |compat_check_pypi| |compat_check_github|

``google-apitools`` is a collection of utilities to make it easier to build
client-side tools, especially those that talk to Google APIs.

**NOTE**: This library is deprecated and unsupported. Please read below for suggested alternatives.

Alternatives to apitools
-----------------------
For the official Cloud client libraries used to communicating with Google Cloud APIs, go to https://cloud.google.com/apis/docs/cloud-client-libraries.

To generate Python API client libraries for APIs specified by protos, such as those inside Google, see https://github.com/googleapis/gapic-generator-python. 
API client library generators for other languages can be found in https://github.com/googleapis.

Installing as a library
-----------------------

To install the library into the current virtual environment::

   $ pip install google-apitools

Installing the command-line tools
---------------------------------

To install the command-line scripts into the current virtual environment::

   $ pip install google-apitools[cli]

Running the tests
-----------------

First, install the testing dependencies::

   $ pip install google-apitools[testing]

and the ``nose`` testrunner::

   $ pip install nose

Then run the tests::

   $ nosetests

.. |build| image:: https://travis-ci.org/google/apitools.svg?branch=master
   :target: https://travis-ci.org/google/apitools
.. |pypi| image:: https://img.shields.io/pypi/v/google-apitools.svg
   :target: https://pypi.python.org/pypi/google-apitools
.. |coverage| image:: https://coveralls.io/repos/google/apitools/badge.svg?branch=master
   :target: https://coveralls.io/r/google/apitools?branch=master
.. |compat_check_pypi| image:: https://python-compatibility-tools.appspot.com/one_badge_image?package=google-apitools
   :target: https://python-compatibility-tools.appspot.com/one_badge_target?package=google-apitools
.. |compat_check_github| image:: https://python-compatibility-tools.appspot.com/one_badge_image?package=git%2Bgit%3A//github.com/google/apitools.git
   :target: https://python-compatibility-tools.appspot.com/one_badge_target?package=git%2Bgit%3A//github.com/google/apitools.git
