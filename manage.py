#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4

"""
    Starts the SMS router with the given settings.
"""

import sys
import os
import argparse

from kombu.connection import BrokerConnection
from kombu.messaging import Exchange, Queue, Producer



def start_router(args):
    try:

        from pragmatic_sms.routing import SmsRouter
        router = SmsRouter()
        router.start()
    except Exception as e:
        try:
            from pragmatic_sms.conf import settings
        except:
            sys.stderr.write("Unable to import router settings."\
                  " You must pass a setting module using the --setting option or"\
                  " set the \"PSMS_SETTINGS_MODULE\" environnement variable. If "\
                  " you did so, ensure your setting module contains no error "\
                  " and is in the Python Path. You can ask manage.py to add a "\
                  " directory to the Python Path with the --python_path option "\
                  " or you can pass to --settings a path to the *py file directly.\n")
           
        else:
            raise e
    

def fake_sms(args):
    try:

        from pragmatic_sms.transports.cmd import CmdMessageTransport
        transport = CmdMessageTransport(args.transport_name, 'receive_messages')
        transport.fake_sms_reception(args.phone_number, " ".join(args.text))
    except Exception as e:
        try:
            from pragmatic_sms.conf import settings
        except:
            sys.stderr.write("Unable to import router settings."\
                  " You must pass a setting module using the --setting option or"\
                  " set the \"PSMS_SETTINGS_MODULE\" environnement variable. If "\
                  " you did so, ensure your setting module contains no error "\
                  " and is in the Python Path. You can ask manage.py to add a "\
                  " directory to the Python Path with the --python_path option "\
                  " or you can pass to --settings a path to the *py file directly.\n")
           
        else:
            raise e



parser = argparse.ArgumentParser(description='Manage most Pragmatic SMS actions')

subparsers = parser.add_subparsers(title='Subcommands')

# subcomand to start the router
runrouter_parser = subparsers.add_parser('runrouter', 
                                         help='Start the SMS router')
runrouter_parser.add_argument('-s', '--settings', default='settings', type=str,
                             help="Specified in which module to look for settings",
                             )
runrouter_parser.add_argument("-p", "--python-path", dest="python_path", 
                    default='.', type=str, 
                    help="Add the following directory to the python path")

runrouter_parser.set_defaults(func=start_router)


# subcomand to start to simulate an incoming SMS
runrouter_parser = subparsers.add_parser('fake_sms', 
                                         help='Fake an incoming message')

runrouter_parser.add_argument('text', default='settings', type=str, nargs='+',
                             help="The text you want to fake being received",
                             )
runrouter_parser.add_argument('-n', '--phone-number', default='+555555', type=str,
                             help="The phone number the SMS is supposed to come from",
                             )
runrouter_parser.add_argument('-s', '--settings', default='settings', type=str,
                             help="Specified in which module to look for settings",
                             )
runrouter_parser.add_argument("-p", "--python-path", dest="python_path", 
                    default='.', type=str, 
                    help="Add the following directory to the python path")

runrouter_parser.add_argument("-t", "--transport-name", dest="transport_name", 
                    default='cmd', type=str, 
                    help="Register the CMD transport to the router with this name")

runrouter_parser.set_defaults(func=fake_sms)

args = parser.parse_args()

os.environ['PYTHON_PATH'] = args.python_path
os.environ['PSMS_SETTINGS_MODULE'] = args.settings

args.func(args)



    
