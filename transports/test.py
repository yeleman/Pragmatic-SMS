#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4


"""
    Transports usefull only for testing purpose
"""

import os
import logging

from base import MessageTransport
from pragmatic_sms.messages import OutgoingMessage
from pragmatic_sms.conf import settings


class DummyMessageTransport(MessageTransport):

    
        def __init__(self, name, purpose, activity='foo'):
            MessageTransport.__init__(self, name, purpose)
            self.activity = activity

        def start_incoming_messages_loop(self):

            while True:
                print "Doing '%s'" % self.activity

        def on_send_message(self, message):
            print "Sending %s" % message
            return True


class CounterMessageTransport(MessageTransport):
    """
        Increment a global counter for each message sent
    """
     
    message_sent = 0

    def __init__(self, *args, **kwargs):
        """
            Reset the counter at each router restart
        """
        self.reset()
        MessageTransport.__init__(self, *args, **kwargs)


    def on_send_message(self, message):
        print "In counter message transport on_send_message()"
        if isinstance(message, OutgoingMessage):
            from pragmatic_sms.transports.test import CounterMessageTransport
            CounterMessageTransport.message_sent += 1
            return True
        

    @classmethod
    def reset(cls):
        """
            Reset counters to 0
        """
        CounterMessageTransport.message_sent = 0



class FileCounterMessageTransport(MessageTransport):
    """
        Increment a global counter for each message sent
    """
     
    counter_file = os.path.join(settings.TEMP_DIR, 'counter')


    def __init__(self, *args, **kwargs):
        """
            Reset the counter at each router restart
        """
        self.reset()
        MessageTransport.__init__(self, *args, **kwargs)


    def on_send_message(self, message):
        if isinstance(message, OutgoingMessage):
            from pragmatic_sms.transports.test import FileCounterMessageTransport
            FileCounterMessageTransport.increment()
            return True
        

    @classmethod
    def message_sent(cls):
        """
           Get number of sent messages
        """
        return int(open(FileCounterMessageTransport.counter_file).read() or 0)


    @classmethod
    def increment(cls):
        """
            Increment counter
        """
        try:
            count = open(FileCounterMessageTransport.counter_file, 'r').read()
        except IOError:
            count = 0
        count = int(count or 0) + 1
        f = open(FileCounterMessageTransport.counter_file, 'w')
        f.write(str(count))
        f.close()


    @classmethod
    def reset(cls):
        """
            Reset counters to 0
        """
        open(FileCounterMessageTransport.counter_file, 'w').close()

    