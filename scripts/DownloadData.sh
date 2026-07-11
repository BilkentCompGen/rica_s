#! /bin/bash
set -x #debug flag

DL_DIR="/opt/rica_s/"
echo "=== downloading data ==="

mkdir -p $DL_DIR/tools/

# echo "=== downloading 16s"
# wget -r -np -nH -nc --cut-dirs=1 -P $DL_DIR/ http://donut.cs.bilkent.edu.tr/rica_s/16s/
# echo "=== downloading amr"
# wget -r -np -nH -nc --cut-dirs=1 -P $DL_DIR/ http://donut.cs.bilkent.edu.tr/rica_s/amr/
# echo "=== downloading test datasets"
# wget -r -np -nH -nc --cut-dirs=1 -P $DL_DIR/ http://donut.cs.bilkent.edu.tr/rica_s/datasets/
# echo "=== downloading simulated reads"
# wget -r -np -nH -nc --cut-dirs=1 -P $DL_DIR/ http://donut.cs.bilkent.edu.tr/rica_s/reads/
# echo "=== downloading reference_genomes"
# wget -r -np -nH -nc --cut-dirs=1 -P $DL_DIR/ http://donut.cs.bilkent.edu.tr/rica_s/reference_genomes/


echo "=== downloading blast db"
wget -nc -P $DL_DIR/tools http://donut.cs.bilkent.edu.tr/rica_s/tools/rica_s_id_blast.tar
tar xf $DL_DIR/tools/rica_s_id_blast.tar -C $DL_DIR/tools/
rm $DL_DIR/tools/rica_s_id_blast.tar


echo "=== downloading bwa index"
wget -nc -P $DL_DIR/tools  http://donut.cs.bilkent.edu.tr/rica_s/tools/rica_s_id_bwa.tar
tar xf $DL_DIR/tools/rica_s_id_bwa.tar -C $DL_DIR/tools/
rm $DL_DIR/tools/rica_s_id_bwa.tar


echo "=== downloading kraken2 db"
wget -nc -P $DL_DIR/tools  http://donut.cs.bilkent.edu.tr/rica_s/tools/rica_s_id_kraken2.tar
tar xf $DL_DIR/tools/rica_s_id_kraken2.tar -C $DL_DIR/tools/
rm $DL_DIR/tools/rica_s_id_kraken2.tar


echo "=== downloading minimap2 index"
wget -nc -P $DL_DIR/tools  http://donut.cs.bilkent.edu.tr/rica_s/tools/rica_s_id_minimap2.tar
tar xf $DL_DIR/tools/rica_s_id_minimap2.tar -C $DL_DIR/tools/
rm $DL_DIR/tools/rica_s_id_minimap2.tar


echo "=== downloading clark db"
wget -nc -P $DL_DIR/tools  http://donut.cs.bilkent.edu.tr/rica_s/tools/rica_s_id_clark.tar
tar xf $DL_DIR/tools/rica_s_id_clark.tar -C $DL_DIR/tools/
rm $DL_DIR/tools/rica_s_id_clark.tar


echo "=== downloading cuclark db"
wget -nc -P $DL_DIR/tools  http://donut.cs.bilkent.edu.tr/rica_s/tools/rica_s_id_cuclark.tar
tar xf $DL_DIR/tools/rica_s_id_cuclark.tar -C $DL_DIR/tools/
rm $DL_DIR/tools/rica_s_id_cuclark.tar


echo "=== finished ==="
