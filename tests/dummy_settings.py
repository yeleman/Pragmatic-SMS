#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4

import tempfile
import os


IS_TEST_SETTINGS = True



# List of transport in charge of sending and receiving messages
MESSAGE_TRANSPORTS = {
    'default': {
        'backend': 'pragmatic_sms.transports.test.DummyMessageTransport',
        'options': {'activity': 'foo'}
    }
}

# Check http://packages.python.org/kombu/reference/kombu.connection.html
# for a list of all the available message broker
# 'memory' is requires no setup and fits well for dev while 'rabbitmq' is
# a very robust production set up



# list of object that will react when a message is received or going to be send
MESSAGE_PROCESSORS = (
    'pragmatic_sms.processors.logger.LoggerMessageProcessor',
    'pragmatic_sms.processors.test.EchoMessageProcessor',
)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '%(levelname)s %(asctime)s %(module)s %(process)d %(thread)d %(message)s'
        },
        'simple': {
            'format': '%(levelname)s %(message)s'
        },
    },
    'handlers': {
        'console':{
            'level':'INFO',
            'class':'logging.StreamHandler',
            'formatter': 'simple'
        },
        'file':{
            'level':'DEBUG',
            'class':'logging.handlers.RotatingFileHandler',
            'formatter': 'verbose',
            'filename': os.path.join(tempfile.gettempdir(), 
                                     'pragmatic_sms', 
                                     'activity.log'),
            'maxBytes': 2000000,
            'backupCount': 1
        },
    },
    'loggers': {
        'psms': {
            'handlers':['console', 'file'],
            'propagate': True,
            'level':'INFO',
        },
    }
    
}