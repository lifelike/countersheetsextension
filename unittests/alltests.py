#!/usr/bin/env python3

import unittest

def add_countersheets_paths():
    import sys
    import os
    sys.path.insert(0, os.getcwd())
    # FIXME temporary for testing
    sys.path.append('/home/pelle/src/extensions-inkscape')
#    sys.path.append('/usr/local/share/inkscape/extensions')
#    sys.path.append('/usr/share/inkscape/extensions')

add_countersheets_paths()

import countersheetstest
import countersheetstyletest
import countertest
import csvcounterdefinitionparsertest
import csvcounterfactorytest

#FIXME it is a bit silly to manually list all tests like this

def make_suite(test):
    loader = unittest.TestLoader()
    return loader.loadTestsFromTestCase(test)

tests = (countersheetstest.CountersheetsTest,
         countersheetstest.SingleCounterTest,
         countersheetstest.LayerTranslationTest,
         countersheetstest.ParseLengthTest,
         countersheetstest.DocumentTopLeftCoordinateConverterTest,
         countertest.SingleCounterTest,
         csvcounterdefinitionparsertest.CSVCounterDefinitionParserTest,
         csvcounterfactorytest.CSVCounterFactoryTest,
         countersheetstyletest.CountersheetStyleTest,
         )

if __name__ == '__main__':
    suite = unittest.TestSuite(list(map(make_suite, tests)))
    runner = unittest.TextTestRunner(verbosity=1)
    runner.run(suite)
