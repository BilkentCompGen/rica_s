#! /bin/bash

echo "[i]> Begin of classification stage"

for dir in ` ls -d rica_s_id_*/`
do
    echo "$dir"/classify.sh
done

echo "[i]> End of classification stage"
