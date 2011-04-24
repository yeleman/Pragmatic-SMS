#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4

"""
    Starts the SMS router with the given settings.
"""

import sys
import os

from optparse import OptionParser

from kombu.connection import BrokerConnection
from kombu.messaging import Exchange, Queue, Producer


usage = "usage: %prog  [options]"
parser = OptionParser()
        
parser.add_option("-s", "--settings", dest="settings", 
                  default='settings', type="str",
                  help="Specified in which module to look for settings")

parser.add_option("-p", "--python-path", dest="python_path", 
                  default='.', type="str",
                  help="Add the following directory to the python path")

(options, args) = parser.parse_args()

sys.path.insert(0, os.path.abspath(options.python_path))

try:
    settings = __import__(options.settings)
except ImportError:
    sys.stderr.write("Unable to import settings module '%s'. Is it in the python path?\n")
    sys.exit(1)

    
