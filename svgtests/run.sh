#!/bin/sh

# FIXME temporary to test
#EXTENSIONSDIR=/usr/share/inkscape/extensions/
EXTENSIONSDIR=$HOME/src/extensions-inkscape

# FIXME this is to run locally compiled inkscape 1.0
TMPPATH=$HOME/inksape/inst/bin:$PATH

PATH=$TMPPATH PYTHONPATH=$EXTENSIONSDIR svgtests/run.py "$@"
