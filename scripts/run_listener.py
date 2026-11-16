
from flask import Flask
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer
import os
import sys
import threading
import waitress
from pathlib import Path
from scripts.config import c
from scripts import run_state
import scripts.main_run as mr
import scripts.rica_s_ui_web.web_ui as ui
import subprocess
import logging
import subprocess


class NewFileHandler(FileSystemEventHandler):
    def __init__(self):
        super().__init__()

        self.started = set()

    def on_created(self, event):
        if not event.is_directory and event.src_path.endswith('.info'):
            path = os.path.realpath(event.src_path)
            if path in self.started:
                print(f"[i]> Ignoring duplicate event for {path}")
                return
            self.started.add(path)
            print(f"[i]> New file detected: {event.src_path}")
            print(f"[i]> === Starting run at {event.src_path}")
            mr.start_run(event.src_path)
            print(f"[i]> Run ended at {event.src_path} ===")


def mark_interrupted_runs(out_dir):
    """Nothing runs yet, so every unfinished run left on disk belongs to a dead process."""
    for run_dir in Path(out_dir).iterdir():
        runid = run_dir.name
        if not (run_dir / f"{runid}.info").is_file():
            continue

        status = run_dir / f"{runid}.status"
        state = status.read_text().strip() if status.exists() else None
        # no status file: it was queued and the watchdog will never pick it up again
        if state in ("started", None):
            status.write_text("interrupted\n")
            print(f"[i]> marked {runid} as interrupted (was {state or 'queued'})")

        for sub_status in run_dir.glob(f"{runid}_*/{runid}_*.status"):
            if (sub_status.stem == sub_status.parent.name
                    and sub_status.read_text().strip() == "started"):
                sub_status.write_text("interrupted\n")


def start_services(path_to_watch=c["OUT_DIR"]):
    mark_interrupted_runs(path_to_watch)
    run_state.listener_active = True

    event_handler = NewFileHandler()
    observer = Observer()
    observer.schedule(event_handler, path=path_to_watch, recursive=True)

    print(f"[i]> Starting Watchdog in background on: {path_to_watch}")
    observer.start()  # Automatically spawns a background thread

    try:
        print("[i]> Starting Flask in the main thread")
        print("[i]> go to: http://localhost:5000")
        ui.start_web_ui()

    except Exception as e:
        # Caught when you press Ctrl+C
        print(f"[e]> Shutting down, an unexpected error occurred: {e}")
    finally:
        # Ensure Watchdog stops cleanly when Flask exits
        observer.stop()
        observer.join()
        print("[i]> Shutdown complete.")


if __name__ == "__main__":
    print(f"[i]> rica_s starting ===\n")

    print(f"[i]> Awaiting jobs ===")
    start_services()

    print(f"[i]> rica_s stopped ===")
