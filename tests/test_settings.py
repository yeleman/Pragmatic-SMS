#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4

import unittest
import os
import sys

test_dir = os.path.dirname(os.path.abspath(__file__))
pragmatic_sms_dir = os.path.dirname(test_dir)
sys.path.insert(0, test_dir)
sys.path.insert(0, pragmatic_sms_dir)
os.environ['PYTHON_PATH'] = test_dir
os.environ['PRAGMATIC_SMS_SETTINGS_MODULE'] = 'test_settings'

import default_settings
import test_settings

from conf import SettingManager, settings
from router import SmsRouter


class TestSettings(unittest.TestCase):


    def setUp(self):
        os.environ['PYTHON_PATH'] = test_dir
        os.environ['PRAGMATIC_SMS_SETTINGS_MODULE'] = 'test_settings'



    def test_extract_settings(self):
        
        settings = SettingManager.extract_settings(test_settings)
        settings.pop('IS_TEST_SETTINGS')
        self.assertEqual(SettingManager.extract_settings(default_settings),
                         settings)
        
        

    def test_settings_are_attached_as_attributes(self):
        
        test = SettingManager({}, renew=True)
        self.assertTrue(getattr(test, 'PERSISTENT_MESSAGE_QUEUES'))


    def test_settings_is_a_singleton(self):
        
        self.assertTrue(SettingManager({}) is SettingManager({}))
                         

    def test_no_settings_fallback_to_environment_variable(self):
        
        settings = SettingManager(test_settings, renew=True)
        self.assertTrue(settings.IS_TEST_SETTINGS)



    def test_no_settings_module_at_all_raise_exception(self):
        
        back = os.environ['PRAGMATIC_SMS_SETTINGS_MODULE']
        del os.environ['PRAGMATIC_SMS_SETTINGS_MODULE']

        try:
            SettingManager()
            self.Fail()
        except:
            pass

        os.environ['PRAGMATIC_SMS_SETTINGS_MODULE'] = back


    def test_user_settings_override_default(self):
        
        test = SettingManager({'PERSISTENT_MESSAGE_QUEUES': False}, renew=True)
        self.assertFalse(getattr(test, 'PERSISTENT_MESSAGE_QUEUES'))


    def test_any_object_will_be_considered_a_setting_module(self):
        
        class AnyObject(object):
            PERSISTENT_MESSAGE_QUEUES = False

        test = SettingManager(AnyObject(), renew=True)
        self.assertFalse(getattr(test, 'PERSISTENT_MESSAGE_QUEUES'))
        

if __name__ == '__main__':
    unittest.main()
