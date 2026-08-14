#!/usr/bin/env bash
# template_builder.sh

# Function to generate the dynamic HTML
# Usage: build_dynamic_html "output_file.html" "Tab 1 Name" "file1.txt" "Tab 2 Name" "file2.txt" ...
build_dynamic_html() {
    local output_file="$1"
    shift # Shift the first argument out so we are left with just the tab/file pairs

    echo "[i]> Building dynamic report: $output_file"

    # 1. Start the HTML and open the tab menu
    cat << 'EOF' > "$output_file"
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>RICAS Dynamic Report</title>
    <link rel="stylesheet" href="style.css">
</head>
<body>

    <!-- Tab Bar -->
    <div class="tab-menu">
EOF

    # 2. Loop through the arguments to build the Tab Buttons
    # We step by 2 because args are in pairs: Title -> File
    local args=("$@")
    local count=0

    for (( i=0; i<${#args[@]}; i+=2 )); do
        local tab_title="${args[$i]}"
        local active_class=""
        
        # Make the first tab active by default
        if [ $count -eq 0 ]; then
            active_class="active"
        fi
        
        # Inject the button HTML
        echo "        <button class=\"tab-button $active_class\" onclick=\"switchTab(event, 'tab${count}')\">${tab_title}</button>" >> "$output_file"
        ((count++))
    done

    echo "    </div>" >> "$output_file"

    # 3. Loop through the arguments AGAIN to build the Tab Contents
    count=0
    for (( i=0; i<${#args[@]}; i+=2 )); do
        local file_path="${args[$i+1]}"
        local active_class=""
        
        if [ $count -eq 0 ]; then
            active_class="active"
        fi
        
        echo "    <!-- Tab Content for ${args[$i]} -->" >> "$output_file"
        echo "    <div id=\"tab${count}\" class=\"tab-content ${active_class}\">" >> "$output_file"
        
        # Check if the file exists before cat-ing, so we don't break the build, ese
        if [ -f "$file_path" ]; then
            cat "$file_path" >> "$output_file"
        else
            echo "        <p><i>Warning: Data file not found at ${file_path}</i></p>" >> "$output_file"
        fi
        
        echo "    </div>" >> "$output_file"
        ((count++))
    done

    # 4. Inject the JavaScript and close it out
    cat << 'EOF' >> "$output_file"
    <!-- Script to handle tab toggling -->
    <script>
        function switchTab(event, tabId) {
            const contents = document.querySelectorAll('.tab-content');
            contents.forEach(content => content.style.display = 'none');

            const buttons = document.querySelectorAll('.tab-button');
            buttons.forEach(button => button.classList.remove('active'));

            document.getElementById(tabId).style.display = 'block';
            event.currentTarget.classList.add('active');
        }
        
        // Force default visibility on init
        document.getElementById('tab0').style.display = 'block';
    </script>
</body>
</html>
EOF

    echo "[i]> Success! Created dynamic HTML with $count tabs."
}

# ==========================================
# HOW TO USE IT IN YOUR MAIN SCRIPT
# ==========================================

# Let's say you just generated your pieces:

projecthome="/opt/rica_s"
runid="RUN_001"
report_dir="$projecthome/output/$runid/report"

# (Assume you already generated style.css, plots.html, amr.html, and log.html here)

# Now, you just call the function and pass the pairs!
# Add 3 tabs, 5 tabs, 10 tabs — the function handles it.
build_dynamic_html \
	"$report_dir/index.html" \
    "Plots & Viz" "$report_dir/plots.html" \
    "AMR Data"    "$report_dir/amr.html" \
    "Raw Logs"    "$report_dir/log.html" \
    "Virulence"   "$report_dir/virulence.html" # You can just keep adding lines!
