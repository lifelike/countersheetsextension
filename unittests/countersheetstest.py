#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest

import inkex
import countersheet

def dummy_logwrite(msg):
    pass

def stdout_logwrite(msg):
    print "LOG >> " + msg,

class DummyLog(object):
    def write(self, msg):
        pass

class CountersheetsTest(unittest.TestCase):
    def setUp(self):
        pass

    def test_one_cell(self):
        self.assertEqual('a', 'a')

class SingleCounterTest(unittest.TestCase):
    def setUp(self):
        self.counter = countersheet.Counter(countersheet.Repeat(1))
        self.setting = countersheet.CounterSettingHolder()

    def test_plain(self):
        self.assertEqual(1, self.counter.repeat.nr)
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

    def test_id(self):
        self.setting.set(countersheet.CounterID('i'))
        self.setting.applyto(self.counter)
        self.assertEqual('i', self.counter.id)

    def test_doublesided_plain(self):
        self.counter.doublesided()
        self.assertTrue(self.counter.back)
        self.assertEqual(1, self.counter.repeat.nr)
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

class MockGroup:
    def __init__(self, group_type, transform, parent = None):
        self._group_type = group_type
        self._transform = transform
        self._parent = parent	

    def get(self, attribute):
        if ( attribute == inkex.addNS('groupmode', 'inkscape') and self._group_type == "layer" ):
            return "layer";
        elif ( attribute == "transform" ):
            return self._transform
        return "something besides layer"

    def getparent(self):
        return self._parent


class LayerTranslationTest(unittest.TestCase):
    def setUp(self):
        self.countersheet_effect = countersheet.CountersheetEffect()

    def test_number_is_not_a_layer(self):
        self.assertFalse(self.countersheet_effect.is_layer( 4 ) )

    def test_None_is_not_a_layer(self):
        self.assertFalse(self.countersheet_effect.is_layer( None ) )

    def test_a_layer_like_object_is_a_layer(self):
        mock_layer = MockGroup( "layer", None )
        self.assertTrue(self.countersheet_effect.is_layer( mock_layer ) )

    def test_a_non_layer_like_object_is_not_a_layer(self):
        mock_not_a_layer = MockGroup( "group not layer", None )
        self.assertFalse(self.countersheet_effect.is_layer( mock_not_a_layer ) )

    def test_get_layer_on_layer(self):
        mock_layer = MockGroup( "layer", None )
        self.assertEqual(self.countersheet_effect.get_layer(mock_layer), mock_layer)

    def test_get_layer_on_group(self):
        mock_layer = MockGroup( "layer", None )
        mock_group = MockGroup( "not a layer", None, mock_layer )
        self.assertEqual(self.countersheet_effect.get_layer(mock_group), mock_layer)

    def test_get_layer_on_object_without_parent(self):
        mock_group = MockGroup( "not a layer", None )
        with self.assertRaises(ValueError):
            self.countersheet_effect.get_layer(mock_group)


class DocumentTopLeftCoordinateConverterTest(unittest.TestCase):
    def setUp(self):
        pass

    def test_no_transform_dtl_to_SVG(self):
        mock_layer = MockGroup( "layer", None )
        converter = countersheet.DocumentTopLeftCoordinateConverter(mock_layer)
        in_point = ( 0, 0 )
        converted_point = converter.dtl_to_SVG( in_point )
        self.assertEqual( in_point, converted_point )
 
    def test_no_transform_SVG_to_dtl(self):
        mock_layer = MockGroup( "layer", None )
        converter = countersheet.DocumentTopLeftCoordinateConverter(mock_layer)
        in_point = ( 0, 0 )
        converted_point = converter.SVG_to_dtl( in_point )
        self.assertEqual( in_point, converted_point )

    def test_translate_0_0_dtl_to_SVG(self):
        mock_layer = MockGroup( "layer", "translate(0,0)" )
        converter = countersheet.DocumentTopLeftCoordinateConverter(mock_layer)
        in_point = ( 0, 0 )
        converted_point = converter.dtl_to_SVG( in_point )
        self.assertEqual( in_point, converted_point )

    def test_translate_0_0_SVG_to_dtl(self):
        mock_layer = MockGroup( "layer", "translate(0,0)" )
        converter = countersheet.DocumentTopLeftCoordinateConverter(mock_layer)
        in_point = ( 0, 0 )
        converted_point = converter.SVG_to_dtl( in_point )
        self.assertEqual( in_point, converted_point )

    def test_translate_25_30_dtl_to_SVG(self):
        mock_layer = MockGroup( "layer", "translate(25,30)" )
        converter = countersheet.DocumentTopLeftCoordinateConverter(mock_layer)
        in_point = ( 0, 0 )
        converted_point = converter.dtl_to_SVG( in_point )
        self.assertEqual( converted_point, ( -25, -30 ) )

    def test_translate_25_30_SVG_to_dtl(self):
        mock_layer = MockGroup( "layer", "translate(25,30)" )
        converter = countersheet.DocumentTopLeftCoordinateConverter(mock_layer)
        in_point = ( 0, 0 )
        converted_point = converter.SVG_to_dtl( in_point )
        self.assertEqual( converted_point, ( 25, 30 ) )

    def test_translate_minus_25_minus_30_dtl_to_SVG(self):
        mock_layer = MockGroup( "layer", "translate(-25,-30)" )
        converter = countersheet.DocumentTopLeftCoordinateConverter(mock_layer)
        in_point = ( 0, 0 )
        converted_point = converter.dtl_to_SVG( in_point )
        self.assertEqual( converted_point, ( 25, 30 ) )

    def test_translate_minus_25_minus_30_SVG_to_dtl(self):
        mock_layer = MockGroup( "layer", "translate(-25,-30)" )
        converter = countersheet.DocumentTopLeftCoordinateConverter(mock_layer)
        in_point = ( 0, 0 )
        converted_point = converter.SVG_to_dtl( in_point )
        self.assertEqual( converted_point, ( -25, -30 ) )

    def test_valid_replace_name(self):
        self.assertTrue(countersheet.is_valid_name_to_replace(
            "ABC_DEF.-GHIabc09zZ"))

    def test_valid_replace_name_not_empty(self):
        self.assertFalse(countersheet.is_valid_name_to_replace(""))

    def test_valid_replace_name_not_percent(self):
        self.assertFalse(countersheet.is_valid_name_to_replace("A%BC"))

    def test_valid_replace_name_not_amp(self):
        self.assertFalse(countersheet.is_valid_name_to_replace("A&"))

class PartialCountersheetEffect(countersheet.CountersheetEffect):
    def __init__(self):
        self.log = DummyLog()

    def getDocumentWidth(self):
        return "210mm"

    def getDocumentHeight(self):
        return "297mm"

    def getDocumentUnit(self):
        return "mm"

class ParseLengthTest(unittest.TestCase):
    def setUp(self):
        self.cs = PartialCountersheetEffect()

    def check_parse(self, s, expected):
        self.assertAlmostEqual(self.cs.from_len_arg(s, "test"),
                               expected, 2)

    def test_1mm(self):
        self.check_parse("1mm", 1.0)

    def test_1in(self):
        self.check_parse("1in", 25.4)

    def test_none(self):
        self.check_parse(None, 0.0)

    def test_empty(self):
        self.check_parse("", 0.0)

    def test_0(self):
        self.check_parse("0", 0.0)

if __name__ == '__main__':
    unittest.main()
