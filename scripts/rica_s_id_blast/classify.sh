#! /bin/bash
# this will classify (align, identify) a read against the pathogen DB.

echo "[i]> === blast"
date



inputfile="$1"
outputfile=$(basename $inputfile).blastout.tab
outdir="$2"

blastdbfile="/rica_s/tools/rica_s_id_blast/pathogen_references.fasta.blastdb"


blastn -query "$1" -db "$blastdbfile" -num_threads `nproc` -outfmt 0 > "$outdir/$outputfile"
/usr/bin/time -v blastn -num_threads `nproc` -query $inputfile -db $blastdbfile -outfmt 0 > $outdir/$outputfile



date
echo "[i]> blast ==="

