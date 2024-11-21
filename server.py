from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
import os
import re
import json
from datetime import datetime
import time

app = Flask(__name__)
CORS(app)

CACHE_FILE = 'cache.json'

if os.path.exists(CACHE_FILE): 
    os.remove(CACHE_FILE) # Clear cache when starting program

def load_cache():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, 'r') as f:
            return json.load(f)
    return {'files': {}, 'order': []}

def save_cache(cache):
    with open(CACHE_FILE, 'w') as f:
        json.dump(cache, f)

def parse_file(file_path, earnings_report_regex, wallet_balance_regex, bandwidth_regex, start_line=0):
    salad_data = []
    with open(file_path, 'r') as f:
        content = f.readlines()[start_line:]
        
        for match in earnings_report_regex.finditer(''.join(content)):
            salad_data.append({
                'timestamp': match.group(1),
                'earnings': float(match.group(2)),
                'containerId': match.group(3)
            })
        
        for match in wallet_balance_regex.finditer(''.join(content)):
            salad_data.append({
                'timestamp': match.group(1),
                'currentBalance': float(match.group(2)),
                'predictedBalance': float(match.group(3))
            })
        
        if "Bandwidth-SGS-" in file_path:
            for match in bandwidth_regex.finditer(''.join(content)):
                salad_data.append({
                    'timestamp': match.group(1),
                    'BidirThroughput': float(match.group(2)) / (250000*30)  # Convert from bits per 30s to MB/s
                })
    
    return salad_data, len(content)

def read_log_files(log_dir):
    start_time = time.perf_counter()
    salad_data = []
    earnings_report_regex = re.compile(r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3} -\d{2}:\d{2}) \[INF\] Predicted Earnings Report: ([\d.]+) from \(([^)]+)\)")
    wallet_balance_regex = re.compile(r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3} -\d{2}:\d{2}) \[INF\] Wallet: Current\(([\d.]+)\), Predicted\(([\d.]+)\)")
    bandwidth_regex = re.compile(r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3} -\d{2}:\d{2}) \[INF\] .*?\"BidirThroughput\":([\d.]+)")

    cache = load_cache()
    files = []

    for root, _, filenames in os.walk(log_dir):
        for file in filenames:
            if file.endswith('.txt') or file.endswith('.log'):
                file_path = os.path.join(root, file)
                files.append(file_path)
            elif os.path.isdir(os.path.join(root, file)) and file.startswith('Bandwidth-SGS-'):
                for subfile in os.listdir(os.path.join(root, file)):
                    subfile_path = os.path.join(root, file, subfile)
                    if subfile.endswith('.txt') or subfile.endswith('.log'):
                        files.append(subfile_path)

    files.sort(key=os.path.getmtime, reverse=True)
    files = files[:20]

    # Collect previously cached data first
    for file_path in cache['order']:
        salad_data.extend(cache['files'][file_path]['data'])
    print(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), "Processing files...")
    new_data_found = False
    for file_path in files:
        start_line = cache['files'].get(file_path, {}).get('last_line', 0)

        new_data, lines_read = parse_file(file_path, earnings_report_regex, wallet_balance_regex, bandwidth_regex, start_line)
        if new_data:
            print(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), "New Data Found:", new_data)
            new_data_found = True
            
        salad_data.extend(new_data)
        cache['files'][file_path] = {'last_line': start_line + lines_read, 'data': cache['files'].get(file_path, {}).get('data', []) + new_data}

        if file_path not in cache['order']:
            cache['order'].append(file_path)
            if len(cache['order']) > 20:
                oldest_file = cache['order'].pop(0)
                cache['files'].pop(oldest_file, None)
    if not new_data_found:
        print(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), "No New Data Found.")
    save_cache(cache)

    salad_data.sort(key=lambda x: datetime.strptime(x['timestamp'], '%Y-%m-%d %H:%M:%S.%f %z'))
    print(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), "Returning Salad Data...")
    end_time = time.perf_counter()
    total_time = (end_time-start_time)*1000
    print(f"Processing took {total_time:.2f}ms")
    return salad_data

@app.route('/api/salad-data', methods=['GET'])
def get_salad_data():
    log_dir = 'C:\\ProgramData\\Salad\\logs'
    salad_data = read_log_files(log_dir)
    print(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), "API accessed")
    return jsonify(salad_data)

@app.route('/')
def serve_index():
    print(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), "site has been accessed.")
    return send_from_directory('', 'index.html')

if __name__ == '__main__':
    app.run(debug=False, port=8000)
