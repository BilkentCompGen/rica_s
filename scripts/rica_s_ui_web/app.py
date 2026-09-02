import pandas as pd
from flask import Flask, render_template, request, jsonify
from pathlib import Path

app = Flask(__name__)

# ==========================================
# Helper Functions
# ==========================================

def parse_summary_file(filepath: Path):
    """Reads the '---' separated text file and returns a list of dictionaries."""
    if not filepath.exists():
        return []

    parsed_data = []
    raw_text = filepath.read_text(encoding='utf-8')

    # Split the text by the "---" delimiter
    for section in raw_text.split("---"):
        section = section.strip()
        if not section: 
            continue
            
        lines = section.split('\n')
        header = lines[0].strip()
        
        # Extract key-value pairs
        section_data = {}
        for line in lines[1:]:
            if ":" in line:
                key, value = line.split(":", 1)
                section_data[key.strip()] = value.strip()
                
        parsed_data.append({
            'header': header,
            'rows': section_data
        })
        
    return parsed_data

def get_run_status(runid: str):
    """Fetches the status from the run's .status file."""
    status_file = Path(f"/opt/rica_s/output/{runid}/{runid}.status")
    
    if status_file.exists():
        return status_file.read_text(encoding='utf-8').strip()
    return "no run ID"

def get_log_text(runid: str):
    """Fetches the status from the run's .status file."""
    log_file = Path(f"/opt/rica_s/output/{runid}/{runid}.log")
    
    if log_file.exists():
        return log_file.read_text(encoding='utf-8')
    return "no log found"

def process_csv_data(output_dir: Path):
    """Finds and formats AMR CSV files into HTML tables."""
    csv_data = []
    columns_to_keep = [
        'GENE', '%COVERAGE', '%IDENTITY', 'PRODUCT',
        'RESISTANCE', 'DATABASE', 'ACCESSION', '#FILE', 'SEQUENCE'
    ]
    
    for index, file_path in enumerate(output_dir.glob("*.abricate.csv")):
        try:
            df = pd.read_csv(file_path, sep="\t")
            df = df[columns_to_keep]
            
            # Use <br> so the line breaks render correctly in the browser
            df['RESISTANCE'] = df['RESISTANCE'].str.replace(';', '<br>', regex=False)
            df['PRODUCT'] = df['PRODUCT'].str.replace(':', '<br>', regex=False)
            
            table_html = df.to_html(
                classes="display compact data-table", 
                table_id=f"csvDataTable_{index}", 
                index=False, 
                escape=False
            )
            
            csv_data.append({'filename': file_path.name, 'table_html': table_html})
        except Exception as e:
            csv_data.append({'filename': file_path.name, 'error': str(e)})
            
    return csv_data

def process_pathogen_htmls(output_dir: Path):
    """Finds and injects CSS into pathogen HTML report files."""
    pathogen_data = []
    style_injection = "<style>body { margin: 0 !important; padding: 0 !important; overflow: hidden !important; }</style>"
    
    # Sort files and filter out the final report to prevent recursive loops
    html_files = sorted(output_dir.glob("*.html"))
    html_files = [f for f in html_files if "final_report." not in f.name]

    for file_path in html_files:
        raw_html = file_path.read_text(encoding='utf-8')

        # Inject CSS to remove the default 8px body margin inside the Plotly HTML
        if "<head>" in raw_html:
            raw_html = raw_html.replace("<head>", f"<head>{style_injection}")
        else:
            raw_html = style_injection + raw_html

        pathogen_data.append({'filename': file_path.name, 'raw_html': raw_html})
        
    return pathogen_data

# ==========================================
# Flask Routes
# ==========================================

@app.route('/status')
def status_page():
    return render_template('status.html')

@app.route('/check_status', methods=['GET'])
def api_check_status():
    runid = request.args.get('runid')
    if not runid:
        return jsonify({"error": "No Run ID provided"}), 400

    return jsonify({
        "runid": runid,
        "is_running": get_run_status(runid)
    })

@app.route('/report/<runid>')
def generate_report(runid):
    output_dir = Path(f"/opt/rica_s/output/{runid}/")

    # 1. Process the Log File
    log_text = get_log_text(runid)
    
    # 2. Process CSV Data
    csv_data = process_csv_data(output_dir)

    # 3. Process Pathogen HTML Files
    pathogen_data = process_pathogen_htmls(output_dir)

    # 4. Process Summary Text File
    summary_data = parse_summary_file(output_dir / f"{runid}.summary")

    # Render Template
    return render_template(
        'report.html',
        runid=runid,
        summary_data=summary_data,
        log_text=log_text,
        csv_data=csv_data,
        pathogen_data=pathogen_data
    )

if __name__ == '__main__':
    # Run the Flask app on all interfaces at port 5000
    app.run(host='0.0.0.0', port=5000, debug=True)