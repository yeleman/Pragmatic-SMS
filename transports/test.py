#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4


"""
    Transports usefull only for testing purpose
"""

from base import MessageTransport
from pragmatic_sms.messages import OutgoingMessage


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