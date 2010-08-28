#!/bin/sh

if [ -n "`inkscape --version|grep 0.48`" ]; then
    EXTDIR=~/.config/inkscape/extensions/
else
    EXTDIR=~/.inkscape/extensions/
fi

cp /usr/share/inkscape/extensions/simplepath.py $EXTDIR
cp *.inx *.py $EXTDIR
inkscape $*
