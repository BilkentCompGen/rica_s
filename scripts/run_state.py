"""
In-process state shared by the pipeline (main_run) and the web UI (web_ui).

Lets the web UI tell a run that is really being processed from one whose status file
still says "started" because the process running it died.
"""

# True only when the pipeline listener runs in this process (scripts.run_listener);
# a standalone web UI cannot see the pipeline and must trust the status files
listener_active = False

# run IDs that start_run is processing right now
active_runs = set()
