
from flask import Flask
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer
import os
import sys
import threading
import waitress
from scripts.config import c
import scripts.main_run as mr
import scripts.rica_s_ui_web.web_ui as ui
import subprocess
import logging
import subprocess

class NewFileHandler(FileSystemEventHandler):
    def __init__(self):
        super().__init__()
        # watchdog can report a file in a freshly created dir twice
        # (real inotify event + simulated one), so remember what ran
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


def start_services(path_to_watch=c["OUT_DIR"]):

    event_handler = NewFileHandler()
    observer = Observer()
    observer.schedule(event_handler, path=path_to_watch, recursive=True)

    print(f"[i]> Starting Watchdog in background on: {path_to_watch}")
    observer.start()  # Automatically spawns a background thread

    try:
        print("[i]> Starting Flask in the main thread")
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
