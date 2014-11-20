google-apitools
===============

.. image:: https://travis-ci.org/craigcitro/apitools.png?branch=master
        :target: https://travis-ci.org/craigcitro/apitools

``google-apitools`` is a collection of utilities to make it easier to build
client-side tools, especially those that talk to Google APIs.

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

Current status
--------------

There are a few imminent large changes:

- finish the protorpc -> proto2 transition
- switch from httplib2 to requests
- better retry support
- R client library generation
- optional support for `dict -> dict` as the signature on client methods,
  doing the proto conversion (and validation!) under the hood.
