#! /bin/bash

inputfile="$1"
outputfile=$(basename $inputfile)
outdir="$2"

# project root: passed in by the stage driver (config.py), else derived from this script's location
RICA_S_HOME="${RICA_S_HOME:-$(cd "$(dirname "$0")/../.." && pwd)}"
k2db=$RICA_S_HOME/tools/rica_s_id_kraken2/pathogen.k2db/


/usr/bin/time -f "\n\tT> %E [h:]m:s.s\n\tM> %M KB" k2 classify --db $k2db --threads `nproc` --report $outdir/$outputfile.kraken2.report --output $outdir/$outputfile.kraken2.output --unclassified-out $outdir/$outputfile.kraken2.unclassified --classified-out $outdir/$outputfile.kraken2.classified $inputfile
awk -F'\t' -v OFS='\t' '$4 == "S" || $4 ~ /^S[0-9]/ {gsub(/^ +/, "", $6); print $6, $2}' $outdir/$outputfile.kraken2.report > $outdir/$outputfile.kraken2.report.tsv
