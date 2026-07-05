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
/usr/bin/time -v \
blastn -num_threads `nproc` \
    -query $inputfile \
    -db $blastdbfile \
    -outfmt 6 \
    > $outdir/$outputfile.6 | \
awk -F': ' '
/Elapsed/ { time = $2 }
/Maximum resident/ { mem = $2 / 1024 }
END {
    print "--------------------------------"
    printf "Time\t%s\n", time
    printf "RAM(MB)\t%.2f\n", mem
    print "--------------------------------"
}'


# fixing output
# Assuming your BLAST output is already sitting at $outdir/$outputfile.6
awk -F'\t' '!seen[$1]++ {print $2}' "$outdir/$outputfile.6" | \
sort | uniq -c | \
awk -v OFS='\t' '{print $2, $1}' > "$outdir/${outputfile}.tsv"



echo ""
echo -n "[i]> " && date
echo "[i]> blast ==="

