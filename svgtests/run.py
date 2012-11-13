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

if not os.path.exists(outputdir):
    os.mkdir(outputdir)

for f in glob.glob(os.path.join(inputdir, "*.png")):
    shutil.copy(f, outputdir)

tests = [
    ['nato1.csv', 'nato.svg'],
    ['nato2.csv', 'nato.svg'],
    ['use.csv', 'use.svg'],
    ['symbols.csv', 'symbols.svg'],
]

for test in tests:
    [basedatafile, basesvginfile] = test
    svgoutbasename = basedatafile + '-' + basesvginfile
    svgoutfile = os.path.join(outputdir, svgoutbasename)
    datafile = os.path.join(inputdir, basedatafile)
    svginfile = os.path.join(inputdir, basesvginfile)
    svgout = open(svgoutfile, "w")
    command = os.path.join('.', 'countersheet.py')
    commandline = [command,
                   '-d', datafile,
                   '-l', '/tmp/cs_svgtests.log',
                   '-r', '10',
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
    #FIXME xml diff, not line diff, would be nice
    import difflib
    if not '-q' in sys.argv:
        for line in difflib.unified_diff(open(svgoutfile).readlines(),
                                         open(expectedfile).readlines(),
                                         fromfile=svgoutfile,
                                         tofile=expectedfile):
            print line
