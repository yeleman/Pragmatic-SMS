#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4


"""
    Transports usefull only for testing purpose
"""

import os
import logging
import threading

from base import MessageTransport
from pragmatic_sms.messages import IncomingMessage
from pragmatic_sms.conf import settings




class CmdMessageTransport(MessageTransport):
    """
        Send a message from the command line an get back the response.
    """

    # todo: add option to transport to indicate to the router wether it
    # should start it automatically or not and care about reception of messages
    # or not


    react = False


    def fake_sms_reception(self, author, text):
        """
            Simulate the reception of a message and wait during 5 seconds
            for the system to respond
        """
        self.react = True
        message = IncomingMessage(author=author, text=text, transport=self.name)
        print "%s >>> %s" % (message.author, message.text)
        message.dispatch()
        self.start_outgoing_messages_loop(1, 5)


    def on_send_message(self, message):
        """
            Print the outgoing message and stop the message loop but only
            if react is True, which would mean we are explitly told this
            instance should react to the messages.
            The router won't set self.react, but fake_sms_reception will.
        """
        if self.react:
            print "%s <<< " % (message.author, message.text)
            self.run = False
            return True