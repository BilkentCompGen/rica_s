#! /bin/bash
# this will classify (align, identify) a read against the pathogen DB.

inputfile="$1"
outputfile="$2"
blastdbfile="/rica_s/tools/rica_s_id_blast/pathogen_references.fasta.blastdb"


echo "[i]> running blast "$blastdbfile" vs. $inputfile"
blastn -query "$1" -db  -outfmt 0 > "$outputfile"
echo "[i]> blast finished. output: $outputfile"


