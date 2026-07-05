#!/usr/bin/env bash
# set -x #debug flag
echo "[i]> Begin of reporting stage"
echo

projecthome=/opt/rica_s/
runid=$1

echo "[i]> merging TSVs..."
awk -F'\t' -v OFS='\t' '
{
    total[$1] += $2
}
END {
    for (ref in total) {
        print ref, total[ref]
    }
}' $projecthome/output/$runid/*.tsv | sort -k2,2nr > $projecthome/output/$runid/$runid.tsv

echo "[i]> done."
echo "[i]> generating plots..."

for file in $projecthome/output/$runid/*.tsv; do 
    # echo $file
    # echo $$projecthome/output/$runid/$file;
    python3 /opt/rica_s/scripts/misc/histogram.py $file; 
    echo
    # read -n 1 -p Continue?;
done

echo "[i]> done."
echo "[i]> generating EPS..."
    for file in $projecthome/output/$runid/*.pdf; do
        pdftops "$file" "$file".eps; 
    done
echo "[i]> done."


echo
echo "[i]> End of reporting stage"
