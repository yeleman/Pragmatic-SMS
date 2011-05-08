#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4

"""
    Classes to create a message transport
"""


import tempfile
import os
import logging
import socket

from kombu.messaging import Queue, Consumer

from daemon import runner

from pragmatic_sms.routing import SmsRouter
from pragmatic_sms.messages import OutgoingMessage



class MessageTransport(object):
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
                        OutgoingMessage(author=sms.phone_number, 
                                        text=sms.content,
                                        transport=self.name).dispatch()
                        sms = self.get_sms_from_your_super_transport()

                def on_send_message(self, message):
                    self.send_sms_with_your_backend(message.recipient, 
                                                    message.text)

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

    pidfile_timeout = 1


    def __init__(self, name, purpose, *args, **kwargs):

        self.name = name
        self.process_dir = os.path.join(tempfile.gettempdir(), 
                                        'pragmatic_sms', 'transports', name)

        assert purpose in ('send_messages', 'receive_messages')

        try:
            os.makedirs(self.process_dir)
        except OSError:
            pass

        self.purpose = purpose

        self.setup_process_file()

        self.router = SmsRouter()


    # todo: provide self.info, self.debug, etc Male a virtual class Loggagble
    def log(self, *args, **kwargs):
        """
            Proxy method to log using the router log so we can centralize logs
            files easily.
        """
        self.router.logger.log(*args, **kwargs)

        
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
                    OutgoingMessage(author=sms.phone_number, 
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
        pass


    def start_outgoing_messages_loop(self):
        """
            Override this method if you wish to change the behavior of 
            OutgoingMessage Processing in your backend.

            If you don't override this method, the current behavior is to
            create a queue listing for messages in the message exchange
            with the routing key matching 'transportname_outoing_message'.
            It then create a consumer for this queue and 
            registers the on_send_message() method as a callback for it
            to finally start listening for messages.

            Typical use is to avoid overriding this method and prefer
            to override on_send_message().
        """
                
        self.log(logging.INFO, 'Starting transport "%s"' % self.name)
        #print 'Starting transport "%s"' % self.name

        name = '%s_incoming_messages' % self.name
        self.connection = self.router.connection

        self.queue = Queue(name,
                      exchange=self.router.messages_exchange,
                      routing_key=name)

        self.consumer = Consumer(self.connection.channel(), self.queue)
        self.consumer.register_callback(self.handle_outgoing_message)
        self.consumer.consume()
          
        try:  
            while True:    
                try:
                    self.connection.drain_events(timeout=1)
                except socket.timeout: 
                    # this happens when timout is reach and no message is
                    # in the queue
                    pass

        # todo : log the errors

        except self.connection.connection_errors, e:
            self.log("Error while connecting with Kombu: %s" % e)
        except socket.error, e:
            self.log("Socket error: %s" % e)
        except (KeyboardInterrupt, SystemExit) as e:
            self.log('Stopping transport "%s"' % self.name)
        
        try:
            self.connection.release()
        except AssertionError:
            # todo: find why there is this assertion error about state
            pass


        #print ('Transport "%s" stopped' % self.name)
        self.log(logging.INFO, 'Transport "%s" stopped' % self.name)


    def handle_outgoing_message(self, body, message):
        """
            Default callback to the OutgoingMessage queue. This callback take
            a JSON message from the queue, turn it into an OutgoingMessage
            object then pass it to on_send_message().
        """

        self.on_send_message(OutgoingMessage(**body))


    # todo: provide a way to tell a message has been sent
    # todo: provide a way to tell a message has not been sent with errors
    # todo: provide a way to tell a message has been received

    def on_send_message(self, message):
        """
            Override this method if you didn't override 
            start_outgoing_messages_loop() and wish to react everytime a
            new outgoing message arrives.

            Typical use is to just call whatever method of your backend
            really send a message here, so it is called everytime a message
            should be sent.

            If you don't override this method nor start_outgoing_message_loop(),
            there is little chance any message is going to be sent.
        """
        pass


    def setup_process_file(self):
        """
            File descriptors and pid files will be different, according to the
            self.purpose variable, so set up them accordingly.
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
        """

        if self.purpose == "send_messages":
            self.start_outgoing_messages_loop()
        if self.purpose == "receive_messages":
            self.start_incoming_messages_loop()

        

