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
            Return a loaded setting manager, and ensure we have only one instance 
            for the setting manager.
        """
        if not cls._inst or renew:
            cls._inst = cls.load_settings(settings_module, renew)

        return cls._inst


    @classmethod
    def load_settings(cls, settings_module=None, renew=False):
        """
            Load settings from a setting file then attache them as attributes
            to a SettingManager instance.

            To load settings it will try the following:
            - load default settings from the default settings module
            - get attributes from the setting_module parameter
            - treat setting_module as a dict and load the key / values

            If not setting module is passed as a parameter,
            if will look for a module name in the environnement 
            variable 'PSMS_SETTINGS_MODULE' and try to import it.

            If the 'PYTHON_PATH' environnement variable is set, it will be
            added to the Python Path prior to this.

            If 'PSMS_SETTINGS_MODULE' is a path to a '.py' file,
            it will attempt to add the directory containing the file 
            in 'PYTHON_PATH' the set 'PSMS_SETTINGS_MODULE' to the
            module name prior to it.

        """
        settings = cls.extract_settings(default_settings)

        # load user settings
        if settings_module is None:
            try:
                
                module_name = os.environ['PSMS_SETTINGS_MODULE']

                # not a module name but a python file, set the env variable
                # accordingly
                if module_name.endswith('.py'):
                    d = os.path.dirname(os.path.abspath(module_name))
                    os.environ['PYTHON_PATH'] = d
                    module_name = os.path.splitext(module_name)[0]
                    os.environ['PSMS_SETTINGS_MODULE'] = module_name

                sys.path.insert(0, os.environ['PYTHON_PATH'])
                settings_module = __import__(module_name)

            except KeyError:
                raise SettingError('You must pass a setting module or set '\
                                   'the "PSMS_SETTINGS_MODULE" '\
                                   'environnement variable')
            except ImportError:
                raise SettingError('Unable to import %s. Is it in the '\
                                   'PYTHON PATH?' % module_name)
                    
        # turn the module into a dict if it's not one          
        if type(settings_module) != type({}):
            settings_module = cls.extract_settings(settings_module)
    
        # erase default settings with the user ones
        settings.update(settings_module) 

        inst = object.__new__(cls)
        inst.__dict__.update(settings)

        return inst


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