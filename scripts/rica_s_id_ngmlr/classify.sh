#! /bin/bash

echo '[i]> === ngmlr'
date
echo ""

inputfile="$1"
outdir="$2"
outputfile=$(basename $inputfile)
referencefile="/opt/rica_s/reference_genomes/joint/all_pathogens.fasta"

# queries=$(find $2 -type f -name "*."$3)
# refs=$(find /rica_s/data/pathogen_reference/ -type f -name "*.fasta")

/usr/bin/time -v ngmlr -t `nproc` -r $referencefile -q $inputfile -o $outdir/$outputfile.ngmlr.sam # 1> $outdir/$outputfile.ngmlr.log 2> $outdir/$outputfile.ngmlr.err
samtools view -F 2308 $outdir/$outputfile.ngmlr.sam | awk '{print $3}' | sort | uniq -c | awk -v OFS='\t' '{print $2, $1}' | sort -nr > $outdir/$outputfile.ngmlr.sam.tsv

echo ""
date
echo '[i]> ngmlr ==='
