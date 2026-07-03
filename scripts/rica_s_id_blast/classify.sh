#! /bin/bash
# this will classify (align, identify) a read against the pathogen DB.

echo "[i]> === blast"
echo -n "[i]> " && date
echo ""
# echo $1
# echo $2
# echo $3


inputfile="$1"
outputfile=$(basename $inputfile).blastout.tab
outdir="$2"

blastdbfile="/opt/rica_s/tools/rica_s_id_blast/pathogen_references.fasta.blastdb"


# blastn -query "$1" -db "$blastdbfile" -num_threads `nproc` -outfmt 0 > "$outdir/$outputfile"
/usr/bin/time -v blastn -num_threads `nproc` \
    -query $inputfile \
    -db $blastdbfile \
    -outfmt 6 \
    > $outdir/$outputfile.6


# fixing output
    sort -k1,1 -k3,3nr $outdir/$outputfile.6 | awk -v OFS='\t' '!seen[$1]++ {print $2, $3}' >$outdir/$outputfile.6.tsv

echo ""
echo -n "[i]> " && date
echo "[i]> blast ==="

