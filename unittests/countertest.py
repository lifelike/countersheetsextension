#!/usr/bin/env python2.6
# -*- coding: utf-8 -*-

import unittest

import countersheet

class SingleCounterTest(unittest.TestCase):
    def setUp(self):
        self.counter = countersheet.Counter(1)
        self.setting = countersheet.CounterSettingHolder()

    def test_plain(self):
        self.assertEqual(1, self.counter.nr)
        self.assertFalse(self.counter.hasback)
        self.assertFalse(self.counter.endbox)
        self.assertFalse(self.counter.back)

    def test_part(self):
        self.setting.set(countersheet.CounterPart('p'))
        self.setting.applyto(self.counter)
        self.assertTrue('p' in self.counter.parts)
        self.assertFalse(self.counter.hasback)
        self.assertFalse(self.counter.back)

    def test_excludeid(self):
        self.setting.set(countersheet.CounterExcludeID('i'))
        self.setting.applyto(self.counter)
        self.assertTrue('i' in self.counter.excludeids)
        self.assertFalse(self.counter.hasback)
        self.assertFalse(self.counter.back)

    def test_attr(self):
        self.setting.set(countersheet.CounterAttribute('i', 'a', 's'))
        self.setting.applyto(self.counter)
        self.assertEqual('s', self.counter.attrs['i']['a'])
        self.assertFalse(self.counter.hasback)
        self.assertFalse(self.counter.back)

    def test_subst(self):
        self.setting.set(countersheet.CounterSubst('n', 'v'))
        self.setting.applyto(self.counter)
        self.assertEqual('v', self.counter.subst['n'])
        self.assertFalse(self.counter.hasback)
        self.assertFalse(self.counter.back)

    def test_doublesided_plain(self):
        self.counter.doublesided()
        self.assertTrue(self.counter.back)
        self.assertEqual(1, self.counter.nr)
        self.assertEqual(1, self.counter.back.nr)
        self.assertFalse(self.counter.endbox)
        self.assertFalse(self.counter.back.endbox)

    def test_doublesided_part(self):
        self.setting.set(countersheet.CounterPart('p'))
        self.setting.setcopytoback()
        self.setting.applyto(self.counter)
        self.assertTrue('p' in self.counter.parts)
        self.assertFalse(self.counter.hasback)
        self.assertTrue(self.counter.back)

    def test_doublesided_excludeid(self):
        self.setting.set(countersheet.CounterExcludeID('i'))
        self.setting.setcopytoback()
        self.setting.applyto(self.counter)
        self.assertTrue('i' in self.counter.excludeids)
        self.assertFalse(self.counter.hasback)
        self.assertTrue(self.counter.back)

    def test_doublesided_attr(self):
        self.setting.set(countersheet.CounterAttribute('i', 'a', 's'))
        self.setting.setcopytoback()
        self.setting.applyto(self.counter)
        self.assertEqual('s', self.counter.attrs['i']['a'])
        self.assertFalse(self.counter.hasback)
        self.assertTrue(self.counter.back)

    def test_doublesided_subst(self):
        self.setting.set(countersheet.CounterSubst('n', 'v'))
        self.setting.setcopytoback()
        self.setting.applyto(self.counter)
        self.assertEqual('v', self.counter.subst['n'])
        self.assertFalse(self.counter.hasback)
        self.assertTrue(self.counter.back)

if __name__ == '__main__':
    unittest.main()
