#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4

import unittest2
import os
import sys
import threading
import time

from kombu.connection import BrokerConnection
from kombu.messaging import Exchange, Queue, Consumer, Producer

from pragmatic_sms.utils import check_output
from pragmatic_sms.settings.manager import declare_settings_module

test_dir = os.path.dirname(os.path.abspath(__file__))
declare_settings_module('dummy_settings', test_dir)

from pragmatic_sms.conf import settings
from pragmatic_sms.transports.base import MessageTransportError
from pragmatic_sms.transports.test import (CounterMessageTransport,
                                           FileCounterMessageTransport)
from pragmatic_sms.messages import OutgoingMessage
from pragmatic_sms.routing import SmsRouter
from pragmatic_sms.workers import WorkerError, PSMSWorker


class TestRouting(unittest2.TestCase):


    def setUp(self):
        CounterMessageTransport.reset()
        FileCounterMessageTransport.reset()
        self.router = SmsRouter()
        self.router.connect()
        self.router.purge()
        self.transport = CounterMessageTransport('default', 'send_messages')


    def tearDown(self):
        self.transport.stop_daemons()
        try:
            self.transport.purge()
        except WorkerError: 
            pass


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


    def test_manual_outgoing_message(self):

      
        OutgoingMessage('foo', 'bar').send()

        self.router.start(1, 1)
        print "here"
        self.transport.start_outgoing_messages_loop(1, 1)
        self.assertEqual(CounterMessageTransport.message_sent, 1)



    # todo : make the router purge() call transport purge



if __name__ == '__main__':
    unittest2.main()
