#!/bin/sh

export PYTHONPATH=/usr/share/inkscape/extensions/:/usr/local/share/inkscape/extensions

unittests/alltests.py "$@"
