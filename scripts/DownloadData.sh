#! /bin/bash
set -x #debug flag

# Canonical downloader for RICA_S reference data and prebuilt databases.
#
# Model: ONE tar per item, served over HTTP from the lab data host, extracted
# into place under /opt/rica_s. Per-tool DBs live under tools/rica_s_id_<tool>/;
# test data (datasets/, reads/) is extracted at the project root.
#
# (Legacy alternatives scripts/misc/download_data.sh and
#  scripts/misc/download_data_from_donut.sh are kept for reference only.)

DL_DIR="/opt/rica_s"
BASE_URL="http://donut.cs.bilkent.edu.tr/rica_s"

echo "=== downloading data ==="

mkdir -p "$DL_DIR/tmp/"
mkdir -p "$DL_DIR/tools/"

# fetch_tar <url-path-relative-to-BASE_URL> <extract-dir>
#   downloads BASE_URL/<url-path> once (-nc) into tmp/, extracts into
#   <extract-dir>, then removes the downloaded tar.
fetch_tar() {
    urlpath="$1"
    dest="$2"
    tarname="$(basename "$urlpath")"

    mkdir -p "$dest"
    wget -nc -P "$DL_DIR/tmp/" "$BASE_URL/$urlpath"
    tar xf "$DL_DIR/tmp/$tarname" -C "$dest"
    rm -f "$DL_DIR/tmp/$tarname"
}

# --- test data (extracted at the project root -> /opt/rica_s/datasets, /opt/rica_s/reads) ---
echo "=== datasets ==="
fetch_tar "datasets.tar" "$DL_DIR/"

echo "=== reads ==="
fetch_tar "reads.tar" "$DL_DIR/"

# Optional shared reference genomes. Superseded by the per-tool DBs below
# (minimap2/bwa/ngmlr each carry their own copy under tools/). Uncomment only
# if you specifically need reference_genomes/joint/.
# echo "=== reference_genomes ==="
# fetch_tar "reference_genomes.tar" "$DL_DIR/"

# --- per-tool databases / indexes (extracted into /opt/rica_s/tools/<tool>/) ---
echo "=== db/index ==="

echo "=== minimap2 (human_v38.mmi for filtering + all_pathogens.mmi for classification) ==="
fetch_tar "tools/rica_s_id_minimap2.tar" "$DL_DIR/tools/"

echo "=== kraken2 ==="
fetch_tar "tools/rica_s_id_kraken2.tar" "$DL_DIR/tools/"

echo "=== blast ==="
fetch_tar "tools/rica_s_id_blast.tar" "$DL_DIR/tools/"

echo "=== bwa ==="
fetch_tar "tools/rica_s_id_bwa.tar" "$DL_DIR/tools/"

echo "=== ngmlr ==="
fetch_tar "tools/rica_s_id_ngmlr.tar" "$DL_DIR/tools/"

echo "=== clark ==="
fetch_tar "tools/rica_s_id_clark.tar" "$DL_DIR/tools/"

echo "=== cuclark ==="
fetch_tar "tools/rica_s_id_cuclark.tar" "$DL_DIR/tools/"

# Optional / scaffolded classifiers (disabled by default).
# echo "=== krakenuniq ==="
# fetch_tar "tools/rica_s_id_krakenuniq.tar" "$DL_DIR/tools/"

echo "=== finished ==="
