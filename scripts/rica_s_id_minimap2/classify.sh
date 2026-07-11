#! /bin/bash

echo '[i]> === minimap2'
date
echo

inputfile="$1"
outputfile=$(basename $inputfile)

outdir="$2"
referencefile="/opt/rica_s/tools/rica_s_id_minimap2/all_pathogens.mmi"


# queries=$(find $2 -type f -name "*."$3)
# refs=$(find /rica_s/data/pathogen_reference/ -type f -name "*.fasta")

/usr/bin/time -v minimap2 -t `nproc` -c -x map-ont $referencefile $inputfile > $outdir/$outputfile.minimap2.paf
sort -k1,1 -k12,12nr $outdir/$outputfile.minimap2.paf | awk '!seen[$1]++ {print $6}' | sort | uniq -c | awk -v OFS='\t' '{print $2, $1}' | sort -nr > $outdir/$outputfile.minimap2.paf.tsv

echo
date
echo '[i]> minimap2 ==='