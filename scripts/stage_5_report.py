import os
import glob
import pandas as pd
import html
import sys
import logging
from scripts.config import run_outdir
import datetime
logger = logging.getLogger(__name__)


def all_report(runid, parent=None):


    logger.info("[i]> Begin of reporting stage")
    logger.info(datetime.datetime.now())


    logger.info(f"[i]> building ===")

    # Consolidate the base directory logic
    output_dir = run_outdir(runid, parent)
    LOG_FILE = os.path.join(output_dir, f"{runid}.log")
    AMR_CSV_PATTERN = os.path.join(output_dir, "*.abricate.csv")
    OUTPUT_HTML = os.path.join(output_dir, f"{runid}_final_report.html")

    # 1. Process the Log File (txt)
    try:
        with open(LOG_FILE, 'r') as f:
            log_text = f.read()
        log_content = f"<pre>{html.escape(log_text)}</pre>"
    except FileNotFoundError:
        log_content = "<p>Log file not found.</p>"

    # 2. Process ALL CSV Data 
    # FIX: Use the specific AMR_CSV pattern, not just "*.csv"
    amr_content = ""
    csv_files = glob.glob(AMR_CSV_PATTERN)
    
    if not csv_files:
        amr_content = "<p>No CSV files found matching the pattern.</p>"
    else:
        for index, file in enumerate(csv_files):
            try:
                df = pd.read_csv(file, sep="\t")
                df = df[['GENE', '%COVERAGE', '%IDENTITY','PRODUCT', 'RESISTANCE', 'DATABASE', 'ACCESSION', '#FILE', 'SEQUENCE' ]]

                # Ensure unique IDs for every table generated
                table_id = f"csvDataTable_{index}"
                
                amr_content += f"""
                <div class="csv-section" style="margin-bottom: 40px;">
                    <h3>Source: {os.path.basename(file)}</h3>
                    {df.to_html(classes="display compact data-table", table_id=table_id, index=False, escape=False)}
                </div>
                """
            except Exception as e:
                amr_content += f"<p>Error loading {file}: {e}</p>"

    # 3. Aggregate Pathogen HTML Files (SANDBOXED)
    pathogen_content = ""
    
    # FIX: Get all HTML files but EXCLUDE the output report itself to prevent infinite loops
    all_html_files = glob.glob(os.path.join(output_dir, "*.html"))
    html_files = [f for f in all_html_files if os.path.abspath(f) != os.path.abspath(OUTPUT_HTML)]
    
    if not html_files:
        pathogen_content = "<p>No HTML files found in the specified directory.</p>"
    else:
        html_files.sort()
        for filepath in html_files:
            filename = os.path.basename(filepath)
            with open(filepath, 'r', encoding='utf-8') as f:
                raw_html = f.read()
            
            safe_srcdoc = html.escape(raw_html)
            
            pathogen_content += f"""
            <div class="aggregated-section">
                <h3>Source: {filename}</h3>
                <iframe srcdoc="{safe_srcdoc}" width="100%" height="800px" style="border: 1px solid #ccc; border-radius: 5px; background: #fff;"></iframe>
            </div>
            <hr>
            """

    # 4. Define the HTML Template
    html_template = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>Analysis Report: {runid}</title>
        
        <!-- jQuery and DataTables Libraries -->
        <script src="https://code.jquery.com/jquery-3.7.1.min.js"></script>
        <link rel="stylesheet" href="https://cdn.datatables.net/1.13.6/css/jquery.dataTables.min.css">
        <script src="https://cdn.datatables.net/1.13.6/js/jquery.dataTables.min.js"></script>

        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; margin: 0; padding: 20px; background-color: #f8f9fa; }}
            .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }}
            
            /* Tab CSS */
            .tab {{ overflow: hidden; border-bottom: 1px solid #ccc; background-color: #f1f1f1; border-radius: 6px 6px 0 0; }}
            .tab button {{ background-color: inherit; float: left; border: none; outline: none; cursor: pointer; padding: 14px 24px; transition: 0.3s; font-size: 16px; font-weight: bold; color: #555; }}
            .tab button:hover {{ background-color: #ddd; }}
            .tab button.active {{ background-color: #fff; border: 1px solid #ccc; border-bottom: none; color: #000; }}
            
            .tabcontent {{ display: none; padding: 20px; border: 1px solid #ccc; border-top: none; background: #fff; border-radius: 0 0 6px 6px; }}
            
            /* Log Formatting */
            pre {{ background: #1e1e1e; color: #d4d4d4; padding: 15px; border-radius: 5px; overflow-x: auto; white-space: pre-wrap; word-wrap: break-word; }}
            
            /* Misc Spacing */
            .aggregated-section {{ margin-bottom: 30px; }}
            .aggregated-section h3, .csv-section h3 {{ color: #333; }}
            .dataTables_wrapper {{ margin-top: 15px; }}
        </style>
    </head>
    <body>

        <div class="container">
            <h2>Analysis Dashboard: {runid}</h2>
            
            <!-- Tab Links -->
            <div class="tab">
                <button class="tablinks" onclick="openTab(event, 'LogTab')" id="defaultOpen">System Log</button>
                <button class="tablinks" onclick="openTab(event, 'CSVTab')">CSV Data</button>
                <button class="tablinks" onclick="openTab(event, 'PathogenTab')">Pathogen Presence</button>
            </div>

            <!-- Tab Content -->
            <div id="LogTab" class="tabcontent">
                {log_content}
            </div>

            <div id="CSVTab" class="tabcontent">
                {amr_content}
            </div>

            <div id="PathogenTab" class="tabcontent">
                {pathogen_content}
            </div>
        </div>

        <script>
            function openTab(evt, tabName) {{
                var i, tabcontent, tablinks;
                
                // Hide all tabs
                tabcontent = document.getElementsByClassName("tabcontent");
                for (i = 0; i < tabcontent.length; i++) {{
                    tabcontent[i].style.display = "none";
                }}
                
                // Remove active class
                tablinks = document.getElementsByClassName("tablinks");
                for (i = 0; i < tablinks.length; i++) {{
                    tablinks[i].className = tablinks[i].className.replace(" active", "");
                }}
                
                // Show current tab
                document.getElementById(tabName).style.display = "block";
                evt.currentTarget.className += " active";
                
                // Adjust all DataTables when the CSV tab is opened to prevent squished columns
                if (tabName === 'CSVTab') {{
                    $.fn.dataTable.tables({{ visible: true, api: true }}).columns.adjust();
                }}
            }}
            
            // Initialize DataTables strictly on our dynamically generated tables
            $(document).ready(function() {{
                $('.data-table').DataTable({{
                    "pageLength": 25,
                    "order": [],
                    "scrollX": true,
                    "destroy": true
                }});
            }});
            
            // Open the default tab
            document.getElementById("defaultOpen").click();
        </script>
    </body>
    </html>
    """

    with open(OUTPUT_HTML, 'w', encoding='utf-8') as f:
        f.write(html_template)
    
    logger.info(f"Success! Report generated at: {OUTPUT_HTML}")

    logger.info(f"[i]> === building")

    logger.info(datetime.datetime.now())
    logger.info("[i]> End of reporting stage")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 -m scripts.stage_5_report <runid> [parent]")
        sys.exit(1)
    all_report(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)