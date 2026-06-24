#!/bin/bash

# Output file
OUT_FILE="custom_16S_db.fasta"
INPUT_LIST=$1

# Clean up previous runs
if [ -f "$OUT_FILE" ]; then
    rm "$OUT_FILE"
fi

echo "Órale, starting the download..."

# Loop through the list
while read -r ACCESSION || [ -n "$ACCESSION" ]; do
    # Skip lines that are comments or empty
    [[ "$ACCESSION" =~ ^#.*$ ]] && continue
    [[ -z "$ACCESSION" ]] && continue
    
    # Strip any trailing comments if you pasted them in
    CLEAN_ACC=$(echo "$ACCESSION" | awk '{print $1}')

    echo "Fetching 16S for: $CLEAN_ACC"
    
    # Download and append directly to the DB file
    # We use the NCBI eutils API for this
    wget -qO- "https://www.ncbi.nlm.nih.gov/sviewer/viewer.fcgi?db=nuccore&dopt=fasta&val=$CLEAN_ACC" >> "$OUT_FILE"
    
    # Add a tiny sleep to be polite to the NCBI server (don't get IP banned, ese)
    sleep 0.5

done < "$INPUT_LIST"

echo "-----------------------------------"
echo "Mission accomplished, ese."
echo "Your database is ready at: $OUT_FILE"
echo "Count of sequences:"
grep -c ">" "$OUT_FILE"