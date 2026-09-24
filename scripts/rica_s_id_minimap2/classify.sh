#! /bin/bash
inputfile="$1"
outputfile=$(basename $inputfile)

outdir="$2"
referencefile="/opt/rica_s/tools/rica_s_id_minimap2/all_pathogens.mmi"

/usr/bin/time -f "\n\tT> %E [h:]m:s.s\n\tM> %M KB" minimap2 -t `nproc` -c -x map-ont $referencefile $inputfile > $outdir/$outputfile.minimap2.paf
sort -k1,1 -k12,12nr $outdir/$outputfile.minimap2.paf | awk '!seen[$1]++ {print $6}' | sort | uniq -c | awk -v OFS='\t' '{print $2, $1}' | sort -nr > $outdir/$outputfile.minimap2.paf.tsv
