#!/usr/bin/env python2.6
# -*- coding: utf-8 -*-

import unittest

import countersheet

def dummy_logwrite(msg):
    pass

def stdout_logwrite(msg):
    print "LOG >> " + msg,

class CSVCounterDefinitionParserTest(unittest.TestCase):
    def setUp(self):
        self.parser = countersheet.CSVCounterDefinitionParser(dummy_logwrite,
                                                              {})
    def test_empty(self):
        counters = self.parse_to_counters([[]])
        self.assertEqual([], counters)

    def test_single_simple(self):
        counters = self.parse_to_counters([['', 'a'],['1', 'e']])
        self.assertEqual(1, len(counters))
        counter = counters[0]
        self.assertEqual('e', counter.subst['a'])
        self.assertFalse(counter.hasback)

    def test_single_simple(self):
        counters = self.parse_to_counters([['', 'a'],['1', 'e']])
        counter = self.assert_get_counter(counters, 0)
        self.assertEqual('e', counter.subst['a'])
        self.assertFalse(counter.hasback)

    def test_single_part(self):
        counters = self.parse_to_counters([['', '@'],['1', 'e']])
        counter = self.assert_get_counter(counters, 0)
        self.assertEqual(1, len(counter.parts))
        self.assertEqual('@e', counter.parts[0])
        self.assertFalse(counter.hasback)

    def test_single_part_doublesided(self):
        counters = self.parse_to_counters([['', '@>', 'BACK'],
                                           ['1', 'e', 'BACK']])
        counter = self.assert_get_counter(counters, 0)
        self.assertEqual(1, len(counter.parts))
        self.assertEqual('@e', counter.parts[0])
        self.assertTrue(counter.hasback)
        self.assertTrue(counter.back)
        self.assertEqual(1, len(counter.back.parts))
        self.assertEqual('@e', counter.back.parts[0])

    def test_single_part_doublesided_background(self):
        counters = self.parse_to_counters([['b>', '@', 'BACK'],
                                           ['1', 'e', 'BACK']])
        counter = self.assert_get_counter(counters, 0)
        self.assertEqual(['b','@e'], counter.parts)
        self.assertTrue(counter.hasback)
        self.assertTrue(counter.back)
        self.assertEqual(['b'], counter.back.parts)

    def test_single_part_doublesided_no_back(self):
        counters = self.parse_to_counters([['', '@>', 'BACK'],
                                           ['1', 'e']])
        counter = self.assert_get_counter(counters, 0)
        self.assertEqual(1, len(counter.parts))
        self.assertEqual('@e', counter.parts[0])
        self.assertFalse(counter.hasback)
        self.assertTrue(counter.back)
        self.assertEqual(['@e'], counter.back.parts)

    def test_single_part_doublesided_no_back_but_empty_string(self):
        counters = self.parse_to_counters([['', '@>', 'BACK'],
                                           ['1', 'e', '']])
        counter = self.assert_get_counter(counters, 0)
        self.assertEqual(1, len(counter.parts))
        self.assertEqual('@e', counter.parts[0])
        self.assertFalse(counter.hasback)
        self.assertTrue(counter.back)
        self.assertEqual(['@e'], counter.back.parts)

    def test_single_doublesided_different_substs(self):
        counters = self.parse_to_counters([['', 'v', 'BACK', 'v'],
                                           ['1', 'f', 'BACK', 'b']])
        counter = self.assert_get_counter(counters, 0)
        self.assertEqual({'v':'f'}, counter.subst)
        self.assertEqual({'v':'b'}, counter.back.subst)

    def test_single_option_include(self):
        counters = self.parse_to_counters([['', 'e?'],
                                           ['1', 'y']])
        counter = self.assert_get_counter(counters, 0)
        self.assertEqual(set([]), counter.excludeids)

    def test_single_option_exclude(self):
        counters = self.parse_to_counters([['', 'e?'],
                                           ['1', '']])
        counter = self.assert_get_counter(counters, 0)
        self.assertEqual(set(['e']), counter.excludeids)

    def test_single_multioption_exclude(self):
        counters = self.parse_to_counters([['', 'e-?'],
                                           ['1', '']])
        counter = self.assert_get_counter(counters, 0)
        self.assertEqual(set(['e']), counter.excludeids)

    def test_single_multioption_include_one(self):
        counters = self.parse_to_counters([['', 'e-?'],
                                           ['1', 'one']])
        counter = self.assert_get_counter(counters, 0)
        self.assertEqual(set(['e']), counter.excludeids)
        self.assertEqual(set(['e-one']), counter.includeids)

    def test_single_multioption_include_two(self):
        counters = self.parse_to_counters([['', 'e-?'],
                                           ['1', 'one two']])
        counter = self.assert_get_counter(counters, 0)
        self.assertEqual(set(['e']), counter.excludeids)
        self.assertEqual(2, len(counter.includeids))
        self.assertTrue('e-one' in counter.includeids)
        self.assertTrue('e-two' in counter.includeids)

    def test_default_value_unset(self):
        counters = self.parse_to_counters([['', 'e=d'],
                                          ['1', '']])
        counter = self.assert_get_counter(counters, 0)
        self.assertEqual({'e':'d'}, counter.subst)

    def test_default_value_set(self):
        counters = self.parse_to_counters([['', 'e=d'],
                                          ['1', 'v']])
        counter = self.assert_get_counter(counters, 0)
        self.assertEqual({'e':'v'}, counter.subst)

    def parse_to_counters(self, reader):
        self.parser.parse(reader)
        return self.parser.counters

    def assert_get_counter(self, counters, nr):
        self.assertTrue(len(counters) > nr)
        return counters[nr]

if __name__ == '__main__':
    unittest.main()
