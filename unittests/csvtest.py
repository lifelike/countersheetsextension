#!/usr/bin/env python2
# -*- coding: utf-8 -*-

import csv
import unittest

class CSVTest(unittest.TestCase):
    def setUp(self):
        self.parser = csv.CSVParser()

    def test_one_cell(self):
        self.assertEqual(self.parser.parse_string('aaa'), [['aaa']])

    def test_simple_commas_line(self):
        self.assertEqual(self.parser.parse_string('a1,b1'), [['a1','b1']])

    def test_two_simple_commas_line(self):
        self.assertEqual(self.parser.parse_string('a1,b1\r\nc1'),
                         [['a1','b1'],['c1']])

    def test_quoted_strings(self):
        self.assertEqual(self.parser.parse_string('"a1","b1"\r\n"c1"'),
                         [['a1','b1'],['c1']])

    def test_quoted_strings_with_quote(self):
        self.assertEqual(self.parser.parse_string('"a""1","b1"\r\n"c1"'),
                         [['a"1','b1'],['c1']])

    def test_cell_with_line_break(self):
        self.assertEqual(self.parser.parse_string('a,"b\n1",c\nd,"e"'),
                         [['a','b\n1','c'],['d','e']])


    def test_semicolons(self):
        self.assertEqual(self.parser.parse_string('"a1";b1\r\n"c1";d;e'),
                         [['a1','b1'],['c1','d','e']])

    def test_international(self):
        self.assertEqual(self.parser.parse_string(u'å,ä,ö'),
                         [[u'å',u'ä',u'ö']])

    def test_multiline_dos(self):
        self.assertEqual(self.parser.parse_string('"a1","b1\r\nb2"\r\n"c1"'),
                         [['a1', 'b1\r\nb2'], ['c1']])

    def test_multiline_unix(self):
        self.assertEqual(self.parser.parse_string('"a1","b1\nb2"\n"c1"'),
                         [['a1', 'b1\nb2'], ['c1']])

if __name__ == '__main__':
    unittest.main()
