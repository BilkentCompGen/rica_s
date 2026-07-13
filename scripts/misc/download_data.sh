#! /bin/bash

# LEGACY / alternative: recursive HTTP mirror of the data host (directory tree,
# not tars). The canonical downloader is scripts/DownloadData.sh (one tar per
# item). Kept for reference; prefer DownloadData.sh.

DL_DIR="/opt/rica_s/"
echo "=== downloading data ==="


echo "=== downloading 16s"
wget -r -np -nH --cut-dirs=1 -P $DL_DIR/ http://donut.cs.bilkent.edu.tr/rica_s/16s/
echo "=== downloading amr"
wget -r -np -nH --cut-dirs=1 -P $DL_DIR/ http://donut.cs.bilkent.edu.tr/rica_s/amr
echo "=== downloading test datasets"
wget -r -np -nH --cut-dirs=1 -P $DL_DIR/ http://donut.cs.bilkent.edu.tr/rica_s/datasets
echo "=== downloading simulated reads"
wget -r -np -nH --cut-dirs=1 -P $DL_DIR/ http://donut.cs.bilkent.edu.tr/rica_s/reads
echo "=== downloading reference_genomes"
wget -r -np -nH --cut-dirs=1 -P $DL_DIR/ http://donut.cs.bilkent.edu.tr/rica_s/reference_genomes
echo "=== downloading blast db"
wget -r -np -nH --cut-dirs=1 -P $DL_DIR/ http://donut.cs.bilkent.edu.tr/rica_s/tools/rica_s_id_blast
echo "=== downloading kraken2 db"
wget -r -np -nH --cut-dirs=1 -P $DL_DIR/ http://donut.cs.bilkent.edu.tr/rica_s/tools/rica_s_id_kraken2
echo "=== downloading krakenuniq db"
wget -r -np -nH --cut-dirs=1 -P $DL_DIR/ http://donut.cs.bilkent.edu.tr/rica_s/tools/rica_s_id_krakenuniq


echo "=== finished ==="
