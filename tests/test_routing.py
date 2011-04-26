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

from conf import SettingManager, settings
from routing import SmsRouter, OutgoingMessage, IncomingMessage
from utils import import_class
from pragmatic_sms.processors.test import EchoMessageProcessor


class TestRouting(unittest2.TestCase):


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



if __name__ == '__main__':
    unittest2.main()
