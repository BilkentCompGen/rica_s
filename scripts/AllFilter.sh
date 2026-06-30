#! /bin/bash

echo "[i]> Begin of Filtering stage"


run_id=$1
read_file="$2"

# for dir in ` ls -d rica_s_fl_*/`
# do
#     cat "$dir"/filter.sh
# done

rica_s_id_minimap2/FilterHumanDna.sh $read_file


echo "[i]> End of Filtering stage"
