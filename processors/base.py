#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4

"""
    Provide the tools you need to create a message processor
"""


class MessageProcessor(object):
    """
        Extend this class when you want your program to react when and SMS is 
        and received.

        Typical usage is:

            from pramatic_sms.processors.base import MessageProcessor

            YourMessageProcessor(MessageProcessor):

                def outgoing_message(self, message):
                    # do something with a message ready to be sent

                def incomming message(self, message):
                    # do something with a message just arriving

        Then in your settings file:

            MESSAGE_PROCESSORS = (
                'your_module.YourMessageProcessor',
            )

        When you'll restart the router, your method will be called 
        automatically.
    """

    def incomming_message(self, message):
        """
            Override this method to react to any message that is just arriving.
        """
        raise NotImplemented


    def outgoing_message(self, message):
        """
            Override this method to react to any message that is going to 
            be sent.
        """
        raise NotImplemented


    def send_message(self, message):
        """
            Stack a message in the sending queue. 'message' should be a message
            object.
        """


    def send(to, text, backend="default"):
        """
            Create a Message object with the following attributes and pass it
            to send_message()
        """

    def add_incoming_message(self, message, backend='default'):
        """
            Add a message to the incomming queue
        """
        queue_name = '%s-incoming-message' % backend
        self.producer.publish(message, routing_key=queue_name)


    def add_outgoing_message(self, message, backend='default'):
        """
            Add a message to the incomming queue
        """
        queue_name = '%s-outgoing-message' % backend
        self.producer.publish(message, routing_key=queue_name)

    

  # set exchanges, consumers and producers
        backends = dict(self.backends)
        self.backends = {}
    
        self.exchange = Exchange("sms-exchange", "direct", durable=self.durable)
        
        self.message_broker = BrokerConnection(**self.message_broker)

        self.channel = self.message_broker.channel()
        self.poducer = Producer(self.channel, exchange=self.exchange)
        self.consumer = Consumer(self.channel, )

        # set on queue for each backend
        self.queues = {'incoming_messages': {}, 'outgoing_messages': {}}        
        for name, params in backends.iteritems():
            
            cls = params.pop(name)
            self.backends[name] = cls(**params) 
            
            queue_name = '%s-incoming-message' % name
            incoming_messages_queue = Queue(queue_name, 
                                            exchange=self.exchange, 
                                            key=queue_name)
            self.queues['incoming_messages'][name] = queue

            queue_name = '%s-outgoing-message' % name
            outgoing_messages_queue = Queue(queue_name, 
                                            exchange=self.exchange, 
                                            key=queue_name)
            self.queues['incoming_messages'][name] = queue

        # attach all the callbacks that need to receive the messages
        for message_processor in self.message_processors:
            processor = __import__(message_processor)
            self.consumer.register_callback(processor)
        
        self.consumer.consume()