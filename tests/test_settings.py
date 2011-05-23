#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4

import unittest2
import os
import sys

from pragmatic_sms.settings.manager import (declare_settings_module, 
                                            SettingsManager, SettingError)

test_dir = os.path.dirname(os.path.abspath(__file__))
declare_settings_module('dummy_settings', test_dir)

from pragmatic_sms.settings import default_settings
from pragmatic_sms.tests import dummy_settings
from pragmatic_sms.conf import settings
from pragmatic_sms.router import SmsRouter


class TestSettings(unittest2.TestCase):


    def setUp(self):
        os.environ['PYTHON_PATH'] = test_dir
        os.environ['PSMS_SETTINGS_MODULE'] = 'dummy_settings'



    def test_extract_settings(self):
        
        settings = SettingsManager.extract_settings(dummy_settings)
        self.assertTrue(settings['IS_TEST_SETTINGS'])


    def dummy_settings_are_attached_as_attributes(self):
        
        test = SettingsManager({}, renew=True)
        self.assertTrue(getattr(test, 'PERSISTENT_MESSAGE_QUEUES'))


    def dummy_settings_is_a_singleton(self):
        
        self.assertTrue(SettingsManager({}) is SettingsManager({}))
                         

    def test_no_settings_fallback_to_environment_variable(self):
        
        settings = SettingsManager(dummy_settings, renew=True)
        self.assertTrue(settings.IS_TEST_SETTINGS)


    def test_no_settings_module_at_all_raise_exception(self):
        
        del os.environ['PSMS_SETTINGS_MODULE']

        with self.assertRaises(SettingError):
            SettingsManager(renew=True)


    def test_user_settings_override_default(self):
        
        test = SettingsManager({'PERSISTENT_MESSAGE_QUEUES': False}, renew=True)
        self.assertFalse(getattr(test, 'PERSISTENT_MESSAGE_QUEUES'))


    def test_any_object_will_be_considered_a_setting_module(self):
        
        class AnyObject(object):
            PERSISTENT_MESSAGE_QUEUES = False

        test = SettingsManager(AnyObject(), renew=True)
        self.assertFalse(getattr(test, 'PERSISTENT_MESSAGE_QUEUES'))

    
    def test_settings_module_can_be_set_as_just_a_file(self):

        del os.environ['PYTHON_PATH']
        os.environ['PSMS_SETTINGS_MODULE'] = os.path.join(test_dir, 
                                                          'dummy_settings.py')
        test = SettingsManager(renew=True)
        self.assertTrue(test.IS_TEST_SETTINGS)



if __name__ == '__main__':
    unittest2.main()
