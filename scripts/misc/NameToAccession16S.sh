#!/bin/bash

INPUT_FILE="$1"
OUTPUT_FILE="accessions_found.txt"

if [ -z "$INPUT_FILE" ]; then
    echo "¡Chale! Usage: $0 list_of_bugs.txt"
    exit 1
fi

> "$OUTPUT_FILE"

echo "Órale, scanning..."

while read -r BUG_NAME || [ -n "$BUG_NAME" ]; do
    [[ -z "$BUG_NAME" ]] && continue

    echo -n "Looking up: $BUG_NAME ... "

    # --- THE FIX IS HERE ---
    # We add "< /dev/null" at the end of the esearch command
    # so it doesn't steal the rest of the lines from the loop.
    
    RESULT=$(esearch -db nucleotide -query "$BUG_NAME[Organism] AND 16S ribosomal RNA[Title] AND RefSeq[filter]" < /dev/null \
        | efetch -format docsum \
        | xtract -pattern DocumentSummary -element Caption Title \
        | head -n 1)

    ACCESSION=$(echo "$RESULT" | awk '{print $1}')
    
    if [ -n "$ACCESSION" ]; then
        echo "Found: $ACCESSION"
        echo "$ACCESSION # $BUG_NAME" >> "$OUTPUT_FILE"
    else
        echo "No hits."
    fi

    sleep 0.3

done < "$INPUT_FILE"

echo "Done. Check $OUTPUT_FILE"