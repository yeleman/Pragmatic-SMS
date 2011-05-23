#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4

import unittest2
import os
import sys
import threading
import time

from pragmatic_sms.utils import check_output
from pragmatic_sms.settings.manager import declare_settings_module

declare_settings_module('pragmatic_sms.tests.dummy_settings')

from pragmatic_sms.conf import settings
from pragmatic_sms.transports.test import CounterMessageTransport
from pragmatic_sms.messages import OutgoingMessage
from pragmatic_sms.routing import SmsRouter


class TestRouting(unittest2.TestCase):


    def setUp(self):
        CounterMessageTransport.reset()
        self.router = SmsRouter()
        self.router.setup_consumers()
        self.transport = CounterMessageTransport('default', 'send_messages')


    def tearDown(self):
        self.transport.stop_daemons()


    def count_processes(self, pattern):
        """
            Return the number of process running matching this regexp
        """

        out = check_output('ps aux | grep %s | grep -v grep | wc -l' % (
                            pattern,), shell=True)
        return int(out)


    def test_start_daemons(self):
        
        self.transport.start_daemons()

        self.assertEqual(self.count_processes("default.*receive_messages"), 1)
        self.assertEqual(self.count_processes("default.*send_messages"), 1)


    def test_stop_daemons(self):

        self.transport.start_daemons()
        self.transport.stop_daemons()
        time.sleep(2)
        self.assertEqual(self.count_processes("default.*receive_messages"), 0)
        self.assertEqual(self.count_processes("default.*send_messages"), 0)


    def test_outgoing_message(self):

        OutgoingMessage('foo', 'bar').send()
        thread = threading.Thread(target= self.router.start, args=(1, 1, True))
        self.transport.start_outgoing_messages_loop(timeout=1, limit=1)
        self.assertEqual(CounterMessageTransport.message_sent, 1)


if __name__ == '__main__':
    unittest2.main()
