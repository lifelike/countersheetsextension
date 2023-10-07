#!/bin/sh

EXTENSIONSDIR=/usr/local/share/inkscape/extensions/:/usr/share/inkscape/extensions/

PYTHONPATH=$EXTENSIONSDIR svgtests/run.py "$@"
