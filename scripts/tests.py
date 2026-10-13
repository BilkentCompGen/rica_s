from os import mkdir
from config import run_outdir
from pathlib import Path
import main_run as mr


def write_runinfo(readpath, runid, run_dir, info_path):

    tools_line = "tools\trica_s_id_blast,rica_s_id_bwa,rica_s_id_clark,rica_s_id_cuclark,rica_s_id_kraken2,rica_s_id_minimap2,rica_s_id_ngmlr,rica_s_pr_abricate\n"

    try:
        run_dir.mkdir(parents=True, exist_ok=True)
        pod5_filenames = sorted(p.name for p in Path(readpath).glob("*.pod5"))
        print(f"searching pod5s in {readpath}")
        print(f"Found {len(pod5_filenames)} POD5 files: {pod5_filenames}")
        info_path.write_text(
            f"runid\t{runid}\n"
            f"readpath\t{readpath}\n"
            f"pod5\t{','.join(pod5_filenames)}\n"
            + tools_line
        )
        print(f"Success: wrote {info_path}")

    except Exception:
        print(f"CRITICAL ERROR: {e}.")
    
    return

##################################################
# tests:


rps=[
    # "/opt/rica_s/input/donut/ricardo/opt/Icarust_docker/output/05B_0.001A_1H/", # done
    "/opt/rica_s/input/donut/ricardo/opt/Icarust_docker/output/15B_0.010A_2H/",
    "/opt/rica_s/input/donut/ricardo/opt/Icarust_docker/output/15B_0.001A_2H/",
    "/opt/rica_s/input/donut/ricardo/opt/Icarust_docker/output/05B_0.010A_1H/",
    # "/opt/rica_s/input/donut/ricardo/opt/Icarust_docker/output/10B_0.001A_2H/",
    # "/opt/rica_s/input/donut/ricardo/opt/Icarust_docker/output/15B_0.100A_2H/",
    # "/opt/rica_s/input/donut/ricardo/opt/Icarust_docker/output/10B_0.010A_2H/",
    # "/opt/rica_s/input/donut/ricardo/opt/Icarust_docker/output/05B_0.100A_1H/",
    # "/opt/rica_s/input/donut/ricardo/opt/Icarust_docker/output/05B_0.100A_2H/",
    # "/opt/rica_s/input/donut/ricardo/opt/Icarust_docker/output/10B_0.010A_1H/",
    # "/opt/rica_s/input/donut/ricardo/opt/Icarust_docker/output/15B_0.100A_1H/",
    # "/opt/rica_s/input/donut/ricardo/opt/Icarust_docker/output/10B_0.001A_1H/",
    # "/opt/rica_s/input/donut/ricardo/opt/Icarust_docker/output/05B_0.010A_2H/",
    # "/opt/rica_s/input/donut/ricardo/opt/Icarust_docker/output/10B_0.100A_1H/",
    # "/opt/rica_s/input/donut/ricardo/opt/Icarust_docker/output/15B_0.001A_1H/",
    # "/opt/rica_s/input/donut/ricardo/opt/Icarust_docker/output/15B_0.010A_1H/",
    # "/opt/rica_s/input/donut/ricardo/opt/Icarust_docker/output/05B_0.001A_2H/"
]


ris=[
    # "05B_0.001A_1H", # done
    "15B_0.010A_2H",
    "15B_0.001A_2H",
    "05B_0.010A_1H",
    # "10B_0.001A_2H",
    # "15B_0.100A_2H",
    # "10B_0.010A_2H",
    # "05B_0.100A_1H",
    # "05B_0.100A_2H",
    # "10B_0.010A_1H",
    # "15B_0.100A_1H",
    # "10B_0.001A_1H",
    # "05B_0.010A_2H",
    # "10B_0.100A_1H",
    # "15B_0.001A_1H",
    # "15B_0.010A_1H",
    # "05B_0.001A_2H"
]

for i in range(len(rps)):
    rp = rps[i]
    ri = ris[i]
    rd = Path(run_outdir(ri))
    ip = rd / f"{ri}.info"

    write_runinfo(rp, ri, rd, ip)
    mr.start_run(ip)

