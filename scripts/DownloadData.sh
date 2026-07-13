#! /bin/bash
set -x #debug flag

DL_DIR="/opt/rica_s/"
echo "=== downloading data ==="

mkdir -p $DL_DIR/tmp/
mkdir -p $DL_DIR/tools/


# echo "=== downloading test datasets"
# wget -nc -P $DL_DIR/tmp http://donut.cs.bilkent.edu.tr/rica_s/datasets.tar
# tar xf $DL_DIR/tmp/datasets.tar -C $DL_DIR/tools/
# rm $DL_DIR/tmp/datasets.tar


# echo "=== downloading reads"
# wget -nc -P $DL_DIR/tmp http://donut.cs.bilkent.edu.tr/rica_s/reads.tar
# tar xf $DL_DIR/tmp/reads.tar -C $DL_DIR/tools/
# rm $DL_DIR/tmp/reads.tar


# echo "=== downloading reference_genomes"
# wget -nc -P $DL_DIR/tmp http://donut.cs.bilkent.edu.tr/rica_s/reference_genomes.tar
# tar xf $DL_DIR/tmp/reference_genomes.tar -C $DL_DIR/tools/
# rm $DL_DIR/tmp/reference_genomes.tar


echo "=== downloading db/index"


# echo "=== BLAST"
# wget -nc -P $DL_DIR/tmp/ http://donut.cs.bilkent.edu.tr/rica_s/tools/rica_s_id_blast.tar
# tar xf $DL_DIR/tmp/rica_s_id_blast.tar -C $DL_DIR/tools/
# rm $DL_DIR/tmp/rica_s_id_blast.tar


# echo "=== bwa"
# wget -nc -P $DL_DIR/tmp/ http://donut.cs.bilkent.edu.tr/rica_s/tools/rica_s_id_bwa.tar
# tar xf $DL_DIR/tmp/rica_s_id_bwa.tar -C $DL_DIR/tools/
# rm $DL_DIR/tmp/rica_s_id_bwa.tar


echo "=== kraken2"
wget -nc -P $DL_DIR/tmp/ http://donut.cs.bilkent.edu.tr/rica_s/tools/rica_s_id_kraken2.tar
tar xf $DL_DIR/tmp/rica_s_id_kraken2.tar -C $DL_DIR/tools/
rm $DL_DIR/tmp/rica_s_id_kraken2.tar


echo "=== clark"
wget -nc -P $DL_DIR/tmp/ http://donut.cs.bilkent.edu.tr/rica_s/tools/rica_s_id_clark.tar
tar xf $DL_DIR/tmp/rica_s_id_clark.tar -C $DL_DIR/tools/
rm $DL_DIR/tmp/rica_s_id_clark.tar


echo "=== cuclark"
wget -nc -P $DL_DIR/tmp/ http://donut.cs.bilkent.edu.tr/rica_s/tools/rica_s_id_cuclark.tar
tar xf $DL_DIR/tmp/rica_s_id_cuclark.tar -C $DL_DIR/tools/
rm  $DL_DIR/tmp/rica_s_id_cuclark.tar


echo "=== minimap"
wget -nc -P $DL_DIR/tmp/ http://donut.cs.bilkent.edu.tr/rica_s/tools/rica_s_id_minimap2.tar
tar xf $DL_DIR/tmp/rica_s_id_minimap2.tar -C $DL_DIR/tools/
rm  $DL_DIR/tmp/rica_s_id_minimap2.tar


echo "=== finished ==="
