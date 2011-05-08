#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4

"""
    The infamous utils.py module with all the things a dev is usually too lazy
    to sort properly.
"""

import os


def import_class(class_path):
    """
        Import a class dynamically, given it's dotted path.
    """

    module_name, class_name = class_path.rsplit('.', 1)
    try:
        return getattr(__import__(module_name, fromlist=[class_name]), class_name)
    except AttributeError:
        raise ImportError('Unable to import %s' % class_path)


