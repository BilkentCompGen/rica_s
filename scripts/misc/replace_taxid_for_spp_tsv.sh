#!/bin/bash
# Run: bash replace_taxid_for_spp_batch.sh 2 file1.tsv file2.tsv
# Or wildcards: bash replace_taxid_for_spp_batch.sh 2 *.tsv

# Grab the column number from the first argument
COL=$1

# Bump the first argument so $@ only holds your files
shift

if [ -z "$COL" ] || [ -z "$1" ]; then
    echo "Usage: $0 <column_number> <file1.tsv> [file2.tsv ...]"
    exit 1
fi


# Grab only numbers so we ignore headers or empty lines
awk -v col="$COL" -F'\t' '{print $col}' "$@" | grep -E '^[0-9]+$' | sort -u > tmp_taxids.txt

if [ ! -s tmp_taxids.txt ]; then
    echo "No TaxIDs found in column $COL across any of those files."
    rm -f tmp_taxids.txt
    exit 1
fi


epost -db taxonomy -input tmp_taxids.txt | \
esummary | \
xtract -pattern DocumentSummary -element TaxId,ScientificName > tmp_tax_map.txt

if [ ! -s tmp_tax_map.txt ]; then
    echo "Check your connection or IDs."
    rm -f tmp_taxids.txt tmp_tax_map.txt
    exit 1
fi


# Loop through every file provided on the command line
for TARGET_TSV in "$@"; do
    echo "    -> Slicing up: $TARGET_TSV"
    
    # Do the in-place swap
    awk -v col="$COL" -F'\t' '
    BEGIN { OFS="\t" }
    FNR==NR {
        taxid = $1
        $1 = ""
        # Capture the rest of the line (species name)
        name = substr($0, 2)
        map[taxid] = name
        next
    }
    {
        val = $col
        if (val in map) {
            $col = map[val]
        }
        print $0
    }' tmp_tax_map.txt "$TARGET_TSV" > tmp_new_target.tsv

    # The street magic: overwriting the old file with the force flag
    mv -f tmp_new_target.tsv "$TARGET_TSV"
done

rm -f tmp_taxids.txt tmp_tax_map.txt

echo "[*] Done."