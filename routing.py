#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4

"""
    Starts the SMS router with the given settings.
"""

import datetime
import uuid
import socket
import logging

from conf import settings
from utils import import_class

from kombu.connection import BrokerConnection
from kombu.messaging import Exchange, Queue, Consumer, Producer


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
        self.connection = routes['connection']

        self.message_producer = Producer(self.connection.channel(), 
                                 exchange=self.messages_exchange, 
                                 serializer="json")

        self.log_producer = Producer(self.connection.channel(), 
                                     exchange=self.logs_exchange, 
                                     serializer="json")        
        # flag the router as not running. call start() to run it
        self.run = False



    def setup_consumers(self):
        """
            Attach callbacks to incoming and outgoing message queues
        """
  
        mps = (import_class(mp) for mp in settings.MESSAGE_PROCESSORS)
        self.message_processors = [mp(self) for mp in mps]

        mps = (mp.rsplit('.', 1)[1] for mp in settings.MESSAGE_PROCESSORS)
        self.logger.info('Loading message processors: %s' % ', '.join(mps))

        # attach callbacks for incoming messages
        self.incoming_messages_consumer = Consumer(self.connection.channel(), 
                                                   self.incoming_messages_queue)
        for mp in self.message_processors:
            self.incoming_messages_consumer.register_callback(mp.handle_incoming_message)
        self.incoming_messages_consumer.consume()

        # attach callbacks for outgoing messages
        self.outgoing_messages_consumer = Consumer(self.connection.channel(), 
                                                   self.outgoing_messages_queue)
        for mp in self.message_processors:
            self.outgoing_messages_consumer.register_callback(mp.handle_outgoing_message)
        self.outgoing_messages_consumer.register_callback(self.relay_message_to_transport)
        self.outgoing_messages_consumer.consume()

        # log everything that is in the logs queue using the Python logger
        self.logs_consumer = Consumer(self.connection.channel(), 
                                      self.logs_queue)
        self.logs_consumer.register_callback(self.handle_log)
        self.logs_consumer.consume()

        # attach a fallback functions to every message non-delivery queue
        self.errors_consumer = []
        for name, queue in self.error_queues.iteritems():
            consumer = Consumer(self.connection.channel(), queue)
            self.errors_consumer.append(consumer)
            consumer.register_callback(self.handle_missing_transport)
            consumer.consume()
        
    
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

        self.setup_consumers()
        self.run = True

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

        print body
        raise FatalRoutingError("No transport ready to send this message. "\
                                "Check that settings.MESSAGE_TRANSPORTS "\
                                "declare a transport named '%s'" % body['transport'])


    def get_routes(self):
        """
            Create the whole routing system, including the exchange,
            the connection and the queue, then returns it.
        """

        routes = {}
        transport = settings.MESSAGE_BROKER['transport']
        transport_options = settings.MESSAGE_BROKER.get("options", {})
        routes['connection'] = BrokerConnection(transport=transport, 
                                                **transport_options)
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
                      routing_key="incoming_messages")
        routes['queues']['incoming_messages'] = queue

        queue = Queue('outgoing_messages',
                      exchange=routes['exchanges']['messages'],
                      routing_key="outgoing_messages")
        routes['queues']['outgoing_messages'] = queue

        # todo: normalize transport names

        # one queue for all logs to centralize them
        routes['queues']['logs'] = Queue('logs', 
                                         exchange=routes['exchanges']['logs'] ,
                                         routing_key="logs")

        # message forwarded directly to message transorts
        # one queue for each transport
        routes['queues']['transports'] = {}
        for transport in settings.MESSAGE_TRANSPORTS:
            queue =  Queue('logs', 
                            exchange=routes['exchanges']['transports'] ,
                            routing_key="%s-send-message" % transport)
            routes['queues']['transports'][transport] = queue

        # queues where message are stacked when the router didn't deliver
        # one exchange can't deliver a message
        routes['queues']['errors'] = {}
        queue = Queue('ae.undeliver', 
                      exchange=routes['exchanges']['transports'] ,
                      routing_key="ae.undeliver")
        routes['queues']['errors']['no-transport'] = queue


        return routes


    def log(self, lvl, msg, *args, **kwargs):
        """
            Push this log message into the log queue
        """
        print msg
        log = {'lvl': lvl, 'msg': msg, 'args': args, 'kwargs': kwargs}
        self.log_producer.publish(body=log, routing_key="logs")  
            

    def handle_log(self, body, message):
        """
            React to log message in the log queue by passing it to the Python
            logger.
        """
        print body
        self.logger.log(body['lvl'], body['msg'], 
                        *body['args'], **body['kwargs'])  
                    

class Message(object):
    """
        Base message class with attributes and methods common to incoming and
        outgoing messages.

        All messages have a unique identifier. This is prefered to using
        the date and author of the message because it removes the hassle
        of taking care of the time zone and settling of the event defining
        the timestamp.
        
        Equality is defined according to this id so it is discouraged to 
        modify the message in place as different message could result in
        being considered equal.
         
    """

    # todo: message id hash of message content ?
    # todo: message are immutable ?

    DATE_FORMAT = "%Y-%m-%d %H:%M:%S.%f"
    router = SmsRouter()


    def __init__(self, text, transport='default', id=None):
        self.text = text
        self.transport = transport
        self.id = id or str(uuid.uuid4())


    def __eq__(self, message):
        return self.id == message.id

    
    @classmethod
    def serialize_date(cls, date):
        """
            Turn the date into string to allow JSON serialization
        """
        return date.strftime(cls.DATE_FORMAT)


    @classmethod
    def unserialize_date(cls, date_string):
        """
            Turn back the date from string to datetime object
            to allow JSON serialization
        """
        return datetime.datetime.strptime(date_string, cls.DATE_FORMAT)



class OutgoingMessage(Message):
    """
        Message to be sent by a transport.
    """

    def __init__(self, recipient, text, transport='default', creation_date=None,
                 id=None, response_to=None):
        Message.__init__(self, text, transport, id)

        # accept None, and IncomingMessage object or a
        # serialized IncomingMessage object as parameter
        self.recipient = recipient
        if response_to:
            try:
                self.response_to = IncomingMessage(**response_to)
            except TypeError:
                self.response_to = response_to
        else:
            self.response_to = response_to

        # accept a string as a date or a date object
        if creation_date:
            try:
                self.creation_date = self.unserialize_date(creation_date)
            except TypeError:
                self.creation_date = self.creation_date
        else:
            self.creation_date = datetime.datetime.now()


    def to_dict(self):
        """
            Turn this object into a dict that is easy to serialize into JSON
        """
        response_to = self.response_to.to_dict() if self.response_to else self.response_to
        return {'recipient': self.recipient, 'text': self.text, 
                'transport': self.transport, 'id': self.id, 
                'response_to': response_to,
                'creation_date': self.serialize_date(self.creation_date)}


    def send(self):
        """
            Stack the message in the outgoing message queue.
        """
        self.router.dispatch_outgoing_message(self)

    
    def __unicode__(self):
        return u"To %(recipient)s: %(text)s" % self.__dict__
    

    def __repr__(self):
        return u"<OutgoingMessage %(id)s via %(transport)s>" % self.__dict__



class IncomingMessage(Message):
    """
        Received message, waiting to be processed.
    """
    
    def __init__(self, author, text, transport='default', reception_date=None,
                 id=None):
        Message.__init__(self, text, transport, id)
        
        self.author = author

        # accept a string as a date or a date object
        if reception_date:
            try:
                self.reception_date = self.unserialize_date(reception_date)
            except TypeError:
                self.reception_date = self.reception_date
        else:
            self.reception_date = datetime.datetime.now()



    def to_dict(self):
        """
            Turn this object into a dict that is easy to serialize into JSON
        """
        return {'author': self.author, 
                'text': self.text, 'transport': self.transport, 'id': self.id,
                'reception_date': self.serialize_date(self.reception_date)}


    def create_response(self, text):
        """
            Create an OutgoingMessage with 'text' as a content for the same transport
            and the author as a recipient thent stack it in the outgoing
            message queue. Set the 'response_to' to the current message id
        """
        return OutgoingMessage(recipient=self.author,
                               text=text, transport=self.transport, 
                               response_to=self)


    def respond(self, text):
        """
            Create an OutgoingMessage object with self.create_reponse and
            send it then return the message object.
        """
        message = self.create_response(text)
        message.send()
        return message


    def dispatch(self):
        """
            Stack the message in the incoming message queue.
        """
        self.router.dispatch_incoming_message(self)


    def __unicode__(self):
        return u"From %(author)s: %(text)s" % self.__dict__
    

    def __repr__(self):
        return u"<IncomingMessage %(id)s via %(transport)s>" % self.__dict__


