from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
import os
import re
import json
from datetime import datetime
import time
import argparse

parser = argparse.ArgumentParser(description='Set webserver port')
parser.add_argument('port', type=int, nargs='?', default=8000, help='the integer port for the webserver (default: 8000)')
args = parser.parse_args()
port = args.port
print(f'Starting webserver on port {port}')

app = Flask(__name__)
CORS(app)

LOG_CACHE_FILE = 'cache.json'
BANDWIDTH_CACHE_FILE = 'bandwidth_cache.json'

for cache_file in [LOG_CACHE_FILE, BANDWIDTH_CACHE_FILE]:
    if os.path.exists(cache_file): 
        os.remove(cache_file) # Clear cache when starting program

def load_cache(file):
    if os.path.exists(file):
        with open(file, 'r') as f:
            return json.load(f)
    return {'files': {}, 'order': []}

def save_cache(cache, file):
    with open(file, 'w') as f:
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
    bandwidth_regex = re.compile(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3} -\d{2}:\d{2}) \[INF\] \{.*?"BidirThroughput":([\d.]+)')
    
    log_cache = load_cache(LOG_CACHE_FILE)
    bandwidth_cache = load_cache(BANDWIDTH_CACHE_FILE)
    files = []

    for root, dirnames, filenames in os.walk(log_dir):
        # Skip ndm and systeminformation directories
        dirnames[:] = [d for d in dirnames if d not in ['ndm', 'systeminformation']]
        for file in filenames:
            if file.endswith('.txt') or file.endswith('.log'):
                file_path = os.path.join(root, file)
                files.append(file_path)

    files.sort(key=os.path.getmtime, reverse=True)
    files = files[:20]

    print(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), "Processing log files...")
    new_data_found = False

    # Process log files
    for file_path in files:
        start_line = log_cache['files'].get(file_path, {}).get('last_line', 0)
        new_data, lines_read = parse_file(file_path, earnings_report_regex, wallet_balance_regex, bandwidth_regex, start_line)
        if new_data:
            print(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), f"New Data Found in {file_path}!")
            new_data_found = True
        salad_data.extend(new_data)
        log_cache['files'][file_path] = {'last_line': start_line + lines_read, 'data': log_cache['files'].get(file_path, {}).get('data', []) + new_data}
        if file_path not in log_cache['order']:
            log_cache['order'].append(file_path)
            if len(log_cache['order']) > 20:
                oldest_file = log_cache['order'].pop(0)
                log_cache['files'].pop(oldest_file, None)

    print(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), "Processing bandwidth files...")

    # Process Bandwidth-SGS files
    bandwidth_files = []
    for root, _, filenames in os.walk(log_dir):
        if "Bandwidth-SGS-" in root:
            for file in filenames:
                if file.endswith('.txt') or file.endswith('.log'):
                    bandwidth_files.append(os.path.join(root, file))
    bandwidth_files.sort(key=os.path.getmtime, reverse=True)
    bandwidth_files = bandwidth_files[:5]

    for file_path in bandwidth_files:
        start_line = bandwidth_cache['files'].get(file_path, {}).get('last_line', 0)
        new_data, lines_read = parse_file(file_path, earnings_report_regex, wallet_balance_regex, bandwidth_regex, start_line)
        if new_data:
            print(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), f"New Bandwidth Data Found in {file_path}!")
            new_data_found = True
        salad_data.extend(new_data)
        bandwidth_cache['files'][file_path] = {'last_line': start_line + lines_read, 'data': bandwidth_cache['files'].get(file_path, {}).get('data', []) + new_data}
        if file_path not in bandwidth_cache['order']:
            bandwidth_cache['order'].append(file_path)
            if len(bandwidth_cache['order']) > 20:
                oldest_file = bandwidth_cache['order'].pop(0)
                bandwidth_cache['files'].pop(oldest_file, None)
                
    if not new_data_found:
        print(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), "No New Data Found. Returning data from cache.")
        for file_path in log_cache['order']:
            salad_data.extend(log_cache['files'][file_path]['data'])
        for file_path in bandwidth_cache['order']:
            salad_data.extend(bandwidth_cache['files'][file_path]['data'])
    
    save_cache(log_cache, LOG_CACHE_FILE)
    save_cache(bandwidth_cache, BANDWIDTH_CACHE_FILE)
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
    print(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), "Site has been accessed.")
    return send_from_directory('', 'index.html')

if __name__ == '__main__':
    app.run(debug=False, port=port)
