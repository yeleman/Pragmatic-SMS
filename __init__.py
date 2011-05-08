#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4

import tempfile
import os


"""
    Pragmatic SMS (PSMS) is a simple and easy to setup library that let you write 
    Python SMS applications using an SMS modem or Kannel, enabling you to:

    - send SMS to multiple persons
    - respond automatically to incoming SMS
    - set callback to react to the various stage of the life of an SMS: 
      incoming, outgoing, in error, etc.

    PSMS focus on being simple:

    - settings are in Python and most have sensible default
    - transports are limited to the bare minium: a Gammu transport if you want
      to set up your own modem, and a Kannel transport for bigger setup
    - the smallest SMS application is a class with one method

    What PSMS is not:

    - A full featured SMS framework including models, map tools, GUI, all-in-one
      (for something like this, see RapidSMS)
    - A high performance SMS handler (for something like this, see Vumi)


"""


# create working dir
try:
    os.mkdir(os.path.join(tempfile.gettempdir(), 
                          'pragmatic_sms'))
except:
    pass