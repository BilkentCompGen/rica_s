# RICA_S

**A container-base, modular workflow for rapid pathogen identification and antimicrobial‑resistance (AMR) profiling from long‑read sequencing data, geared toward sepsis diagnostics.**

`RICA_S` takes raw sequencing reads (e.g. Oxford Nanopore FASTA/FASTQ), filters out human DNA, classifies the remaining reads against a curated pathogen database using several independent classifiers in ensemble, profiles the sample for antimicrobial‑resistance and virulence genes, and (optionally) surfaces results through a small web UI. Every stage runs inside its own Docker container so tools with conflicting dependencies coexist cleanly and the pipeline is reproducible across machines.

---

## Table of contents

- [Overview](#overview)
- [Pipeline architecture](#pipeline-architecture)
- [Requirements](#requirements)
- [Installation](#installation)
- [Downloading data and databases](#downloading-data-and-databases)
- [Running the pipeline](#running-the-pipeline)
- [Stage and tool reference](#stage-and-tool-reference)
- [Output files](#output-files)
- [Web UI](#web-ui)
- [Utility and misc scripts](#utility-and-misc-scripts)
- [Notes and conventions](#notes-and-conventions)
- [Troubleshooting](#troubleshooting)
- [Authors and acknowledgements](#authors-and-acknowledgements)

---

## Overview

Diagnosing bloodstream infections and sepsis quickly matters - every hour of delay in effective therapy worsens outcomes. `RICA_S` is built to move a sample from raw reads to an actionable identification + resistance profile with minimal manual intervention, using a metagenomic, alignment‑and‑classification approach.

The design philosophy is **one tool, one container**. Each bioinformatics tool (minimap2, kraken2, BLAST, ABRicate, ...) lives in its own image, and the host orchestrates them by executing scripts inside the running containers. This keeps dependency graphs isolated, makes it trivial to add or swap a classifier, and lets the same read set be evaluated against many methods at once for comparison.

A processing run is identified by a **run id** (`runid`) and all of its artifacts are written under `output/<runid>/`.

<!-- 
## Pipeline architecture

Work is organized into named **stages**, and every service follows the naming convention: `rica_s_<stage>_<tool>`

| Stage code | Stage | Purpose |
|-----------|-------|---------|
| `sq` | Sequencing | Sequencing‑side inputs (placeholder / future) |
| `bc` | Basecalling | Basecalling of raw signal (placeholder / future) |
| `fl` | Filtering | Remove human reads before classification |
| `id` | Identification | Classify reads against the pathogen database |
| `pr` | Profiling | Detect AMR / virulence genes |
| `rp` | Reporting | Assemble the final report |
| `ui` | User interface | Web front end |
| `tl` | Tooling | Read simulators used to generate test data |

The three stages you run today, in order, are **Filter → Classify → Profile**, driven by the three top‑level scripts:

```
_1AllFilter.sh   →  _2AllClassify.sh   →  _3AllProfile.sh
```

1. **Filter (`_1AllFilter.sh`)** — runs `rica_s_id_minimap2`'s `filterHumanDna.sh`, aligning reads to the human reference (GRCh38) and keeping only the unmapped (non‑human) reads.
2. **Classify (`_2AllClassify.sh`)** — iterates over every `rica_s_id_*` container and runs its `classify.sh` against the pathogen database, producing per‑tool results plus a normalized `.tsv`.
3. **Profile (`_3AllProfile.sh`)** — iterates over every `rica_s_pr_*` container and runs its `profile.sh` to detect resistance and virulence genes.

Each stage appends its stdout/stderr to a per‑run log at `output/<runid>/<runid>.log`.

```
        raw reads (FASTA/FASTQ)
                 │
        ┌────────▼─────────┐
        │  _1AllFilter.sh  │  minimap2 vs. human GRCh38 → keep unmapped
        └────────┬─────────┘
                 │  non‑human reads
        ┌────────▼──────────┐
        │  _2AllClassify.sh │  minimap2 / kraken2 / blast / bwa / ngmlr / clark / … (classifiers)
        └────────┬──────────┘
                 │  per‑tool species hits (.tsv)
        ┌────────▼─────────┐
        │  _3AllProfile.sh │  ABRicate vs. AMR/virulence DBs → resistance genes
        └────────┬─────────┘
                 │
             report / UI
```

> **Note on `/opt/rica_s`.** Inside every container the project is mounted at **`/opt/rica_s`** (see the `volumes:` entries in the compose files: `/opt/rica_s:/opt/rica_s`). The stage scripts therefore assume the repo lives at `/opt/rica_s` on the host. See [Installation](#installation).
 -->


## Requirements

- Ubuntu 24.04
  - poppler-utils
  - wget
- 32+ GB memory
- 1+ TB SSD/HDD
- NVIDIA GeForce RTX 4060 Max-Q / Mobile or better
  - NVIDIA CUDA Toolkit (https://developer.nvidia.com/cuda/toolkit)
- Docker
  - Docker-compose v2
  - NVIDIA Container Toolkit (https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html)
- Python 3
  - Pandas
  - plotly


<!--
- A Linux host (the pipeline uses Linux containers and `docker exec`). Sufficient CPU cores and RAM for the classifiers; alignment against the human genome and pathogen references is the heaviest step.
- **Disk space** for reference genomes and prebuilt databases (BLAST, kraken2, krakenuniq, minimap2, ABRicate). These can be large (tens of GB), and are **not** stored in git (they live under git‑ignored directories such as `tools/`, `reference_genomes/`, `datasets/`, `reads/`).
- A modern CUDA-enable device, if the GPU-enable classifiers are to be used (i.e. cuCLARK).
- Network access to the data host (`donut.cs.bilkent.edu.tr` over HTTP) to download reference data and databases.
- **Docker** and the **Docker Compose** plugin (`docker compose`, v2 syntax).
- NVIDIA Container Toolkit.
- The prebuilt images are published under the Docker Hub org **`alkanlab/`** (e.g. `alkanlab/rica_s_id_kraken2:v1.1`). Docker will pull them automatically on first `up`.
-->
## Installation

1. **Clone the repository to `/opt/rica_s`.** 
The containers mount the project at `/opt/rica_s`, so cloning there keeps host and container paths identical.

   ```bash
   $ sudo git clone https://github.com/BilkentCompGen/rica_s /opt/rica_s
   $ sudo chown -R "$USER" /opt/rica_s
   $ cd /opt/rica_s
   ```
   If you must clone elsewhere, either symlink it to `/opt/rica_s` or change every mention of `/opt/rica_s` to your custom path.

2. **Download reference data and databases** 
These populate the git‑ignored `datasets/` and `tools/` directories. Other data is available if needed. It can be downloaded from: `http://donut.cs.bilkent.edu.tr/rica_s/` or by modifying the `data` and `tools` variables of `DownloadData.sh`

   ```bash
   $ scripts/DownloadData.sh
   ```

3. **Start the docker comtainers:**

   ```bash
   $ cd /opt/rica_s/builder
   $ ./start_all.sh
   ```

4. **Confirm the containers are running:**

   ```bash
   $ docker ps --format '{{.Names}}' | grep rica_s
   ```

   You should see `rica_s_id_minimap2`, `rica_s_id_kraken2`, etc.


<!-- 
1. **Clone the repository to `/opt/rica_s`.** The containers mount the project at `/opt/rica_s`, so cloning there keeps host and container paths identical.

   ```bash
   sudo git clone https://github.com/BilkentCompGen/rica_s /opt/rica_s
   sudo chown -R "$USER" /opt/rica_s
   cd /opt/rica_s
   ```

   If you must clone elsewhere, either symlink it to `/opt/rica_s` or edit the `volumes:` entries in `builder/**/*-compose.yml` and the `projecthome=/opt/rica_s/` line at the top of each stage driver.

2. **Download reference data and databases** (see the next section). These populate the git‑ignored `16s/`, `amr/`, `datasets/`, `reads/`, `reference_genomes/`, and `tools/` directories.

3. **Build/pull and start the services:**

   ```bash
   cd /opt/rica_s/builder
   ./start_all.sh
   # equivalent to:
   # docker compose -f ./rica_s-compose.yml up
   ```

   This brings up all identification containers, the ABRicate profiler, and the web UI. Add `-d` to run detached:

   ```bash
   docker compose -f ./rica_s-compose.yml up -d
   ```

4. **Confirm the containers are running:**

   ```bash
   docker ps --format '{{.Names}}' | grep rica_s
   ```

   You should see `rica_s_id_minimap2`, `rica_s_id_kraken2`, `rica_s_id_blast`, `rica_s_pr_abricate`, `rica_s_ui_web`, and the others.

## Downloading data and databases

Reference data and prebuilt databases are fetched from the lab HTTP server with `scripts/DownloadData.sh`.

```bash
cd /opt/rica_s
bash scripts/DownloadData.sh
```

The downloader uses a **one‑tar‑per‑item** model: each item is a single `.tar` served over HTTP from `http://donut.cs.bilkent.edu.tr/rica_s/`, downloaded once (`wget -nc`) and extracted into place, then the tar is deleted. Test data extracts at the project root; each tool's database extracts into its own directory under `tools/`.

Test data (extracted at the project root):

- `datasets.tar` → `datasets/` — test datasets
- `reads.tar` → `reads/` — simulated reads

Per‑tool databases / indexes (extracted into `tools/rica_s_id_<tool>/`), one tar each:

- `tools/rica_s_id_minimap2.tar` → `tools/rica_s_id_minimap2/` — `human_v38.mmi` (human filter index) **and** `all_pathogens.mmi` (pathogen classification index)
- `tools/rica_s_id_kraken2.tar` → `tools/rica_s_id_kraken2/pathogen.k2db/`
- `tools/rica_s_id_blast.tar` → `tools/rica_s_id_blast/`
- `tools/rica_s_id_bwa.tar` → `tools/rica_s_id_bwa/all_pathogens.fasta` (+ BWA index files)
- `tools/rica_s_id_ngmlr.tar` → `tools/rica_s_id_ngmlr/all_pathogens.fasta`
- `tools/rica_s_id_clark.tar` → `tools/rica_s_id_clark/`
- `tools/rica_s_id_cuclark.tar` → `tools/rica_s_id_cuclark/`

Every classifier reads its reference/DB from `tools/rica_s_id_<tool>/` — there is no shared `reference_genomes/` on the run path. The optional `reference_genomes.tar` (shared `joint/all_pathogens.*`) and the scaffolded `krakenuniq` DB are present in `DownloadData.sh` but commented out; uncomment them only if you need those. The ABRicate profiling databases ship **inside** the `rica_s_pr_abricate` image, so there is no separate ABRicate download.

> **Note.** `scripts/misc/download_data.sh` (recursive HTTP) and `scripts/misc/download_data_from_donut.sh` (recursive FTP) are legacy alternatives kept for reference only. Use `scripts/DownloadData.sh`. 
-->
## Running the pipeline

Each stage driver takes a **run id** and an **absolute path to the input reads** (the path must resolve inside the containers, i.e. under `/opt/rica_s/...`). Run the three stages in order.

```bash
$ cd /opt/rica_s
$ scripts/AllRun.sh 1234_uniqueidentifier /path/to/input/data.fasta
```

<!--
## Stage and tool reference

### Filtering — `rica_s_id_minimap2/filterHumanDna.sh`
Aligns reads to the human reference index `tools/rica_s_id_minimap2/human_v38.mmi` with `minimap2 -a`, then uses `samtools` to split mapped (human) vs. unmapped (non‑human) read names and `seqtk subseq` to extract the non‑human reads. Produces, in `output/<runid>/rica_s_fl_minimap2/`:
- `human_mapped_sequence_names.txt`
- `nonhuman_unmapped_sequence_names.txt`
- `nonhuman_unmapped_sequence_names.fasta` ← the input for classification.

### Identification (`id`) classifiers
All classify against the curated pathogen database and emit a normalized two‑column `.tsv` (species vs. read count / identity) that downstream tooling can plot.

| Tool | Container | Method | Reference / DB | Key outputs |
|------|-----------|--------|----------------|-------------|
| **minimap2** | `rica_s_id_minimap2` | Long‑read mapping (`map-ont`) | `tools/rica_s_id_minimap2/all_pathogens.mmi` | `*.minimap2.paf`, `*.minimap2.paf.tsv` |
| **kraken2** | `rica_s_id_kraken2` | k‑mer classification | `tools/rica_s_id_kraken2/pathogen.k2db/` | `*.kraken2.report(.tsv)`, classified/unclassified reads |
| **BLAST** | `rica_s_id_blast` | `blastn` alignment | `tools/rica_s_id_blast/pathogen_references.fasta.blastdb` | `*.blastout.tab.6`, `*.blastout.tab.6.tsv` |
| **BWA** | `rica_s_id_bwa` | `bwa mem -x ont2d` | `tools/rica_s_id_bwa/all_pathogens.fasta` | `*.bwa.sam`, `*.bwa.sam.tsv` |
| **NGMLR** | `rica_s_id_ngmlr` | Long‑read mapping | `tools/rica_s_id_ngmlr/all_pathogens.fasta` | `*.ngmlr.sam`, `*.ngmlr.sam.tsv` |
| **CLARK** | `rica_s_id_clark` | k‑mer classification | `tools/rica_s_id_clark/` (build with `set_targets.sh`) | `*.clark.csv`, `*.clark.csv.tsv` |
| **CU‑CLARK** | `rica_s_id_cuclark` | GPU CLARK | `tools/rica_s_id_cuclark/` | `*.cuclark.csv`, `*.cuclark.csv.tsv` |
| **krakenuniq** | `rica_s_id_krakenuniq` | k‑mer + unique‑k‑mer counts | `tools/rica_s_id_krakenuniq/pathogen.kudb` | *(scaffolded; classify body currently disabled)* |
| **ganon2** | `rica_s_id_ganon2` | k‑mer classification | — | *(scaffolded / placeholder)* |

> **Status note.** `krakenuniq/classify.sh` and `ganon2/classify.sh` are scaffolded — their commands are present but commented out and they currently print `N/A`. minimap2, kraken2, BLAST, BWA, NGMLR, CLARK, and CU‑CLARK are the working classifiers. CLARK/CU‑CLARK require their databases (see the download step) and run `set_targets.sh` before classifying.

### Profiling (`pr`) — `rica_s_pr_abricate/profile.sh`
Runs **ABRicate** over the read file against a broad set of resistance and virulence databases and concatenates the hits into one TSV with a full header. Databases queried: `resfinder`, `victors`, `vfdb`, `upec_expec_vf`, `ecoli_vf`, `argannot`, `megares`, `plasmidfinder`, `card`, `ncbi`, `bacmet2`, `ecoh`. Output: `output/<runid>/<reads>.abricate.csv` (tab‑separated).

The companion `get_common_treatment.py` queries the bundled SQLite database `rica_s.db` to map an identified organism name to a suggested/common treatment:

```bash
python scripts/rica_s_pr_abricate/get_common_treatment.py "Escherichia coli"
```

> This maps organisms to treatments recorded in the local reference database and is **not** clinical guidance; treatment decisions must be made by a qualified clinician.

### Tooling (`tl`) — read simulators
`builder/tl/rica_s_tl_pbsim3.yml` (PBSIM3) and `rica_s_tl_tksm.yml` (TKSM) define containers for generating synthetic long reads used to build the test `datasets/` and `reads/`.
-->

## Output files

For a given run, all the output files are collected at `/opt/rica/output/<runid>/`:

```
output/<runid>/
├── <runid>.log                                  # combined stage log
├── rica_s_fl_minimap2/                          # filtering stage
│   ├── human_mapped_sequence_names.txt
│   ├── nonhuman_unmapped_sequence_names.txt
│   └── nonhuman_unmapped_sequence_names.fasta
├── <inputfile>.minimap2.[ paf|tsv|pdf|eps ]
├── <inputfile>.kraken2.[ report|tsv|pdf|eps ]
├── <inputfile>.blastout.tab.[ 6|tsv|pdf|eps ]
├── <inputfile>.bwa.[ sam|tsv|pdf|eps ]
├── <inputfile>.ngmlr.[ sam|tsv|pdf|eps ]
├── <inputfile>.[ clark|cuclark ].csv.[ csv|tsv|pdf|eps ]
└── <inputfile>.abricate.csv                         # profiling stage
```
<!-- 
The `.tsv` files are the normalized, comparable summaries (species vs. read count / identity). Use `scripts/histogram.py` to visualize the top hits:

```bash
python scripts/histogram.py output/<runid>/<reads>.kraken2.report.tsv
```

It reads a two‑column TSV, keeps the top 20 subjects by hit count, and renders a horizontal Plotly bar chart. (Requires `pandas` and `plotly`.) -->



---


## Notes and conventions

- **Naming.** Services, script directories, and containers all follow `rica_s_<stage>_<tool>`. The stage drivers discover work by globbing `rica_s_id_*` / `rica_s_pr_*`, so adding a new tool is as simple as adding its compose file, a script directory with a `classify.sh`/`profile.sh`, and bringing the container up.
- **Paths.** Inside containers the project is always `/opt/rica_s`; input read paths passed to the drivers must be absolute and container‑visible.
- **Compose structure.** `builder/rica_s-compose.yml` doesn't define services inline — it `extends` each per‑service file under `builder/<stage>/`. Images are pulled from `alkanlab/*` on Docker Hub; the `build.dockerfile_inline` blocks add common CLI tools (`samtools`, `seqtk`, `seqkit`, …) on top.
- **Git‑ignored data.** `16s/`, `amr/`, `datasets/`, `output/`, `reads/`, `reference_genomes/`, and `tools/` are excluded from version control (see `.gitignore`). They're populated by the download step and by pipeline runs.
- **Reproducibility.** Every classifier wraps its main command in `/usr/bin/time -v`, so per‑run resource usage (wall time, peak memory) is captured in the log for benchmarking.
- **Not for clinical use.** This is a research pipeline. Identifications and treatment mappings are for investigation and benchmarking, not diagnosis.
<!-- 
## Troubleshooting

- **`docker exec` fails / container not found** — confirm the stack is up (`docker ps | grep rica_s`) and that the container name matches the script directory name under `scripts/`.
- **A classifier can't find its database** — you likely skipped the download step; verify the expected DB exists under `tools/rica_s_id_<tool>/` (every classifier, including the alignment‑based minimap2/bwa/ngmlr, reads from its own `tools/` directory). `DownloadData.sh` extracts each tool's tar there automatically.
- **Nothing happens for a stage** — the drivers only act on containers that are actually running; bring up the relevant services first.
- **Permission errors writing `output/`** — ensure the host `/opt/rica_s` is writable by your user, since it's bind‑mounted read‑write into the containers.
- **Web UI can't reach Docker** — `orch.py`/`start.py` connect to the Docker daemon over TCP; adjust the socket/URL and the orchestrator's hardcoded paths to match your environment.
-->
## Authors and acknowledgements 


Developed by **Ricardo Roman‑Brenes** (Bilkent University, Alkan Lab).

The pipeline builds on excellent open‑source tools: **minimap2**, **kraken2**, **krakenuniq**, **BLAST**, **BWA**, **NGMLR**, **CLARK / CU‑CLARK**, **ganon**, **ABRicate** (and its bundled databases: ResFinder, CARD, NCBI AMRFinder, VFDB, MEGARes, ARG‑ANNOT, PlasmidFinder, and others), and the **PBSIM3** / **TKSM** long‑read simulators.
