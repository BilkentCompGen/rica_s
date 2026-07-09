#! /bin/bash


DL_DIR="/opt/rica_s/"
echo "=== downloading data ==="


echo "=== downloading 16s"
wget -r -np -nH --cut-dirs=1 -P $DL_DIR/ http://donut.cs.bilkent.edu.tr/rica_s/16s/
echo "=== downloading amr"
wget -r -np -nH --cut-dirs=1 -P $DL_DIR/ http://donut.cs.bilkent.edu.tr/rica_s/amr/
echo "=== downloading test datasets"
wget -r -np -nH --cut-dirs=1 -P $DL_DIR/ http://donut.cs.bilkent.edu.tr/rica_s/datasets/
echo "=== downloading simulated reads"
wget -r -np -nH --cut-dirs=1 -P $DL_DIR/ http://donut.cs.bilkent.edu.tr/rica_s/reads/
echo "=== downloading reference_genomes"
wget -r -np -nH --cut-dirs=1 -P $DL_DIR/ http://donut.cs.bilkent.edu.tr/rica_s/reference_genomes/


### ready to use databases or indexes

echo "=== downloading blast db"
wget -r -np -nH --cut-dirs=1 -P $DL_DIR/ http://donut.cs.bilkent.edu.tr/rica_s/tools/rica_s_id_blast/
echo "=== downloading kraken2 db"
wget -r -np -nH --cut-dirs=1 -P $DL_DIR/ http://donut.cs.bilkent.edu.tr/rica_s/tools/rica_s_id_kraken2/
echo "=== downloading krakenuniq db"
wget -r -np -nH --cut-dirs=1 -P $DL_DIR/ http://donut.cs.bilkent.edu.tr/rica_s/tools/rica_s_id_krakenuniq/
echo "=== downloading minimap2 db"
wget -r -np -nH --cut-dirs=1 -P $DL_DIR/ http://donut.cs.bilkent.edu.tr/rica_s/tools/rica_s_id_minimap2/
echo "=== downloading abricate db"
wget -r -np -nH --cut-dirs=1 -P $DL_DIR/ http://donut.cs.bilkent.edu.tr/rica_s/tools/rica_s_pr_abricate/



# echo "=== downloading clark db"
# wget -r -np -nH --cut-dirs=1 -P $DL_DIR/ http://donut.cs.bilkent.edu.tr/rica_s/tools/rica_s_id_clark/

# echo "=== downloading cu-clark db"
# wget -r -np -nH --cut-dirs=1 -P $DL_DIR/ http://donut.cs.bilkent.edu.tr/rica_s/tools/rica_s_id_cuclark/

# echo "=== downloading cu-clark db"
# wget -r -np -nH --cut-dirs=1 -P $DL_DIR/ http://donut.cs.bilkent.edu.tr/rica_s/tools/rica_s_id_metabuli/


echo "=== finished ==="
