#! /bin/bash

echo '[i]> === minimap2'
date

inputfile="$1"
outputfile=$(basename $inputfile)

outdir="$2"
referencefile="/rica_s/reference_genomes/joint/all_pathogens.mmi"

# queries=$(find $2 -type f -name "*."$3)
# refs=$(find /rica_s/data/pathogen_reference/ -type f -name "*.fasta")

/usr/bin/time -v minimap2 -t `nproc` -c -x map-ont $referencefile $inputfile > $outdir/$outputfile.minimap2.paf

date
echo '[i]> minimap2 ==='