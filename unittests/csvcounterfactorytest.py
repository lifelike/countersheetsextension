#!/usr/bin/env python2
# -*- coding: utf-8 -*-

import unittest

import countersheet

class CSVCounterFactoryTest(unittest.TestCase):
    def setUp(self):
        pass

    def test_empty(self):
        factory = self.create_factory([])
        self.assertEqual([], factory.headers)

    def test_simple(self):
        factory = self.create_factory(['', 'a'])
        counter = factory.create_counter(1, ['1', 'b'])
        self.assertEqual({'a' : 'b'}, counter.subst)

    def test_create_subst(self):
        factory = self.create_factory(['', 'a'])
        self.assertEqual(2, len(factory.headers))
        self.assertEqual('a', factory.headers[1].id)

    def create_factory(self, row):
        return countersheet.CSVCounterFactory({}, row)

if __name__ == '__main__':
    unittest.main()
