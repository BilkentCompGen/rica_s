#! /bin/bash


sed '/^[[:space:]]*$/d' $1 > /tmp/_tmp_$1

awk '/^>/ { if(NR>1) print ""; print; next } { printf "%s", $0 } END { print "" }' /tmp/_tmp_$1 > $1.nonewline.flat.fasta