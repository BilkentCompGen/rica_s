#! /bin/bash

echo "[i]> === kraken2"
date


# run_id=$1
inputfile="$1"
outputfile=$(basename $inputfile)
outdir="$2"

k2db=/rica_s/tools/rica_s_id_kraken2/pathogen.k2db/

/usr/bin/time -v k2 classify --db $k2db --threads `nproc` --report $outdir/$outputfile.kraken2.report --output $outputfile.kraken2.output --unclassified-out $outdir/$outputfile.kraken2.unclassified --classified-out $outdir/$outputfile.kraken2.classified $inputfile


date
echo "[i]> kraken2 ==="