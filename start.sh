#!/bin/sh

VENVDIR=/home/ankou/site/rasp/rasp_venv
BINDIR=/home/ankou/site/rasp

cd $BINDIR
. $VENVDIR/bin/activate
uwsgi --ini uwsgi.ini
