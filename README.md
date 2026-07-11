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

## Requirements

- A Linux host (the pipeline uses Linux containers and `docker exec`). Sufficient CPU cores and RAM for the classifiers; alignment against the human genome and pathogen references is the heaviest step.
- **Disk space** for reference genomes and prebuilt databases (BLAST, kraken2, krakenuniq, minimap2, ABRicate). These can be large (tens of GB), and are **not** stored in git (they live under git‑ignored directories such as `tools/`, `reference_genomes/`, `datasets/`, `reads/`).
- A modern CUDA-enable device, if the GPU-enable classifiers are to be used (i.e. cuCLARK).
- Network access to the data host (`donut.cs.bilkent.edu.tr` over HTTP) to download reference data and databases.
- **Docker** and the **Docker Compose** plugin (`docker compose`, v2 syntax).
- NVIDIA Container Toolkit.
- The prebuilt images are published under the Docker Hub org **`alkanlab/`** (e.g. `alkanlab/rica_s_id_kraken2:v1.1`). Docker will pull them automatically on first `up`.

## Installation

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

It fetches, via `wget` over HTTP:

- `16s/` — 16S rRNA reference sequences
- `amr/` — antimicrobial‑resistance references
- `datasets/` — test datasets
- `reads/` — simulated reads
- `reference_genomes/` — pathogen reference genomes (including the joint `all_pathogens.fasta` / `all_pathogens.mmi`)
- Prebuilt tool databases under `tools/`: `rica_s_id_blast/`, `rica_s_id_kraken2/`, `rica_s_id_krakenuniq/`, `rica_s_id_minimap2/`, and `rica_s_pr_abricate/`.

The CLARK / CU‑CLARK / Metabuli database downloads are present but commented out; uncomment them if you plan to run those classifiers.

## Running the pipeline

Each stage driver takes a **run id** and an **absolute path to the input reads** (the path must resolve inside the containers, i.e. under `/opt/rica_s/...`). Run the three stages in order.

```bash
cd /opt/rica_s

RUNID=test_run_01
READS=/opt/rica_s/datasets/_1/dataset_5120reads.fasta   # absolute, container‑visible path

# 1) Filter out human reads
bash scripts/_1AllFilter.sh   "$RUNID" "$READS"

# 2) Classify the (filtered) reads with every id_* tool
#    Typically point this at the non‑human reads from step 1:
FILTERED=/opt/rica_s/output/$RUNID/rica_s_fl_minimap2/nonhuman_unmapped_sequence_names.fasta
bash scripts/_2AllClassify.sh "$RUNID" "$FILTERED"

# 3) Profile for AMR / virulence genes
bash scripts/_3AllProfile.sh  "$RUNID" "$FILTERED"
```

What each driver does:

- **`_1AllFilter.sh <runid> <inputfile>`** — creates `output/<runid>/`, then `docker exec`s into `rica_s_id_minimap2` and runs `filterHumanDna.sh`. Output non‑human reads land in `output/<runid>/rica_s_fl_minimap2/`.
- **`_2AllClassify.sh <runid> <inputfile>`** — loops over every directory matching `rica_s_id_*` under `scripts/`, and for each runs `docker exec -it <container> <script>/classify.sh <inputfile> /opt/rica_s/output/<runid>/`.
- **`_3AllProfile.sh <runid> <inputfile>`** — loops over every `rica_s_pr_*` and runs its `profile.sh` the same way.

All three tee their output to `output/<runid>/<runid>.log`.

> **Tip.** The drivers run *whatever* `rica_s_id_*` / `rica_s_pr_*` containers exist. To run only a subset of classifiers, bring up only those services, or invoke a single tool's `classify.sh` directly with `docker exec`.

## Stage and tool reference

### Filtering — `rica_s_id_minimap2/filterHumanDna.sh`
Aligns reads to the human reference index `tools/rica_s_id_minimap2/human_dna_db/human_v38.mmi` with `minimap2 -a`, then uses `samtools` to split mapped (human) vs. unmapped (non‑human) read names and `seqtk subseq` to extract the non‑human reads. Produces, in `output/<runid>/rica_s_fl_minimap2/`:
- `human_mapped_sequence_names.txt`
- `nonhuman_unmapped_sequence_names.txt`
- `nonhuman_unmapped_sequence_names.fasta` ← the input for classification.

### Identification (`id`) classifiers
All classify against the curated pathogen database and emit a normalized two‑column `.tsv` (species vs. read count / identity) that downstream tooling can plot.

| Tool | Container | Method | Reference / DB | Key outputs |
|------|-----------|--------|----------------|-------------|
| **minimap2** | `rica_s_id_minimap2` | Long‑read mapping (`map-ont`) | `reference_genomes/joint/all_pathogens.mmi` | `*.minimap2.paf`, `*.minimap2.paf.tsv` |
| **kraken2** | `rica_s_id_kraken2` | k‑mer classification | `tools/rica_s_id_kraken2/pathogen.k2db/` | `*.kraken2.report(.tsv)`, classified/unclassified reads |
| **BLAST** | `rica_s_id_blast` | `blastn` alignment | `tools/rica_s_id_blast/pathogen_references.fasta.blastdb` | `*.blastout.tab.6`, `*.blastout.tab.6.tsv` |
| **BWA** | `rica_s_id_bwa` | `bwa mem -x ont2d` | `reference_genomes/joint/all_pathogens.fasta` | `*.bwa.sam`, `*.bwa.sam.tsv` |
| **NGMLR** | `rica_s_id_ngmlr` | Long‑read mapping | `reference_genomes/joint/all_pathogens.fasta` | `*.ngmlr.sam`, `*.ngmlr.sam.tsv` |
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

## Output files

For a given run, everything lands under `output/<runid>/`:

```
output/<runid>/
├── <runid>.log                                  # combined stage log
├── rica_s_fl_minimap2/                          # filtering stage
│   ├── human_mapped_sequence_names.txt
│   ├── nonhuman_unmapped_sequence_names.txt
│   └── nonhuman_unmapped_sequence_names.fasta
├── <reads>.minimap2.paf(.tsv)                   # per‑classifier raw + normalized
├── <reads>.kraken2.report(.tsv) + classified/unclassified
├── <reads>.blastout.tab.6(.tsv)
├── <reads>.bwa.sam(.tsv)
├── <reads>.ngmlr.sam(.tsv)
├── <reads>.clark.csv(.tsv) / .cuclark.csv(.tsv)
└── <reads>.abricate.csv                         # profiling stage
```

The `.tsv` files are the normalized, comparable summaries (species vs. read count / identity). Use `scripts/histogram.py` to visualize the top hits:

```bash
python scripts/histogram.py output/<runid>/<reads>.kraken2.report.tsv
```

It reads a two‑column TSV, keeps the top 20 subjects by hit count, and renders a horizontal Plotly bar chart. (Requires `pandas` and `plotly`.)

## Web UI

A small Flask app (`scripts/rica_s_ui_web/`) provides a browser front end, served by the `rica_s_ui_web` container on **port 5000** at the static address `172.20.0.10` on the `rica_s_net` bridge network.

- **`start.py`** — routes: `/` (build a run: pick stages/tools and the read path), `/submitted` (POST handler that generates a timestamp `run_id` and calls the orchestrator), and a report route that renders `output/runs/<id>/report.html`.
- **`orch.py`** — talks to the Docker daemon via the Docker SDK and executes each identification container's script for the submitted run.
- **`run.sh`** — launches Flask: `flask --app start run --host=0.0.0.0 --debug`.
- **`templates/`** — `start.html`, `submitted.html`, `report.html`.

Once the stack is up, open **http://localhost:5000/**.

> The web UI is a research prototype; the orchestrator paths (`/rica_s/...`) and the Docker socket address are wired for the developer's environment and may need adjusting to match your `/opt/rica_s` mount and Docker daemon configuration.

## Utility and misc scripts

Under `scripts/misc/` are one‑off helpers used to build the 16S and AMR reference material (not part of the routine run path):

- `Download16SSeq.sh`, `NameToAccession16S.sh`, `download_fromname.sh` — fetch 16S sequences by name/accession.
- `FastaStandarizer.sh` — normalize FASTA headers.
- `acc2taxid.sh`, `add_taxid_to_fasta.py` — annotate sequences with NCBI taxonomy IDs.
- `renamer_sd2spp.py` — rename records from strain designation to species.
- `histogram.py`, `rlhist.py` — plotting helpers (read‑length / hit histograms).

And under the minimap2 script directory:

- `scripts/rica_s_id_minimap2/CreateFastaIndexFromDir.sh <dir>` — recursively builds a minimap2 `.mmi` index for every `.fasta`/`.fa` under a directory.

## Notes and conventions

- **Naming.** Services, script directories, and containers all follow `rica_s_<stage>_<tool>`. The stage drivers discover work by globbing `rica_s_id_*` / `rica_s_pr_*`, so adding a new tool is as simple as adding its compose file, a script directory with a `classify.sh`/`profile.sh`, and bringing the container up.
- **Paths.** Inside containers the project is always `/opt/rica_s`; input read paths passed to the drivers must be absolute and container‑visible.
- **Compose structure.** `builder/rica_s-compose.yml` doesn't define services inline — it `extends` each per‑service file under `builder/<stage>/`. Images are pulled from `alkanlab/*` on Docker Hub; the `build.dockerfile_inline` blocks add common CLI tools (`samtools`, `seqtk`, `seqkit`, …) on top.
- **Git‑ignored data.** `16s/`, `amr/`, `datasets/`, `output/`, `reads/`, `reference_genomes/`, and `tools/` are excluded from version control (see `.gitignore`). They're populated by the download step and by pipeline runs.
- **Reproducibility.** Every classifier wraps its main command in `/usr/bin/time -v`, so per‑run resource usage (wall time, peak memory) is captured in the log for benchmarking.
- **Not for clinical use.** This is a research pipeline. Identifications and treatment mappings are for investigation and benchmarking, not diagnosis.

## Troubleshooting

- **`docker exec` fails / container not found** — confirm the stack is up (`docker ps | grep rica_s`) and that the container name matches the script directory name under `scripts/`.
- **A classifier can't find its database** — you likely skipped or misconfigured the download step; verify the expected DB exists under `tools/<tool>/` (and `reference_genomes/joint/` for alignment‑based tools). Remember to set `DL_DIR` in `DownloadData.sh`.
- **Nothing happens for a stage** — the drivers only act on containers that are actually running; bring up the relevant services first.
- **Permission errors writing `output/`** — ensure the host `/opt/rica_s` is writable by your user, since it's bind‑mounted read‑write into the containers.
- **Web UI can't reach Docker** — `orch.py`/`start.py` connect to the Docker daemon over TCP; adjust the socket/URL and the orchestrator's hardcoded paths to match your environment.

## Authors and acknowledgements

Developed by **Ricardo Roman‑Brenes** (Bilkent University, Alkan Lab).

The pipeline builds on excellent open‑source tools: **minimap2**, **kraken2**, **krakenuniq**, **BLAST**, **BWA**, **NGMLR**, **CLARK / CU‑CLARK**, **ganon**, **ABRicate** (and its bundled databases: ResFinder, CARD, NCBI AMRFinder, VFDB, MEGARes, ARG‑ANNOT, PlasmidFinder, and others), and the **PBSIM3** / **TKSM** long‑read simulators.
