# /bin/bash

for d in "$1"/*/; do
    # Strip the trailing slash for cleaner logs (optional)
    dirname="${d%/}"


    # echo "Cleaning up barrio: $dirname"

    # echo $d
    # echo $dirname
    # 1. Pull all deep files up to the subdirectory root ($dirname)
    # -mindepth 2 ensures we don't try to move files that are already at the top of $dirname
    find "$d" -mindepth 2 -type f -exec mv --backup=numbered -t "$d" {} +

    # 2. Kill the empty nested folders inside $dirname
    find "$d" -type d -empty -delete


    for f in `ls $dirname/*.fasta`; do
        cat "$f"
        echo "" # Forces a newline just in case
    done > $dirname/$dirname\_refs.fasta


    for f in `ls $dirname/*.fna`; do
        cat "$f"
        echo "" # Forces a newline just in case
    done > $dirname/$dirname\_refs.fasta
done