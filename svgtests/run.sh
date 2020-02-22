#!/bin/sh

# FIXME temporary to test
#EXTENSIONSDIR=/usr/share/inkscape/extensions/
EXTENSIONSDIR=/home/pelle/src/extensions-inkscape

PYTHONPATH=$EXTENSIONSDIR svgtests/run.py "$@"
