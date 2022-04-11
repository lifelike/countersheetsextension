#!/bin/sh

EXTENSIONSDIR=/usr/share/inkscape/extensions/

PYTHONPATH=$EXTENSIONSDIR unittests/alltests.py "$@"
