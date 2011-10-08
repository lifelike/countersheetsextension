Countersheets Extension for Inkscape
====================================

(This readme file is very much just a draft at the moment.)

Inkscape extension for the layout of sheets of cards, tiles, or counters
for boardgames. It was originally part of the Inkscape Board Game
Extensions project (see http://www.lysator.liu.se/~perni/iboardgameexts/).

Since the extension was originally created for wargame counters, the
generated images in this document will be refered to as counters,
except in examples explicitly about making something else (like sheets
of cards). There is very little in the tool that is specific to
counters though, or to board games. It can probably be used as a
generic templating tool.

Main Features
-------------

* Two-sided counters with back of sheets properly mirrored.
* Templates for counters to generate drawn in Inkscape.
* Use Comma Separated Values (CSV) files for describing what counters to make.
* First row in the CSV says how many of each counter to make.
* Several templates can be combined to make up a single counter.
* Automatically make as many sheets needed to fit all counters.
* Replace text strings and bitmap images for each counter.
* Toggle specified parts of counters on or off for each couter.
* Set colors and other attributes of (parts of) counters.
* Any counters can be mixed on the same sheet (even different sizes).
* Registration marks for manual cutting of the sheets.
* Decide exactly where on a sheet to put blocks of counters, for die cutting.

Main Problem
------------

Not everything you can draw in Inkscape can be handled by the
extension.  Known to work are rectangles, bitmap images, paths, and
text. If something you need isn't supported, render it to a bitmap and
use the bitmap instead.

Installation
------------

You need Inkscape installed (version 0.48, although 0.47 might still work too).

From the latest download archive (zip) copy countersheet.py, csv.py, and
countersheet.inx to where Inkscape looks for extensions.  On my Mac
and Linux computers this is in .config/inkscape/extensions.  In
Windows it will be something like C:\Program Files\Inkscape\share\extensions.

After you (re)start Inscape you should find "Create Countersheet"
in the "Boardgames" submenu of the "Extensions" menu.

There is an old tutorial also on youtube by Erulisseuiin:
http://www.youtube.com/watch?v-sZ__PwMZp_8
While it is for an older version of the Inkscape Board Game Extensions,
it might still be easier to follow than my short instructions above.

I recommend Google or the Inkscape Guild on BoardGameGeek for help.

Getting Started
---------------

You need a SVG file with template objects open in Inkscape, and
a CSV data file with information about what to generate. Run
the Create Countersheet extension and provide the name of
the data file (the other options in the dialog window you can
ignore for now).

Of course making a SVG file and corresponding CSV can be a bit tricky
at first, since the included documentation isn't very helpful, so I
recommend trying to start with the included examples, as
described below.

Countersheet Example
--------------------

Instructions how to use included templates for typical wargame
countersheets.

TBD

Sheet of Cards Example
----------------------

Instructions how to use included templates for game cards.

TBD


