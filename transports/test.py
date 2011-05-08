#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4


"""
    Transports usefull only for testing purpose
"""

from base import MessageTransport

# todo : provide method stop_in/out_messsage loop

class DummyMessageTransport(MessageTransport):

    
        def __init__(self, name, purpose, activity='foo'):
            MessageTransport.__init__(self, name, purpose)
            self.activity = activity

        def start_incoming_messages_loop(self):

            while True:
                print "Doing '%s'" % self.activity

        def on_send_message(self, message):
            print "Sending %s" % message