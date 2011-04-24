#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4

# if False, message will be deleted when the router shut down or crash
# if true, they will be saved when queued and retrieved on router starts up
PERSISTENT_MESSAGE_QUEUES = True


# List of backend in charge of sending and receiving messages
BACKENDS = {
    'default': {
        'engine': 'pramatic_sms.backends.shell.ShellBackend',
    }
}

# Check http://packages.python.org/kombu/reference/kombu.connection.html
# for a list of all the available message broker
# 'memory' is requires no setup and fits well for dev while 'rabbitmq' is
# a very robust production set up
MESSAGE_BROKER = {'transport': 'memory' }


# list of object that will react when a message is received or going to be send
MESSAGE_PROCESSORS = (
    'pramatic_sms.processors.shell.shell_message_processor',
)
