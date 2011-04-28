#!/usr/bin/env python
#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4

import unittest2
import os
import sys
import datetime

from kombu.connection import BrokerConnection
from kombu.messaging import Exchange, Queue

from pragmatic_sms.settings.manager import declare_settings_module, SettingsManager

test_dir = os.path.dirname(os.path.abspath(__file__))
declare_settings_module('dummy_settings', test_dir)

from pragmatic_sms.settings import default_settings
from pragmatic_sms.tests import dummy_settings
from pragmatic_sms.conf import settings
from pragmatic_sms.routing import SmsRouter, OutgoingMessage, IncomingMessage, Message


class TestMessage(unittest2.TestCase):


    def test_create_message(self):
        
        outgoing_message = OutgoingMessage('to', 'test')
        incomming_message = IncomingMessage('from', 'test')


    def test_message_equality(self):


        outgoing_message = OutgoingMessage('to', 'test')
        incoming_message = IncomingMessage('from', 'test')

        self.assertNotEqual(outgoing_message, incoming_message)
        self.assertNotEqual(outgoing_message, OutgoingMessage('you', 'test'))
        self.assertEqual(outgoing_message, 
                         OutgoingMessage('foo', 'bar', id=outgoing_message.id))

    
    def test_serialize_date(self):

        d = datetime.datetime.now()
        s = Message.serialize_date(d)

        self.assertTrue(isinstance(s, str))
        self.assertEqual(d, Message.unserialize_date(s))


    def test_to_dict(self):

        m = OutgoingMessage("to", "test")
        d = m.to_dict()
        self.assertIn("recipient", d)
        self.assertIn("backend", d)
        self.assertIn("creation_date", d)
        self.assertIn("id", d)
        self.assertIn("response_to", d)

        m = IncomingMessage("from", "test")
        d = m.to_dict()
        self.assertIn("author", d)
        self.assertIn("backend", d)
        self.assertIn("reception_date", d)
        self.assertIn("id", d)


    



if __name__ == '__main__':
    unittest2.main()
