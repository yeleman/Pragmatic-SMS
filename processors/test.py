#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4

"""
    Collection of demo message processors and processors used for testing 
    purpose. Usually very simple, so good as well to understand how
    message processors work.
"""

from pragmatic_sms.processors.base import MessageProcessor
from pragmatic_sms.messages import OutgoingMessage, IncomingMessage


class EchoMessageProcessor(MessageProcessor):
    """
        Demo Message Processor used to demonstrate how to setup a custom Message
        Processor.

        It just respond "Echo" + the text you sent to it.
    """

    def on_receive_message(self, message):

        message.respond(text='Echo "%s"' % message.text)


class CounterMessageProcessor(MessageProcessor):
    """
        Increment a global counter for each message sent or received.
    """
     
    message_received = 0
    message_sent = 0

    def __init__(self, *args, **kwargs):
        """
            Reset the counter at each router restart
        """
        self.reset()
        MessageProcessor.__init__(self, *args, **kwargs)


    def on_receive_message(self, message):
        if isinstance(message, IncomingMessage):
            from pragmatic_sms.processors.test import CounterMessageProcessor
            CounterMessageProcessor.message_received += 1


    def on_send_message(self, message):
        if isinstance(message, OutgoingMessage):
            from pragmatic_sms.processors.test import CounterMessageProcessor
            CounterMessageProcessor.message_sent += 1
        

    @classmethod
    def reset(cls):
        """
            Reset counters to 0
        """
        CounterMessageProcessor.message_received = 0
        CounterMessageProcessor.message_sent = 0