#!/usr/bin/env python2

import difflib
import glob
import os
import os.path
import shutil
import subprocess
import sys

def add_countersheets_paths():
    sys.path.insert(0, os.getcwd())

add_countersheets_paths()

inputdir = os.path.join('svgtests', 'input')
outputdir = os.path.join('svgtests', 'output')
expecteddir = os.path.join('svgtests', 'expected')
bitmapsdir = os.path.join('svgtests', 'bitmaps')
pdfdir = os.path.join('svgtests', 'pdf')
logdir = os.path.join('svgtests', 'log')

if not os.path.exists(outputdir):
    os.mkdir(outputdir)

tests = [
    ['nato1.csv', 'nato.svg'],
    ['nato2.csv', 'nato.svg'],
    ['use.csv', 'use.svg'],
    ['symbols.csv', 'symbols.svg'],
    ['commas_in_semicolons.csv', 'card.svg'],
    ['semicolons_in_commas.csv', 'card.svg'],
    ['fills.csv', 'fills.svg'],
    ['layout11.csv', 'layout.svg'],
    ['layout12.csv', 'layout.svg'],
    ['layout10+10+10.csv', 'layout.svg'],
    ['cards.csv', 'cards.svg'],
    ['counters.csv', 'counters.svg'],
    ['counters-2sides.csv', 'counters.svg'],
    ['faces_multiselect.csv', 'faces_multiselect.svg'],
    ['bold.csv', 'bold.svg'],
    ['yndice-en.csv', 'yndice.svg'],
    ['jndice-sv.csv', 'yndice.svg'],
    ['dicefold.csv', 'dicefold.svg'],
    ['labels17mm.csv', 'labels17mm.svg'],
    ['labels17mm-140.csv', 'labels17mm-140.svg'],
    ['cloneslayout.csv', 'cloneslayout.svg'],
    ['imagereplace.csv', 'imagereplace.svg'],
    ['numbers.csv', 'numbers.svg'],
    ['numbers-endrow.csv', 'numbers.svg'],
    ['autonumbers.csv', 'numbers.svg'],
]

for f in glob.glob(os.path.join(inputdir, "*.png")):
    shutil.copy(f, outputdir)
    shutil.copy(f, bitmapsdir)
    shutil.copy(f, pdfdir)

successes = 0
for test in tests:
    [basedatafile, basesvginfile] = test
    svgoutbasename = basedatafile + '-' + basesvginfile
    svgoutfile = os.path.join(outputdir, svgoutbasename)
    datafile = os.path.join(inputdir, basedatafile)
    svginfile = os.path.join(inputdir, basesvginfile)
    svgout = open(svgoutfile, "w")
    command = os.path.join('.', 'countersheet.py')
    logfile = os.path.join(logdir, 'cs_svgtests-%s.txt' % svgoutbasename)
    layer_names = "cs_" + svgoutbasename
    commandline = [command,
                   '-d', datafile,
                   '-l', logfile,
                   '-r', '10',
                   '-f', '90',
                   '-b', bitmapsdir,
                   '-p', pdfdir,
                   '-N', svgoutbasename + '--',
                   svginfile
                   ]

    if ['-v' in sys.argv]:
        print >> sys.stderr, ' '.join(commandline)

    effect = subprocess.Popen(commandline,
                              stdout=svgout)
    effect.wait()
    svgout.close()
    if effect.returncode:
        sys.exit('Failed to run svgtest for %s and %s.'
                 % (datafile, svginfile))

    expectedfile = os.path.join(expecteddir, svgoutbasename)
    outputsvg = open(svgoutfile).read()
    expectedsvg = open(expectedfile).read()
    if outputsvg == expectedsvg:
        successes += 1
    else:
        print "FAIL: diff %s %s" % (svgoutfile, expectedfile)

print ("%d/%d tests OK (%d FAILED)\n"
       % (successes, len(tests), len(tests)-successes))
