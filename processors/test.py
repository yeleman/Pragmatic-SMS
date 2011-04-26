#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4

"""
    Demo Message Processor used to demonstrate how to setup a custom Message
    Processor.

    It just respond "Echo" + the text you sent to it.
"""

from pragmatic_sms.processors.base import MessageProcessor


class EchoMessageProcessor(MessageProcessor):
    """
        Demo Message Processor used to demonstrate how to setup a custom Message
        Processor.

        It just respond "Echo" + the text you sent to it.
    """

    def on_receive_message(self, message):

        message.respond(text='Echo "%s"' % message.text)