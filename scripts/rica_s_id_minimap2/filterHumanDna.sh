#! /bin/bash

echo '[i]> === minimap2'
date
echo ""



inputfile="$1"
outdir="$2"
indexfile="/opt/rica_s/tools/rica_s_id_minimap2/human_v38.mmi"

# 2. Extract just the filename without the path
filename=$(basename "$inputfile")

# 3. Strip the file extension (e.g., removes .fastq or .fasta)
clean_id="${filename%.*}"


/usr/bin/time -f "\n\tT> %E [h:]m:s.s\n\tM> %M KB" minimap2 -a -R "@RG\tID:$filename\tSM:$clean_id" "$indexfile" "$inputfile" > $outdir/$filename.filterHumanDna.sam

# mkdir -p $outdir/rica_s_fl_minimap2/

samtools view -F 4 "$outdir/$filename".filterHumanDna.sam |awk '{print $1}' | sort -u > $outdir/$filename.human_mapped_sequence_names.txt
samtools view -f 4 "$outdir/$filename".filterHumanDna.sam |awk '{print $1}' | sort -u > $outdir/$filename.nonhuman_unmapped_sequence_names.txt
# echo "seqtk subseq $inputfile $outdir/rica_s_fl_minimap2/nonhuman_unmapped_sequence_names.txt > $outdir/rica_s_fl_minimap2/$filename.cleaned.fasta"
# seqtk subseq -A $inputfile $outdir/$filename.nonhuman_unmapped_sequence_names.txt > $outdir/$filename.cleaned.fasta
seqtk subseq $inputfile $outdir/$filename.nonhuman_unmapped_sequence_names.txt | seqtk seq -A > $outdir/$filename.cleaned.fasta
echo ""
date
echo '[i]> minimap2 ==='
