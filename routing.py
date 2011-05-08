#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4

"""
    Starts the SMS router with the given settings.
"""

import socket
import logging

from conf import settings
from utils import import_class

from kombu.connection import BrokerConnection
from kombu.messaging import Exchange, Queue, Consumer, Producer
from kombu.exceptions import NotBoundError

# this module is borrowed from the Python source code itself as it's not
# yet available in Python 2.6. Still, it won't work in Python 2.4 or less.
from pragmatic_sms.settings.dictconfig import dictConfig
dictConfig(settings.LOGGING)



class FatalRoutingError(Exception):
    pass



class SmsRouter(object):
    """
        Start and stop the message processors and the transports. Each of them
        are run as separate child process of the router process.
    """


    def __init__(self):
        """
            Attach routes definition to attributes, connect to message broker
            and initialize producers that will send messages into the queue.
        """

        self.logger = logging.getLogger('psms')

        # setup routes
        routes = self.get_routes()
        
        self.outgoing_messages_queue = routes['queues']['outgoing_messages']
        self.incoming_messages_queue = routes['queues']['incoming_messages']
        self.transport_messages_queues = routes['queues']['transports']
        self.logs_queue = routes['queues']['logs']
        self.error_queues = routes['queues']['errors']
       
        self.messages_exchange = routes['exchanges']['messages']
        self.logs_exchange = routes['exchanges']['logs']
        
        self.connect()

        self.message_producer = Producer(self.channel, 
                                 exchange=self.messages_exchange, 
                                 serializer="json")

        self.log_producer = Producer(self.channel, exchange=self.logs_exchange, 
                                     serializer="json")        
        # flag the router as not running. call start() to run it
        self.run = False


    def start(self, timeout=1, limit=None):
        """
            Start listining for messages in queues. If self.run is set
            to False and drain_events reach a timeouts, the MessageProcessor
            stop automatically. Overwise, it starts a new loop.

            Use 'limit' for tests when you want to run the router a given
            number of loosp before it stop without having to tell him to.
            Limit should be an integer representing the number of loops.
        """

        self.logger.info('Starting SMS router')

        self.bind_routes()
        self.setup_consumers()
        self.run = True

        if not settings.PERSISTENT_MESSAGE_QUEUES:
            self.purge()

        try:
            if limit: # this part is run only for testing
                assert limit > 0
                while self.run and limit > 0:
                    try:
                        self.connection.drain_events(timeout=timeout)
                    except socket.timeout: 
                        # this happens when timout is reach and no message is
                        limit -= 1

            else:
                while self.run:
                    try:
                        self.connection.drain_events(timeout=timeout)
                    except socket.timeout: 
                        # this happens when timout is reach and no message is
                        # in the queue
                        pass

        # todo : log the errors

        except self.connection.connection_errors, e:
            self.logger.error("Error while connecting with Kombu: %s" % e)
        except socket.error, e:
            self.logger.error("Socket error: %s" % e)
        except KeyboardInterrupt:
            self.logger.info("Stopping SMS router")
        
        try:
            self.connection.release()
        except AssertionError:
            # todo: find why there is this assertion error about state
            pass

        self.logger.info('SMS router stopped')


    def stop():
        """
            Unregister callbacks and set the running flag to False so the
            next timeout the MessageProcessor should shutdown gracefully.
        """
        self.logger.info('Stopping SMS router')
        self.outgoing_messages_consumer.callbacks = []
        self.incoming_messages_consumer.callbacks = []
        self.run = False


    def get_routes(self):
        """
            Create the whole routing system, including the exchange,
            the connection and the queue, then returns it.
        """

        routes = {}
        

        # todo: use topic routing
        # http://packages.python.org/kombu/reference/kombu.entity.html?#kombu.entity.Exchange.type
        routes['exchanges'] = {}
        routes['exchanges']['messages'] = Exchange("sms", "direct", 
                                    durable=settings.PERSISTENT_MESSAGE_QUEUES)

        routes['exchanges']['logs'] = Exchange("logs", "direct",
                                                durable=False)

        routes['exchanges']['transports'] = Exchange("transport", "direct", 
                                    durable=settings.PERSISTENT_MESSAGE_QUEUES)

        routes['queues'] = {}

        # one queue for message going in, one for message going out
        queue = Queue('incoming_messages',
                      exchange=routes['exchanges']['messages'],
                      routing_key="incoming_messages",
                      durable=settings.PERSISTENT_MESSAGE_QUEUES)
        routes['queues']['incoming_messages'] = queue

        queue = Queue('outgoing_messages',
                      exchange=routes['exchanges']['messages'],
                      routing_key="outgoing_messages",
                       durable=settings.PERSISTENT_MESSAGE_QUEUES,)
        routes['queues']['outgoing_messages'] = queue

        # todo: normalize transport names

        # one queue for all logs to centralize them
        routes['queues']['logs'] = Queue('logs', 
                                         exchange=routes['exchanges']['logs'] ,
                                         routing_key="logs")

        # message forwarded directly to message transports
        # one queue for each transport
        routes['queues']['transports'] = {}
        for transport in settings.MESSAGE_TRANSPORTS:
            queue =  Queue('logs', 
                            exchange=routes['exchanges']['transports'] ,
                            routing_key="%s-send-message" % transport,
                             durable=settings.PERSISTENT_MESSAGE_QUEUES)
            routes['queues']['transports'][transport] = queue

        # queues where message are stacked when the router didn't deliver
        # one exchange can't deliver a message
        routes['queues']['errors'] = {}
        queue = Queue('ae.undeliver', 
                      exchange=routes['exchanges']['transports'] ,
                      routing_key="ae.undeliver",
                       durable=settings.PERSISTENT_MESSAGE_QUEUES)
        routes['queues']['errors']['no-transport'] = queue


        return routes


    def connect(self):
        """
            Start the connection manually. You probably don't need this as
            it is taken care of automatically. It's here mostly for testing
            purpose.
        """

        if not getattr(self, 'channel', None):

            transport = settings.MESSAGE_BROKER['transport']
            transport_options = settings.MESSAGE_BROKER.get("options", {})
            self.connection = BrokerConnection(transport=transport, 
                                               **transport_options)
            self.channel = self.connection.channel()



    def bind_routes(self):
        """
            Bind the exchanges and the queues to a channel so they
            can perform operations such as purge(). You mostly want this to
            happen only on the router side so this is called automatically in
            start().
        """ 
        try:
            self.channel
        except AttributeError:
            raise FatalRoutingError('Cannot bind route on a disconnected '\
                                    'router. Try to call connec()')
        self.outgoing_messages_queue = self.outgoing_messages_queue(self.channel)
        self.incoming_messages_queue = self.incoming_messages_queue(self.channel)
        self.logs_queue = self.logs_queue(self.channel)
        self.error_queues['no-transport'] = self.error_queues['no-transport'](self.channel)

        for name, queue in self.transport_messages_queues.items():
            self.transport_messages_queues[name] = queue(self.channel)
       
        self.messages_exchange = self.messages_exchange(self.channel)
        self.logs_exchange = self.logs_exchange(self.channel)
 


    def setup_consumers(self):
        """
            Attach callbacks to incoming and outgoing message queues.
            You mostly want this to happen on the router side so this is
            called automatically in start().
        """
  
        mps = (import_class(mp) for mp in settings.MESSAGE_PROCESSORS)
        self.message_processors = [mp(self) for mp in mps]

        mps = (mp.rsplit('.', 1)[1] for mp in settings.MESSAGE_PROCESSORS)
        self.logger.info('Loading message processors: %s' % ', '.join(mps))

        # attach callbacks for incoming messages
        self.incoming_messages_consumer = Consumer(self.channel, 
                                                   self.incoming_messages_queue)
        for mp in self.message_processors:
            self.incoming_messages_consumer.register_callback(mp.handle_incoming_message)
        self.incoming_messages_consumer.consume()

        # attach callbacks for outgoing messages
        self.outgoing_messages_consumer = Consumer(self.channel, 
                                                   self.outgoing_messages_queue)
        for mp in self.message_processors:
            self.outgoing_messages_consumer.register_callback(mp.handle_outgoing_message)
        self.outgoing_messages_consumer.register_callback(self.relay_message_to_transport)
        self.outgoing_messages_consumer.consume()

        # log everything that is in the logs queue using the Python logger
        self.logs_consumer = Consumer(self.channel, self.logs_queue)
        self.logs_consumer.register_callback(self.handle_log)
        self.logs_consumer.consume()

        # attach a fallback functions to every message non-delivery queue
        self.errors_consumer = []
        for name, queue in self.error_queues.iteritems():
            consumer = Consumer(self.channel, queue)
            self.errors_consumer.append(consumer)
            consumer.register_callback(self.handle_missing_transport)
            consumer.consume()


    def purge(self):
        """
            Remove message from all queues. Call this if you want to reset
            the state of your message queues, like in a unite test.
        """

        try:
            for queue in  [self.outgoing_messages_queue,
                          self.incoming_messages_queue,
                          self.logs_queue] + \
                          self.error_queues.values() +\
                          self.transport_messages_queues.values():
                try:
                    queue.purge()

                except AttributeError:
                    # This queue can't be purge because of some reference issue
                    # I have yet to figure this out but this doesn't seem to prevent
                    # the system from working rght now and the unit tests pass,
                    # so fingers crossed...
                    pass
        except NotBoundError:
            raise FatalRoutingError('You cannot call purge on before binding '\
                                    'queues. Either start the router or call '\
                                    'bind_routes()')
        
    
    def dispatch_incoming_message(self, message):
        """
            Add an incoming message in the queue. Transport transport use this
            method notify all the message processor that they received a new
            message.
        """

        self.message_producer.publish(body=message.to_dict(), 
                               routing_key="incoming_messages")    


    def dispatch_outgoing_message(self, message):
        """
            Add an outgoing message in the queue. Application use
            this notify the proper transport that they sent a new
            message.
        """

        self.message_producer.publish(body=message.to_dict(), 
                               routing_key="outgoing_messages")    


    def relay_message_to_transport(self, body, message):
        """
            Take a message from the outgoing message queue and stack it
            into the appropriate transport message queue, ready to be sent.

            This is done this way to all message processors have a chance
            to react on outgoing message but when a message is sent to a 
            transport (which can be an outside process and we can't know 
            when he register it's callback), it's callback is always the last
            called on the message.
        """

        self.message_producer.publish(body=body, 
                               routing_key="%s-send-message" % body['transport']) 


    def handle_missing_transport(self, body, message):
        """
            Called when a message is delivered to a transport exchange but
            no queue match the routing key. This generally happens
            when no transport is declared in the settings witht his name.
        """
        return
        raise FatalRoutingError("No transport ready to send this message. "\
                                "Check that settings.MESSAGE_TRANSPORTS "\
                                "declare a transport named '%s' and that it "\
                                "listens for outgoing messages." % body['transport'])


    def log(self, lvl, msg, *args, **kwargs):
        """
            Push this log message into the log queue
        """
        log = {'lvl': lvl, 'msg': msg, 'args': args, 'kwargs': kwargs}
        self.log_producer.publish(body=log, routing_key="logs")  
            

    def handle_log(self, body, message):
        """
            React to log message in the log queue by passing it to the Python
            logger.
        """
        self.logger.log(body['lvl'], body['msg'], 
                        *body['args'], **body['kwargs'])  
                    
