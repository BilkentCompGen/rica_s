#! /bin/bash


DL_DIR="/opt/rica_s/"
echo "=== downloading data ==="


# echo "=== downloading 16s"
# wget -r -np -nH --cut-dirs=1 -P $DL_DIR/ ftp://donut.cs.bilkent.edu.tr/rica_s/16s/
# echo "=== downloading amr"
# wget -r -np -nH --cut-dirs=1 -P $DL_DIR/ ftp://donut.cs.bilkent.edu.tr/rica_s/amr
echo "=== downloading test datasets"
wget -r -np -nH --cut-dirs=1 -P $DL_DIR/ ftp://donut.cs.bilkent.edu.tr/rica_s/datasets
echo "=== downloading simulated reads"
wget -r -np -nH --cut-dirs=1 -P $DL_DIR/ ftp://donut.cs.bilkent.edu.tr/rica_s/reads
echo "=== downloading reference_genomes"
wget -r -np -nH --cut-dirs=1 -P $DL_DIR/ ftp://donut.cs.bilkent.edu.tr/rica_s/reference_genomes
echo "=== downloading blast db"
wget -r -np -nH --cut-dirs=1 -P $DL_DIR/ ftp://donut.cs.bilkent.edu.tr/rica_s/tools/rica_s_id_blast
echo "=== downloading kraken2 db"
wget -r -np -nH --cut-dirs=1 -P $DL_DIR/ ftp://donut.cs.bilkent.edu.tr/rica_s/tools/rica_s_id_kraken2
echo "=== downloading krakenuniq db"
wget -r -np -nH --cut-dirs=1 -P $DL_DIR/ ftp://donut.cs.bilkent.edu.tr/rica_s/tools/rica_s_id_krakenuniq
echo "=== downloading clark db"
wget -r -np -nH --cut-dirs=1 -P $DL_DIR/ ftp://donut.cs.bilkent.edu.tr/rica_s/tools/rica_s_id_clark
echo "=== downloading cuclark db"
wget -r -np -nH --cut-dirs=1 -P $DL_DIR/ ftp://donut.cs.bilkent.edu.tr/rica_s/tools/rica_s_id_cuclark
echo "=== downloading minimap2 db"
wget -r -np -nH --cut-dirs=1 -P $DL_DIR/ ftp://donut.cs.bilkent.edu.tr/rica_s/tools/rica_s_id_minimap2
echo "=== downloading bwa db"
wget -r -np -nH --cut-dirs=1 -P $DL_DIR/ ftp://donut.cs.bilkent.edu.tr/rica_s/tools/rica_s_id_bwa
echo "=== downloading ngmlr db"
wget -r -np -nH --cut-dirs=1 -P $DL_DIR/ ftp://donut.cs.bilkent.edu.tr/rica_s/tools/rica_s_id_ngmlr

echo "=== finished ==="
