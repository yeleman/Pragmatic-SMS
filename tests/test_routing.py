#!/usr/bin/env python
#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4

import unittest2
import os
import sys

from kombu.connection import BrokerConnection
from kombu.messaging import Exchange, Queue

test_dir = os.path.dirname(os.path.abspath(__file__))
pragmatic_sms_dir = os.path.dirname(test_dir)
sys.path.insert(0, test_dir)
sys.path.insert(0, pragmatic_sms_dir)
os.environ['PYTHON_PATH'] = test_dir
os.environ['PRAGMATIC_SMS_SETTINGS_MODULE'] = 'dummy_settings'

import default_settings
import dummy_settings
import processors.base

from conf import SettingManager, settings
from routing import SmsRouter, OutgoingMessage, IncomingMessage
from utils import import_class
from pragmatic_sms.processors.test import EchoMessageProcessor
from processors.base import MessageProcessor



class TestRouting(unittest2.TestCase):

    def setUp(self):
        os.environ['PYTHON_PATH'] = test_dir
        os.environ['PRAGMATIC_SMS_SETTINGS_MODULE'] = 'dummy_settings'
        settings._inst = None
        SettingManager(renew=True)
        self.message_received = 0
        self.message_sent = 0

        class CounterMessageProcessor(MessageProcessor):
             
             ref = self

             def on_receive_message(self, message):
                if isinstance(message, IncomingMessage):
                    self.ref.message_received += 1

             def on_send_message(self, message):
                if isinstance(message, OutgoingMessage):
                    self.ref.message_sent += 1

        processors.base.CounterMessageProcessor = CounterMessageProcessor


    def test_import_class(self):
        # todo: probably should be placed somewhere else
        self.assertEqual(import_class('pragmatic_sms.processors.test.EchoMessageProcessor'),
                         EchoMessageProcessor)


    def test_start_router(self):
        
        router = SmsRouter()
        router.start(limit=1)


    def test_routes_init(self):
        routes = SmsRouter().get_routes()
        self.assertTrue(isinstance(routes['connection'], BrokerConnection))
        self.assertTrue(isinstance(routes['exchange'], Exchange))
        self.assertTrue(isinstance(routes['queues']['incoming_messages'], Queue))
        self.assertTrue(isinstance(routes['queues']['outgoing_messages'], Queue))


    def test_handle_incoming_message(self):

        settings.MESSAGE_PROCESSORS = ('processors.base.CounterMessageProcessor',)
        router = SmsRouter()
        router.setup_consumers()
        router.producer.publish(body={'author': 'foo', 'text': 'bar'}, 
                               routing_key="incoming_messages")
        router.start(timeout=1, limit=1)
        self.assertTrue(self.message_received)


    def test_dispatch_incoming_message(self):

        settings.MESSAGE_PROCESSORS = ('processors.base.CounterMessageProcessor',)
        router = SmsRouter()
        router.setup_consumers()
        router.dispatch_incoming_message(IncomingMessage('foo', 'bar'))
        router.start(timeout=1, limit=1)
        self.assertTrue(self.message_received)


    def test_handle_outgoing_message(self):

        settings.MESSAGE_PROCESSORS = ('processors.base.CounterMessageProcessor',)
        router = SmsRouter()
        router.setup_consumers()
        router.producer.publish(body={'recipient': 'foo', 'text': 'bar'}, 
                               routing_key="outgoing_messages")
        router.start(timeout=1, limit=1)
        self.assertTrue(self.message_sent)


    def test_dispatch_outgoing_message(self):

        settings.MESSAGE_PROCESSORS = ('processors.base.CounterMessageProcessor',)
        router = SmsRouter()
        router.setup_consumers()
        router.dispatch_outgoing_message(OutgoingMessage('foo', 'bar'))
        router.start(timeout=1, limit=1)
        self.assertTrue(self.message_sent)


    def test_several_message_processors(self):

        settings.MESSAGE_PROCESSORS = ('processors.base.CounterMessageProcessor',
                                       'processors.base.CounterMessageProcessor')
        router = SmsRouter()
        router.setup_consumers()
        router.dispatch_outgoing_message(OutgoingMessage('foo', 'bar'))
        router.dispatch_incoming_message(IncomingMessage('foo', 'bar'))
        router.start(timeout=1, limit=1)
        self.assertEqual(self.message_sent, 2)
        self.assertEqual(self.message_received, 2)


    def test_message_send_method(self):

        settings.MESSAGE_PROCESSORS = ('processors.base.CounterMessageProcessor',)
        message = OutgoingMessage('foo', 'bar')
        message.send()
        router = SmsRouter()
        router.setup_consumers()
        router.start(timeout=1, limit=1)
        self.assertEqual(self.message_sent, 1)


    def test_message_dispatch_method(self):

        settings.MESSAGE_PROCESSORS = ('processors.base.CounterMessageProcessor',)
        message = IncomingMessage('foo', 'bar')
        message.dispatch()
        router = SmsRouter()
        router.setup_consumers()
        router.start(timeout=1, limit=1)
        self.assertEqual(self.message_received, 1)


    def test_message_respond_method(self):

        settings.MESSAGE_PROCESSORS = ('processors.base.CounterMessageProcessor',)
        message = IncomingMessage('foo', 'bar')
        response = message.respond('doh')
        router = SmsRouter()
        router.setup_consumers()
        router.start(timeout=1, limit=1)
        self.assertEqual(self.message_sent, 1)
        self.assertTrue(isinstance(response, OutgoingMessage))
        self.assertEqual(response.text, 'doh')
        self.assertEqual(response.recipient, message.author)
        self.assertEqual(response.backend, message.backend)
        self.assertEqual(response.response_to, message)



if __name__ == '__main__':
    unittest2.main()
