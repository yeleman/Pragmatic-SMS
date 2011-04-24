#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4

"""
    Tools to manipulate settings
"""

import os
import sys

import default_settings


class SettingError(Exception):
    pass


class SettingManager(object):
    """
        Provide a central access for the settings of this application,
        with overridable default.
    """

    _inst = None

    def __new__(cls, settings_module=None, renew=False):
        """
            Ensure we have only one instance for the setting manager.
        """
        if not cls._inst or renew:

            settings = cls.extract_settings(default_settings)

            if settings_module is None:
                try:
                    sys.path.insert(0, os.environ['PYTHON_PATH'])
                    module_name = os.environ['PRAGMATIC_SMS_SETTINGS_MODULE']
                    settings_module = __import__(module_name)
                except KeyError:
                    raise SettingError('You must pass a setting module or set '\
                                       'the "PRAGMATIC_SMS_SETTINGS_MODULE" '\
                                       'environnement variable')
                except ImportError:
                    raise SettingError('Unable to import %s. Is it in the '\
                                       'PYTHON PATH?' % module_name)
                                  
            if type(settings_module) != type({}):
                settings_module = cls.extract_settings(settings_module)
        
            
            settings.update(settings_module) # settings_module is a dict

            cls._inst = object.__new__(cls)
            cls._inst.__dict__.update(settings)

        return cls._inst


    @staticmethod
    def extract_settings(settings_module):
        """
            Extract settings from the given module and turn it into
            a dict.

            Each uppercase attribute that does not start with an underscore
            is considered as settings.

            This is a class method to ease override.
        """
        
        attrs = (attr for attr in dir(settings_module) if attr.isupper())
        attrs = (attr for attr in attrs if not attr.startswith('_'))
        return dict((attr, getattr(settings_module, attr)) for attr in attrs)





settings = SettingManager()