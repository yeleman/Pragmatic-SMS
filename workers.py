#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4

"""
    Base classes for all the workers in PSMS
"""

import socket
import logging

from conf import settings
from utils import import_class

from kombu.connection import BrokerConnection
from kombu.messaging import Exchange, Queue, Consumer, Producer
from kombu.exceptions import NotBoundError

# this module is borrowed from the Python source code itself as it's not
# yet available in Python 2.6. Still, it won't work in Python 2.4 or less.
from pragmatic_sms.settings.dictconfig import dictConfig


class WorkerError(Exception):
    pass


class Worker(object):
    """
        Base class of an object declaring exchanges, queues, consumers and
        producers then perform a loop to listen for messages.
    """

    name = "worker"


    def __init__(self):
        """
            Attach routes definition to attributes, connect to message broker
            and initialize producers that will send messages into the queue.
        """

        self.logger = self.get_logger()

        self.run = False
        self.connection = None
        self.channel = None

        self.exchanges = self.get_exchanges()
        self.queues = self.get_queues()
        self.consumers = None
        self.producers = None
        

    def get_logger(self):
        """
            Override this if you want a custom logger instance. Default
            is to use the root logger.
        """
        return logging.getLogger()


    def is_connected(self):
        return bool(self.connection and self.channel)

    
    def get_connection(self):
        """
            Return a kombu connection object to the message broker.
            You must override this otherwise your worker will fail in 
            self.connect
        """
        raise WorkerError('Not implemented')


    def connect(self):
        """
            Start the connection manually. You probably don't need this as
            it is taken care of automatically if you call self.start()
        """

        if not self.is_connected():

            self.connection = self.get_connection()

            self.channel = self.connection.channel()

            self.bind_exchanges()
            self.bind_queues()

            self.consumers = self.get_consumers()
            self.producers = self.get_producers()

            self.on_worker_connected()


    def main_loop(self, timeout=1, limit=-1):
        """
            Start to listen for messages untill one comes or the timeout is
            reached. 

            Use 'limit' for tests when you want to run the worker a given
            number of loops before it stop without having to tell him to.
            Limit should be an integer representing the number of loops.
            This is mainly used for testing purpose and is default to -1,
            which is no limit.
        """
        assert limit > 0

        self.run = True

        self.on_main_loop()

        try:
            while self.run and limit != 0:
                try:
                    self.connection.drain_events(timeout=timeout)
                except socket.timeout: 
                    # this happens when timeout is reached and no message is
                    # in the queue
                    limit -= 1

        except self.connection.connection_errors, e:
            self.logger.error("Error while connecting with Kombu: %s" % e)
            raise
        except socket.error, e:
            self.logger.error("Socket error: %s" % e)
            raise
        except (KeyboardInterrupt, SystemExit) as e:
            self.logger.info("\nStopping %s" % self.name)

        try:
            self.connection.release()
        except AssertionError:
            # todo: find why there is this assertion error about state
            pass

    
    def start(self, timeout=1, limit=-1, force_purge=False):
        """
            Connect the worker to th message broker, purge queues
            if required then starts the main loop to listen
            and react for messages.

            Provide callbacks to perform action before and after the
            main loop starts.

            Use 'limit' for tests when you want to run the worker a given
            number of loops before it stop without having to tell him to.
            Limit should be an integer representing the number of loops.
            This is mainly used for testing purpose and is default to -1,
            which is no limit.
        """

        self.on_worker_starts()

        self.connect()

        self.logger.info('%s is starting' % self.name)

        if force_purge:
            self.purge()

        self.main_loop(timeout, limit)

        self.on_worker_stopped()

        self.logger.info('%s stopped' % self.name)


    def on_worker_starts(self):
        """
            Override this if you want to perform an action when the worker start
        """
        pass


    def on_worker_stopped(self):
        """
            Override this if you want to perform an action when the worker 
            has stoped
        """
        pass


    def on_main_loop(self):
        """
            Action to perform right before entering in the main loop
        """
        pass


    def on_worker_connected(self):
        """
            Override this if you want to perform an action when the worker 
            has connected to the messag broker
        """
        pass


    def get_exchanges(self):
        """
            Override this to return the exchanges you are going to use
            for you worker. It should return a mapping of exchange names 
            and exchanges object.
        """
        pass


    def bind_exchanges(self):
        """
            Loop on all exchanges in the self.exchanges dictionary and 
            bind them to the current channel.

            Called in self.connect() right after the connection with the 
            message broker has been established.

            Assume there is only one channel and one connection.
        """

        for name, exchange in self.exchanges.items():
            self.exchanges[name] = exchange(self.channel)


    def get_queues(self):
        """
            Override this to return the queues you are going to use
            for you worker. It should return a mapping of exchange names 
            and exchanges object.
        """
        pass


    def bind_queues(self):
        """
            Loop on all queues in the self.queues dictionary and 
            bind them to the current channel.

            Called in self.connect() right after the connection with the 
            message broker has been established.

            Assume there is only one channel and one connection.
        """

        for name, queue in self.queues.items():
            self.queues[name] = queue(self.channel)
            self.queues[name].declare()



    def get_consumers(self):
        """
            Override this to return the consumers you are going to use
            for you worker. It should return a mapping of exchange names 
            and exchanges object.

            There are no 'bind_consumers' method as kombu forces you to 
            instanciate producers already bounded
        """
        pass


    def get_producers(self):
        """
            Override this to return the producers you are going to use
            for you worker. It should return a mapping of exchange names 
            and exchanges object.

            There are no 'bind_producers' method as kombu forces you to 
            instanciate producers already bounded
        """
        pass


    def purge(self):
        """
            Remove message from all queues. Call this if you want to reset
            the state of your message queues, like in a unit test.
        """

        try:
            for name, queue in self.queues.iteritems():
                try:
                    queue.purge()

                except AttributeError as e:
                    # This queue can't be purge because of some reference issue
                    # I have yet to figure this out but this doesn't seem to prevent
                    # the system from working rght now and the unit tests pass,
                    # so fingers crossed...
                    self.logger.error('Unable to purge queue %s: %s' % (name, e))
        except NotBoundError:
            raise WorkerError('You cannot call purge on before binding '\
                              'queues. Either start the worker or call '\
                              'connect()')


class PSMSWorker(Worker):
    """
        Worker classe adapted to PSMS type of processing
    """

    name = "PSMS Worker"
    persistent = settings.PERSISTENT_MESSAGE_QUEUES


    def get_logger(self):
        """
            Return a loggger instance configured as described in the settings
            file.
        """
        dictConfig(settings.LOGGING)
        return logging.getLogger('psms')

    
    def get_queues(self):
        """
            Return a dict with queues all worker should be able
            to use:

            - log queue to all the router to receive logs from external process
            - undelivered kombo message queues to handle orphan messages
        """
        queues = {} 

        queues['logs'] = Queue('logs', 
                                 exchange=self.exchanges['psms'],
                                 routing_key="logs",
                                 durable=False)

                        
        queues['undelivered_kombu_message'] = Queue('ae.undeliver', 
                                              exchange=self.exchanges['psms'],
                                              routing_key="ae.undeliver",
                                              durable=self.persistent)
                                              
        return queues                                      


    def get_connection(self):
        """
            Return a connection instance configured as described in the settings
            file.
        """
        transport = settings.MESSAGE_BROKER['transport']
        transport_options = settings.MESSAGE_BROKER.get("options", {})

        return BrokerConnection(transport=transport, **transport_options)


    def get_exchanges(self):
        """
            Define one exchange only for all messages and log. Routing
            will be done only at the routing key level.
        """

        # todo: use topic routing ?
        # http://packages.python.org/kombu/reference/kombu.entity.html?#kombu.entity.Exchange.type

        return {'psms': Exchange("psms", "direct", durable=self.persistent)}


    def get_producers(self):
        """
            One producer only for all messages, since we have only one exchange.
        """
        return {'psms': Producer(self.channel, exchange=self.exchanges['psms'])}


    def start(self, timeout=1, limit=-1, force_purge=None):
        """
            Ensure force purge if required by the settting file
        """

        purge = not getattr(settings, 'PERSISTENT_MESSAGE_QUEUES', True)
        if force_purge is not None:
            purge = force_purge

        return Worker.start(self, timeout, limit, force_purge=purge)


    def log(self, lvl, msg, *args, **kwargs):
        """
            Push this log message into the log queue so the router
            can pop it and print it on the main terminal.
        """
        log = {'lvl': lvl, 'msg': msg, 'args': args, 'kwargs': kwargs}
        self.producers['psms'].publish(body=log, routing_key="logs")  
