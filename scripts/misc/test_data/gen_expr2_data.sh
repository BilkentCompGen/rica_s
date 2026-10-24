#!/bin/bash

./sample_maker.py -n 2500860 --length 3000,8000 -o ./output/expr2_05B_0.100A_1H_1G.fasta --error-types sub,ins,del --error-rate 0.2 ./05B_1G.txt &

./sample_maker.py -n 3641677 --length 3000,8000 -o ./output/expr2_10B_0.100A_1H_1G.fasta --error-types sub,ins,del --error-rate 0.2 ./10B_1G.txt &

./sample_maker.py -n 2168217 --length 3000,8000 -o ./output/expr2_15B_0.100A_1H_1G.fasta --error-types sub,ins,del --error-rate 0.2 ./15B_1G.txt &

./sample_maker.py -n 2500860 --length 3000,8000 -o ./output/expr2_05B_0.100A_1H_3G.fasta --error-types sub,ins,del --error-rate 0.2 ./05B_3G.txt &

./sample_maker.py -n 3641677 --length 3000,8000 -o ./output/expr2_10B_0.100A_1H_3G.fasta --error-types sub,ins,del --error-rate 0.2 ./10B_3G.txt &

./sample_maker.py -n 2168217 --length 3000,8000 -o ./output/expr2_15B_0.100A_1H_3G.fasta --error-types sub,ins,del --error-rate 0.2 ./15B_3G.txt &
