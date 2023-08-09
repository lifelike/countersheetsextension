#!/usr/bin/env python3

import difflib
import glob
import os
import os.path
import shutil
import subprocess
import sys

def add_countersheets_paths():
    sys.path.insert(0, os.getcwd())

def namefrom(args):
    if len(list(args.keys())):
        argslist = []
        for a in args.items():
            argslist.extend(a)
        return "_".join(argslist) + ".svg"
    else:
        return ""

add_countersheets_paths()

inputdir = os.path.join('svgtests', 'input')
outputdir = os.path.join('svgtests', 'output')
expecteddir = os.path.join('svgtests', 'expected')
bitmapsdir = os.path.join('svgtests', 'bitmaps')
pdfdir = os.path.join('svgtests', 'pdf')
logdir = os.path.join('svgtests', 'log')

if not os.path.exists(outputdir):
    os.mkdir(outputdir)

chosen = [a for a in sys.argv[1:]
          if not a.startswith("-")]

tests = [
    ['battlelabels.csv', 'battlelabels.svg'],
    ['nato1.csv', 'nato.svg'],
    ['nato1.csv', 'nato.svg', {'-o' : 'true'}],
    ['nato2.csv', 'nato.svg'],
    ['nato2.csv', 'nato.svg', {'-o' : 'true'}],
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
    ['counters-swatches.csv', 'counters.svg'],
    ['counters-2sides.csv', 'counters.svg'],
    ['counters-2sides.csv', 'counters.svg', {'-D' : 'true'}],
    ['counters-2sides.csv', 'counters.svg', {'-R' : 'true'}],
    ['counters-2sides.csv', 'counters.svg', {'-R' : 'true',
                                             '-D' : 'true'}],
    ['counters-2sides.csv', 'counters.svg', {'-o' : 'true'}],
    ['faces_multiselect.csv', 'faces_multiselect.svg'],
    ['yndice-en.csv', 'yndice.svg'],
    ['yndice-en.csv', 'yndice.svg', {'-O' : '15pt'}],
    ['jndice-sv.csv', 'yndice.svg'],
    ['dicefold.csv', 'dicefold.svg'],
    ['labels17mm.csv', 'labels17mm.svg'],
    ['labels17mm-140.csv', 'labels17mm-140.svg'],
    ['cloneslayout.csv', 'cloneslayout.svg'],
    ['imagereplace.csv', 'imagereplace.svg'],
    ['imagereplace-option.csv', 'imagereplace.svg'],
    ['imagetiles.csv', 'imagetiles.svg'],
    ['numbers.csv', 'numbers.svg'],
    ['numbers-endrow.csv', 'numbers.svg'],
    ['autonumbers.csv', 'numbers.svg'],
    ['square.csv', 'square.svg'],
    ['square.csv', 'square092.svg'],
    ['stars-3.csv', 'star.svg'],
    ['stars-4.csv', 'star.svg'],
    ['stars-5.csv', 'star.svg'],
    ['bleed.csv', 'bleed.svg', {'-B' : 'true'}],
    ['backgrounds.csv', 'backgrounds.svg'],
    ['backgrounds.csv', 'backgrounds.svg', {'-o' :  'true'}],
    ['textformat.csv', 'textformat.svg'],
    ['textformat.csv', 'textformat.svg', {'-i' : '50'}],
    ['textformat.csv', 'textformat.svg', {'-i' : '100'}],
    ['textformat.csv', 'textformat.svg', {'-i' : '400'}],
    ['textformat.csv', 'textformat.svg', {'-i' : '100',
                                          '-P' : 'nn'}],
    ['textformat.csv', 'textformat.svg', {'-s' : '1.0'}],
    ['textformat.csv', 'textformat.svg', {'-s' : ' -1.0'}],
    ['textspan.csv', 'textspan.svg'],
    ['dynamic.csv', 'texttokens.svg'],
    ['dynamic.csv', 'texttokens.svg', {'-1' : 'true'}],
    ['prototype_cards_all.csv', 'prototype_cards.svg'],
    ['prototype_cards_ccg.csv', 'prototype_cards.svg'],
    ['svgcolors.csv', 'colors.svg'],
    ['aspect_ratio.csv', 'aspect_ratio.svg'],
    ['aspect_ratio_h.csv', 'aspect_ratio.svg'],
    ['nostyle.csv', 'nostyle.svg'],
    ['badsvg.csv', 'missing_viewbox.svg'],
    ['counters_symbol_list.csv', 'template-counters.svg', {'-r' : '0',
                                                           '-f' : '90',
                                                           '-O' : '0'}],
    ['counters_size_list.csv', 'template-counters.svg', {'-r' : '0',
                                                         '-f' : '90',
                                                         '-O' : '0'}],
    ['markers_list.csv', 'template-counters.svg', {'-r' : '0',
                                                   '-f' : '90',
                                                   '-O' : '0'}],
    ['nato_counters.csv', 'template-counters.svg'],
    ['nato_counters_2_sides.csv', 'template-counters.svg'],
    ['standees.csv', 'standees.svg', {'-R' : 'true', '-O' : '0'}],
    ['image_counters.csv', 'template-counters.svg'],
    ['bomsquare.csv', 'square.svg'],
    ['centercard.csv', 'prototype_cards.svg'],

    ['clone-colors.csv', 'clone-colors.svg'],
]

copyfiles = (glob.glob(os.path.join(inputdir, "*.png"))
             + [os.path.join(inputdir, "extcard.svg")])
for f in copyfiles:
    shutil.copy(f, outputdir)
    shutil.copy(f, bitmapsdir)
    shutil.copy(f, pdfdir)

successes = 0
fails = 0
skipped = 0
for test in tests:
    basedatafile = test[0]
    basesvginfile = test[1]
    if len(test) == 3:
        extraargs = test[2]
    else:
        extraargs = {}
    if chosen:
        matches = False
        for c in chosen:
            if c in basedatafile or c in basesvginfile:
                matches = True
                break
        if not matches:
            skipped += 1
            continue
    svgoutbasename = basedatafile + '-' + basesvginfile + namefrom(extraargs).replace(' ', '')
    svgoutfile = os.path.join(outputdir, svgoutbasename)
    datafile = os.path.join(inputdir, basedatafile)
    svginfile = os.path.join(inputdir, basesvginfile)
    svgout = open(svgoutfile, "w")
    command = os.path.join('.', 'countersheet.py')
    logfile = os.path.join(logdir, 'cs_svgtests-%s.txt' % svgoutbasename)
    layer_names = "cs_" + svgoutbasename
    default_args = {'-d' : datafile,
                    '-I' : os.path.realpath(outputdir),
                   '-l' : logfile,
                   '-r' : '10pt',
                   '-O' : '7pt',
                   '-f' : '90',
                   '-w' : '0',
                   '-y' : '0'}
    combined_args_dict = default_args.copy()
    combined_args_dict.update(extraargs)
    combined_args = []
    for k, v in combined_args_dict.items():
        combined_args.append(k)
        combined_args.append(v)
    commandline = [command,
                   '-b', bitmapsdir,
                   '-p', pdfdir,
                   '-N', svgoutbasename] + combined_args +  ['--', svginfile]

    if ['-v' in sys.argv]:
        print(' '.join(commandline), file=sys.stderr)

    effect = subprocess.Popen(commandline,
                              stdout=svgout)
    effect.wait()
    svgout.close()
    if effect.returncode:
        sys.exit('Failed to run svgtest for %s and %s.'
                 % (datafile, svginfile))

    expectedfile = os.path.join(expecteddir, svgoutbasename)
    outputsvg = open(svgoutfile).read()
    print("diff %s %s" % (svgoutfile, expectedfile))
    expectedsvg = open(expectedfile).read()
    if outputsvg == expectedsvg:
        successes += 1
    else:
        print("FAIL: diff %s %s" % (svgoutfile, expectedfile))
        fails += 1

print(("%d/%d tests OK (%d skipped, %d FAILED)\n"
       % (successes, len(tests), skipped, fails)))
