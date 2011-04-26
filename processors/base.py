#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4

"""
    Provide the tools you need to create a message processor and react to
    incoming and outgoing messages.
"""

import socket

from routing import SmsRouter, IncomingMessage, OutgoingMessage
from conf import settings



class MessageProcessor(object):
    """
        Extend this class when you want your program to react when a SMS is 
        sent or received.

        Typical usage is:

            from pramatic_sms.processors.base import MessageProcessor

            YourMessageProcessor(MessageProcessor):

                def on_send_message(self, message):
                    # do something with a message ready to be sent

                def on_receive_message(self, message):
                    # do something with a message just arriving

        Then in your settings file:

            MESSAGE_PROCESSORS = (
                'your_module.YourMessageProcessor',
            )

        When you'll restart the router, your method will be called 
        automatically.
    """


    # todo: implement on return so we can handle message you can't deliver
    # http://packages.python.org/kombu/reference/kombu.messaging.html?k#message-producer

    def handle_incoming_message(self, body, message):
        """
            Callback called when a new message available on the incomming message
            queue. It unpacks the JSON message, turn it into an IncomingMessage
            instance an pass it to 'on_receive_message'.

            This method is used for internal purpose and you should
            not override it unless you know what you are doing.

            To react on the reception of messages, override 'on_receive_message'.
        """
        # todo: try / except message reception and log error
        if self.on_receive_message(IncommingMessage(**body)):
            message.ack()


    def handle_outgoing_message(self, body, message):
        """
            Callback called when a message ready to be sent. 
            It unpacks the JSON message, turn it into an OutgoingMessage
            instance an pass it to 'on_send_message'.

            This method is used for internal purpose and you should
            not override it unless you know what you are doing.

            To react on the reception of messages, override 'on_send_message'.
        """
        # todo: try / except message reception and log error
        if self.on_send_message(IncommingMessage(**body)):
            message.ack()


    def on_receive_message(self, message):
        """
            Override this method to react to any message that is just arriving.

            Return True if you handled the message and don't want other handlers
            to receive it.

            If you don't override it, it will silently do nothin, which allow
            you to create MessageProcessors that only cares about either
            OutoingMessage or IncomingMessage and not both.
        """
        pass


    def on_send_message(self, message):
        """
            Override this method to react to any message that is going to 
            be sent.

            Return True if you handled the message and don't want other handlers
            to receive it.

            If you don't override it, it will silently do nothin, which allow
            you to create MessageProcessors that only cares about either
            OutoingMessage or IncomingMessage and not both.
        """
        pass


    # todo: add the 'origin' of the message as the piece of code that produced 
    # the message

    # todo: make a with Message.recipient / backend context manager to send 
    # several message to the same recipient / backend in a raw
    def send(recipient, text, backend="default"):
        """
            Create a Message object with the following attributes and send it.

            Return the Message object
        """
        message = OutgoingMessage(recipient, text, backend=backend)
        message.send()
        return message

