#!/usr/bin/env python2.6


# Copyright 2011 Pelle Nilsson (krigsspel@pelle-n.net)
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

CSNS = ""

NSS[u'cs'] = u'http://www.hexandcounter.org/countersheetsextension/'

class Counter:
    def __init__(self, nr):
        self.nr = nr
        self.parts = []
        self.subst = {}
        self.back = None
        self.id = None
        self.endbox = False
        self.hasback = False
        self.attrs = {}
        self.excludeids = []
        self.includeids = []

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
            self.back = Counter(self.nr)
        return self.back

    def is_included(self, eid):
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

class CountersheetEffect(inkex.Effect):
    def __init__(self):
        inkex.Effect.__init__(self)
        self.log = False
        self.nextid = 1000000
        self.OptionParser.add_option('-l', '--log', action = 'store',
                                     type = 'string', dest = 'logfile')
        self.OptionParser.add_option('-n', '--what', action = 'store',
                                     type = 'string', dest = 'what',
                                     default = '',
                                     help = 'Name')
        self.OptionParser.add_option('-d', '--data', action = 'store',
                                     type = 'string', dest = 'datafile',
                                     default = 'countersheet.csv',
                                     help = 'CSV or XML data file.')
        self.OptionParser.add_option('-w', '--bitmapw', action = 'store',
                                     type = 'int', dest = 'bitmapwidth',
                                     default = '56',
                                     help = 'ID bitmap width')
        self.OptionParser.add_option('-y', '--bitmaph', action = 'store',
                                     type = 'int', dest = 'bitmapheight',
                                     default = '56',
                                     help = 'Number of columns.')
        self.OptionParser.add_option('-f', '--bitmapsheetsdpi',
                                     action = 'store',
                                     type = 'int', dest = 'bitmapsheetsdpi',
                                     default = '0')
        self.OptionParser.add_option('-b', '--bitmapdir', action = 'store',
                                     type = 'string', dest = 'bitmapdir')
        self.OptionParser.add_option('-r', '--registrationmarkslen',
                                     action = 'store',
                                     type = 'int',
                                     dest = 'registrationmarkslen')

        self.translatere = re.compile("translate[(]([-0-9.]+),([-0-9.]+)[)]")
        self.matrixre = re.compile("(matrix[(](?:[-0-9.]+,){4})([-0-9.]+),([-0-9.]+)[)]")
        self.fillgradientre=re.compile("(.*fill:url[(]#)([^)]+Gradient)([0-9]+)(.*)")

    def logwrite(self, msg):
        if not self.log and self.options.logfile:
            self.log = open(self.options.logfile, 'w')
        if self.log:
            self.log.write(msg)

    def replaceattrs(self, elements, attrs):
        for n in elements:
            id = n.get("id")
            if not id:
                continue
            for glob,attr in attrs.iteritems():
                if fnmatch.fnmatchcase(id, glob):
                    for a,v in attr.iteritems():
                        if a.startswith('style:'):
                            pname = a[6:]
                            a = "style"
                            v = stylereplace(n.get(a), pname, v)
                        if ':' in a:
                            [ns,tag] = a.split(':')
                            a = inkex.addNS(tag, ns)
                        n.set(a, v)

    def fix_gradients(self, group, dx, dy):
        self.logwrite('fix_gradients %s:\n' % group.get('id'))
        for e in group.getiterator():
            style = e.get('style')
            if style != None:
                m = self.fillgradientre.match(style)
                if m != None:
                    gradient_type = m.group(2)
                    gradient_id = gradient_type + m.group(3)
                    prestyle = m.group(1)
                    poststyle = m.group(4)
                    self.logwrite("found gradient %s %s\n"
                                  % (gradient_type, gradient_id))
                    gpath = ("//svg:%s[@id='%s']" %
                             (gradient_type, gradient_id))
                    for t in self.document.xpath(gpath,
                                                 namespaces=NSS):
                        gradient_clone = deepcopy(t)
                        gradient_clone_id = self.gen_id(gradient_id)
                        gradient_clone.set('id', gradient_clone_id)
                        self.translate_gradient(gradient_clone, dx, dy)
                        t.getparent().append(gradient_clone)
                        e.set('style',
                              '%s%s%s' % (prestyle,
                                          gradient_clone_id,
                                          poststyle))
                        break
    def gen_id(self, base=None):
        if base == None:
            base = 'cs_gen_id'
        res = '%s_%d' % (base, self.nextid)
        self.nextid = self.nextid + 1
        return res

    def translate_gradient(self, element, dx, dy):
        transform = element.get("gradientTransform")
        if transform:
            m = self.translatere.match(transform)
            if m == None:
                return
        self.logwrite("gradient transform %s: %f  %f\n" % (element.get('id'),
                                                           dx, dy))
        element.set("gradientTransform",
                    "translate(%f,%f)" % (dx, dy))

    def translate_element(self, element, dx, dy):
        transform = element.get("transform")
        if transform:
            mm = self.matrixre.match(transform)
            if mm != None:
                element.set("transform", "%s%f,%f)" % (mm.group(1),dx, dy))
                return
        element.set("transform",
                    "translate(%f,%f)" % (dx, dy))

    def translate_use_element(self, use, old_ref, new_ref):
        self.logwrite("translate_use_element %s %s\n" % (old_ref, new_ref))
        use_translate = self.get_translation(use)
        if use_translate:
            self.logwrite("found transform\n")
            old_element = self.document.xpath("//*[@id='%s']"% old_ref,
                                              namespaces=NSS)[0]
            new_element = self.document.xpath("//*[@id='%s']"% new_ref,
                                              namespaces=NSS)[0]
            (old_x, old_y) = self.find_reasonable_center_xy(old_element)
            (new_x, new_y) = self.find_reasonable_center_xy(new_element)
            self.logwrite(" use data: %f,%f %f,%f %f,%f\n"
                          % (use_translate[0],
                             use_translate[1],
                             old_x, old_y,
                             new_x, new_y))
            use.set("transform",
                    "translate(%f,%f)" % (
                    use_translate[0] - new_x + old_x,
                    use_translate[1] - new_y + old_y))

    def find_reasonable_center_xy(self, element):
        x = element.get('x')
        if x:
            return ((float(inkex.unittouu(x))
                     + float(inkex.unittou(element.get('width'))) / 2),
                    (float(inkex.unittouu(element.get('y')))
                     + float(inkex.unittou(element.get('height'))) / 2))
        else:
            return (float(element.get(inkex.addNS('cx', 'sodipodi'))),
                    float(element.get(inkex.addNS('cy', 'sodipodi'))))

        y = element.get('y')
        if y:
            y = float(inkex.unittouu(y))
        else:
            y = float(element.get(inkex.addNS('cy', 'sodipodi')))
        return (x, y)

    def get_translation(self, element):
        m = self.translatere.match(element.get('transform'))
        if not m:
            return None
        x = float(m.group(1))
        y = float(m.group(2))
        return (x, y)

    def setMultilineText(self, element, lines):
        self.logwrite("setting multiline text: %s\n" % lines)
        self.deleteFlowParas(element)
        for line in lines:
            para = etree.Element(inkex.addNS('flowPara', 'svg'))
            para.text = line
            element.append(para)

    def deleteFlowParas(self, parent):
        for c in parent.getchildren():
            if c.tag == inkex.addNS('flowPara','svg'):
                parent.remove(c)

    def setFirstTextChild(self, element, text):
        for c in element.getchildren():
            if c.text:
                c.text = text
                return True
            elif self.setFirstTextChild(c, text):
                return True
        return False

    def addLayer(self, what, nr, extra=""):
        if len(extra) > 0:
            extralabel = " (%s)" % extra
            extraid = "_%s" % extra
        else:
            extralabel = ""
            extraid = ""
        llabel = 'Countersheet %s %d%s' % (what, nr, extralabel)
        lid = 'cs_layer_%d%s' % (nr, extraid)
        self.cslayers.append(lid)
        layer = etree.Element(inkex.addNS('g', 'svg'))
        layer.set(inkex.addNS('label', 'inkscape'), llabel)
        layer.set('id', lid)
        layer.set(inkex.addNS('groupmode', 'inkscape'), 'layer')
        return layer

    def generatecounter(self, c, rects, layer, colx, rowy):
        res = [0, 0]
        foundold = False
        clonegroup = None
        if c.id:
            oldc = self.document.xpath("//svg:g[@id='%s']"% c.id,
                                       namespaces=NSS)
            if oldc:
                foundold = True
                clonegroup = oldc[0]
                layer = clonegroup.getparent()
                for i in clonegroup.iterchildren():
                    clonegroup.remove(i)
        if not foundold:
            clonegroup = etree.Element(inkex.addNS('g', 'svg'))
        if c.id != None and len(c.id):
            clonegroup.set('id', c.id)
            self.exportids.append(c.id)
        for p in c.parts:
            if len(p) == 0:
                continue
            rectname = p
            killrect = False
            if rectname[0] == "@":
                killrect = True
                rectname = rectname[1:]
            if not rects.has_key(rectname):
                self.logwrite("COULD NOT FIND rect '%s'.\n" % rectname)
                continue
            rect = rects[rectname]
            x = float(rect.get('x'))
            y = float(rect.get('y'))
            width = float(rect.get('width'))
            height = float(rect.get('height'))
            res[0] = max(res[0], width)
            res[1] = max(res[1], height)
            group = rect.getparent()
            if group.get(inkex.addNS('groupmode', 'inkscape')) == 'layer':
                self.logwrite("rect not in group '%s'.\n" % rectname)
                clone = deepcopy(rect)
                clone.set('x', "0.0")
                clone.set('y', "0.0")
                self.replaceattrs([clone], c.attrs)
                self.fix_gradients(clone, -x, -y)
            else:
                clone = deepcopy(group)
                if killrect:
                    for r in clone.xpath('//svg:rect', namespaces=NSS):
                        if r.get("id") == rectname:
                            clone.remove(r)
                            break
                textishnodes = []
                textishnodes.extend(clone.xpath('//svg:text', namespaces=NSS))
                textishnodes.extend(clone.xpath('//svg:flowRoot',
                                                namespaces=NSS))
                for t in textishnodes:
                    self.substitute_text(c, t, t.get("id"))
                for i in clone.xpath('//svg:image', namespaces=NSS):
                    imageid = i.get("id")
                    if not imageid:
                        continue
                    for glob,image in c.subst.iteritems():
                        if fnmatch.fnmatchcase(imageid, glob):
                            i.set(inkex.addNS("absref", "sodipodi"), image)
                            i.set(inkex.addNS("href", "xlink"), image)
                for u in clone.xpath('//svg:use', namespaces=NSS):
                    useid = u.get("id")
                    if not useid:
                        continue
                    usekey = useid.split("-")[0]
                    for glob,new_ref in c.subst.iteritems():
                        if fnmatch.fnmatchcase(useid, glob):
                            xlink_attribute = inkex.addNS("href", "xlink")
                            old_ref = u.get(xlink_attribute)[1:]
                            u.set(xlink_attribute, "#" + new_ref)
                            self.translate_use_element(u, old_ref, new_ref)
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
                self.translate_element(clone, -x, -y)
                self.fix_gradients(clone, -x, -y)
            self.logwrite("cloning %s\n" % clone.get("id"))
            clonegroup.append(clone)
        if not foundold:
            self.translate_element(clonegroup, colx, rowy)
        layer.append(clonegroup)
        return res

    def substitute_text(self, c, t, textid):
        for glob,subst in c.subst.iteritems():
            if fnmatch.fnmatchcase(textid, glob):
                if t.text:
                    t.text = subst
                if (t.tag == inkex.addNS('flowRoot','svg')
                    and subst.find("\\n") >= 0):
                    self.setMultilineText(t, subst.split("\\n"))
                elif not self.setFirstTextChild(t, subst):
                    self.logwrite("...failed to set subst %s\n" % textid)
                if c.id:
                    t.set("id", textid + "_" + c.id)

    def readLayout(self, svg):
        for g in svg.xpath('//svg:g', namespaces=NSS):
            if (g.get(inkex.addNS('groupmode', 'inkscape')) == 'layer'
                and (g.get(inkex.addNS('label', 'inkscape'))
                     == 'countersheet_layout')):
                res = []
                self.logwrite("Found layout layer!\n")
                #  for r in g.xpath('//svg:rect', namespaces=NSS):
                for c in g.getchildren():
                    if c.tag == inkex.addNS('rect','svg'):
                        res.append(
                            {'x':float(inkex.unittouu(c.get('x'))),
                             'y':float(inkex.unittouu(c.get('y'))),
                             'w':float(inkex.unittouu(c.get('width'))),
                             'h':float(inkex.unittouu(c.get('height')))
                             })
                    elif c.tag == inkex.addNS('text','svg'):
                        pass # use to set countersheet label?
                return res
        return False

    def addbacks(self, layer, bstack, docwidth, rects):
        for c in bstack:
            for x,y in zip(c.backxs, c.backys):
                self.generatecounter(c.back, rects,
                                     layer,
                                     docwidth - x,
                                     y)

    def exportBitmaps(self, ids, width, height, dpi=0):
        tmpfilename = os.path.join(self.options.bitmapdir, ".__tmp__.svg")
        tmpfile = open(tmpfilename, 'w')
        self.document.write(tmpfile)
        tmpfile.close()
        if dpi > 0:
            exportsize = "-d %d" % dpi
        else:
            exportsize = "-w %d -h %d" % (width, height)
        for id in ids:
            cmd="inkscape -i %s -j -e %s %s %s" % (
                id, self.getbitmapfilename(id),
                exportsize, tmpfilename)
            self.logwrite(cmd + "\n")
            f = os.popen(cmd,'r')
            f.read()
            f.close()
        os.remove(tmpfilename)

    def getbitmapfilename(self, id):
        return os.path.join(self.options.bitmapdir, id) + ".png"

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
            self.exportBitmaps(self.exportids,
                               self.options.bitmapwidth,
                               self.options.bitmapheight)
            return True
        return False

    def create_registrationline(self, x1, y1, x2, y2):
        line = etree.Element('line')
        line.set("x1", str(x1))
        line.set("y1", str(y1))
        line.set("x2", str(x2))
        line.set("y2", str(y2))
        line.set("style", "stroke:#838383")
        return line

    def addregistrationmarks(self, xregistrationmarks, yregistrationmarks,
                             position, layer):
        linelen = self.options.registrationmarkslen
        if linelen < 1:
            return
        for x in xregistrationmarks:
            layer.append(
                self.create_registrationline(position['x'] + x,
                                             position['y'] - linelen,
                                             position['x'] + x,
                                             position['y'] - 1))
            layer.append(
                self.create_registrationline(
                position['x'] + x,
                position['y'] + position['h'],
                position['x'] + x,
                position['y'] + position['h'] + linelen))
        for y in yregistrationmarks:
            layer.append(self.create_registrationline(position['x'] - linelen,
                                                      position['y'] + y,
                                                      position['x'] - 1,
                                                      position['y'] + y))
            layer.append(self.create_registrationline(
                position['x'] + position['w'],
                position['y'] + y,
                position['x'] + position['w'] + linelen,
                position['y'] + y))

    def effect(self):
        # Get script "--what" option value.
        what = self.options.what
        datafile = self.options.datafile

        doc = self.document

        self.exportids = []
        self.cslayers = []

        # Get access to main SVG document element and get its dimensions.
        svg = self.document.xpath('//svg:svg', namespaces=NSS)[0]

        if os.path.isfile(os.path.join(os.getcwd(), datafile)):
            datafile = os.path.join(os.getcwd(), datafile)
        elif os.path.isfile(datafile):
            pass
        else:
            sys.exit('Unable to find file %s. Tried to search for it '
                     'relative to current directory "%s". '
                     'The easiest way to fix this is to use the absolute '
                     'path of the data file when running the effect (eg '
                     'C:\\where\\my\\files\\are\\%s).'
                     % (datafile, os.getcwd(),
                        os.path.basename(datafile)))

        rects = {}
        for r in doc.xpath('//svg:rect', namespaces=NSS):
            rects[r.get("id")] = r

        self.logwrite('Using data file %s.\n'
                      % os.path.abspath(datafile))
        # FIXME load CSV or XML file
        reader = csv.reader(open(datafile, "rb"))

        parser = CSVCounterDefinitionParser(self.logwrite, rects)
        parser.parse(reader)
        counters = parser.counters
        hasback = parser.hasback

        # Create a new layer.
        layer = self.addLayer(what, 1)

        backlayer = False

        if hasback:
            backlayer = self.addLayer(what, 1, "back")

        docwidth = float(inkex.unittouu(svg.get('width')))

        haslayout = True
        positions = self.readLayout(svg)
        if not positions or len(positions) < 1:
            haslayout = False
            positions = [{'x' : 0.0,
                          'y' : 0.0,
                          'w' : docwidth,
                          'h' : float(inkex.unittouu(svg.get('height')))
                          }]
            if self.options.registrationmarkslen > 0:
                margin = self.options.registrationmarkslen
                positions[0]['x'] += margin
                positions[0]['y'] += margin
                positions[0]['w'] -= margin * 2
                positions[0]['h'] -= margin * 2

        for n,p in enumerate(positions):
            self.logwrite("layout position %d: %f %f %f %f\n"
                          % (n, p['x'], p['y'], p['w'], p['h']))

        row = 0
        col = 0
        colx = 0
        rowy = 0
        nextrowy = 1
        box = 0
        nr = 0
        csn = 1
        bstack = []

        xregistrationmarks = set([0])
        yregistrationmarks = set([0])

        for i,c in enumerate(counters):
            self.before_counter(c)
            c.backxs = []
            c.backys = []
            for n in range(c.nr):
                nr = nr + 1
                c.addsubst("autonumber", str(nr))
                if c.hasback:
                    c.back.addsubst("autonumber", str(nr))
                width, height=self.generatecounter(c, rects, layer,
                                                   positions[box]['x']+colx,
                                                   positions[box]['y']+rowy)
                if c.hasback:
                    c.backxs.append(positions[box]['x'] + colx + width)
                    c.backys.append(positions[box]['y'] + rowy)
                    bstack.append(c)
                col = col + 1
                colx = colx + width
                xregistrationmarks.add(colx)
                if rowy + height > nextrowy:
                    nextrowy = rowy + height
                if colx + width > positions[box]['w'] or c.endbox:
                    col = 0
                    colx = 0
                    row = row + 1
                    rowy = nextrowy
                    nextrowy = rowy + 1
                    yregistrationmarks.add(nextrowy - 1)
                    if (nextrowy + height > positions[box]['h']
                        or c.endbox):
                        if hasback:
                            self.addbacks(backlayer, bstack, docwidth,
                                          rects)
                        self.addregistrationmarks(
                            xregistrationmarks, yregistrationmarks,
                            positions[box], layer)
                        xregistrationmarks = set([0])
                        yregistrationmarks = set([0])
                        bstack = []
                        box = box + 1
                        row = 0
                        rowy = 0
                        nextrowy = 1
                        if box == len(positions) and i < len(counters) - 1:
                            csn = csn + 1
                            if hasback:
                                svg.append(backlayer)
                                backlayer = self.addLayer(what, csn, "back")
                            svg.append(layer)
                            layer = self.addLayer(what, csn)
                            box = 0

        if ((len(xregistrationmarks) > 1
             or len(yregistrationmarks) > 1)
            and len(layer.getchildren())):
            yregistrationmarks.add(nextrowy - 1)
            self.addregistrationmarks(
                xregistrationmarks, yregistrationmarks,
                positions[box], layer)

        if hasback:
            self.addbacks(backlayer, bstack, docwidth, rects)

        if hasback and len(backlayer.getchildren()):
            svg.append(backlayer)

        if len(layer.getchildren()):
            svg.append(layer)
        exportedbitmaps = self.exportIDBitmaps()
        self.post(counters)
        self.exportSheetBitmaps()

    def before_counter(self, counter):
        pass

    def post(self, counters):
        pass

class CSVCounterDefinitionParser:
    def __init__(self, logwrite, rects):
        self.logwrite = logwrite
        self.rects = rects
        self.counters = []
        self.hasback = False

    def parse(self, reader):
        factory = None
        for row in reader:
            factory = self.parse_row(row, factory)

    def parse_row(self, row, factory):
#        self.logwrite(":".join(row) + "\n")
        if self.is_counterrow(factory, row):
            return self.parse_counter_row(row, factory)
        elif self.is_newheaders(row):
            self.logwrite('Found new headers\n')
            return CSVCounterFactory(self.rects, row)
        else:
            self.logwrite('Empty row... reset headers.\n')
            return False

    def is_counterrow(self, factory, row):
        return factory and len(row) > 0 and len("".join(row)) > 0

    def is_newheaders(self, row):
        return len(row) > 0 and len("".join(row)) > 0

    def parse_counter_row(self, row, factory):
        nr = 1
        if len(row[0]) > 0:
            if row[0] == 'ENDBOX':
                if len(self.counters) > 0:
                    self.counters[-1].endbox = True
                return factory
            else:
                try:
                    nr = int(row[0])
                except ValueError:
                    return CSVCounterFactory(self.rects, row)
        self.logwrite('new counter, nr=%d\n' % nr)
        cfront = factory.create_counter(nr, row)
        self.hasback = self.hasback or factory.hasback
        self.counters.append(cfront)
        if cfront.id and cfront.hasback and not cfront.back.id:
            cfront.back.id = cfront.id + "_back"
        return factory

class CounterFactory (object):
    def __init__(self, rects):
        self.rects = rects
        self.hasback = False

class CSVCounterFactory (CounterFactory):
    def __init__(self, rects, row):
        super(CSVCounterFactory, self).__init__(rects)
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
            return AttributeLayout(h, self.rects)
        elif self.isidheader(h):
            return IDLayout()
        elif self.isbackheader(h):
            return BackLayout(h)
        elif self.isdefaultvalueheader(h):
            return self.parse_defaultvalueheader(h)
        else:
            return CounterSubstLayout(h)

    def create_counter(self, nr, row):
        cfront = Counter(nr)
        c = cfront
        for i,ho in enumerate(self.headers):
            h = ho.raw
            setting = CounterSettingHolder()
            if i < len(row):
                value = row[i]
            else:
                value = None
            ho.set_setting(setting, value)
            if setting.back:
                if i >= len(row) or row[i] != 'BACK':
                    break
                c.hasback = True
                c = c.doublesided()
                self.hasback = True
            if c:
                setting.applyto(c)
        return cfront

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

class CounterOptionLayout:
    def __init__(self, id):
        self.id = id
        self.raw = id

    def set_setting(self, setting, value):
        if value != 'y' and value != 'Y':
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
    def __init__(self, h, rects):
        self.raw = h
        self.rects = rects
        astart = h.find('[')
        self.aid = h[:astart]
        self.aname = h[astart+1:-1]

    def set_setting(self, setting, value):
        aname = self.aname
        if len(value) and value[0] == '<':
            if self.aname.startswith('style:'):
                pname = aname[6:]
                oldv = self.rects[value[1:]].get("style")
                value = self.getrefstyle(oldv, pname, value)
        setting.set(CounterAttribute(self.aid, aname, value))

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

def find_stylepart(oldv, pname):
    pstart = oldv.find(pname + ":")
    if pstart < 0:
        return [-1, -1]
    pend = oldv.find(";", pstart) + 1
    return [pstart, pend]

def stylereplace(oldv, pname, v):
    out = ""
    for part in oldv.split(";"):
        if part.startswith(pname + ':'):
            out += "%s:%s;" % (pname, v) 
        elif len(part):
            out += part + ";"
    return out

if __name__ == '__main__':
    effect = CountersheetEffect()
    effect.affect()
