#! /bin/bash

# (abricate_env) root@rica_s_pr_abricate:~# abricate --list
# DATABASE	SEQUENCES	DBTYPE	DATE
# resfinder	3206	nucl	2026-Apr-3
# victors	4545	nucl	2026-Apr-3
# vfdb		4592	nucl	2026-Apr-3
# upec_expec_vf	77	nucl	2026-Apr-3
# ecoli_vf	2701	nucl	2026-Apr-3
# argannot	2224	nucl	2026-Apr-3
# megares	6635	nucl	2026-Apr-3
# plasmidfinder	488	nucl	2026-Apr-3
# card		6052	nucl	2026-Apr-3
# ncbi		8232	nucl	2026-Apr-3
# bacmet2	746	prot	2026-Apr-3
# ecoh		597	nucl	2026-Apr-3


# $1 is the read file


# 2. Run the loop to hit every database and append the raw data (without extra headers)
for db in resfinder victors vfdb upec_expec_vf ecoli_vf argannot megares plasmidfinder card ncbi bacmet2 ecoh; do
    echo "=== $db ===" >> out.tsv
    abricate --db $db $1 >> out.tsv
done

echo "[+] Jale finished, carnal. Master file is ready."
