#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4

import unittest2
import os
import sys

from kombu.connection import BrokerConnection
from kombu.messaging import Exchange, Queue

import dummy_settings


from pragmatic_sms.settings.manager import declare_settings_module, SettingsManager

test_dir = os.path.dirname(os.path.abspath(__file__))
declare_settings_module('dummy_settings', test_dir)

from pragmatic_sms.conf import settings
from pragmatic_sms.routing import SmsRouter, OutgoingMessage, IncomingMessage
from pragmatic_sms.utils import import_class
from pragmatic_sms.processors.test import EchoMessageProcessor, CounterMessageProcessor
from pragmatic_sms.processors.base import MessageProcessor
from pragmatic_sms.settings import default_settings



class TestRouting(unittest2.TestCase):


    def setUp(self):
        os.environ['PYTHON_PATH'] = test_dir
        os.environ['PSMS_SETTINGS_MODULE'] = 'dummy_settings'
        settings._inst = None
        SettingsManager(renew=True)
        settings.MESSAGE_PROCESSORS = ( 'pragmatic_sms.processors.test.CounterMessageProcessor',)
        CounterMessageProcessor.reset()
        self.router = SmsRouter()
        self.router.setup_consumers()


    def test_import_class(self):
        # todo: probably should be placed somewhere else
        self.assertEqual(import_class('pragmatic_sms.processors.test.EchoMessageProcessor'),
                         EchoMessageProcessor)


    def test_start_router(self):
        
        self.router.start(limit=1)


    def test_routes_init(self):
        routes = self.router.get_routes()
        self.assertTrue(isinstance(routes['connection'], BrokerConnection))
        self.assertTrue(isinstance(routes['exchanges']['messages'], Exchange))
        self.assertTrue(isinstance(routes['exchanges']['logs'], Exchange))
        self.assertTrue(isinstance(routes['queues']['incoming_messages'], Queue))
        self.assertTrue(isinstance(routes['queues']['outgoing_messages'], Queue))
        self.assertTrue(isinstance(routes['queues']['logs'], Queue))


    def test_handle_incoming_message(self):

        self.router.message_producer.publish(body={'author': 'foo', 'text': 'bar'}, 
                               routing_key="incoming_messages")
        self.router.start(timeout=1, limit=1)
        self.assertTrue(CounterMessageProcessor.message_received)


    def test_dispatch_incoming_message(self):

        self.router.dispatch_incoming_message(IncomingMessage('foo', 'bar'))
        self.router.start(timeout=1, limit=1)
        self.assertTrue(CounterMessageProcessor.message_received)


    def test_handle_outgoing_message(self):

        self.router.message_producer.publish(body={'recipient': 'foo', 'text': 'bar'}, 
                                        routing_key="outgoing_messages")
        self.router.start(timeout=1, limit=1)
        self.assertTrue(CounterMessageProcessor.message_sent)


    def test_dispatch_outgoing_message(self):

        self.router.dispatch_outgoing_message(OutgoingMessage('foo', 'bar'))
        self.router.start(timeout=1, limit=1)
        self.assertTrue(CounterMessageProcessor.message_sent)


    def test_several_message_processors(self):

        settings.MESSAGE_PROCESSORS += ('pragmatic_sms.processors.test.CounterMessageProcessor',)
        router = SmsRouter()
        router.setup_consumers()
        router.dispatch_outgoing_message(OutgoingMessage('foo', 'bar'))
        router.dispatch_incoming_message(IncomingMessage('foo', 'bar'))
        router.start(timeout=1, limit=1)
        self.assertEqual(CounterMessageProcessor.message_sent, 2)
        self.assertEqual(CounterMessageProcessor.message_received, 2)


    def test_message_send_method(self):

        message = OutgoingMessage('foo', 'bar')
        message.send()
        self.router.start(timeout=1, limit=1)
        self.assertEqual(CounterMessageProcessor.message_sent, 1)


    def test_message_dispatch_method(self):

        message = IncomingMessage('foo', 'bar')
        message.dispatch()
        self.router.start(timeout=1, limit=1)
        self.assertEqual(CounterMessageProcessor.message_received, 1)


    def test_message_respond_method(self):

        message = IncomingMessage('foo', 'bar')
        response = message.respond('doh')
        self.router.start(timeout=1, limit=1)
        self.assertEqual(CounterMessageProcessor.message_sent, 1)
        self.assertTrue(isinstance(response, OutgoingMessage))
        self.assertEqual(response.text, 'doh')
        self.assertEqual(response.recipient, message.author)
        self.assertEqual(response.backend, message.backend)
        self.assertEqual(response.response_to, message)



if __name__ == '__main__':
    unittest2.main()
