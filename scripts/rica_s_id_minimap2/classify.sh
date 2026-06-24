#! /bin/bash

echo "start run" $1
echo $(date)


queries=$(find $2 -type f -name "*."$3)
refs=$(find /rica_s/data/pathogen_reference/ -type f -name "*.fasta")


for r in $refs; do
        for q in $queries; do
                echo $r
                echo $q

                minimap2 -t 14 -c -x map-ont $r $q > /rica_s/output/runs/$1/id/$(basename $q)_vs_$(basename $r).paf
        done
done


echo $(date)