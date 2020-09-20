#!/bin/sh

EXTENSIONSDIR=/usr/share/inkscape/extensions/

PYTHONPATH=$EXTENSIONSDIR svgtests/run.py "$@"
