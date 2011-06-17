#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4

"""
    Classes to create a message transport
"""


import os
import sys
import logging
import socket
import subprocess

from kombu.messaging import Queue, Consumer
from kombu.exceptions import NotBoundError

from daemon import runner

from pragmatic_sms.routing import SmsRouter, RoutingError
from pragmatic_sms.messages import OutgoingMessage
from pragmatic_sms.conf import settings
from pragmatic_sms.workers import PSMSWorker

# todo : provide method stop_in/out_messsage loop


# todo: provide purge for message transports

class MessageTransportError(RoutingError):
    pass


class MessageTransport(PSMSWorker):
    """
        Inherit from this class if you wish to create your own message
        transport. This class is not meant to be instanciated directly.

        A tranport is composed of two part:
        
        1 - one part that get real SMS message and turn them into 
            IncomingMessage objects
        2 - one part that receive OutgoingMessage objects and send real SMS
            message from them

        To create your own message transport, you must inherit from this class,
        override some methods (see later), and then add your message transport
        class to the settings in MESSAGE_TRANSPORTS.


        E.G:


            from pramatic_sms.transports.base import MessageTransport
            from pragmatic_sms.messages import OutgoingMessage

            YourMessageTansport(MessageTransport):

                def __init__(self, name, purpose, arg1, arg2):
                    MessageTransport.__init__(self, name, purpose)
                    self.arg1 = arg1
                    self.arg2 = arg2

                def start_incoming_messages_loop(self):
                    
                    sms = self.get_sms_from_your_super_transport()
                    while sms:
                        IncomingMessage(author=sms.phone_number, 
                                         text=sms.content,
                                         transport=self.name).dispatch()
                        sms = self.get_sms_from_your_super_transport()

                def on_send_message(self, message):
                    self.send_sms_with_your_backend(message.recipient, 
                                                    message.text)
                    return True

        Then in your settings file:

            MESSAGE_TRANSPORTS = {
                'default': {
                    'backend': 'yourapp.your_message_transport.YourMessageTransport',
                    'options': {'arg1': 'foo': 'arg2': 'bar'}
                }
            }

        The SmsRouter thread will automatically run two subprocesses for
        each message transport class, one for incoming messages, the other
        one for outgoing messages.

        It will terminate these processes as well automatically on shut down.
        
        If you wish to control what happens when your backend receive a message,
        override start_incoming_messages_loop(). It will be run as a background
        process automatically for you. 

        If you wish to control what happens when your backend must send a message,
        override on_send_message(). It will be called as a callback for each
        new message to be sent. 

        If you want more control over the way to process message to be send, 
        override start_incoming_messages_loop(). It will be run as a background
        process automatically for you. 

        See the each method docstring for more infos.

        Remember your message transport class will be instanciated TWICE in 
        two different processes, so be aware of concurrency. States are not 
        shared but other ressources such as files will be access concurrently.

        In the rare case where you need a different setup for outgoing messages
        and incoming messages processing, you can check the self.purpose
        variable. It can be either 'send_messages' or 'receive_messages'.

        When you'll need to debug your backend, you will not find informations
        in the pragmatic_sms logs because these are logs that the program does
        when it at least started correctly. You must check for the usual 
        stderr, which is redirected in into a file. The file path is built
        this way:

        sterr_path = os.path.join(tempfile.gettempdir(), 
                                        'pragmatic_sms',
                                        'transports',
                                        transport_name, 
                                        '%s_stderr' % self.purpose)

        For example : /tmp/pragmatic_sms/transports/default/receive_messages_stderr
    """

    RUNNER_SCRIPT = os.path.join(settings.PSMS_DIR, 'transports', 'runner.py')

    pidfile_timeout = 1


    def __init__(self, name, purpose='send_messages', *args, **kwargs):

        self.name = name

        PSMSWorker.__init__(self)
        
        self.process_dir = os.path.join(settings.TEMP_DIR, 'transports', name)

        assert purpose in ('send_messages', 'receive_messages')

        try:
            os.makedirs(self.process_dir)
        except OSError:
            pass

        self.purpose = purpose

        self._setup_process_fd()

        
    def start_incoming_messages_loop(self):
        """
            Override this method if you wish to start any process requiring
            to wait for events in order to look for new incoming SMS
            that your backend will then pass to the SMS router.

            Typical use is to check the modem or the SMPP server for activity,
            get the message from it, create an IncomingMessage object with
            it and call dispatch on it, in a while loop. E.G:

                sms = self.get_sms_from_your_super_transport()
                while sms:
                    IncomingMessage(author=sms.phone_number, 
                                    text=sms.content,
                                    transport=self.name).dispatch()
                    sms = self.get_sms_from_your_super_transport()

            Another way to do that would be to start here a webserver waiting
            for POST request with the message data, then create
            the IncommingMessage for each POST request.

            This method will be called automatically by the router and run
            as a background process for your.

            If you don't override this method, no loop is started and 
            you are expected to provide incoming messages manually. If you 
            don't, the SmsRouter will simply not receive IncomingMessage 
            from your backend but won't complain.
        """
        self.log(logging.INFO, 
                 'Transport "%s" starts listening for incoming messages' % self.name)
        self.log(logging.INFO, 
                 'Transport "%s" stops listening for incoming messages' % self.name)


    def start_outgoing_messages_loop(self, *args, **kwargs):
        """
            You usually don't want to override this method, as it just 
            calls the standard worker behavior for the main loop.
        """
        return self.start(*args, **kwargs)


    def get_queues(self):
        """
            We need only one queue for outgoing message
        """
        queues = PSMSWorker.get_queues(self)
        name = "%s_transport" % self.name
        queues[name] = Queue(name, exchange=self.exchanges['psms'],
                               routing_key=name)
        return queues


    def get_consumers(self):
        """
            Only one consumer for the only transport queue
        """
        name = "%s_transport" % self.name
        consumer = Consumer(self.channel, self.queues[name])
        consumer.register_callback(self.handle_outgoing_message)
        consumer.consume()
        return {name: consumer}


    def handle_outgoing_message(self, body, message):
        """
            Default callback to the OutgoingMessage queue. This callback take
            a JSON message from the queue, turn it into an OutgoingMessage
            object then pass it to on_send_message().
        """
        if self.on_send_message(OutgoingMessage(**body)):
            message.ack()


    # todo: provide a way to tell a message has been sent
    # todo: provide a way to tell a message has not been sent with errors
    # todo: provide a way to tell a message has been received

    def on_send_message(self, message):
        """
            Override this method to react everytime a
            new outgoing message arrives.

            Typical use is to just call whatever method of your backend
            really send a message here, so it is called everytime a message
            should be sent.

            If you don't override this method,,
            there is little chance any message is going to be sent.

            Return True is the message has been sent. If you don't, the message
            will be kept in the queue of messages to be sent.
        """
        pass


    def _setup_process_fd(self):
        """
            Implementation details for daemonizeation.

            File descriptors and pid files will be different, according to the
            self.purpose variable, so setting up them accordingly.
        """
        self.stdout_path = os.path.join(self.process_dir, '%s_stdout' % self.purpose)
        self.stdin_path = os.path.join(self.process_dir, '%s_stdin' % self.purpose)
        self.stderr_path = os.path.join(self.process_dir, '%s_stderr' % self.purpose)
        self.pidfile_path =  os.path.join(self.process_dir, '%s.pid' % self.purpose)

        open(self.stdout_path, 'a').close()
        open(self.stdin_path , 'a').close()


    def run(self):
        """
            Start running the backend according to what you want to do with it.
            This is choosen by setting the self.purpose attribute.

            "send_message" will start listing for message to send by 
            running start_outgoing_messages_loop() 

            "receive_message" will start listing for message to receive by 
            running start_incoming_messages_loop() 

            This is an legacy of the way the Python daemon lib
            is implemented, requiring this method to exists.
        """

        if self.purpose == "send_messages":
            self.start_outgoing_messages_loop()
        if self.purpose == "receive_messages":
            self.start_incoming_messages_loop()


    def manage_message_transport(self, action, purpose):
        """
            Call the transport runner with the current transport as
            name argument, the current settings module as settings argument,
            and the action and purpose from this method arguments.
        """

        subprocess.call([sys.executable,
                         self.RUNNER_SCRIPT,
                         action,
                         self.name,
                         purpose,
                         '-p %s' % os.environ['PYTHON_PATH'],
                         '-s %s' % os.environ['PSMS_SETTINGS_MODULE']])            


    def start_receiving_messages_daemon(self):
        """
            Call manage_message_transport() with action as start, and 
            purpose as receive_messages
        """
        self.manage_message_transport('start', 'receive_messages')


    def start_sending_messages_daemon(self):
        """
            Call manage_message_transport() with action as start, and 
            purpose as send_messages
        """
        self.manage_message_transport('start', 'send_messages')


    def start_daemons(self):
        """
            Start all daemons for this transport
        """
        self.start_receiving_messages_daemon()
        self.start_sending_messages_daemon()


    def stop_receiving_messages_daemon(self):
        """
            Call manage_message_transport() with action as stop, and 
            purpose as receive_messages
        """
        self.manage_message_transport('stop', 'receive_messages')


    def stop_sending_messages_daemon(self):
        """
            Call manage_message_transport() with action as stop, and 
            purpose as send_messages
        """
        self.manage_message_transport('stop', 'send_messages')


    def stop_daemons(self):
        """
            Stop all daemons for this transport
        """
        self.stop_receiving_messages_daemon()
        self.stop_sending_messages_daemon()


    def restart_receiving_messages_daemon(self):
        """
            Call manage_message_transport() with action as restart, and 
            purpose as receive_messages
        """
        self.manage_message_transport('restart', 'receive_messages')


    def restart_sending_messages_daemon(self):
        """
            Call manage_message_transport() with action as restart, and 
            purpose as send_messages
        """
        self.manage_message_transport('restart', 'send_messages')


    def restart_daemons(self):
        """
            Restart all daemons for this transport
        """
        self.restart_receiving_messages_daemon()
        self.restart_sending_messages_daemon()        
