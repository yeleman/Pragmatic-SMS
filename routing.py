#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4

"""
    Starts the SMS router with the given settings.
"""

import socket
import logging
import time

from conf import settings
from utils import import_class

from kombu.connection import BrokerConnection
from kombu.messaging import Exchange, Queue, Consumer, Producer
from kombu.exceptions import NotBoundError

# this module is borrowed from the Python source code itself as it's not
# yet available in Python 2.6. Still, it won't work in Python 2.4 or less.
from pragmatic_sms.settings.dictconfig import dictConfig
dictConfig(settings.LOGGING)

from messages import MessageWorker
from workers import PSMSWorker, WorkerError


class RoutingError(WorkerError):
    pass


class SmsRouter(PSMSWorker):
    """
        Central worker that routes SMS.

        Start and stop the message processors and transports. 

        Each transport are started as separated child processes.
    """

    name = "SMS router"


    def __init__(self, no_transports=False, *args, **kwargs):

        self.no_transports = no_transports

        self.transports = self.get_transports()

        PSMSWorker.__init__(self, *args, **kwargs)


    def get_queues(self):
        """
            Gather the queues from the parent class, the messages classes
            and the transports.
        """

        # get the queues common to all psms workers
        queues = PSMSWorker.get_queues(self)

        # queues for outgoing and incoming messages
        queues.update(MessageWorker().get_queues())

        # transport queues
        # todo: normalize transport names
        for name, transport in self.transports.iteritems():
            queues.update(transport.get_queues())
        
        return queues 


    def get_consumers(self):
        """
            Create two consumers for each message processor: one
            for the outgoing message queue, and one for the incoming message
            queue.
        """

        consumers = {}

        # import dynamically (use the import path in the settings file) all
        # message processor then create one instance for each of them
        mps = (import_class(mp) for mp in settings.MESSAGE_PROCESSORS)
        self.message_processors = [mp() for mp in mps]

        # Just a log loop to say that we do
        mps = (mp.rsplit('.', 1)[1] for mp in settings.MESSAGE_PROCESSORS)
        self.logger.info('Loading message processors: %s' % ', '.join(mps))

        # Create the consumer for incoming messages and attach the callback
        # of each message processor
        queue = self.queues['incoming_messages']
        c = consumers['incoming_messages'] = Consumer(self.channel, queue)

        for mp in self.message_processors:
            c.register_callback(mp.handle_incoming_message)

        c.consume()

        # Create the consumer for incoming messages and attach the callback
        # of each message processor
        # then attach a router callback that is going to relay the message
        # to the proper transport queue
        queue = self.queues['outgoing_messages']
        c = consumers['outgoing_messages'] = Consumer(self.channel, queue)

        for mp in self.message_processors:
            c.register_callback(mp.handle_outgoing_message)

        c.register_callback(self.relay_message_to_transport)
        c.consume()

        # Create the consumer for the log messages and attach a callback
        # from the SMS router: all messages sent to this queue are going
        # to be logged in the router log
        consumers['logs'] = Consumer(self.channel, self.queues['logs'])
        consumers['logs'].register_callback(self.handle_log)
        consumers['logs'].consume()

        # attach a fall back functions to handle message that kombu can't deliver
        queue = self.queues['undelivered_kombu_message']
        c = consumers['undeliverd_kombu_messages'] = Consumer(self.channel, 
                                                              queue)
        c.register_callback(self.handle_undelivered_kombu_message)
        c.consume()


    def get_transports(self):
        """
            Return a dict of message transports instances as describes in
            the settings file
        """
        transports = {}
        for name, transport in settings.MESSAGE_TRANSPORTS.iteritems():
            
            klass = import_class(transport['backend'])
            transports[name] = klass(name, 'send_messages',
                                           **transport.get('options', {}))
        return transports


    def on_main_loop(self):
        if not self.no_transports:
            self.start_transports_daemons()
            time.sleep(1)


    def on_worker_stops(self):
        if not self.no_transports:
            self.stop_transports_daemons()


    def start_transports_daemons(self):
        """
            Start the transports daemons as separate processes
        """
        self.transports = {}
        for name, transport in self.transports.iteritems():
            self.logger.info('Start transport: %s' % name)
            transport.start_daemons()


    def stop_transports_daemons(self):
        """
            Stop the transports daemons.
        """
        for name, transport in self.transports.iteritems():
            self.logger.info('Stop transport: %s' % name)
            transport.stop_daemons()


    def relay_message_to_transport(self, body, message):
        """
            Take a message from the outgoing message queue and stack it
            into the appropriate transport message queue, ready to be sent.

            This is done this way so all message processors have a chance
            to react on outgoing messages and can modify them or prevent
            them to be sent.

            For this reason, it should be the last callback on the outgoing
            messages queue and set the message as 'acknowledged'.
        """
        key = "%s_transport" % body['transport']


        self.producers['psms'].publish(body=body, routing_key=key) 
        message.ack()


    def handle_undelivered_kombu_message(self, body, message):
        """
            Called when a message is delivered to a transport exchange but
            no queue match the routing key. This generally happens
            when no transport is declared in the settings.
        """
        self.logger.error('Kombu fails to deliver message %s to "%s"' % (
                          message,
                          message.properties['delivery_info']['routing_key']))


    def handle_log(self, body, message):
        """
            React to log message in the log queue by passing it to the Python
            logger.
        """
        self.logger.log(body['lvl'], body['msg'], 
                        *body['args'], **body['kwargs'])  
                    
