import os
import subprocess
from config import DL_DIR, BASE_URL

def fetch_tar(urlpath, dest):
    tarname = os.path.basename(urlpath)
    tmp_dir = os.path.join(DL_DIR, "tmp")
    os.makedirs(dest, exist_ok=True)
    os.makedirs(tmp_dir, exist_ok=True)
    
    subprocess.run(["wget", "-nc", "-P", tmp_dir, f"{BASE_URL}/{urlpath}"], check=True)
    tar_path = os.path.join(tmp_dir, tarname)
    subprocess.run(["tar", "xf", tar_path, "-C", dest], check=True)
    os.remove(tar_path)

if __name__ == "__main__":
    print("=== downloading data ===")
    print("=== datasets ===")
    fetch_tar("datasets.tar", DL_DIR)
    
    print("=== db/index ===")
    tools = [
        ("tools/rica_s_bc_dorado.tar", "dorado DNA r10 model"),
        ("tools/rica_s_id_minimap2.tar", "minimap2"),
        ("tools/rica_s_id_kraken2.tar", "kraken2"),
        ("tools/rica_s_id_blast.tar", "blast"),
        ("tools/rica_s_id_bwa.tar", "bwa"),
        ("tools/rica_s_id_ngmlr.tar", "ngmlr"),
        ("tools/rica_s_id_clark.tar", "clark"),
        ("tools/rica_s_id_cuclark.tar", "cuclark")
    ]
    for url, desc in tools:
        print(f"=== {desc} ===")
        fetch_tar(url, os.path.join(DL_DIR, "tools"))
        
    print("=== finished ===")
