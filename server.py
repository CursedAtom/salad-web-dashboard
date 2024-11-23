from flask import Flask, jsonify, send_from_directory, request
from flask_cors import CORS
import os
import re
import json
from datetime import datetime
import time
import argparse
import bleach

# Argument parser setup
parser = argparse.ArgumentParser(description='Set webserver port and machine name')
parser.add_argument('-port', type=int, nargs='?', default=8000, help='Port for the webserver (default: 8000)')
parser.add_argument('-machine_name', type=str, required=True, help='Name of the machine')
args = parser.parse_args()
port = args.port
machine_name = args.machine_name
print(f'Starting webserver on port {port} for machine {machine_name}')

# Flask app setup
app = Flask(__name__)
CORS(app)

# Cache file names
LOG_CACHE_FILE = 'cache.json'
BANDWIDTH_CACHE_FILE = 'bandwidth_cache.json'
ERROR_CACHE_FILE = 'error_cache.json'

# Ensure caches are cleared at startup
for cache_file in [LOG_CACHE_FILE, BANDWIDTH_CACHE_FILE, ERROR_CACHE_FILE]:
    if os.path.exists(cache_file):
        os.remove(cache_file)

# Utility functions for cache handling
def load_cache(file_path):
    if os.path.exists(file_path):
        with open(file_path, 'r') as f:
            return json.load(f)
    return {'files': {}, 'order': [], 'dismissed_errors': []}

def save_cache(cache_data, file_path):
    with open(file_path, 'w') as f:
        json.dump(cache_data, f)

# Regex patterns for log parsing
EARNINGS_REPORT_REGEX = re.compile(
    r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3} -\d{2}:\d{2}) \[INF\] Predicted Earnings Report: ([\d.]+) from \(([^)]+)\)"
)
WALLET_BALANCE_REGEX = re.compile(
    r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3} -\d{2}:\d{2}) \[INF\] Wallet: Current\(([\d.]+)\), Predicted\(([\d.]+)\)"
)
BANDWIDTH_REGEX = re.compile(
    r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3} -\d{2}:\d{2}) \[INF\] \{.*?"BidirThroughput":([\d.]+)'
)
ERROR_REGEX = re.compile(
    r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3} -\d{2}:\d{2}) \[WRN\] Node Compatibility Workload Failure (.*?) NodeCompatibilityMessage {(.*?)}',
    re.DOTALL
)

# Log file parsing function
def parse_file(file_path, start_line=0):
    salad_data = []
    with open(file_path, 'r') as f:
        content = f.readlines()[start_line:]

        # Process earnings reports
        for match in EARNINGS_REPORT_REGEX.finditer(''.join(content)):
            salad_data.append({
                'timestamp': match.group(1),
                'earnings': float(match.group(2)),
                'containerId': match.group(3)
            })

        # Process wallet balances
        for match in WALLET_BALANCE_REGEX.finditer(''.join(content)):
            salad_data.append({
                'timestamp': match.group(1),
                'currentBalance': float(match.group(2)),
                'predictedBalance': float(match.group(3))
            })

        # Process bandwidth data
        if "Bandwidth-SGS-" in file_path:
            for match in BANDWIDTH_REGEX.finditer(''.join(content)):
                salad_data.append({
                    'timestamp': match.group(1),
                    'BidirThroughput': float(match.group(2)) / (250000 * 30)  # Convert from bits/30s to MB/s
                })

    return salad_data, len(content)

# Search logs for data
def search_logs(log_dir):
    start_time = time.perf_counter()
    salad_data = []

    log_cache = load_cache(LOG_CACHE_FILE)
    bandwidth_cache = load_cache(BANDWIDTH_CACHE_FILE)

    # Collect log files
    log_files = []
    for root, dirnames, filenames in os.walk(log_dir):
        dirnames[:] = [d for d in dirnames if d not in ['ndm', 'systeminformation']]
        log_files.extend(
            os.path.join(root, file) for file in filenames if file.endswith(('.txt', '.log'))
        )
    log_files.sort(key=os.path.getmtime, reverse=True)
    log_files = log_files[:20]

    # Process logs
    new_data_found = False
    for file_path in log_files:
        start_line = log_cache['files'].get(file_path, {}).get('last_line', 0)
        new_data, lines_read = parse_file(file_path, start_line)
        if new_data:
            print(f"{datetime.now()}: New data found in {file_path}")
            new_data_found = True
        salad_data.extend(new_data)
        log_cache['files'][file_path] = {
            'last_line': start_line + lines_read,
            'data': log_cache['files'].get(file_path, {}).get('data', []) + new_data
        }
        if file_path not in log_cache['order']:
            log_cache['order'].append(file_path)
            if len(log_cache['order']) > 20:
                oldest_file = log_cache['order'].pop(0)
                log_cache['files'].pop(oldest_file, None)

    # Process bandwidth logs
    bandwidth_files = [
        os.path.join(root, file)
        for root, _, filenames in os.walk(log_dir)
        if "Bandwidth-SGS-" in root
        for file in filenames if file.endswith(('.txt', '.log'))
    ]
    bandwidth_files.sort(key=os.path.getmtime, reverse=True)
    bandwidth_files = bandwidth_files[:5]

    for file_path in bandwidth_files:
        start_line = bandwidth_cache['files'].get(file_path, {}).get('last_line', 0)
        new_data, lines_read = parse_file(file_path, start_line)
        if new_data:
            print(f"{datetime.now()}: New bandwidth data found in {file_path}")
            new_data_found = True
        salad_data.extend(new_data)
        bandwidth_cache['files'][file_path] = {
            'last_line': start_line + lines_read,
            'data': bandwidth_cache['files'].get(file_path, {}).get('data', []) + new_data
        }
        if file_path not in bandwidth_cache['order']:
            bandwidth_cache['order'].append(file_path)
            if len(bandwidth_cache['order']) > 20:
                oldest_file = bandwidth_cache['order'].pop(0)
                bandwidth_cache['files'].pop(oldest_file, None)

    if not new_data_found:
        print(f"{datetime.now()}: No new data found. Returning cached data.")
        for file_path in log_cache['order']:
            salad_data.extend(log_cache['files'][file_path]['data'])
        for file_path in bandwidth_cache['order']:
            salad_data.extend(bandwidth_cache['files'][file_path]['data'])

    save_cache(log_cache, LOG_CACHE_FILE)
    save_cache(bandwidth_cache, BANDWIDTH_CACHE_FILE)

    salad_data.sort(key=lambda x: datetime.strptime(x['timestamp'], '%Y-%m-%d %H:%M:%S.%f %z'))
    print(f"Log processing completed in {(time.perf_counter() - start_time) * 1000:.2f} ms")
    return salad_data

# Check logs for errors
def check_errors(log_dir):
    error_cache = load_cache(ERROR_CACHE_FILE)
    files = [
        os.path.join(root, file)
        for root, _, filenames in os.walk(log_dir)
        for file in filenames if file.endswith(('.txt', '.log')) and "Bandwidth-SGS-" not in root
    ]
    files.sort(key=os.path.getmtime, reverse=True)
    files = files[:3]  # Check the most recent 3 files

    errors = []
    for file_path in files:
        with open(file_path, 'r', encoding='utf-8') as f:
            for match in ERROR_REGEX.finditer(f.read()):
                error_timestamp = match.group(1)
                if error_timestamp not in error_cache['dismissed_errors']:
                    error_cache['files'][error_timestamp] = {
                        'timestamp': error_timestamp,
                        'machine_name': machine_name,
                        'error_message': match.group(3)
                    }
                    errors.append(error_cache['files'][error_timestamp])

    save_cache(error_cache, ERROR_CACHE_FILE)
    return errors

# Flask routes
@app.route('/api/salad-data', methods=['GET'])
def get_salad_data():
    return jsonify(search_logs('C:\\ProgramData\\Salad\\logs'))

@app.route('/api/error-status', methods=['GET'])
def get_error_status():
    return jsonify(check_errors('C:\\ProgramData\\Salad\\logs'))

@app.route('/api/dismiss-error', methods=['POST'])
def dismiss_error():
    error_timestamp = bleach.clean(request.json.get('timestamp', ''), strip=True)
    error_cache = load_cache(ERROR_CACHE_FILE)
    if error_timestamp not in error_cache['dismissed_errors']:
        error_cache['dismissed_errors'].append(error_timestamp)
    save_cache(error_cache, ERROR_CACHE_FILE)
    return jsonify({'status': 'success', 'dismissed': error_timestamp})

@app.route('/')
def serve_index():
    return send_from_directory('', 'index.html')

if __name__ == '__main__':
    app.run(debug=False, port=port)
