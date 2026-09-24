#!/bin/bash

INPUT_FILE="/opt/rica_s/scripts/misc/spp.txt"

if [[ ! -f "$INPUT_FILE" ]]; then
    echo "[!] Error: '$INPUT_FILE' not found."
    exit 1
fi

# Print a formatted table header
printf "%-30s | %-10s | %-20s\n" "Species" "TaxID" "Accession"
echo "-----------------------------------------------------------------"

# Read the file line by line
while IFS= read -r species || [[ -n "$species" ]]; do
    # Skip empty lines
    [[ -z "$species" ]] && continue

    # 1. datasets summary genome taxon fetches the metadata (--reference filters it)
    # 2. dataformat tsv genome extracts just the two fields we care about
    # 3. tail -n +2 drops the TSV header row so it doesn't print for every species
    output=$(datasets summary genome taxon "$species" --reference --as-json-lines  2>/dev/null | dataformat tsv genome --fields organism-name,accession,organism-tax-id) 2>/dev/null

    if [[ -z "$output" ]]; then
        printf "%-30s\t%-10s\t%-20s\n" "$species" "-" "No reference found"
    else
        # Process the output (this loop handles cases where a species returns multiple references)
        echo "$output" | while IFS=$'\t' read -r taxid accession; do
            printf "%-30s\t%-10s\t%-20s\n" "$species" "$taxid" "$accession"
        done
    fi

done < "$INPUT_FILE"