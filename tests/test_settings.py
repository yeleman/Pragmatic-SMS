#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4

import unittest2
import os
import sys

test_dir = os.path.dirname(os.path.abspath(__file__))
pragmatic_sms_dir = os.path.dirname(test_dir)
sys.path.insert(0, test_dir)
sys.path.insert(0, pragmatic_sms_dir)
os.environ['PYTHON_PATH'] = test_dir
os.environ['PRAGMATIC_SMS_SETTINGS_MODULE'] = 'dummy_settings'

import default_settings
import dummy_settings

from conf import SettingManager, SettingError, settings
from router import SmsRouter


class TestSettings(unittest2.TestCase):


    def setUp(self):
        os.environ['PYTHON_PATH'] = test_dir
        os.environ['PRAGMATIC_SMS_SETTINGS_MODULE'] = 'dummy_settings'



    def test_extract_settings(self):
        
        settings = SettingManager.extract_settings(dummy_settings)
        settings.pop('IS_TEST_SETTINGS')
        self.assertEqual(SettingManager.extract_settings(default_settings),
                         settings)
        
        

    def dummy_settings_are_attached_as_attributes(self):
        
        test = SettingManager({}, renew=True)
        self.assertTrue(getattr(test, 'PERSISTENT_MESSAGE_QUEUES'))


    def dummy_settings_is_a_singleton(self):
        
        self.assertTrue(SettingManager({}) is SettingManager({}))
                         

    def test_no_settings_fallback_to_environment_variable(self):
        
        settings = SettingManager(dummy_settings, renew=True)
        self.assertTrue(settings.IS_TEST_SETTINGS)



    def test_no_settings_module_at_all_raise_exception(self):
        
        del os.environ['PRAGMATIC_SMS_SETTINGS_MODULE']

        with self.assertRaises(SettingError):
            SettingManager(renew=True)


    def test_user_settings_override_default(self):
        
        test = SettingManager({'PERSISTENT_MESSAGE_QUEUES': False}, renew=True)
        self.assertFalse(getattr(test, 'PERSISTENT_MESSAGE_QUEUES'))


    def test_any_object_will_be_considered_a_setting_module(self):
        
        class AnyObject(object):
            PERSISTENT_MESSAGE_QUEUES = False

        test = SettingManager(AnyObject(), renew=True)
        self.assertFalse(getattr(test, 'PERSISTENT_MESSAGE_QUEUES'))

    
    def test_settings_module_can_be_set_as_just_a_file(self):

        del os.environ['PYTHON_PATH']
        os.environ['PRAGMATIC_SMS_SETTINGS_MODULE'] = 'dummy_settings.py'
        test = SettingManager(renew=True)
        self.assertTrue(test.IS_TEST_SETTINGS)



if __name__ == '__main__':
    unittest2.main()
