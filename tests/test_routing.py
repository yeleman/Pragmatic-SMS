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
        self.message_received = False

        class AddIncomingMessageTestMessageProcessor(MessageProcessor):
             
             ref = self

             def on_receive_message(self, message):
                if isinstance(message, IncomingMessage):
                    self.ref.message_received = True


        processors.base.AddIncomingMessageTestMessageProcessor = AddIncomingMessageTestMessageProcessor


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

        settings.MESSAGE_PROCESSORS = ('processors.base.AddIncomingMessageTestMessageProcessor',)
        router = SmsRouter()
        router.setup_consumers()
        mp = processors.base.AddIncomingMessageTestMessageProcessor()


        router.producer.publish(body={'author': 'foo', 'text': 'bar'}, 
                               routing_key="incoming_messages")
        router.start(timeout=1, limit=1)
    # def test_add_incoming_message(self):

    #     class AddIncomingMessageTestMessageProcessor(MessageProcessor):
             
    #          ref = self

    #          def on_receive_message(self, message):
    #             if isinstance(message, IncomingMessage):
    #                 self.message_received = True
    #                 return True

    #     processors.base.AddIncomingMessageTestMessageProcessor = AddIncomingMessageTestMessageProcessor


    #     settings.MESSAGE_PROCESSORS = ('processors.base.AddIncomingMessageTestMessageProcessor',)
    #     router = SmsRouter()
    #     router.setup_consumers()
    #     mp = AddIncomingMessageTestMessageProcessor()
    #     router.incoming_messages_consumer.register_callback(mp.handle_incoming_message)
    #     router.incoming_messages_consumer.consume()

    #     router.add_incoming_message(IncomingMessage('foo', 'bar'))

    #     router.start(timeout=1, limit=1)

        self.assertTrue(self.message_received)




if __name__ == '__main__':
    unittest2.main()
