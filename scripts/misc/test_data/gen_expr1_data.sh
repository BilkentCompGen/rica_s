#!/bin/bash

BASEDIR="./output"
INDIR="./input"

TOML=()
TOML+=("/config/05B_0.001A_1H.toml")
TOML+=("/config/05B_0.001A_2H.toml")
TOML+=("/config/05B_0.010A_1H.toml")
TOML+=("/config/05B_0.010A_2H.toml")
TOML+=("/config/05B_0.100A_1H.toml")
TOML+=("/config/05B_0.100A_2H.toml")
TOML+=("/config/10B_0.001A_1H.toml")
TOML+=("/config/10B_0.001A_2H.toml")
TOML+=("/config/10B_0.010A_1H.toml")
TOML+=("/config/10B_0.010A_2H.toml")
TOML+=("/config/10B_0.100A_1H.toml")
TOML+=("/config/10B_0.100A_2H.toml")
TOML+=("/config/15B_0.001A_1H.toml")
TOML+=("/config/15B_0.001A_2H.toml")
TOML+=("/config/15B_0.010A_1H.toml")
TOML+=("/config/15B_0.010A_2H.toml")
TOML+=("/config/15B_0.100A_1H.toml")
TOML+=("/config/15B_0.100A_2H.toml")

for T in "${TOML[@]}"; do

	docker compose run --remove-orphans --rm icarust -vv -s $T
	# read
	X=$(basename -s .toml $T)
	OLDDIR=$(ls -td $BASEDIR/$X/$X/2026*/fast5_pass | head -1)
	# read
	mv $OLDDIR/* $BASEDIR/$X/
	rm -rf $BASEDIR/$X/$X/
	# read
	pod5 convert fast5 \
		$BASEDIR/$X/ \
		--output "$INDIR/$X.pod5" \
		--threads $(nproc) \
		--force-overwrite
	
	# read
	rm -rf $BASEDIR/$X/*.fast5
	# read
done
