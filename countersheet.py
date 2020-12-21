#!/usr/bin/env python3

# Copyright 2008-2020 Pelle Nilsson and contributors
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
#along with this program; if not, write to the Free Software
#Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

import inkex
from inkex import NSS
import csv
import fnmatch
import re
import os
import os.path
import lxml
from lxml import etree
from copy import deepcopy
import sys
from tempfile import mkstemp
import subprocess

NSS['cs'] = 'http://www.hexandcounter.org/countersheetsextension/'

# Trying to make inserted inlined images show up slightly
# more well-aligned with the surrounding text by shifting
# them slightly downwards. This will fail for non-horizontal
# text. Hopefully sometihing better can be implemented.
DEFAULT_INLINE_IMAGE_YSHIFT = 0.2

# A bit of a hack because of rounding errors sometimes
# making boxes not fill up properly.
# There should be a better fix.
BOX_MARGIN = 2.0

# Hardcoded (for now?) what DPI to use for
# some non-vector content in exported PDF.
PDF_DPI = 300

DEFAULT_REGISTRATION_MARK_STYLE = "stroke:#aaa"

def popen3(cmd):
    p = subprocess.Popen(cmd,
        shell=True, universal_newlines=True, close_fds=True,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE)
    return p.communicate()

class Counter:
    def __init__(self, repeat):
        self.repeat = repeat
        self.parts = []
        self.subst = {}
        self.back = None
        self.id = None
        self.endbox = False
        self.endrow = False
        self.hasback = False
        self.attrs = {}
        self.excludeids = []
        self.includeids = []
        self.bleed_up = []
        self.bleed_left = []
        self.elements = [] # generated top-level groups
        self.width = 0 # actual width when generated
        self.height = 0 # actual height when generated
        self.bleed_added = {}

    def can_add_another(self):
        return self.repeat.can_add_another()

    def added_one(self, last_on_row, last_in_box, last_on_sheet):
        self.repeat.added_one(last_on_row, last_in_box, last_on_sheet)

    def set(self, setting):
        setting.applyto(self)

    def addpart(self, id):
        self.parts.append(id)

    def excludeid(self, id):
        self.excludeids.append(id)

    def includeid(self, id):
        self.includeids.append(id)

    def addattr(self, id, attribute, source):
        if not id in self.attrs:
            self.attrs[id] = {}
        self.attrs[id][attribute] = source

    def addsubst(self, name, value):
        self.subst[name] = value

    def doublesided(self):
        if not self.back:
            self.back = Counter(DummyRepeat())
        return self.back

    def is_included(self, eid):
       if eid is None:
           return True
       for iglob in self.includeids:
            if fnmatch.fnmatchcase(eid, iglob):
                return True
       for eglob in self.excludeids:
            if fnmatch.fnmatchcase(eid, eglob):
                return False
       return True

class CounterSettingHolder:
    def __init__(self):
        self.copytoback = False
        self.setting = NoSetting()
        self.back = False

    def setcopytoback(self):
        self.copytoback = True
        return self

    def setback(self):
        self.back = True

    def set(self, setting):
        self.setting = setting

    def applyto(self, counter):
        self.setting.applyto(counter)
        if self.copytoback:
            back = counter.doublesided()
            self.setting.applyto(back)

class DummyRepeat:
    def can_add_another(self):
        return False

    def added_one(self, last_on_row, last_in_box, last_on_sheet):
        pass

class Repeat:
    def __init__(self, nr):
        self.nr = nr
        self.keep_going = True

    def can_add_another(self):
        return self.nr > 0 or self.keep_going

class RepeatExact(Repeat):
    def added_one(self, last_on_row, last_in_box, last_on_sheet):
        self.nr -= 1
        self.keep_going = False

class RepeatMinFillRow(Repeat):
    def added_one(self, last_on_row, last_in_box, last_on_sheet):
        self.nr -= 1
        if last_on_row and self.nr <= 0:
            self.keep_going = False

class RepeatMinFillBox(Repeat):
    def added_one(self, last_on_row, last_in_box, last_on_sheet):
        self.nr -= 1
        if last_in_box and self.nr <= 0:
            self.keep_going = False

class RepeatMinFillSheet(Repeat):
    def added_one(self, last_on_row, last_in_box, last_on_sheet):
        self.nr -= 1
        if last_on_sheet and self.nr <= 0:
            self.keep_going = False

class BleedMaker:
    def __init__(self, svg, defs):
        self.defs = defs
        self.bleed_added = {}
        self.unbleed = {}

    def getbleed(self, width, height,
                 bleed_up, bleed_left, bleed_down, bleed_right):
        """
        Create a clippath rectangle in svg defs and return its name.
        Or just return the name if it already exists.
        Note that with the current implementation there is always
        bleed drawn below and to the right of every counter.
        That is almost always the correct thing to do. Possibly
        always for all practical purposes. Except on counter
        backs where left and right are exchanged, so they will
        always have bleed_left, but not always bleed_right.
        Leaving this generic enough to handle clip-paths extended
        in all directions since it is not a huge additional
        effort anyway to handle 3 instead of 4 directions.
        """
        name = "bleed_%dx%d_%r_%r_%r_%r" % (width,
                                            height,
                                            bleed_up,
                                            bleed_left,
                                            bleed_down,
                                            bleed_right)
        existing = self.defs.xpath("svg:clipPath[@id='%s']"% name,
                                   namespaces=NSS)
        if len(existing) == 0:
            clipPath = etree.Element(inkex.addNS("clipPath", "svg"))
            clipPath.set('id', name)
            rect = etree.Element(inkex.addNS("rect", "svg"))

            x1 = 0
            y1 = 0
            x2 = width
            y2 = height

            if bleed_up:
                y1 -= height
            if bleed_left:
                x1 -= width
            if bleed_down:
                y2 += height
            if bleed_right:
                x2 += width

            rect.set('x', str(min(x1, x2)))
            rect.set('y', str(min(y1, y2)))
            rect.set('width', str(abs(x1 - x2)))
            rect.set('height', str(abs(y1 - y2)))

            clipPath.append(rect)
            self.defs.append(clipPath)
        return name

    def add_bleed_to(self, counters):
        for counter in counters:
            front_unbleed = self.getbleed(counter.width,
                                          counter.height,
                                          False, False, False, False)
            for i,element in enumerate(counter.elements):
                bleedclip = self.getbleed(counter.width,
                                          counter.height,
                                          counter.bleed_up[i],
                                          counter.bleed_left[i],
                                          True,
                                          True)
                self.setclip(element, bleedclip)
                self.bleed_added[element] = bleedclip
                self.unbleed[bleedclip] = front_unbleed
            if counter.hasback:
                back_unbleed = self.getbleed(counter.back.width,
                                             counter.back.height,
                                             False, False, False, False)
                for i,element in enumerate(counter.back.elements):
                    back_bleedclip = self.getbleed(counter.back.width,
                                                   counter.back.height,
                                                   counter.bleed_up[i],
                                                   True,
                                                   True,
                                                   counter.bleed_left[i])
                    self.setclip(element, back_bleedclip)
                    self.bleed_added[element] = back_bleedclip
                    self.unbleed[back_bleedclip] = back_unbleed

    def setclip(self, element, clip):
        element.set('clip-path',
                    "url(#%s)"
                    % clip)

    def hideall(self):
        for element,clip in self.bleed_added.items():
            self.setclip(element, self.unbleed[clip])

    def showall(self):
        for element,clip in self.bleed_added.items():
            self.setclip(element, clip)

class NoSetting:
    def applyto(self, counter):
        pass

class CounterPart:
    def __init__(self, id):
        self.id = id

    def applyto(self, counter):
        counter.addpart(self.id)

class CounterExcludeID:
    def __init__(self, id):
        self.id = id
        self.exceptions = set()

    def addexception(self, id):
        self.exceptions.add(id)

    def applyto(self, counter):
        counter.excludeid(self.id)
        for e in self.exceptions:
            counter.includeid(e)

class CounterAttribute:
    def __init__(self, id, attribute, source):
        self.id = id
        self.attribute = attribute
        self.source = source

    def applyto(self, counter):
        counter.addattr(self.id, self.attribute, self.source)

class CounterSubst:
    def __init__(self, name, value):
        self.name = name
        self.value = value

    def applyto(self, counter):
        counter.addsubst(self.name, self.value)

class CounterID:
    def __init__(self, id):
        self.id = id

    def applyto(self, counter):
        counter.id = self.id

class Rectangle:
    def __init__(self, x, y, w, h):
        self.x = x
        self.y = y
        self.w = w
        self.h = h

class CountersheetEffect(inkex.Effect):
    def __init__(self):
        inkex.Effect.__init__(self)
        self.log = False
        self.nextid = 1000000
        self.arg_parser.add_argument('-,', '--name')
        self.arg_parser.add_argument('-l', '--log',
                                     type = str, dest = 'logfile')
        self.arg_parser.add_argument('-n', '--what',
                                     type = str, dest = 'what',
                                     default = '',
                                     help = 'Name')
        self.arg_parser.add_argument('-N', '--sheets-bitmap-name', dest='bitmapname',
                                     default = '') # undocumented, for svgtests
        self.arg_parser.add_argument('-d', '--data',
                                     type = str, dest = 'datafile',
                                     default = 'countersheet.csv',
                                     help = 'CSV or XML data file.')
        self.arg_parser.add_argument('-I', '--imagedir',
                                     type = str, dest = 'imagedir',
                                     default = '',
                                     help = 'Base path to external images')
        self.arg_parser.add_argument('-w', '--bitmapw',
                                     type = int, dest = 'bitmapwidth',
                                     default = '56',
                                     help = 'ID bitmap width')
        self.arg_parser.add_argument('-F', '--rotatefronts',
                                     type = int, dest = 'rotatefronts',
                                     default = '0',
                                     help = 'Rotate Fronts (degrees)')
        self.arg_parser.add_argument('-G', '--rotatebacks',
                                     type = int, dest = 'rotatebacks',
                                     default = '0',
                                     help = 'Rotate Backs (degrees)')
        self.arg_parser.add_argument('-y', '--bitmaph',
                                     type = int, dest = 'bitmapheight',
                                     default = '56',
                                     help = 'Number of columns.')
        self.arg_parser.add_argument('-f', '--bitmapsheetsdpi',
                                     type = int, dest = 'bitmapsheetsdpi',
                                     default = '0')
        self.arg_parser.add_argument('-b', '--bitmapdir',
                                     type = str, dest = 'bitmapdir')
        self.arg_parser.add_argument('-p', '--pdfdir',
                                     type = str, dest = 'pdfdir')
        self.arg_parser.add_argument('-r', '--registrationmarkslen',
                                     type = str,
                                     default = '',
                                     dest = 'registrationmarkslen')
        self.arg_parser.add_argument('-z', '--registrationmarksdist',
                                     type = str,
                                     default = '',
                                     dest = 'registrationmarksdist')
        self.arg_parser.add_argument('-R', '--fullregistrationmarks',
                                     dest = 'fullregistrationmarks',
                                     default = "false")
        self.arg_parser.add_argument('-D', '--registrationmarksbothsides',
                                     dest = 'registrationmarksbothsides',
                                     default = "false")
        self.arg_parser.add_argument('-O', '--outlinedist',
                                     type = str,
                                     dest = 'outlinedist',
                                     default = "")
        self.arg_parser.add_argument('-S', '--spacing',
                                     type = str,
                                     dest = 'spacing',
                                     default = "0")
        self.arg_parser.add_argument('-m', '--textmarkup', dest='textmarkup',
                                     default = "true")
        self.arg_parser.add_argument('-B', '--bleed', dest='bleed',
                                     default = "false")
        self.arg_parser.add_argument('-o', '--oneside', default = "false",
                                     dest="oneside")
        self.arg_parser.add_argument('-X', '--backoffsetx', default = "0mm",
                                     dest="backoffsetx")
        self.arg_parser.add_argument('-Y', '--backoffsety', default = "0mm",
                                     dest="backoffsety")

        self.translatere = re.compile("translate[(]([-0-9.]+),([-0-9.]+)[)]")
        self.matrixre = re.compile("(matrix[(](?:[-0-9.]+,){4})([-0-9.]+),([-0-9.]+)[)]")
        self.placeholders = {}
        self.nr_styles_added = 0

    def logwrite(self, msg):
        logfile = self.options.logfile
        if (not self.log and logfile
            and not os.path.isdir(logfile)):
            self.log = open(logfile, 'w')
        if self.log:
            try:
                self.log.write(msg)
            except UnicodeEncodeError:
                self.log.write(msg.encode('utf8'))

    def replaceattrs(self, elements, attrs):
        for n in elements:
            id = n.get("id")
            if not id:
                continue
            for glob,attr in attrs.items():
                if fnmatch.fnmatchcase(id, glob):
                    for a,v in attr.items():
                        if a.startswith('style:'):
                            pname = a[6:]
                            a = "style"
                            v = stylereplace(n.get(a), pname, v)
                        if ':' in a:
                            [ns,tag] = a.split(':')
                            a = inkex.addNS(tag, ns)
                        n.set(a, v)


    def translate_element(self, element, dx, dy, append=False):
        self.logwrite("translate_element %f,%f\n"
                      % (dx, dy))
        translate = "translate(%f,%f)" % (dx, dy)
        old_transform = element.get('transform')
        if old_transform and append:
            self.logwrite("old transform append: %s\n" % old_transform)
            element.set('transform', old_transform + " " + translate)
        elif old_transform:
            self.logwrite("old transform prepend: %s\n" % old_transform)
            element.set('transform', translate + " " + old_transform)
        else:
            element.set('transform', translate)

    def rotate_element(self, element, degrees, width, height):
        if degrees == 0 or degrees == 180:
            return
        rotate = "rotate(%f,%f,%f)" % (degrees,
                                          width / 2.0,
                                          height / 2.0)
        if degrees == 90 or degrees == -90:
            rotate_xshift = (height - width) / 2.0
            rotate_yshift = (width - height) / 2.0
            rotate = "translate(%f,%f) %s" % (rotate_xshift,
                                              rotate_yshift,
                                              rotate)
        old_transform = element.get('transform')
        if old_transform:
            element.set('transform', old_transform + " " + rotate)
        else:
            element.set('transform', rotate)

    def translate_use_element(self, use, old_ref, new_ref):
        self.logwrite("translate_use_element %s %s\n" % (old_ref, new_ref))
        old_element = self.document.xpath("//*[@id='%s']"% old_ref,
                                          namespaces=NSS)[0]
        new_elements = self.document.xpath("//*[@id='%s']"% new_ref,
                                           namespaces=NSS)
        if len(new_elements) < 1:
            sys.exit("Failed to find new clone target: %s" % new_ref)
        new_element = new_elements[0]
        (old_x, old_y) = self.find_reasonable_center_xy(old_element)
        (new_x, new_y) = self.find_reasonable_center_xy(new_element)
        self.logwrite(" use data: old %f,%f   new %f,%f\n"
                      % (old_x, old_y,
                         new_x, new_y))
        self.translate_element(use, old_x - new_x, old_y - new_y, True)

    def find_reasonable_center_xy(self, element):
        rect = self.geometry[element.get('id')]
        return (rect.x + rect.w / 2.0,
                rect.y + rect.h / 2.0)

    def setMultilineText(self, element, name, lines):
        self.logwrite("setting multiline text: %s\n" % lines)
        self.deleteTextChildren(element)
        added_style = {}
        for line in lines:
            para = etree.Element(inkex.addNS('flowLine', 'svg'))
            self.setFormattedText(para, name,
                                  line, 'flowSpan',
                                  added_style,
                                  inkex.Style.parse_str(element.get('style')))
            element.append(para)

    def deleteTextChildren(self, parent):
        for c in parent.getchildren():
            if c.tag != inkex.addNS('flowRegion','svg'):
                parent.remove(c)

    def setFormattedText(self, element, name, text, spantag,
                         added_style, styles):
        self.logwrite('setFormattedText: %s %s %s %s\n'
                      % (element.tag, text, spantag, styles))
        if not self.textmarkup:
            element.text = text
            return

        first_bold = text.find("*")
        first_italics = text.find("/")
        second_bold = text.find("*", first_bold + 1)
        second_italics = text.find("/", first_italics + 1)

        self.logwrite("first_bold: %d, first_italics: %d, "
                      "second_bold: %d, second_italics: %d\n"
                      % (first_bold, first_italics,
                         second_bold, second_italics))

        skip = False

        if (first_italics > first_bold
            and second_bold > first_italics
            and second_italics > second_bold
            or first_bold > first_italics
            and second_italics > first_bold
            and second_bold > second_italics):
            self.logwrite("Bad nesting bold/italics (skip format): %s\n"
                          % text)
            skip = True

        if first_bold >= 0 and second_bold < 0:
            self.logwrite("Single bold-mark (*) (skip format): %s\n" % text)
            skip = True

        if first_italics >= 0 and second_italics < 0:
            self.logwrite("Single italics-mark (/) (skip format): %s\n" % text)
            skip = True

        if (not skip
            and first_bold >= 0
            and second_bold > first_bold
            and (first_italics < 0 or first_bold < first_italics)):
            self.formatTextPart(element, name, text, spantag,
                                first_bold, second_bold,
                                "font-weight", "bold",
                                added_style, "b", styles)
        elif (not skip
              and first_italics >=0
              and second_italics > first_italics
              and (first_bold < 0 or first_italics < first_bold)):
            self.formatTextPart(element, name, text, spantag,
                                first_italics, second_italics,
                                "font-style", "italic",
                                added_style, "i", styles)
        else:
            self.formatTextImages(element, name, text, spantag,
                                  added_style, styles)

    def formatTextImages(self, element, name, text, spantag,
                         added_style, styles):
        m = re.search(r"[{][^{}]+[}]", text)
        if m:
            self.logwrite("Inline image: %s\n" % m.group(0))
            self.insertImagePlaceholder(element,
                                        name,
                                        text,
                                        spantag,
                                        m.start(),
                                        m.end() - 1,
                                        added_style,
                                        styles)
        else:
            element.text = text

    def insertImagePlaceholder(self, element, name,
                               text, spantag,
                               begin_index, end_index,
                               added_style, styles):
        filename = text[begin_index+1:end_index]
        if spantag != "tspan":
            sys.exit("Failed to insert inlined image %s "
                     "in a %s element. Unfortunately only "
                     "one-line text elements can have inlined "
                     "images for boring technical reasons. "
                     "Perhaps in a future version of Inkscape "
                     "it will be possible to add support for "
                     "inlined images in (flowing) multi-line "
                     "text elements." % (filename, spantag))
        span = etree.Element(inkex.addNS(spantag, 'svg'))
        if 'image' in added_style:
            nr = added_style['image'] + 1
        else:
            nr = 1
        spanid = '%s-%d-cs-image-%s' % (name, len(self.placeholders),
                                        nr)
        span.set('id', spanid)
        # span.text = "\u2b1b"
        span.text = "X" # FIXME, there is something wrong with unicode rendering in Inkscape 1.0?
        span.set('style', 'font-size: 200%;fill-opacity:0;'
                 'font-style:normal;font-weight:normal;'
                 'font-variant:normal;font-family:sans-serif;')

        self.logwrite("inline image placeholder: %s %s\n"
                      % (spanid, filename))

        self.placeholders[spanid] = {
            "parent" : element,
            "span" : span,
            "filename" : filename,
        }

        restspan = etree.Element(inkex.addNS(spantag, 'svg'))
        resttext = text[end_index+1:]
        self.setFormattedText(restspan,
                              name,
                              resttext,
                              spantag,
                              added_style,
                              styles)
        element.text = text[:begin_index]
        element.append(span)
        element.append(restspan)

    def formatTextPart(self, element, name,
                       text, spantag,
                       begin_index, end_index,
                       style, style_value,
                       added_style,
                       style_tag,
                       styles):
        if style_tag in added_style:
            nr = added_style[style_tag] + 1
        else:
            nr = 1
        added_style[style_tag] = nr
        self.nr_styles_added += 1

        stylespan = etree.Element(inkex.addNS(spantag, 'svg'))
        combinedStyles = dict(styles)
        combinedStyles[style] = style_value
        stylespan.set('style', str(inkex.Style(combinedStyles)))

        spanid = '%s-%d-cs-%s-%s' % (name,
                                     self.nr_styles_added,
                                     style_tag,
                                     nr)
        self.logwrite("setting %s style id %s"
                      % (style_value, spanid))
        stylespan.set('id', spanid)
        self.setFormattedText(stylespan, name,
                              text[begin_index+1:end_index],
                              spantag,
                              added_style, styles)
        restspan = etree.Element(inkex.addNS(spantag, 'svg'))
        restspan.set('style', str(inkex.Style(styles)))
        self.setFormattedText(restspan, name,
                              text[end_index+1:],
                              spantag,
                              added_style, styles)
        self.formatTextImages(element, name,
                              text[:begin_index], spantag,
                              added_style, styles)
        element.append(stylespan)
        element.append(restspan)

    def setFirstTextChild(self, element, name, text):
        """Find the first child of a text element that already has
        some text in it. This could be a tspan in a tspan nested
        any number of times. Then delete all other tspans from the
        text. Otherwise parts of the original text will remain
        after the substitution. It is important to drill down and
        find the first tspan that actually contains text (if any)
        because that will have the style that the user expects
        the new text to have, as any empty tspan will be invisible
        (and is probably there by accident)."""
        if ((element.tag == inkex.addNS('text', 'svg')
             or element.tag == inkex.addNS('tspan', 'svg'))
            and element.text is not None and len(element.text) > 0):
            self.logwrite("text replace %s %s %r\n" % (element.get('id'),
                                                       element.tag,
                                                       text))
            self.deleteTextChildren(element)
            self.setFormattedText(element, name, text,
                                  'tspan',
                                  {}, inkex.Style.parse_str(element.get('style')))
            return True
        elif ((element.tag == inkex.addNS('flowPara', 'svg')
               or element.tag == inkex.addNS('flowLine', 'svg')
               or element.tag == inkex.addNS('flowSpan', 'svg'))
              and element.text is not None and len(element.text) > 0):
            self.logwrite("flow replace %s %s %r\n" % (element.get('id'),
                                                       element.tag,
                                                       text))
            self.deleteTextChildren(element)
            self.setFormattedText(element, name, text,
                                  'flowSpan',
                                  {}, inkex.Style.parse_str(element.get('style')))
            return True
        replaced = False
        for c in element.getchildren():
            if replaced and c.tag != inkex.addNS('flowRegion', 'svg'):
                element.remove(c)
            elif c.tag != inkex.addNS('flowRegion', 'svg'):
                child_replaced = self.setFirstTextChild(c, name, text)
                if child_replaced:
                    replaced = True
                else:
                    element.remove(c)
        return replaced

    def addLayer(self, svg, what, nr, extra=""):
        if len(extra) > 0:
            extralabel = " (%s)" % extra
            extraid = "_%s" % extra
        else:
            extralabel = ""
            extraid = ""
        llabel = 'Countersheet %s %d%s' % (what, nr, extralabel)
        lid = 'cs_layer_%04d%s' % (nr, extraid)

        if self.find_layer(svg, llabel) is not None:
            sys.exit("Image already contains a layer '%s'. "
                     "Remove that layer before running extension again. "
                     "Or set a different Name when running the extension. "
                     "Or just rename the existing layer." % llabel)

        layer = etree.Element(inkex.addNS('g', 'svg'))
        layer.set(inkex.addNS('label', 'inkscape'), llabel)
        layer.set('id', lid)
        layer.set(inkex.addNS('groupmode', 'inkscape'), 'layer')
        return layer

    def generatecounter(self, c, rects, layer, colx, rowy, rotate):
        oldcs = self.document.xpath("//svg:g[@id='%s']"% c.id,
                                    namespaces=NSS)
        if len(oldcs):
            self.logwrite("Found existing %d old counters for %s"
                          % (len(oldcs), c.id))
            for oldc in oldcs:
                oldc.set('id', '')
        clonegroup = etree.Element(inkex.addNS('g', 'svg'))
        c.elements.append(clonegroup)
        if c.id != None and len(c.id):
            clonegroup.set('id', c.id)
            self.exportids.append(c.id)
        self.logwrite("adding counter with %d parts at %d,%d\n"
                      % (len(c.parts), colx, rowy))
        for p in c.parts:
            if len(p) == 0:
                continue
            rectname = p
            killrect = False
            if rectname[0] == "@":
                killrect = True
                rectname = rectname[1:]
            if rectname not in rects:
                sys.exit("Unable to find rectangle with id '%s' "
                         "that was specified in the CSV data file."
                         % rectname)
            rect = rects[rectname]
            group = find_top_level_group_for(rect)
            if group is None:
                self.logwrite("rect not in group '%s'.\n" % rectname)
                sys.exit("Rectangle '%s' not in a group. Can not be template."
                         % rectname)
            source_layer = get_layer(rect)
            x = self.geometry[rectname].x
            y = self.geometry[rectname].y
            width = self.geometry[rectname].w
            height = self.geometry[rectname].h
            c.width = max(c.width, width)
            c.height = max(c.height, height)
            clone = deepcopy(group)
            if killrect:
                for r in clone.xpath('//svg:rect', namespaces=NSS):
                    if r.get("id") == rectname:
                        r.getparent().remove(r)
                        break
            textishnodes = []
            textishnodes.extend(clone.xpath('//svg:text', namespaces=NSS))
            textishnodes.extend(clone.xpath('//svg:flowSpan',
                                            namespaces=NSS))
            textishnodes.extend(clone.xpath('//svg:flowRoot',
                                            namespaces=NSS))
            for t in textishnodes:
                self.substitute_text(c, t, t.get("id"))

            for i in clone.xpath('//svg:image', namespaces=NSS):
                imageid = i.get("id")
                if not imageid:
                    continue
                for glob,image in c.subst.items():
                    if fnmatch.fnmatchcase(imageid, glob):
                        if len(image) > 0:
                            href = self.make_image_href(image)
                            i.set(inkex.addNS("absref", "sodipodi"), href)
                            i.set(inkex.addNS("href", "xlink"), href)
                        else:
                            i.getparent().remove(i)
                    elif is_valid_name_to_replace(glob) and image is not None:
                        absref = i.get(inkex.addNS("absref", "sodipodi"), image)
                        href = self.make_image_href(i.get(inkex.addNS("href", "xlink"), image))
                        i.set(inkex.addNS("absref", "sodipodi"),
                              absref.replace("%%%s%%" % glob, image))
                        i.set(inkex.addNS("href", "xlink"),
                              href.replace("%%%s%%" % glob, image))

            for u in clone.xpath('//svg:use', namespaces=NSS):
                useid = u.get("id")
                if not useid:
                    continue
                for glob,new_ref in c.subst.items():
                    if fnmatch.fnmatchcase(useid, glob):
                        if len(new_ref) > 0:
                            xlink_attribute = inkex.addNS("href", "xlink")
                            old_ref = u.get(xlink_attribute)[1:]
                            u.set(xlink_attribute, "#" + new_ref)
                            self.translate_use_element(u, old_ref, new_ref)
                        else:
                            u.getparent().remove(u)

            for name,value in c.subst.items():
                if is_valid_name_to_replace(name):
                    string_replace_xml_text(clone, "%%%s%%" % name, value)

            if len(c.excludeids):
                excludeelements = []
                for e in clone.iterdescendants():
                    eid = e.get("id")
                    if not c.is_included(eid):
                        excludeelements.append(e)
                for ee in excludeelements:
                    eeparent = ee.getparent()
                    if eeparent is not None:
                        ee.getparent().remove(ee)
            self.replaceattrs(clone.iterdescendants(), c.attrs)
            converter = DocumentTopLeftCoordinateConverter( source_layer )
            ( source_layer_adjusted_x, source_layer_adjusted_y) = converter.SVG_to_dtl( ( -x, -y ) )
            self.translate_element(clone, source_layer_adjusted_x, source_layer_adjusted_y)
            self.logwrite("cloning %s\n" % clone.get("id"))
            clonegroup.append(clone)
        self.translate_element(clonegroup, colx, rowy)
        self.rotate_element(clonegroup, rotate, c.width, c.height)
        layer.append(clonegroup)
        # this is not ideal, but works for the inx enum
        if rotate == 90 or rotate == -90:
            return [c.height, c.width]
        else:
            return [c.width, c.height]

    def substitute_text(self, c, t, textid):
        for glob,subst in c.subst.items():
            if glob is None:
                continue
            if subst is None:
                subst = ""
            if fnmatch.fnmatchcase(textid, glob):
                if (t.tag == inkex.addNS('flowRoot','svg')
                    and subst.find("\\n") >= 0):
                    self.setMultilineText(t, textid, subst.split("\\n"))
                else:
                    if not self.setFirstTextChild(t, textid, subst):
                        # Could not find anything to replace, so just delete
                        # everything and set the text for all the text element.
                        self.deleteTextChildren(t)
                        childtype = 'tspan'
                        if t.tag == inkex.addNS('flowRoot','svg'):
                            childtype = 'flowSpan'
                        self.setFormattedText(t, textid, subst,
                                              childtype, {},
                                              inkex.Style.parse_str(t.get('style')))
                if c.id:
                    t.set("id", textid + "_" + c.id)

    def find_layer(self, svg, layer_name):
        """Find a layer with given label in the SVG.

        Returns None if there is none, so always
        check the return value. Nothing exceptional
        about a SVG not containing a specific layer
        so not going to throw an exception."""

        for g in svg.xpath('//svg:g', namespaces=NSS):
            if (g.get(inkex.addNS('groupmode', 'inkscape')) == 'layer'
                and (g.get(inkex.addNS('label', 'inkscape'))
                     == layer_name)):
                return g

    def readLayout(self, svg):
        g = self.find_layer(svg, "cs_layout")
        if g is None:
            g = self.find_layer(svg, "countersheet_layout")
        if g is not None:
            res = []
            self.logwrite("Found layout layer!\n")
            for c in g.getchildren():
                if c.tag == inkex.addNS('rect','svg'):
                    res.append(self.geometry[c.get('id')])
                elif c.tag == inkex.addNS('use','svg'):
                    # using all clones even if they might not be rectangles
                    # not sure if that is a problem in practice
                    # but perhaps worth a FIXME some rainy day
                    res.append(self.geometry[c.get('id')])
                elif c.tag == inkex.addNS('text','svg'):
                    pass # use to set countersheet label?
            return res
        return False

    def addbacks(self, layer, bstack, backxs, backys, docwidth, rects):
        self.logwrite("addbacks %d\n" % len(bstack))
        for c,x,y in zip(bstack, backxs, backys):
            self.logwrite("   adding back\n")
            self.generatecounter(c.back, rects,
                                 layer,
                                 docwidth - x,
                                 y,
                                 self.options.rotatebacks)

    # Looked a bit at code in Inkscape text_merge.py for this idea.
    # That file is Copyright (C) 2013 Nicolas Dufour (jazzynico).
    # See README file for license.
    def queryAll(self, filename):
        "Return geometry Rectangle (x, y, w, h) for each element id, as dict."
        geometry = {}
        # TODO some error-checking would be good for the next few lines
        inputfile = open(filename, "r")
        filecontents = inputfile.read()
        inputfile.close()
        tmpfile = mkstemp(".svg")
        tmpfilefile = os.fdopen(tmpfile[0], 'w')
        tmpfilefile.write(filecontents)
        tmpfilefile.close()
        cmd = 'inkscape --query-all "%s"' % tmpfile[1]
        out, err = popen3(cmd)
        reader = csv.reader(out.splitlines())
        for line in reader:
            if len(line) == 5:
                self.logwrite(",".join(line) + "\n")
                element_id = line[0]
                r = Rectangle(float(line[1]) / self.xscale,
                              float(line[2]) / self.yscale,
                              float(line[3]) / self.xscale,
                              float(line[4]) / self.yscale)
                self.logwrite(" %s %f,%f %fx%f\n"
                              % (element_id, r.x, r.y, r.w, r.h))
                geometry[element_id] = r
        print_filtered_stderr(err)
        os.remove(tmpfile[1])
        return geometry

    def exportBitmaps(self, ids, width, height, dpi=0):
        if dpi > 0:
            exportsize = "-d %d" % dpi
        else:
            exportsize = "-w %d -h %d" % (width, height)
        self.export_using_inkscape(ids, exportsize,
                                   self.options.bitmapdir,
                                   "png")

    def make_temporary_svg(self, exportdir=None):
        """ Renders SVG DOM as it currently looks like
        in the extension with modifications made (or not)
        since reading the original file. The caller is
        responsible for removing the file
        when done with it.
        Use exportdir=None to use default system tmp dir.
        Returns filename."""
        if exportdir is not None:
            exportdir = os.path.abspath(exportdir)
        tmpfile = mkstemp(".svg", "tmp", exportdir, True)
        tmpfileobject = os.fdopen(tmpfile[0], 'wb')
        self.document.write(tmpfileobject)
        tmpfileobject.close()
        return tmpfile[1]

    def export_using_inkscape(self, ids, size_flags,
                                exportdir, extension,
# this is an ugly workaround for
# https://bugs.launchpad.net/inkscape/+bug/1714365
                              noidexportworkaround=False):
        tmpfilename = self.make_temporary_svg(exportdir)
        self.logwrite("export to tmpfilename: %s\n" % tmpfilename)
        self.logwrite(" ids to export: %r\n" % ids)
        for id in ids:
            if len(self.document.xpath("//*[@id='%s']" % id,
                                       namespaces=NSS)) == 0:
                continue
            if noidexportworkaround:
                idflag = ""
            else:
                idflag = "-i %s" % id
            cmd='inkscape %s -j -o "%s" %s "%s"' % (
                idflag,
                self.getbitmapfilename(id, exportdir, extension), #FIXME
                size_flags, tmpfilename)
            self.logwrite(cmd + "\n")
            _out, err = popen3(cmd)
            print_filtered_stderr(err)
        os.remove(tmpfilename)

    def getbitmapfilename(self, id, directory, extension):
        return os.path.join(os.path.abspath(directory),
                            self.bitmapname + id) + "." + extension

    def hidelayers(self, layer_ids):
        self.set_style_on_elements(layer_ids, 'display', 'none')

    def showlayers(self, layer_ids):
        self.set_style_on_elements(layer_ids, 'display', None)

    def set_style_on_elements(self, element_ids, part, value):
        self.logwrite("set_style_on_elements %r %s=%s\n"
                      % (element_ids, part, value))
        for element_id in element_ids:
            matching_elements = self.document.xpath("//*[@id='%s']" % element_id,
                                                    namespaces=NSS)
            if not matching_elements:
                return
            self.set_style(matching_elements[0],
                           part, value)

    def set_style(self, element, part, value):
        oldstyle = element.get('style') or ""
        newstyle = stylereplace(oldstyle, part, value)
        element.set('style', newstyle)
        self.logwrite("set_style %s: '%s' -> '%s'\n"
                      % (element.get('id'), oldstyle, newstyle))

    def exportSheetPDFs(self):
        self.logwrite("exportSheetPDFs %s %d\n" % (self.options.pdfdir,
                                                   len(self.cslayers)))
        if (self.options.pdfdir
            and len(self.cslayers) > 0):
            for layer in self.cslayers:
                self.logwrite("  export PDF layer\n")
                self.hidelayers(self.cslayers)
                self.showlayers([layer])
                self.export_using_inkscape([layer],
                                           "-d %d" % PDF_DPI,
                                           self.options.pdfdir,
                                           "pdf",
                                           True)
        self.showlayers(self.cslayers)

    def exportSheetBitmaps(self):
        if (self.options.bitmapsheetsdpi > 0
            and len(self.cslayers) > 0
            and self.options.bitmapdir
            and len(self.options.bitmapdir)):
            self.exportBitmaps(self.cslayers, 0, 0,
                               self.options.bitmapsheetsdpi)

    def exportIDBitmaps(self):
        if (len(self.exportids) > 0
            and self.options.bitmapdir
            and len(self.options.bitmapdir) > 0
            and self.options.bitmapwidth > 0
            and self.options.bitmapheight > 0):
            if self.bleed:
                self.bleedmaker.hideall()
            self.exportBitmaps(self.exportids,
                               self.options.bitmapwidth,
                               self.options.bitmapheight)
            if self.bleed:
                self.bleedmaker.showall()
            return True
        return False

    def create_registrationline(self, x1, y1, x2, y2):
        self.logwrite("create_registrationline %f,%f %f,%f\n"
                      % (x1, y1, x2, y2))
        line = etree.Element('line')
        line.set("x1", str(x1))
        line.set("y1", str(y1))
        line.set("x2", str(x2))
        line.set("y2", str(y2))
        line.set("style", self.find_registration_line_style())
        line.set("stroke-width", str(PS * 0.5))
        return line

    def find_registration_line_style(self):
        regstyle_elements = self.document.xpath("//*[@id='cs_regstyle']",
                                               namespaces=NSS)
        if len(regstyle_elements) > 0:
            regstyle = regstyle_elements[0].get("style")
            if regstyle is not None and len(regstyle) > 0:
                return regstyle
        return DEFAULT_REGISTRATION_MARK_STYLE

    def add_registration_line(self, x1, y1, x2, y2, layer):
            layer.append(self.create_registrationline(x1, y1, x2, y2))

    def add_registration_line_both_sides(self, x1, y1, x2, y2, layer,
                                         backlayer, docwidth):
        self.add_registration_line(x1, y1, x2, y2, layer)
        if backlayer is not None and self.registrationmarksbothsides:
                self.add_registration_line(docwidth-x1, y1, docwidth-x2,
                                           y2, backlayer)

    def addregistrationmarks(self, xregistrationmarks, yregistrationmarks,
                             position, layer, backlayer, docwidth):
        if self.registrationmarkslen <= 0:
            return
        linelen = self.registrationmarkslen
        linestart = self.registrationmarksdist
        max_x = 0
        max_y = 0
        for x in xregistrationmarks:
            self.logwrite("registrationmark x: %f\n" % x)
            self.add_registration_line_both_sides(position.x + x,
                                                  position.y - linestart,
                                                  position.x + x,
                                                  position.y - linelen - linestart,
                                                  layer,
                                                  backlayer,
                                                  docwidth)
            max_x = max(max_x, x)

        for y in yregistrationmarks:
            self.logwrite("registrationmark y: %f\n" % y)
            self.add_registration_line_both_sides(position.x - linestart,
                                                  position.y + y,
                                                  position.x - linelen - linestart,
                                                  position.y + y,
                                                  layer,
                                                  backlayer,
                                                  docwidth)
            max_y = max(max_y, y)

        for x in xregistrationmarks:
            start_y = position.y + max_y
            if self.fullregistrationmarks:
                start_y = position.y
            self.add_registration_line_both_sides(
                position.x + x,
                start_y + linestart,
                position.x + x,
                position.y + max_y + linelen + linestart,
                layer,
                backlayer,
                docwidth)

        for y in yregistrationmarks:
            start_x = position.x + max_x
            if self.fullregistrationmarks:
                start_x = position.x
            self.add_registration_line_both_sides(
                start_x + linestart,
                position.y + y,
                position.x + max_x + linelen + linestart,
                position.y + y,
                layer,
                backlayer,
                docwidth)

        if self.outlinemarks:
            x1 = position.x - self.outlinedist
            y1 = position.y - self.outlinedist
            x2 = position.x + max_x + self.outlinedist
            y2 = position.y + max_y + self.outlinedist
            self.add_outlinemarks(layer, x1, y1, x2, y2)
            if backlayer is not None:
                self.add_outlinemarks(backlayer,
                                      docwidth - x1, y1,
                                      docwidth - x2, y2)

    def add_outlinemarks(self, layer, x1, y1, x2, y2):
        self.logwrite("Outline rectangle around %f,%f %f,%f\n"
                      % (x1, y1, x2, y2))
        layer.append(self.create_registrationline(
            x1, y1, x2, y1))
        layer.append(self.create_registrationline(
            x1, y1, x1, y2))
        layer.append(self.create_registrationline(
            x1, y2, x2, y2))
        layer.append(self.create_registrationline(
            x2, y1, x2, y2))


    def from_len_arg(self, argvalue, name, allow_negative=False):
        if argvalue is None or len(argvalue) == 0:
            return 0.0
        value = self.svg.unittouu(argvalue)
        if not allow_negative and value < 0:
            sys.exit("Negative %s marks makes no sense." % name)

        self.logwrite("%s: %f\n"
                      % (name, value))
        return value

    def calculateScale(self, svg):
        """Calculates scale of the document (user-units size) and
        saves as self.xscale and self.yscale.
        Because of this bug:
        https://bugs.launchpad.net/inkscape/+bug/1508400
        Code is based on code in measure.py included in the Inkscape 0.92
        distribution (see that file for credits), license GPLv2 like
        the rest of this extension.
        Error-handling is lacking.
        """
        self.xscale = self.yscale = 1.0 / self.svg.unittouu('1px')
        xscale = yscale = 0.0
        try:
            viewbox = svg.get('viewBox')
            if viewbox:
                self.logwrite("viewBox: %s\n" % viewbox)
                (viewx, viewy, vieww, viewh) = list(map(float, re.sub(' +|, +|,',' ', viewbox).strip().split(' ', 4)))
                svgwidth = svg.get('width')
                svgheight = svg.get('height')
                svguuwidth = self.svg.unittouu(svgwidth)
                svguuheight = self.svg.unittouu(svgheight)
                self.logwrite("SVG widthxheight: %sx%s\n"
                              % (svgwidth, svgheight))
                self.logwrite("SVG size in user-units: %fx%f\n"
                              % (svguuwidth, svguuheight))
                xscale = self.svg.unittouu(svg.get('width')) / vieww / self.svg.unittouu("1px")
                yscale = self.svg.unittouu(svg.get('height')) / viewh / self.svg.unittouu("1px")
                self.xscale = xscale
                self.yscale = yscale
        except Exception as e:
            self.logwrite("Failed to calculate document scale:\n%s\n" % repr(e))

    def getDocumentViewBoxValue(self, svg, n, fallback):
        try:
            return float(svg.get('viewBox').split(' ')[n])
        except:
            return self.svg.unittouu(svg.get(fallback)) # let it crash if this fails

    # Because getDocumentWidth in inkex fails because it makes assumptions about
    # user-units. Trusting the viewBox instead for now.
    def getViewBoxWidth(self, svg):
        return self.getDocumentViewBoxValue(svg, 2, "width")

    # Because getDocumentHeight in inkex fails because it makes assumptions about
    # user-units. Trusting the viewBox instead for now.
    def getViewBoxHeight(self, svg):
        return self.getDocumentViewBoxValue(svg, 3, "height")

    def effect(self):
        global PS

        # Get script "--what" option value.
        what = self.options.what

        doc = self.document

        self.exportids = []
        self.cslayers = []
        self.bitmapname = self.options.bitmapname

        self.textmarkup = self.options.textmarkup == "true"
        self.bleed = self.options.bleed == "true"
        self.oneside = self.options.oneside == "true"

        self.logwrite("svg path: %s\n" % self.svg_path())

        self.logwrite("bleed enabled: %r\n" % self.bleed)

        self.logwrite("one-sided sheets: %r\n" % self.oneside)

        self.logwrite("svg.width: %s\n" % self.svg.width)
        self.logwrite("svg.height: %s\n" % self.svg.height)
        self.logwrite("svg.unit: %s\n" % self.svg.unit)

        self.fullregistrationmarks = (self.options.fullregistrationmarks
                                      == "true")
        self.registrationmarksbothsides = (self.options.registrationmarksbothsides
                                           == "true")

        self.logwrite("full registration marks: %r\n"
                      % self.fullregistrationmarks)

        # Get access to main SVG document element and get its dimensions.
        svg = self.document.xpath('//svg:svg', namespaces=NSS)[0]

        founddefs = svg.xpath('//svg:defs', namespaces=NSS)
        if len(founddefs) > 0:
            self.defs = founddefs[0]
        else:
            self.defs = etree.Element(inkex.addNS("defs", "svg"))
            svg.append(self.defs)

        if self.bleed:
            self.bleedmaker = BleedMaker(svg, self.defs)

        self.registrationmarkslen = self.from_len_arg(
            self.options.registrationmarkslen,
            "registration marks length")
        self.registrationmarksdist = self.from_len_arg(
            self.options.registrationmarksdist,
            "registration marks distance from component")
        self.outlinedist = self.from_len_arg(
            self.options.outlinedist,
            "outline distance")
        self.spacing = self.from_len_arg(
            self.options.spacing,
            "spacing")
        self.backoffsetx = self.from_len_arg(self.options.backoffsetx,
                                             "back horizontal offset", True)
        self.backoffsety = self.from_len_arg(self.options.backoffsety,
                                             "back vertical offset", True)

        self.outlinemarks = (self.outlinedist > 0)

        self.calculateScale(svg)

        datafile = find_file(self.options.datafile)

        if self.options.imagedir and os.path.isdir(self.options.imagedir):
            self.imagedir = self.options.imagedir
        else:
            self.imagedir = os.path.dirname(datafile)

        # a small, "pixel-size", length, to use for making small
        # adjustments that works in Inkscape 0.91 and later, similar
        # to what "1px" always was in earlier Inkscape versions
        PS = self.svg.unittouu("%fin" % (1.0 / 90))

        rects = {}
        for r in doc.xpath('//svg:rect', namespaces=NSS):
            rects[r.get("id")] = r

        self.logwrite("queryAll for: %s\n" % sys.argv[-1])
        self.geometry = self.queryAll(os.path.abspath(sys.argv[-1]))

        self.logwrite('Using data file %s.\n'
                      % os.path.abspath(datafile))

        try:
            csv.Sniffer
        except:
            sys.exit("Not able to find csv.Sniffer. "
                     "Please delete csv.py and csv.pyc "
                     "files from your Inkscape extensions."
                     "folder. They are no longer used.");

        csv_file = open(datafile, "rt", encoding="utf-8-sig")
        try:
            csv_dialect = csv.Sniffer().sniff(csv_file.read(2000))
        except:
            self.logwrite("csv sniffer failed, trying just first line.\n")
            csv_file.seek(0)
            csv_dialect = csv.Sniffer().sniff(csv_file.readline())
        csv_file.seek(0)
        reader = csv.reader(csv_file, csv_dialect)

        parser = CSVCounterDefinitionParser(
            self.logwrite, rects,
            self.defs,
            os.path.dirname(datafile))
        parser.parse(reader)
        csv_file.close()
        counters = parser.counters
        hasback = parser.hasback

        frontlayers = []
        backlayers = []

        # Create a new layer.
        layer = self.addLayer(svg, what, 1)

        backlayer = None

        if hasback:
            if self.oneside:
                backlayer = layer
            else:
                backlayer = self.create_backlayer(svg, what, 1)

        docwidth = self.getViewBoxWidth(svg)

        self.logwrite("user-units in 1 inch: %f\n" % self.svg.unittouu("1in"))
        self.logwrite("user-units in 1 px: %f\n" % self.svg.unittouu("1px"))
#        self.logwrite("uuconv['in']: %f\n" % self.__uuconv["in"])

        self.logwrite("calculated document scale: %f %f\n"
                      % (self.xscale, self.yscale))

        haslayout = True
        positions = self.readLayout(svg)
        if not positions or len(positions) < 1:
            haslayout = False
            positions = [Rectangle(0.0,
                                   0.0,
                                   docwidth,
                                   self.getViewBoxHeight(svg))]
            margin = max(self.registrationmarkslen,
                         self.outlinedist)
            positions[0].x += margin
            positions[0].y += margin
            positions[0].w -= margin * 2
            positions[0].h -= margin * 2

        for n,p in enumerate(positions):
            self.logwrite("layout position %d: %f %f %f %f\n"
                          % (n, p.x, p.y, p.w, p.h))

        row = 0
        col = 0
        colx = 0
        rowy = 0
        nextrowy = 0
        box = 0
        nr = 0
        csn = 1

        xregistrationmarks = set([0])
        yregistrationmarks = set([0])

        is_first_col = True
        is_first_row = True

        bstack = []
        backxs = []
        backys = []

        for i,c in enumerate(counters):
            self.before_counter(c)
            while(c.can_add_another()):
                last_on_row = False
                last_in_box = False
                last_on_sheet = False
                nr = nr + 1
                self.logwrite("laying out counter %d (nr %d/%r, c.nr %d)"
                              " (hasback: %s)\n"
                              % (i, nr, c.repeat.nr, c.repeat.keep_going,
                                 c.hasback))
                c.addsubst("autonumber", str(nr))
                if c.hasback:
                    c.back.addsubst("autonumber", str(nr))
                xregistrationmarks.add(colx)
                yregistrationmarks.add(rowy)
                self.logwrite("   adding front\n")
                width, height=self.generatecounter(c, rects, layer,
                                                   positions[box].x+colx,
                                                   positions[box].y+rowy,
                                                   self.options.rotatefronts)
                self.logwrite("generated counter size: %fx%f\n"
                              % (width, height))
                c.bleed_left.append(is_first_col or self.spacing > 0)
                is_first_col = False
                c.bleed_up.append(is_first_row or self.spacing > 0)
                if c.hasback:
                    bstack.append(c)
                    backxs.append(positions[box].x + colx + width)
                    backys.append(positions[box].y + rowy)
                col = col + 1
                xregistrationmarks.add(colx + width)
                colx = colx + width + self.spacing
                if rowy + height + self.spacing > nextrowy:
                    nextrowy = rowy + height + self.spacing
                    yregistrationmarks.add(rowy + height)
                if (colx + width > positions[box].w + BOX_MARGIN
                    or c.endbox or c.endrow):
                    last_on_row = True
                    col = 0
                    colx = 0
                    row = row + 1
                    rowy = nextrowy
                    nextrowy = rowy
                    self.logwrite("new row %d (y=%f)\n"
                                  % (row, rowy))
                    is_first_col = True
                    is_first_row = False
                    if (nextrowy + height > positions[box].h + BOX_MARGIN
                        or c.endbox):
                        last_in_box = True
                        self.addregistrationmarks(
                            xregistrationmarks, yregistrationmarks,
                            positions[box], layer, backlayer, docwidth)
                        xregistrationmarks = set([0])
                        yregistrationmarks = set([0])
                        box = box + 1
                        self.logwrite(" now at box %d of %d\n" % (box, len(positions)))
                        self.logwrite(" i: %d    len(counters): %d\n" % (i, len(counters)))
                        row = 0
                        rowy = 0
                        nextrowy = 0
                        is_first_row = True
                        if box == len(positions) and i < len(counters):
                            last_on_sheet = True
                            csn = csn + 1
                            if hasback:
                                self.addbacks(backlayer, bstack,
                                              backxs, backys,
                                              docwidth,
                                              rects)
                                bstack = []
                                backxs = []
                                backys = []
                                if not self.oneside:
                                    svg.append(backlayer)
                                    backlayers.append((backlayer, csn-1))
                                    self.cslayers.append(backlayer.get('id'))
                                    backlayer = self.create_backlayer(svg, what, csn)
                            svg.append(layer)
                            frontlayers.append((layer, csn-1))
                            self.cslayers.append(layer.get('id'))
                            layer = self.addLayer(svg, what, csn)
                            box = 0
                            if self.oneside:
                                backlayer = layer
                c.added_one(last_on_row, last_in_box, last_on_sheet)

        if ((len(xregistrationmarks) > 1
             or len(yregistrationmarks) > 1)
            and len(layer.getchildren())):
            self.addregistrationmarks(
                xregistrationmarks, yregistrationmarks,
                positions[box], layer, backlayer, docwidth)

        if hasback:
            self.addbacks(backlayer, bstack,
                          backxs, backys,
                          docwidth, rects)

        if self.bleed:
            self.logwrite(" add_bleed_to %d\n" % len(counters))
            self.bleedmaker.add_bleed_to(counters)

        if not self.oneside and hasback and len(backlayer.getchildren()):
            svg.append(backlayer)
            backlayers.append((backlayer, csn))
            self.cslayers.append(backlayer.get('id'))

        if len(layer.getchildren()):
            svg.append(layer)
            frontlayers.append((layer, csn))
            self.cslayers.append(layer.get('id'))

        nrsheets = max(len(frontlayers), len(backlayers))

        if len(self.placeholders) > 0:
            tmpfile = self.make_temporary_svg()
            self.logwrite("Placeholders replace temporary file: %s\n" % tmpfile)
            geometry = self.queryAll(tmpfile)
            for spanid, info in self.placeholders.items():
                if not spanid in geometry:
                    self.logwrite("Could not query location for %s."
                                  % spanid)
                    continue
                position = geometry[spanid]
                self.logwrite('placeholder position: {},{} {}x{}'.format(position.x, position.y, position.w, position.h))
                image = etree.Element(inkex.addNS('image', 'svg'))
                href = self.make_image_href(info["filename"])
                image.set(inkex.addNS("absref", "sodipodi"), href)
                image.set(inkex.addNS("href", "xlink"), href)
                dim_diff = position.h - position.w
                dx = position.x
                dy = position.y + position.h * DEFAULT_INLINE_IMAGE_YSHIFT + dim_diff / 2
                image.set('width', str(position.w))
                image.set('height', str(position.h - dim_diff))
                group = find_top_level_group_for(info["parent"])
                transform = group.get('transform')
                translate = self.translatere.match(transform)
                if translate:
                    dx -= float(translate.group(1))
                    dy -= float(translate.group(2))
                    self.logwrite('placeholder translate: {},{}\n'.format(dx, dy))
                self.translate_element(image, dx, dy)
                group.append(image)
        #os.remove(tmpfile)

        self.logwrite("nrsheets: %d\n" % nrsheets)
        self.logwrite("layers in self.cslayers: %d\n" % len(self.cslayers))
        self.add_layer_backgrounds(frontlayers,
                                   self.find_layer(svg, "cs_background_front"),
                                   nrsheets)
        self.add_layer_backgrounds(backlayers,
                                   self.find_layer(svg, "cs_background_back"),
                                   nrsheets)

        exportedbitmaps = self.exportIDBitmaps()
        self.post(counters)
        self.exportSheetBitmaps()
        self.exportSheetPDFs()

        if self.log:
            self.log.close()

    def add_layer_backgrounds(self, layers, sheet_template, nrsheets):
        if sheet_template is None:
            return
        for target,nr in layers:
            self.logwrite("  add layer background %d\n" % nr)
            background = deepcopy(sheet_template)
            string_replace_xml_text(background, "%SHEET%",
                                    str(nr))
            string_replace_xml_text(background, "%SHEETS%",
                                    str(nrsheets))
            del background.attrib[inkex.addNS('groupmode', 'inkscape')]
            del background.attrib[inkex.addNS('label', 'inkscape')]
            self.set_style(background, 'display', None)
            target.insert(0, background)

    def create_backlayer(self, svg, what, csn):
        backlayer = self.addLayer(svg, what,
                      csn, "back")
        if self.backoffsetx != 0 or self.backoffsety != 0:
            self.translate_element(backlayer,
                                   self.backoffsetx,
                                   self.backoffsety)
        return backlayer

    def make_image_href(self, filename):
        if os.path.isabs(filename):
            return filename
        else:
            return os.path.join(self.imagedir, filename)

    def before_counter(self, counter):
        pass

    def post(self, counters):
        pass

class CSVCounterDefinitionParser:
    def __init__(self, logwrite, rects, defs, datadir):
        self.logwrite = logwrite
        self.rects = rects
        self.defs = defs
        self.counters = []
        self.hasback = False
        self.datadir = datadir

    def parse(self, reader):
        factory = None
        for row in reader:
            factory = self.parse_row(row, factory)

    def parse_row(self, row, factory):
        if self.is_counterrow(factory, row):
            return self.parse_counter_row(row, factory)
        elif self.is_newheaders(row):
            self.logwrite('Found new headers: %s\n' % ';'.join(row))
            return CSVCounterFactory(self.rects, self.defs,
                                     row, self.datadir)
        else:
            self.logwrite('Empty row... reset headers.\n')
            return False

    def is_counterrow(self, factory, row):
        return factory and len(row) > 0 and len("".join(row)) > 0

    def is_newheaders(self, row):
        return len(row) > 0 and len("".join(row)) > 0

    def must_parse_int(self, nrstr, endindex):
        try:
            return int(nrstr[:endindex].strip())
        except:
            sys.exit("Failed to parse repeat cell '%s'"
                     % nrstr)

    def parse_counter_row(self, row, factory):
        repeat = RepeatExact(1)
        if len(row[0]) > 0:
            if row[0] == 'ENDBOX':
                if len(self.counters) > 0:
                    self.counters[-1].endbox = True
                return factory
            elif row[0] == 'ENDROW':
                if len(self.counters) > 0:
                    self.counters[-1].endrow = True
                return factory
            else:
                nrstr = row[0]
                if nrstr.endswith('+++'):
                    nr = self.must_parse_int(nrstr, -3)
                    repeat = RepeatMinFillSheet(nr)
                elif nrstr.endswith('++'):
                    nr = self.must_parse_int(nrstr, -2)
                    repeat = RepeatMinFillBox(nr)
                elif nrstr.endswith('+'):
                    nr = self.must_parse_int(nrstr, -1)
                    repeat = RepeatMinFillRow(nr)
                else:
                    try:
                        nr = int(nrstr)
                        repeat = RepeatExact(nr)
                    except ValueError:
                        return CSVCounterFactory(self.rects,
                                                 self.defs,
                                                 row,
                                                 self.datadir)
        self.logwrite('new counter: %s\n' % ';'.join(row))
        cfront = factory.create_counter(repeat, row)
        self.hasback = self.hasback or factory.hasback
        self.logwrite('self.hasback: %s  factory.hasback: %s\n'
                      % (str(self.hasback), str(factory.hasback)))
        self.counters.append(cfront)
        if cfront.id and cfront.hasback and not cfront.back.id:
            cfront.back.id = cfront.id + "_back"
        return factory

class CounterFactory (object):
    def __init__(self, rects, defs, datadir):
        self.rects = rects
        self.defs = defs
        self.hasback = False
        self.datadir = datadir

class CSVCounterFactory (CounterFactory):
    def __init__(self, rects, defs, row, datadir):
        super(CSVCounterFactory, self).__init__(rects, defs, datadir)
        self.parse_headers(row)

    def parse_headers(self, row):
        self.headers = []
        nextbackground = True
        if len(row) == 0:
            return
        self.headers.append(self.parse_background_header(row[0]))
        for i,h in enumerate(row[1:]):
            if len(h) > 0:
                header = self.parse_header(h)
            else:
                header = EmptyLayout()
            self.headers.append(header)

    def parse_background_header(self, h):
        if self.iscopytoback(h):
            return CopyToBackLayoutDecorator(
                self.parse_background_header(h[:-1]))
        elif len(h):
            return CounterPartBackgroundLayout(h)
        else:
            return EmptyLayout()

    def parse_header(self, h):
        if self.iscopytoback(h):
            return CopyToBackLayoutDecorator(self.parse_header(h[:-1]))
        elif self.isaddpartheader(h):
            return CounterPartLayout(h[1:])
        elif self.isaddpartwithoutrectangleheader(h):
            return CounterPartCopyWithoutRectangleLayout(h[1:])
        elif self.isoptionheader(h):
            return CounterOptionLayout(h[:-1])
        elif self.ismultioptionheader(h):
            return CounterMultiOptionLayout(h[:-2])
        elif self.isattributeheader(h):
            return AttributeLayout(h, self.rects,
                                   self.defs)
        elif self.isidheader(h):
            return IDLayout()
        elif self.isbackheader(h):
            return BackLayout(h)
        elif self.isdefaultvalueheader(h):
            return self.parse_defaultvalueheader(h)
        else:
            return CounterSubstLayout(h)

    def create_counter(self, repeat, row):
        cfront = Counter(repeat)
        c = cfront
        for i,ho in enumerate(self.headers):
            h = ho.raw
            setting = CounterSettingHolder()
            if i < len(row):
                value = row[i]
                if value.startswith('<<') and len(value) > 2:
                    value = self.read_value_from_file(value[2:])
            else:
                value = None
            ho.set_setting(setting, value)
            if setting.back:
                if (i >= len(row)
                    or (row[i] != 'BACK'
                        and not is_yes_value(row[i]))):
                    break
                c.hasback = True
                c = c.doublesided()
                self.hasback = True
            if c:
                setting.applyto(c)
        return cfront

    def read_value_from_file(self, filename):
        real_filename = find_file(filename, [self.datadir])
        f = open(real_filename, 'rt', encoding="utf-8-sig")
        res = "\\n".join(f.readlines())
        f.close()
        return res

    def isbackheader(self, h):
        return h == 'BACK'

    def isaddpartheader(self, h):
        return h[0] == '+'

    def isaddpartwithoutrectangleheader(self, h):
        return h[0] == '@'

    def iscopytoback(self, h):
        return len(h) and h[-1] == ">"

    def isoptionheader(self, h):
        return len(h) > 1 and h[-1] == '?' and h[-2] != '-'

    def ismultioptionheader(self, h):
        return len(h) > 2 and h[-1] == '?' and h[-2] == '-'

    def isattributeheader(self, h):
        return len(h) > 2 and h.find('[') > 0 and h[-1] == ']'

    def isidheader(self, h):
        return h == 'ID'

    def isdefaultvalueheader(self, h):
        return len(h) >= 3 and h.find('=') > 0

    def parse_defaultvalueheader(self, h):
        i = h.find('=')
        return DefaultValueLayoutDecorator(h[i+1:], self.parse_header(h[:i]))



class EmptyLayout:
    def __init__(self):
        self.raw = ''

    def set_setting(self, setting, value):
        pass

class CounterPartLayout:
    def __init__(self, id):
        self.id = id
        self.raw = id

    def set_setting(self, setting, value):
        setting.set(CounterPart(value or self.id))

class CounterPartBackgroundLayout:
    def __init__(self, id):
        self.id = id
        self.raw = id

    def set_setting(self, setting, value):
        setting.set(CounterPart(self.id))

class CounterPartCopyWithoutRectangleLayout:
    def __init__(self, value):
        self.value = value
        self.raw = value

    def set_setting(self, setting, value):
        setting.set(CounterPart("@" + (value or self.value)))

class CounterSubstLayout:
    def __init__(self, id):
        self.raw = id
        self.id = id

    def set_setting(self, setting, value):
        setting.set(CounterSubst(self.id, value))

YES_VALUES = set(['y', 'yes', 'x'])

def is_yes_value(s):
    return s.strip().lower() in YES_VALUES

class CounterOptionLayout:
    def __init__(self, id):
        self.id = id
        self.raw = id

    def set_setting(self, setting, value):
        if not is_yes_value(value):
            setting.set(CounterExcludeID(self.id))

class CounterMultiOptionLayout:
    def __init__(self, id):
        self.id = id
        self.raw = id

    def set_setting(self, setting, value):
        exclude = CounterExcludeID(self.id + "-*")
        for s in value.split(" "):
            if len(s):
                exclude.addexception(self.id + '-' + s)
        setting.set(exclude)

class BackLayout:
    def __init__(self, h):
        self.raw = h

    def set_setting(self, setting, value):
        setting.setback()

class CopyToBackLayoutDecorator:
    def __init__(self, other_header):
        self.raw = other_header.raw
        self.header = other_header

    def set_setting(self, setting, value):
        setting.setcopytoback()
        self.header.set_setting(setting, value)

class DefaultValueLayoutDecorator:
    def __init__(self, value, other_header):
        self.value = value
        self.raw = other_header.raw
        self.header = other_header

    def set_setting(self, setting, value):
        if not value:
            value = self.value
        self.header.set_setting(setting, value)

class AttributeLayout:
    def __init__(self, h, rects, defs):
        self.raw = h
        self.rects = rects
        self.defs = defs
        astart = h.find('[')
        self.aid = h[:astart]
        self.aname = h[astart+1:-1]

    def set_setting(self, setting, value):
        aname = self.aname
        if self.aname.startswith('style:') and len(value) > 0 :
            pname = aname[6:]
            if value[0] == '<':
                oldv = self.rects[value[1:]].get("style")
                value = self.getrefstyle(oldv, pname, value)
            elif pname in set(['fill', 'stroke']):
                value = self.color_lookup(value)
        setting.set(CounterAttribute(self.aid, aname, value))

    def color_lookup(self, color):
        found_id = self.defs.xpath("*[@id='%s']" % color,
                                   namespaces=NSS)
        found_href = self.defs.xpath("*[@xlink:href='#%s']" % color,
                                     namespaces=NSS)
        if len(found_href) > 0:
            return make_def_ref(found_href[0].get('id'))
        elif len(found_id) > 0:
            return make_def_ref(color)
        else:
            return color

    def getrefstyle(self, oldv, pname, value):
        [pstart, pend] = (
            find_stylepart(oldv, pname))
        if pstart >= 0 and pend > pstart:
            value = oldv[pstart:pend]
        elif pstart >= 0:
            value = oldv[pstart:]
        else:
            value = self.rects[value[1:]].get("style")
        value = value[len(pname)+1:]
        if value[-1] == ';':
            value = value[:-1]
        return value

class IDLayout:
    def __init__(self):
        self.raw = 'ID'

    def set_setting(self, setting, value):
        if len(value):
            setting.set(CounterID(value))


class DocumentTopLeftCoordinateConverter:
    '''
    Converts SVG coordinates from/to coordinates with origin at the top-left of the document.
    These coordinates can get out of sync when the page size is changed.

    The class computes any offset at time of initialization. If an instance of the class is changed
    then the page size is changed, the results of calculation will be wrong. Construct and discard
    instances of this class as needed; do not keep instances for long times.

    Different layers in the svg document can have different offsets. Create a separate converter for every
    layer you are working with.

    This class only works with simple translation transforms of the layer group element. I am hoping that
    those are the only transforms that are ever applied to layer group elements. If any other type of
    transform is applied to a layer group element, hilarity will ensue.
    '''

    def __init__(self, layerElement):
        '''
        '''
        transform = layerElement.get( "transform" )
        if not transform is None:
           matrix = inkex.Transform(transform).matrix
           dx = matrix[ 0 ][ 2 ]
           dy = matrix[ 1 ][ 2 ]
        else:
           dx = 0
           dy = 0
        self._transformX = dx
        self._transformY = dy


    def dtl_to_SVG(self, dtl_point ):
        '''
        :param point: 2-tuple (pair) of numerics (x,y) in document-top-left-coordinates (pixels)
        :type arg1: 2-tuple (pair) of numerics
        :return: returns 2-tuple of floats with values in SVG coordinates (pixels)
        :rtype: 2-tuple
        '''
        return ( dtl_point[ 0 ] - self._transformX, dtl_point[ 1 ] - self._transformY )

    def SVG_to_dtl( self, svg_point ):
        return ( svg_point[ 0 ] + self._transformX, svg_point[ 1 ] + self._transformY )


def find_stylepart(oldv, pname):
    pstart = oldv.find(pname + ":")
    if pstart < 0:
        return [-1, -1]
    pend = oldv.find(";", pstart) + 1
    return [pstart, pend]

def get_part(style, pname):
    [pstart, pend] = find_stylepart(style, pname)
    if pstart >= 0 and pend > pstart:
        return style[pstart:pend].split(":")[1]
    elif pstart >= 0:
        return style[pstart:].split(":")[1]
    else:
        return ""

def stylereplace(oldv, pname, v):
    out = ""
    replaced = False
    if v:
        newstylepart = "%s:%s;" % (pname, v)
    else:
        newstylepart = ""
    if not oldv:
        return newstylepart
    for part in oldv.split(";"):
        if part.startswith(pname + ':'):
            out += newstylepart
            replaced = True
        elif len(part):
            out += part + ";"
    if not replaced:
        out += newstylepart
    return out

validreplacenamere = re.compile("^[-\w.:]+$", re.UNICODE)

def is_valid_name_to_replace(s):
    """True if s is a string that would be OK to use
    as identifier between % for substitutions. IE if
    it matches validreplacenamere (English alphanumerics and dashes
    and underscores and slashes and periods and colons)."""
    return bool(validreplacenamere.match(s))

def string_replace_xml_text(element, pattern, value):
    """Find all text in XML element and its children
    and replace %name% with value."""
    if value is None:
        return
    if element.text:
        element.text = element.text.replace(pattern, value)
    for c in element.getchildren():
        string_replace_xml_text(c, pattern, value)

def find_file(filename, extra_paths=None):
    search_paths = get_search_paths(filename, extra_paths)
    for path in search_paths:
        if os.path.isfile(path):
            return path
    else:
        sys.exit('Unable to find file. Looked for:\n'
                 '%s\n'
                 'The easiest way to fix this is to use the absolute '
                 'path of the data file when running the effect (eg '
                 'C:\\where\\my\\files\\are\\%s), or put '
                 'the file in any of the locations listed above.'
                 % ('\n'.join(search_paths),
                    os.path.basename(filename)))

def get_search_paths(filename, extra_paths=None):
    home = os.path.expanduser('~')
    return ([os.path.join(ep, filename) for ep in (extra_paths or [])]
            + [filename,
               os.path.join(home, ".countersheetsextension", filename),
               os.path.join(home, filename),
               os.path.join(home, 'Documents', filename),
               os.path.join(home, 'Documents', 'countersheets', filename),
            ])

def make_def_ref(color):
    return "url(#%s)" % color

def find_top_level_group_for(element):
    if element is None:
        return None
    parent = element.getparent()
    if parent is None:
        return None
    elif is_group(element) and is_layer(parent):
        return element
    else:
        return find_top_level_group_for(parent)

IGNORE_PATTERNS = ["did not resolve to a valid image file",
                       ": dbind-WARNING **",
                       ": WARNING **",
                       "SPDocument::doUnref(): invalid ref count!"]
def print_filtered_stderr(err):
    for errline in err.splitlines():
        ignore_line = False
        for p in IGNORE_PATTERNS:
            if errline.find(p) >= 0:
                ignore_line = True
                break
        if (not ignore_line
            and len(errline.strip()) > 0):
            print(errline, file=sys.stderr)

def is_layer(element):
    try:
        return element.get(inkex.addNS('groupmode', 'inkscape')) == 'layer'
    except:
        return False

def is_group(element):
    return element.tag == inkex.addNS('g','svg')

def get_layer(element, sourceElementId=None):
    '''
        finds the layer that the svg element is under

        Should be called without the sourceElementId. The routine fills that in.
        '''
    if sourceElementId is None:
        sourceElementId = element.get("id")
    top_level_group = find_top_level_group_for(element)
    if top_level_group is None:
        raise ValueError("Unable to find layer for element [" + sourceElementId + "]")
    else:
        return top_level_group.getparent()

if __name__ == '__main__':
    effect = CountersheetEffect()
    effect.run()
