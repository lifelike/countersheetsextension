#!/usr/bin/env python2.6

import unittest

def add_countersheets_paths():
    import sys
    import os
    sys.path.insert(0, os.getcwd())
    sys.path.append('/usr/local/share/inkscape/extensions')
    sys.path.append('/usr/share/inkscape/extensions')

add_countersheets_paths()

import csvtest
import countersheetstest
import countersheetstyletest
import countertest
import csvcounterdefinitionparsertest
import csvcounterfactorytest

#FIXME it is a bit silly to manually list all tests like this

def make_suite(test):
    return unittest.makeSuite(test, 'test_')

tests = (csvtest.CSVTest,
         countersheetstest.CountersheetsTest,
         countersheetstest.SingleCounterTest,
         countertest.SingleCounterTest,
         csvcounterdefinitionparsertest.CSVCounterDefinitionParserTest,
         csvcounterfactorytest.CSVCounterFactoryTest,
         countersheetstyletest.CountersheetStyleTest,
         )

if __name__ == '__main__':
    suite = unittest.TestSuite(map(make_suite, tests))
    runner = unittest.TextTestRunner(verbosity=1)
    runner.run(suite)
