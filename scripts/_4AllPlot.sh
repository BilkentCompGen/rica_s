#!/usr/bin/env bash
# set -x #debug flag

AllPlot()
{
	echo "[i]> Begin of reporting stage"
	date
	echo

	project_home=/opt/rica_s/
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
	}' $project_home/output/$runid/*.tsv | sort -k2,2nr > $project_home/output/$runid/$runid.tsv

	echo "[i]> done."
	echo "[i]> generating plots..."

	for file in $project_home/output/$runid/*.tsv; do 
		# echo $file
		# echo $$project_home/output/$runid/$file;
		python3 /opt/rica_s/scripts/misc/histogram.py $file; 
		echo
		# read -n 1 -p Continue?;
	done

	echo "[i]> done."
	echo "[i]> generating EPS..."
		for file in $project_home/output/$runid/*.pdf; do
			pdftops "$file" "$file".eps; 
		done
	echo "[i]> done."


	echo
	date
	echo "[i]> End of reporting stage"
}

# AllPlot $1