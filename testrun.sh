#!/bin/sh

cp /usr/share/inkscape/extensions/simplepath.py ~/.inkscape/extensions/
cp *.inx *.py ~/.inkscape/extensions/
inkscape $*
