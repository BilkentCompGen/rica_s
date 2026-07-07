#!/usr/bin/env python3
import re
import sys
import os

if len(sys.argv) < 2:
    print("Hold up, ese. Usage: python3 parse_strace_to_dot.py <syscalls.log>")
    sys.exit(1)

log_file = sys.argv[1]
out_dot = "strace_flow.dot"

# Grab the whole array block from execve
pattern = re.compile(r'\d+\s+execve\("[^"]+",\s*\[(.*?)\]')

flow = []
seen = set()

print(f"[*] Sweeping the streets in {log_file}...")

with open(log_file, 'r') as f:
    for line in f:
        match = pattern.search(line)
        if match:
            raw_args = match.group(1)
            
            # The street upgrade: purely extract text inside quotes, ignores commas completely
            args = re.findall(r'"([^"]+)"', raw_args)
            
            if not args:
                continue
                
            cmd = os.path.basename(args[0])
            
            # If it's an interpreter, look for the actual script name, skipping flags like '-c'
            if cmd in ['python', 'python3', 'bash', 'sh', 'time', 'awk'] and len(args) > 1:
                for a in args[1:]:
                    if not a.startswith('-'):
                        cmd = os.path.basename(a)
                        break
            
            # THE FIX: Scrub the name clean so Graphviz never chokes
            # Replaces anything that isn't a letter, number, underscore, dot, or dash with an underscore
            clean_cmd = re.sub(r'[^A-Za-z0-9_.-]', '_', cmd)
            
            # Keep the graph clean: only log unique steps in order
            if clean_cmd and clean_cmd not in seen:
                flow.append(clean_cmd)
                seen.add(clean_cmd)

print(f"[*] Found {len(flow)} unique execution steps. Building the graph map...")

# Write the custom dark-themed Graphviz file
with open(out_dot, 'w') as f:
    f.write('digraph Execution_Flow {\n')
    f.write('  graph [bgcolor="#1e1e1e", fontcolor="white", rankdir="LR", pad="0.5"];\n')
    f.write('  node [style=filled, fillcolor="#005f87", fontcolor="white", shape=box, fontname="Courier New", penwidth=0];\n')
    f.write('  edge [color="#00ff00", penwidth=2];\n\n')
    
    for i in range(len(flow)-1):
        f.write(f'  "{flow[i]}" -> "{flow[i+1]}";\n')
        
    f.write('}\n')

print(f"[*] ¡Ya estuvo! Graph blueprint saved to {out_dot}")