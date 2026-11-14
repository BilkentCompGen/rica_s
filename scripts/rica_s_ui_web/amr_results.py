"""
AMR result files of one sub-run, read into rows shaped like the ABRicate table.

Shared by the web report and the run-wide merge in main_run, so both see the same
tools and columns. Kept free of Flask so main_run can import it.
"""
import csv
from pathlib import Path

from scripts.tool_registry import display_name
from scripts.rica_s_ui_web import leasyarg

AMR_COLUMNS = [
    'GENE', '%COVERAGE', '%IDENTITY', 'PRODUCT',
    'RESISTANCE', 'DATABASE', 'ACCESSION', '#FILE', 'SEQUENCE'
]


def abricate_rows(file_path: Path):
    with open(file_path, newline='', encoding='utf-8') as handle:
        reader = csv.DictReader(handle, delimiter='\t')

        missing = [c for c in AMR_COLUMNS
                   if c not in (reader.fieldnames or [])]
        if missing:
            raise KeyError("missing columns: " + ", ".join(missing))

        # one header per database run can be concatenated into the file
        return [[row.get(column) or "" for column in AMR_COLUMNS]
                for row in reader if row.get('#FILE') != '#FILE']


# hits from these databases are mobile genetic elements, everything else is AMR
MOBILE_DATABASES = {"mobileOG", "plasmidfinder"}


def amr_counts(tagged_rows, files):
    """Summary rows for (tool, AMR_COLUMNS row) hits loaded from the given files."""
    gene_i, db_i, seq_i = (AMR_COLUMNS.index(c)
                           for c in ('GENE', 'DATABASE', 'SEQUENCE'))
    genes = {False: set(), True: set()}
    hits = {False: set(), True: set()}
    db_genes = {}
    for _tool, row in tagged_rows:
        mobile = row[db_i] in MOBILE_DATABASES
        genes[mobile].add(row[gene_i])
        hits[mobile].add((row[gene_i], row[seq_i]))
        db_genes.setdefault(row[db_i] or "?", set()).add(row[gene_i])

    tools = list(dict.fromkeys(tool for tool, _name in files))
    return {
        "AMR genes detected": len(genes[False]),
        "AMR hits (reads)": len(hits[False]),
        "Mobile genetic elements detected": len(genes[True]),
        "MGE hits (reads)": len(hits[True]),
        "Sources": f"{len(tools)} tool{'s' if len(tools) != 1 else ''} "
                   f"({', '.join(tools)}), {len(files)} file{'s' if len(files) != 1 else ''}",
        "Databases": ", ".join(f"{db}: {len(g)}" for db, g in sorted(db_genes.items()))
                     or "none with hits",
    }


def amr_sources(run_dir: Path):
    """(tool, file name, rows loader) for every AMR result file in one sub-run dir."""
    sources = [(display_name("rica_s_pr_abricate"), path.name,
                lambda p=path: abricate_rows(p))
               for path in sorted(run_dir.glob("*.abricate.csv"))]
    sources += [(display_name("rica_s_pr_l-easyarg"), name, load)
                for name, load in leasyarg.result_rows(run_dir)]
    return sources
