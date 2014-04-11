# apitools

[![Build Status](https://travis-ci.org/craigcitro/apitools.svg?branch=master)](https://travis-ci.org/craigcitro/apitools)

`apitools` is a collection of utilities to make it easier to build client-side
tools, especially those that talk to Google APIs.

## Current status

There are a few imminent large changes:

* finish the protorpc -> proto2 transition
* switch from httplib2 to requests
* better retry support
* R client library generation
* optional support for `dict -> dict` as the signature on client methods,
  doing the proto conversion (and validation!) under the hood.
