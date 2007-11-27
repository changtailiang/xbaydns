#!/usr/bin/env python
# encoding: utf-8
"""
__init__.py

Created by 黄 冬 on 2007-11-19.
Copyright (c) 2007 XbayDNS Team. All rights reserved.
"""

import unittest
from xbaydns.tests import commandtest,initconftest,namedconftest,sysintergratetest

def suite():
    suite = unittest.TestSuite()
    suite.addTest(commandtest.suite())
    suite.addTest(initconftest.suite())
    suite.addTest(namedconftest.suite())
    suite.addTest(sysintergratetest.suite())
    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='suite')