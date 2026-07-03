#! /bin/bash

echo '[i]> === minimap2'
date
echo ""

echo $1
echo $2
# 1. Quote your variables to handle spaces
inputfile="$1"
outdir="$2"
indexfile="/opt/rica_s/tools/rica_s_id_minimap2/human_dna_db/human_v38.mmi"

# 2. Extract just the filename without the path
filename=$(basename "$inputfile")

# 3. Strip the file extension (e.g., removes .fastq or .fasta)
clean_id="${filename%.*}"


minimap2 -a -R "@RG\tID:$filename\tSM:$clean_id" "$indexfile" "$inputfile" > $outdir/"$filename".filterHumanDna.sam
mkdir -p $outdir/rica_s_fl_minimap2/
samtools view -F 4 "$outdir/$filename".filterHumanDna.sam |awk '{print $1}' | sort -u > $outdir/rica_s_fl_minimap2/human_mapped_sequence_names.txt
samtools view -f 4 "$outdir/$filename".filterHumanDna.sam |awk '{print $1}' | sort -u > $outdir/rica_s_fl_minimap2/nonhuman_unmapped_sequence_names.txt
seqtk subseq $inputfile $outdir/rica_s_fl_minimap2/nonhuman_unmapped_sequence_names.txt > $outdir/rica_s_fl_minimap2/nonhuman_unmapped_sequence_names.fasta

echo ""
date
echo '[i]> minimap2 ==='
