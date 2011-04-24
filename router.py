#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4

"""
    Starts the SMS router with the given settings.
"""



    
class SmsRouter(object):
    """
        Start and stop the message processors and the backends
    """
    pass


class Message(object):
    """
        Base message class with attributes and methods common to incoming and
        outgoing messages.
    """


    def __init__(self, author, recipient, text):
        self.author = author
        self.recipient = recipient
        self.text = text



class OutgoingMessage(Message):
    pass
    

class Incoming(Message):
    pass

    

        
        




    
