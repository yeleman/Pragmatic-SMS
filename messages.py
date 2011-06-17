#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4

"""
    Class to wrap incoming and outgoing messages and provide a simple
    API to deal with them.
"""

import datetime
import uuid

from kombu.messaging import Queue

from workers import PSMSWorker


class MessageWorker(PSMSWorker):
    """
        This is a fake worker, as it will never perform any main loop.

        It just reuse the worker setup to be able to send a message
        on the message queues.
    """

    name = 'message worker'


    def dispatch_incoming_message(self, message):
        """
            Add an incoming message in the queue. Transport transport use this
            method notify all the message processor that they received a new
            message.
        """

        self.producers['psms'].publish(body=message.to_dict(), 
                                      routing_key="incoming_messages")   


    def dispatch_outgoing_message(self, message):
        """
            Add an outgoing message in the queue. Application use
            this notify the proper transport that they sent a new
            message.
        """
        self.producers['psms'].publish(body=message.to_dict(), 
                                      routing_key="outgoing_messages")     


    def get_queues(self):
        """
            One queue for incomming messages, one queue for outgoing messages.
        """

        queues = {}

        queues['incoming_messages'] = Queue('incoming_messages',
                                            exchange=self.exchanges['psms'],
                                            routing_key="incoming_messages",
                                            durable=self.persistent)
        queues['outgoing_messages'] = Queue('outgoing_messages',
                                            exchange=self.exchanges['psms'],
                                            routing_key="outgoing_messages",
                                            durable=self.persistent)
        return queues


class Message(object):
    """
        Base message class with attributes and methods common to incoming and
        outgoing messages.

        All messages have a unique identifier. This is prefered to using
        the date and author of the message because it removes the hassle
        of taking care of the time zone.
        
        Equality is defined according to this id so it is discouraged to 
        modify the message in place as different message could result in
        being considered equal.
         
    """

    # todo: message id hash of message content ?
    # todo: message are immutable ?

    DATE_FORMAT = "%Y-%m-%d %H:%M:%S.%f"
    
    worker = MessageWorker()
    worker.connect()


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
        self.worker.dispatch_outgoing_message(self)

    
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
        self.worker.dispatch_incoming_message(self)


    def __unicode__(self):
        return u"From %(author)s: %(text)s" % self.__dict__
    

    def __repr__(self):
        return u"<IncomingMessage %(id)s via %(transport)s>" % self.__dict__


