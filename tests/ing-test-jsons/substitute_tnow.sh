#!/bin/bash

set -xe

shopt -s nullglob

# seconds since the Epoch
TNOW=`date +%s`

for FIN in *.template; do
	FOUT="${FIN%.template}"
	cat "$FIN" | sed "s/\$TS/$TNOW/g" > "$FOUT"
done
