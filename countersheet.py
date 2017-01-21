#!/usr/bin/env python2


# Copyright 2017 Pelle Nilsson
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
import simpletransform

CSNS = ""

NSS[u'cs'] = u'http://www.hexandcounter.org/countersheetsextension/'


# A bit of a hack because of rounding errors sometimes
# making boxes not fill up properly.
# There should be a better fix.
BOX_MARGIN = 2.0

# Hardcoded (for now?) what DPI to use for
# some non-vector content in exported PDF.
PDF_DPI = 300

class Counter:
    def __init__(self, nr):
        self.nr = nr
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

class Rectangle:
    def __init__(self, x, y, w, h):
        self.x = x
        self.y = y
        self.w = w
        self.h = h

class CountersheetEffect(inkex.Effect):
    def __init__(self):
        inkex.Effect.__init__(self)
        # quick attempt compatibility with Inkscape older than 0.91:
        if not hasattr(self, 'unittouu'):
            self.unittouu = inkex.unittouu
        self.log = False
        self.nextid = 1000000
        self.OptionParser.add_option('-l', '--log', action = 'store',
                                     type = 'string', dest = 'logfile')
        self.OptionParser.add_option('-n', '--what', action = 'store',
                                     type = 'string', dest = 'what',
                                     default = '',
                                     help = 'Name')
        self.OptionParser.add_option('-N', '--sheets-bitmap-name', dest='bitmapname',
                                     default = '') # undocumented, for svgtests
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
        self.OptionParser.add_option('-p', '--pdfdir', action = 'store',
                                     type = 'string', dest = 'pdfdir')
        self.OptionParser.add_option('-r', '--registrationmarkslen',
                                     action = 'store',
                                     type = 'int',
                                     dest = 'registrationmarkslen')

        self.translatere = re.compile("translate[(]([-0-9.]+),([-0-9.]+)[)]")
        self.matrixre = re.compile("(matrix[(](?:[-0-9.]+,){4})([-0-9.]+),([-0-9.]+)[)]")

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


    def translate_element(self, element, dx, dy):
        self.logwrite("translate_element %f,%f\n"
                      % (dx, dy))
        translate = "translate(%f,%f)" % (dx, dy)
        old_transform = element.get('transform')
        if old_transform:
            self.logwrite("old transform: %s\n" % old_transform)
            element.set('transform', translate + " " + old_transform)
        else:
            element.set('transform', translate)

    def translate_use_element(self, use, old_ref, new_ref):
        self.logwrite("translate_use_element %s %s\n" % (old_ref, new_ref))
        old_element = self.document.xpath("//*[@id='%s']"% old_ref,
                                          namespaces=NSS)[0]
        new_element = self.document.xpath("//*[@id='%s']"% new_ref,
                                          namespaces=NSS)[0]
        (old_x, old_y) = self.find_reasonable_center_xy(old_element)
        (new_x, new_y) = self.find_reasonable_center_xy(new_element)
        self.logwrite(" use data: old %f,%f   new %f,%f\n"
                      % (old_x, old_y,
                         new_x, new_y))
        self.translate_element(use, old_x - new_x, old_y - new_y)

    def find_reasonable_center_xy(self, element):
        rect = self.geometry[element.get('id')]
        return (rect.x + rect.w / 2.0,
                rect.y + rect.h / 2.0)

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

    def addLayer(self, svg, what, nr, extra=""):
        if len(extra) > 0:
            extralabel = " (%s)" % extra
            extraid = "_%s" % extra
        else:
            extralabel = ""
            extraid = ""
        llabel = 'Countersheet %s %d%s' % (what, nr, extralabel)
        lid = 'cs_layer_%d%s' % (nr, extraid)

        if self.find_layer(svg, llabel) is not None:
            sys.exit("Image already contains a layer '%s'. "
                     "Remove that layer before running extension again. "
                     "Or set a different Name when running the extension. "
                     "Or just rename the existing layer." % llabel)

        self.cslayers.append(lid)
        layer = etree.Element(inkex.addNS('g', 'svg'))
        layer.set(inkex.addNS('label', 'inkscape'), llabel)
        layer.set('id', lid)
        layer.set(inkex.addNS('groupmode', 'inkscape'), 'layer')
        return layer

    def is_layer( self, element ):
        try:
            return element.get(inkex.addNS('groupmode', 'inkscape')) == 'layer'
        except:
            return False

    def get_layer( self, element, sourceElementId = None ):
        '''
        finds the layer that the svg element is under

        Should be called without the sourceElementId. The routine fills that in.
        '''
        if sourceElementId is None: sourceElementId = element.get( "id" )
        if self.is_layer( element ): return element
        parent = element.getparent()
        if parent is None:
            raise ValueError( "Unable to find layer for element [" + sourceElementId + "]" )
        if self.is_layer( parent ): return parent
        return self.get_layer( parent, sourceElementId )
        
    def generatecounter(self, c, rects, layer, colx, rowy):
        res = [0, 0]
        oldcs = self.document.xpath("//svg:g[@id='%s']"% c.id,
                                    namespaces=NSS)
        if len(oldcs):
            self.logwrite("Found existing %d old counters for %s"
                          % (len(oldcs), c.id))
            for oldc in oldcs:
                oldc.set('id', '')
        clonegroup = etree.Element(inkex.addNS('g', 'svg'))
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
            if not rects.has_key(rectname):
                sys.exit("Unable to find rectangle with id '%s' "
                         "that was specified in the CSV data file."
                         % rectname)
            rect = rects[rectname]
            group = rect.getparent()
            source_layer = self.get_layer( rect )
            groupid = group.get('id')
            x = self.geometry[groupid].x
            y = self.geometry[groupid].y
            width = self.geometry[groupid].w
            height = self.geometry[groupid].h
            res[0] = max(res[0], width)
            res[1] = max(res[1], height)
            if self.is_layer( group ):
                self.logwrite("rect not in group '%s'.\n" % rectname)
                sys.exit("Rectangle '%s' not in a group. Can not be template."
                         % rectname)
            clone = deepcopy(group)
            if killrect:
                for r in clone.xpath('//svg:rect', namespaces=NSS):
                    if r.get("id") == rectname:
                        clone.remove(r)
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
                for glob,image in c.subst.iteritems():
                    if fnmatch.fnmatchcase(imageid, glob):
                        i.set(inkex.addNS("absref", "sodipodi"), image)
                        i.set(inkex.addNS("href", "xlink"), image)
                    elif is_valid_name_to_replace(glob):
                        absref = i.get(inkex.addNS("absref", "sodipodi"), image)
                        href = i.get(inkex.addNS("href", "xlink"), image)
                        i.set(inkex.addNS("absref", "sodipodi"),
                              absref.replace("%%%s%%" % glob, image))
                        i.set(inkex.addNS("href", "xlink"),
                              href.replace("%%%s%%" % glob, image))

            for u in clone.xpath('//svg:use', namespaces=NSS):
                useid = u.get("id")
                if not useid:
                    continue
                for glob,new_ref in c.subst.iteritems():
                    if fnmatch.fnmatchcase(useid, glob):
                        xlink_attribute = inkex.addNS("href", "xlink")
                        old_ref = u.get(xlink_attribute)[1:]
                        u.set(xlink_attribute, "#" + new_ref)
                        self.translate_use_element(u, old_ref, new_ref)

            for name,value in c.subst.iteritems():
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
        layer.append(clonegroup)
        return res

    def substitute_text(self, c, t, textid):
        for glob,subst in c.subst.iteritems():
            if fnmatch.fnmatchcase(textid, glob):
                if t.text:
                    t.text = subst
                elif (t.tag == inkex.addNS('flowRoot','svg')
                    and subst.find("\\n") >= 0):
                    self.setMultilineText(t, subst.split("\\n"))
                elif not self.setFirstTextChild(t, subst):
                    sys.exit("Failed to put substitute text in '%s'"
                             % textid)
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

    def addbacks(self, layer, bstack, docwidth, rects):
        self.logwrite("addbacks %d\n" % len(bstack))
        for c in bstack:
            for x,y in zip(c.backxs, c.backys):
                self.generatecounter(c.back, rects,
                                     layer,
                                     docwidth - x,
                                     y)

    # Looked a bit at code in Inkscape text_merge.py for this idea.
    # That file is Copyright (C) 2013 Nicolas Dufour (jazzynico).
    # See README file for license.
    def queryAll(self, filename):
        "Return geometry Rectangle (x, y, w, h) for each element id, as dict."
        geometry = {}
        cmd = 'inkscape --query-all "%s"' % filename
        _, f, err = os.popen3(cmd, 't')
        reader = csv.reader(f)
        err.close()
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

        f.close()
        return geometry

    def exportBitmaps(self, ids, width, height, dpi=0):
        if dpi > 0:
            exportsize = "-d %d" % dpi
        else:
            exportsize = "-w %d -h %d" % (width, height)
        self.export_using_inkscape(ids, exportsize, "-e",
                                   self.options.bitmapdir,
                                   "png")

    def export_using_inkscape(self, ids, size_flags, export_flags,
                              exportdir, extension):
        tmpfilename = os.path.join(exportdir, ".__tmp__.svg")
        tmpfile = open(tmpfilename, 'w')
        self.document.write(tmpfile)
        tmpfile.close()
        for id in ids:
            if len(self.document.xpath("//*[@id='%s']" % id,
                                       namespaces=NSS)) == 0:
                continue
            cmd='inkscape -i %s -j %s "%s" %s "%s"' % (
                id,
                export_flags,
                self.getbitmapfilename(id, exportdir, extension), #FIXME
                size_flags, tmpfilename)
            self.logwrite(cmd + "\n")
            f = os.popen(cmd,'r')
            f.read()
            f.close()
        os.remove(tmpfilename)

    def getbitmapfilename(self, id, directory, extension):
        return os.path.join(directory,
                            self.bitmapname + id) + "." + extension

    def exportSheetPDFs(self):
        if (self.options.pdfdir
            and len(self.cslayers) > 0):
            self.export_using_inkscape(self.cslayers,
                                       "-d %d" % PDF_DPI,
                                       "-A",
                                       self.options.pdfdir,
                                       "pdf")

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
        self.logwrite("create_registrationline %f,%f %f,%f\n"
                      % (x1, y1, x2, y2))
        line = etree.Element('line')
        line.set("x1", str(x1))
        line.set("y1", str(y1))
        line.set("x2", str(x2))
        line.set("y2", str(y2))
	line.set("style", "stroke:#838383")
	line.set("stroke-width", str(PS)) 
        return line

    def addregistrationmarks(self, xregistrationmarks, yregistrationmarks,
                             position, layer):
        linelen = self.unittouu("%fpt" % self.options.registrationmarkslen)
        self.logwrite("addregistrationmarks linelen=%f\n" % linelen)
        if linelen < 1:
            return
        max_x = 0
        max_y = 0
        for x in xregistrationmarks:
            layer.append(
                self.create_registrationline(position.x + x,
                                             position.y - linelen,
                                             position.x + x,
                                             position.y))
            max_x = max(max_x, x)

        for y in yregistrationmarks:
            layer.append(self.create_registrationline(position.x - linelen,
                                                      position.y + y,
                                                      position.x,
                                                      position.y + y))
            max_y = max(max_y, y)

        for x in xregistrationmarks:
            layer.append(
                self.create_registrationline(
                position.x + x,
                position.y + max_y,
                position.x + x,
                position.y + max_y + linelen))

        for y in yregistrationmarks:
            layer.append(self.create_registrationline(
                position.x + max_x,
                position.y + y,
                position.x + max_x + linelen,
                position.y + y))

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
        self.xscale = self.yscale = 1.0 / self.unittouu('1px')
        xscale = yscale = 0.0
        try:
            viewbox = svg.get('viewBox')
            if viewbox:
                self.logwrite("viewBox: %s\n" % viewbox)
                (viewx, viewy, vieww, viewh) = map(float, re.sub(' +|, +|,',' ', viewbox).strip().split(' ', 4))
                svgwidth = svg.get('width')
                svgheight = svg.get('height')
                svguuwidth = self.unittouu(svgwidth)
                svguuheight = self.unittouu(svgheight)
                self.logwrite("SVG widthxheight: %sx%s\n"
                              % (svgwidth, svgheight))
                self.logwrite("SVG size in user-units: %fx%f\n"
                              % (svguuwidth, svguuheight))
                xscale = self.unittouu(svg.get('width')) / vieww / self.unittouu("1px")
                yscale = self.unittouu(svg.get('height')) / viewh / self.unittouu("1px")
                self.xscale = xscale
                self.yscale = yscale
        except Exception, e:
            self.logwrite("Failed to calculate document scale:\n%s\n" % repr(e))

    def getDocumentViewBoxValue(self, svg, n, fallback):
        try:
            return float(svg.get('viewBox').split(' ')[n])
        except:
            return float(svg.get(fallback)) # let it crash if this fails

    # Because getDocumentWiddth in inkex fails because it makes assumptions about
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
        datafile = self.options.datafile

        doc = self.document

        self.exportids = []
        self.cslayers = []
        self.bitmapname = self.options.bitmapname

        # Get access to main SVG document element and get its dimensions.
        svg = self.document.xpath('//svg:svg', namespaces=NSS)[0]

        self.calculateScale(svg)

        search_paths = get_search_paths(datafile)
        for path in search_paths:
            if os.path.isfile(path):
                datafile = path
                break
        else:
            sys.exit('Unable to find data file. Looked for:\n'
                     '%s\n'
                     'The easiest way to fix this is to use the absolute '
                     'path of the data file when running the effect (eg '
                     'C:\\where\\my\\files\\are\\%s), or put '
                     'the file in any of the locations listed above.'
                     % ('\n'.join(search_paths),
                        os.path.basename(datafile)))

        # a small, "pixel-size", length, to use for making small
        # adjustments that works in Inkscape 0.91 and later, similar
        # to what "1px" always was in earlier Inkscape versions
        PS = self.unittouu("%fin" % (1.0 / 90))

        rects = {}
        for r in doc.xpath('//svg:rect', namespaces=NSS):
            rects[r.get("id")] = r

        self.logwrite("queryAll for: %s\n" % sys.argv[-1])
        self.geometry = self.queryAll(sys.argv[-1])

        self.logwrite('Using data file %s.\n'
                      % os.path.abspath(datafile))

        try:
            csv.Sniffer
        except:
            sys.exit("Not able to find csv.Sniffer. "
                     "Please delete csv.py and csv.pyc "
                     "files from your Inkscape extensions."
                     "folder. They are no longer used.");

        csv_file = open(datafile, "rb")
        csv_dialect = csv.Sniffer().sniff(csv_file.read(2000))
        csv_file.seek(0)
        reader = csv.reader(csv_file, csv_dialect)

        parser = CSVCounterDefinitionParser(self.logwrite, rects)
        parser.parse(reader)
        counters = parser.counters
        hasback = parser.hasback

        # Create a new layer.
        layer = self.addLayer(svg, what, 1)

        backlayer = False

        if hasback:
            backlayer = self.addLayer(svg, what, 1, "back")

        docwidth = self.getViewBoxWidth(svg)

        self.logwrite("user-units in 1 inch: %f\n" % self.unittouu("1in"))
        self.logwrite("user-units in 1 px: %f\n" % self.unittouu("1px"))
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
            if self.options.registrationmarkslen > 0:
                margin = self.unittouu("%fpt" % self.options.registrationmarkslen)
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
                self.logwrite("laying out counter %d (nr %d, c.nr %d) (hasback: %s)\n"
                              % (i, nr, c.nr, c.hasback))
                c.addsubst("autonumber", str(nr))
                if c.hasback:
                    c.back.addsubst("autonumber", str(nr))
                width, height=self.generatecounter(c, rects, layer,
                                                   positions[box].x+colx,
                                                   positions[box].y+rowy)
                self.logwrite("generated counter size: %fx%f\n"
                              % (width, height))
                if c.hasback:
                    c.backxs.append(positions[box].x + colx + width)
                    c.backys.append(positions[box].y + rowy)
                    bstack.append(c)
                col = col + 1
                colx = colx + width
                xregistrationmarks.add(colx)
                if rowy + height > nextrowy:
                    nextrowy = rowy + height
                if (colx + width > positions[box].w + BOX_MARGIN
                    or c.endbox or c.endrow):
                    col = 0
                    colx = 0
                    row = row + 1
                    rowy = nextrowy
                    nextrowy = rowy + 1
                    yregistrationmarks.add(rowy)
                    if (nextrowy + height > positions[box].h + BOX_MARGIN
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
                        self.logwrite(" now at box %d of %d\n" % (box, len(positions)))
                        self.logwrite(" i: %d    len(counters): %d\n" % (i, len(counters)))
                        row = 0
                        rowy = 0
                        nextrowy = 0
                        if box == len(positions) and i < len(counters):
                            csn = csn + 1
                            if hasback:
                                svg.append(backlayer)
                                backlayer = self.addLayer(svg, what,
                                                          csn, "back")
                            svg.append(layer)
                            layer = self.addLayer(svg, what, csn)
                            box = 0

        if ((len(xregistrationmarks) > 1
             or len(yregistrationmarks) > 1)
            and len(layer.getchildren())):
            yregistrationmarks.add(nextrowy)
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
        self.exportSheetPDFs()

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
        if self.is_counterrow(factory, row):
            return self.parse_counter_row(row, factory)
        elif self.is_newheaders(row):
            self.logwrite('Found new headers: %s\n' % ';'.join(row))
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
            elif row[0] == 'ENDROW':
                if len(self.counters) > 0:
                    self.counters[-1].endrow = True
                return factory
            else:
                try:
                    nr = int(row[0])
                except ValueError:
                    return CSVCounterFactory(self.rects, row)
        self.logwrite('new counter: %s\n' % ';'.join(row))
        cfront = factory.create_counter(nr, row)
        self.hasback = self.hasback or factory.hasback
        self.logwrite('self.hasback: %s  factory.hasback: %s\n'
                      % (str(self.hasback), str(factory.hasback)))
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
           matrix = simpletransform.parseTransform( transform )
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
    for part in oldv.split(";"):
        if part.startswith(pname + ':'):
            out += "%s:%s;" % (pname, v) 
        elif len(part):
            out += part + ";"
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
    if element.text:
        element.text = element.text.replace(pattern, value)
    for c in element.getchildren():
        string_replace_xml_text(c, pattern, value)

def get_search_paths(filename):
    home = os.path.expanduser('~')
    return [filename,
            os.path.join(home, ".countersheetsextension", filename),
            os.path.join(home, filename),
            os.path.join(home, 'Documents', filename),
            os.path.join(home, 'Documents', 'countersheets', filename),
            ]

if __name__ == '__main__':
    effect = CountersheetEffect()
    effect.affect()
