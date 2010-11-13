#!/usr/bin/env python

import unittest

import csvtest
import countersheetstest
import countersheetstyletest
import countertest
import counterdefinitionparsertest
import counterfactorytest

#FIXME it is a bit silly to manually list all tests like this

def make_suite(test):
    return unittest.makeSuite(test, 'test_')

tests = (csvtest.CSVTest,
         countersheetstest.CountersheetsTest,
         countersheetstest.SingleCounterTest,
         countertest.SingleCounterTest,
         counterdefinitionparsertest.CounterDefinitionParserTest,
         counterfactorytest.CounterFactoryTest,
         countersheetstyletest.CountersheetStyleTest,
         )

if __name__ == '__main__':
    suite = unittest.TestSuite(map(make_suite, tests))
    runner = unittest.TextTestRunner(verbosity=1)
    runner.run(suite)
