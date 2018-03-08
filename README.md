Countersheets Extension for Inkscape
====================================

Inkscape extension for the layout of sheets of cards, tiles, or counters
for boardgames.

Since the extension was originally created for wargame counters, the
generated images are refered to as counters,
except in examples explicitly about making something else (like sheets
of cards). There is very little in the tool that is specific to
counters though, or to board games. It can be used as a
generic templating tool (mail merge or data merge).

Features
--------

* Two-sided counters with back of sheets properly mirrored.
* Templates for counters to generate drawn in Inkscape.
* Use Comma Separated Values (CSV) files for describing what counters to make.
* First column in the CSV says how many of each counter to make.
* Several templates can be combined to make up a single counter.
* Automatically make as many sheets needed to fit all counters.
* Replace text strings and bitmap images for each counter.
* Toggle specified parts of counters on or off for each couter.
* Set colors and other attributes of (parts of) counters.
* Any counters can be mixed on the same sheet (even different sizes).
* Registration marks for manual cutting of the sheets.
* Bleed around counters. (new in 2.1)
* Simple text mark-up for bold and italics text styles and inlined images. (new in 2.1)
* Decide exactly where on a sheet to put blocks of counters, for die cutting.
* Export created sheets to PNG or PDF.
* Export individual counters to PNG images.

Installation
------------

You need Inkscape 0.92 or later installed.

Copy countersheet.py, and countersheet.inx to where Inkscape
looks for extensions. On my Mac and Linux computers this is in
.config/inkscape/extensions.  In Windows it will be something like
C:\Program Files\Inkscape\share\extensions.

After you (re)start Inkscape you should find "Create Countersheet"
in the "Boardgames" submenu of the "Extensions" menu.

See more complete instructions [on the wiki](https://github.com/lifelike/countersheetsextension/wiki/Install).

Try Google or the Inkscape Guild on BoardGameGeek for help.

Getting Started
---------------

You need a SVG file with template objects open in Inkscape, and
a CSV data file with information about what to generate. Run
the Create Countersheet extension and provide the name of
the data file (the other options in the dialog window you can
ignore for now).

See the [wiki](https://github.com/lifelike/countersheetsextension/wiki/) for more.

Changelogs
----------
[Changelogs](https://github.com/lifelike/countersheetsextension/wiki/Changelogs)
for recent versions of the countersheetsextension can be found
[on the wiki](https://github.com/lifelike/countersheetsextension/wiki/Changelogs).

License
--------

Copyright (C) 2008-2018 Pelle Nilsson

This program is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public License
as published by the Free Software Foundation; either version 2
of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.


queryAll method is derived from code included in Inkscape 0.91
(share/extensions/text_merge.py) that has this header:

Copyright (C) 2013 Nicolas Dufour (jazzynico)
Direction code from the Restack extension, by Rob Antonishen

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.


Documentation is Copyright 2009-2018 Eric Hanuise and Pelle Nilsson,
available under the Creative Commons Attribution 3.0 License
http://creativecommons.org/licenses/by/3.0/


Included examples in the documentation (the SVG and CSV files) are copyright
Pelle Nilsson and made avilable under the Creative Commons Zero License
(https://creativecommons.org/publicdomain/zero/1.0/) for any use (including
commercial). Some images used in the examples are by KenneyNL
(https://kenney.itch.io/), some by various users on https://openclipart.org, all
also made available under the Creative Commons Zero License.

