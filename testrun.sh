#!/bin/sh

if [ -e ~/.config/inkscape/extensions/ ]; then
    EXTDIR=~/.config/inkscape/extensions/
else
    EXTDIR=~/.inkscape/extensions/
fi

cp *.inx *.py $EXTDIR

inkscape $*
