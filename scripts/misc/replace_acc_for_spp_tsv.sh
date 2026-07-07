#!/bin/bash

# Run: bash replace_acc_for_spp_batch.sh 2 file1.tsv file2.tsv file3.tsv
# Or use wildcards: bash replace_acc_for_spp_batch.sh 2 *.tsv

# Grab the column number from the first argument
COL=$1


shift

if [ -z "$COL" ] || [ -z "$1" ]; then
    echo "Usage: $0 <column_number> <file1.tsv> [file2.tsv ...]"
    exit 1
fi


# Awk seamlessly reads through every file passed in $@
awk -v col="$COL" -F'\t' '{print $col}' "$@" | grep -E '^[A-Za-z]+_?[A-Za-z0-9]+\.?[0-9]*$' | sort -u > tmp_accs.txt

if [ ! -s tmp_accs.txt ]; then
    echo "No accessions found in column $COL."
    rm -f tmp_accs.txt
    exit 1
fi


epost -db nuccore -input tmp_accs.txt | \
esummary | \
xtract -pattern DocumentSummary -element AccessionVersion,TaxId > tmp_acc_taxid.txt


awk '{print $2}' tmp_acc_taxid.txt | grep -E '^[0-9]+$' | sort -u > tmp_taxids.txt

if [ ! -s tmp_taxids.txt ]; then
    echo "No taxids!"
    rm -f tmp_accs.txt tmp_acc_taxid.txt tmp_taxids.txt
    exit 1
fi

echo "[*] 2/2 Hitting NCBI Taxonomy database to pull Species Names..."
epost -db taxonomy -input tmp_taxids.txt | \
esummary | \
xtract -pattern DocumentSummary -element TaxId,ScientificName > tmp_taxid_spp.txt

echo "[*] Building the master map..."
# Pre-combine the two maps together so the final swap runs instantly
awk '
FNR==NR {
    taxid = $1
    $1 = ""
    tax2spp[taxid] = substr($0, 2)
    next
}
{
    acc = $1
    taxid = $2
    if (taxid in tax2spp) {
        print acc "\t" tax2spp[taxid]
    }
}' tmp_taxid_spp.txt tmp_acc_taxid.txt > tmp_acc_spp_map.txt

echo "[*] Overwriting files with fresh species names..."

# Loop through every file provided in the command
for TARGET_TSV in "$@"; do
    echo "    -> $TARGET_TSV"
    
    # Do the in-place swap using the master map
    awk -v col="$COL" -F'\t' '
    BEGIN { OFS="\t" }
    FNR==NR {
        acc = $1
        $1 = ""
        name = substr($0, 2)
        map[acc] = name
        
        # Store a versionless copy just in case your TSV dropped the .1
        acc_no_ver = acc
        sub(/\.[0-9]+$/, "", acc_no_ver)
        map[acc_no_ver] = name
        next
    }
    {
        val = $col
        if (val in map) {
            $col = map[val]
        } else {
            val_no_ver = val
            sub(/\.[0-9]+$/, "", val_no_ver)
            if (val_no_ver in map) {
                $col = map[val_no_ver]
            }
        }
        print $0
    }' tmp_acc_spp_map.txt "$TARGET_TSV" > tmp_new_target.tsv

    # Overwrite the specific file
    mv -f tmp_new_target.tsv "$TARGET_TSV"
done

rm -f tmp_accs.txt tmp_acc_taxid.txt tmp_taxids.txt tmp_taxid_spp.txt tmp_acc_spp_map.txt

echo "[*] Done."