#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4

"""
    Message processors dedicated to log incoming and outgoing messages
"""

from pragmatic_sms.processors.base import MessageProcessor
from pragmatic_sms.routing import OutgoingMessage, IncomingMessage

import logging

class LoggerMessageProcessor(MessageProcessor):
    """
        Make a call to router.log() for every incoming or outgoing message.
    """

    def on_receive_message(self, message):
        self.router.log(logging.INFO, unicode(message))

    def on_send_message(self, message):
        self.router.log(logging.INFO, unicode(message))
