#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest

import countersheet

def dummy_logwrite(msg):
    pass

def stdout_logwrite(msg):
    print "LOG >> " + msg,

class CountersheetStyleTest(unittest.TestCase):
    def setUp(self):
        self.effect = countersheet.CountersheetEffect()

    def test_first(self):
        oldv = "a:1;b:2;c:3;"
        self.assertEqual("a:x;b:2;c:3;",
                         countersheet.stylereplace(oldv, 'a', 'x'))
    def test_middle(self):
        oldv = "a:1;b:2;c:3;"
        self.assertEqual("a:1;b:x;c:3;",
                         countersheet.stylereplace(oldv, 'b', 'x'))

    def test_last(self):
        oldv = "a:1;b:2;c:3;"
        self.assertEqual("a:1;b:2;c:x;",
                         countersheet.stylereplace(oldv, 'c', 'x'))

    def test_double_replace_bug(self):
        oldv = "font-size:6px;font-style:normal;font-variant:normal;font-weight:normal;font-stretch:normal;text-align:center;line-height:100%;writing-mode:lr-tb;text-anchor:middle;fill:#000000;fill-opacity:1;stroke:none;stroke-width:1px;stroke-linecap:butt;stroke-linejoin:miter;stroke-opacity:1;font-family:Serif;-inkscape-font-specification:Serif;"
        self.assertEqual("font-size:6px;font-style:normal;font-variant:normal;font-weight:normal;font-stretch:normal;text-align:center;line-height:100%;writing-mode:lr-tb;text-anchor:middle;fill:white;fill-opacity:1;stroke:none;stroke-width:1px;stroke-linecap:butt;stroke-linejoin:miter;stroke-opacity:1;font-family:Serif;-inkscape-font-specification:Serif;",
                         countersheet.stylereplace(oldv, 'fill', 'white'))

    def test_double_replace_minimized(self):
        oldv="a:1;a-b:2;"
        self.assertEqual("a:x;a-b:2;",
                         countersheet.stylereplace(oldv, 'a', 'x'))

if __name__ == '__main__':
    unittest.main()

