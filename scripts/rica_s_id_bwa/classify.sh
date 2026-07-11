#! /bin/bash
# this will classify (align, identify) a read against the pathogen DB.
# set -x

echo "[i]> === bwa"
date
echo ""


inputfile="$1"
outputfile=$(basename $inputfile)
outdir="$2"

index=/opt/rica_s/tools/rica_s_id_bwa/all_pathogens.fasta


/usr/bin/time -v bwa mem -t `nproc` -x ont2d $index $inputfile > $outdir/$outputfile.bwa.sam
# /usr/bin/time -v bwa mem -t `nproc` -x ont2d /opt/rica_s/tools/rica_s_id_bwa/all_pathogens.fasta /opt/rica_s/datasets/_1/amr_EreA.fasta > ./outputfile.bwa.sam


samtools view -F 2308 $outdir/$outputfile.bwa.sam | awk '{print $3}' | sort | uniq -c | awk -v OFS='\t' '{print $2, $1}' | sort -nr > $outdir/$outputfile.bwa.sam.tsv


echo ""
date
echo "[i]> bwa ==="

