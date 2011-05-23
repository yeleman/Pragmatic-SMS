#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4

"""
    Start | stop | restart a message transport
"""


import sys
import os
import argparse
import tempfile
import os

from daemon import runner

from pragmatic_sms.utils import import_class



def start_message_transport(args):
    """
        Import the message transport class, instanciate it and turn in into
        a daemon or stop / reload it according to action.
    """

    action, name, purpose = args.action, args.name, args.purpose

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
        sys.exit(1)

    try:
        transport = settings.MESSAGE_TRANSPORTS[name]
        module = import_class(transport['backend'])
    except KeyError:
        sys.stderr.write("Unable find message transport named '%s'."\
                        " Check your settings.MESSAGE_TRANSPORTS list.\n" % name)
        sys.exit(1)

    try:
        runner.DaemonRunner(module(name, purpose, **transport['options'])).do_action()
    except runner.DaemonRunnerStopFailureError as e:
        # ignore the error if it's about a messing PID file lock
        # it just mean the process finished before 
        if 'PID' not in str(e): 
            raise
        sys.stderr.write("Transport '%s' is not running\n" % name)
     

parser = argparse.ArgumentParser(description='Start|stop|reload pragmatic sms message transport')


parser.add_argument('-s', '--settings', default='settings', type=str,
                             help="Specified in which module to look for settings",
                             )
parser.add_argument("-p", "--python-path", dest="python_path", 
                    default='.', type=str, 
                    help="Add the following directory to the python path")

parser.add_argument("action", help="start|stop|reload")

parser.add_argument("name",  help="The name of the transport backend to start")

parser.add_argument("purpose", 
                    help="Wether to start the backend to send or receive message")

parser.set_defaults(func=start_message_transport)

args = parser.parse_args()

os.environ['PYTHON_PATH'] = args.python_path.strip()
os.environ['PSMS_SETTINGS_MODULE'] = args.settings.strip()

args.func(args)









