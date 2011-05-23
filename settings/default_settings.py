#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4

import tempfile
import os


TEMP_DIR = os.path.join(tempfile.gettempdir(), 'pragmatic_sms')
PSMS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# if False, message will be deleted when the router shut down or crash
# if true, they will be saved when queued and retrieved on router starts up
PERSISTENT_MESSAGE_QUEUES = True


# List of transport in charge of sending and receiving messages
MESSAGE_TRANSPORTS = {
    'default': {
        'backend': 'pragmatic_sms.transports.test.DummyMessageTransport',
        'options': {}
    }
}


# Check http://packages.python.org/kombu/reference/kombu.connection.html
# for a list of all the available message broker
# 'memory' is requires no setup and fits well for dev while 'rabbitmq' is
# a very robust production set up
MESSAGE_BROKER = {'transport': "sqlakombu.transport.Transport",
                  'options': {
                       "hostname":"sqlite:///%s" % os.path.join(TEMP_DIR, 
                                                                'psms.db')
                   } 
}


# list of object that will react when a message is received or going to be send
# You should need to add your owns to create
# and SMS application
MESSAGE_PROCESSORS = (
    'pragmatic_sms.processors.logger.LoggerMessageProcessor', # log message
    'pragmatic_sms.processors.test.EchoMessageProcessor', # respond 'echo to any message'
)


# Python logger dict config.
# This configure the logger used when you call router.log
# Router.log send the message to the log queue, then in the router thread
# the message is turned into a real logger call.
# Current set up should be enough for everybody as it print logs on 
# the screen and in a log file
# See http://docs.python.org/library/logging.config.html?#logging-config-dictschema
# for advanced usage
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
            'filename': os.path.join(TEMP_DIR, 'activity.log'),
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

