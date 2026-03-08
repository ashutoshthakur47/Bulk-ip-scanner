from flask import Flask, request, render_template, jsonify, Response
import requests
import json
import re
import csv
import io
import uuid
import threading
import time

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB limit

# Background job storage
jobs = {}

def is_valid_ip(ip):
    pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
    if not re.match(pattern, ip):
        return False
    parts = ip.split('.')
    return all(0 <= int(part) <= 255 for part in parts)

def format_ip_result(ip_address, data):
    return {
        "ip_address": ip_address,
        "country_code": data.get("countryCode"),
        "country_name": data.get("country"),
        "org_name": data.get("org", "N/A"),
        "city": data.get("city"),
        "postal_code": data.get("zip"),
        "isp": data.get("isp"),
        "latitude": data.get("lat"),
        "longitude": data.get("lon"),
        "region": data.get("regionName"),
        "whois_url": f"https://whoisfreaks.com/tools/ip-whois/lookup/{ip_address}",
    }

def get_ip_info(ip_address):
    for attempt in range(2):
        try:
            resp = requests.get(f"http://ip-api.com/json/{ip_address}", timeout=10)
            data = resp.json()
            if data.get('status') == 'success':
                return format_ip_result(ip_address, data)
        except (requests.RequestException, json.JSONDecodeError):
            pass
        if attempt == 0:
            time.sleep(2)
    return {"ip_address": ip_address, "error": "Failed after retry"}

def process_bulk_job(job_id, ip_list):
    job = jobs[job_id]
    job["status"] = "running"
    total = len(ip_list)
    results = []

    for i in range(0, total, 100):
        if job.get("cancelled"):
            job["status"] = "cancelled"
            return

        batch = ip_list[i:i+100]
        batch_done = False
        for attempt in range(2):
            try:
                resp = requests.post("http://ip-api.com/batch", json=batch, timeout=30)
                batch_results = resp.json()
                for item in batch_results:
                    ip = item.get("query", "")
                    if item.get("status") == "success":
                        results.append(format_ip_result(ip, item))
                    else:
                        results.append({"ip_address": ip, "error": item.get("message", "Lookup failed")})
                batch_done = True
                break
            except (requests.RequestException, json.JSONDecodeError):
                if attempt == 0:
                    time.sleep(2)

        if not batch_done:
            for ip in batch:
                results.append({"ip_address": ip, "error": "Batch request failed"})

        job["processed"] = min(i + 100, total)
        job["results"] = results

        # Rate limit: small delay between batches to stay under API limits
        if i + 100 < total:
            time.sleep(1.5)

    job["status"] = "done"
    job["results"] = results

def parse_ips_from_content(file_content, filename):
    lines = file_content.splitlines()
    if filename.endswith('.csv'):
        reader = csv.reader(lines)
        ips = []
        for row in reader:
            if row:
                ips.append(row[0].strip())
        return ips
    return [line.strip() for line in lines]

@app.route('/', methods=['GET', 'POST'])
def index():
    ip_info = []
    job_id = None
    total_ips = 0

    if request.method == 'POST':
        if 'ip_address' in request.form and request.form['ip_address'].strip():
            ip_address = request.form['ip_address'].strip()
            if not is_valid_ip(ip_address):
                ip_info = [{"ip_address": ip_address, "error": "Invalid IP address format"}]
            else:
                ip_info = [get_ip_info(ip_address)]

        elif 'file' in request.files:
            file = request.files['file']
            if file and (file.filename.endswith('.txt') or file.filename.endswith('.csv')):
                file_content = file.read().decode('utf-8')
                ip_addresses = parse_ips_from_content(file_content, file.filename)
                valid_ips = [ip for ip in ip_addresses if ip and is_valid_ip(ip)]
                total_ips = len(valid_ips)

                if total_ips == 0:
                    ip_info = [{"ip_address": "N/A", "error": "No valid IPs found in file"}]
                elif total_ips <= 100:
                    # Small file: scan inline with batch API
                    try:
                        resp = requests.post("http://ip-api.com/batch", json=valid_ips, timeout=30)
                        batch_results = resp.json()
                        for item in batch_results:
                            ip = item.get("query", "")
                            if item.get("status") == "success":
                                ip_info.append(format_ip_result(ip, item))
                            else:
                                ip_info.append({"ip_address": ip, "error": item.get("message", "Lookup failed")})
                    except (requests.RequestException, json.JSONDecodeError):
                        ip_info = [{"ip_address": "N/A", "error": "Batch request failed"}]
                else:
                    # Large file: start background job
                    job_id = str(uuid.uuid4())[:8]
                    jobs[job_id] = {
                        "status": "queued",
                        "total": total_ips,
                        "processed": 0,
                        "results": [],
                    }
                    thread = threading.Thread(target=process_bulk_job, args=(job_id, valid_ips), daemon=True)
                    thread.start()

    return render_template('index.html', ip_info=ip_info, job_id=job_id, total_ips=total_ips)

@app.route('/job_status/<job_id>')
def job_status(job_id):
    job = jobs.get(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404
    return jsonify({
        "status": job["status"],
        "total": job["total"],
        "processed": job["processed"],
    })

@app.route('/job_results_json/<job_id>')
def job_results_json(job_id):
    job = jobs.get(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404
    offset = request.args.get('offset', 0, type=int)
    results = job["results"][offset:]
    return jsonify({"results": results, "total": len(job["results"])})

@app.route('/job_results/<job_id>')
def job_results(job_id):
    job = jobs.get(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404
    if job["status"] != "done":
        return jsonify({"error": "Job not finished yet"}), 400

    output = io.StringIO()
    fieldnames = ["ip_address", "country_name", "country_code", "region", "city", "postal_code", "isp", "org_name", "latitude", "longitude", "whois_url", "error"]
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    for row in job["results"]:
        writer.writerow({k: row.get(k, "") for k in fieldnames})
    output.seek(0)

    # Clean up job after download
    del jobs[job_id]

    return Response(output, mimetype="text/csv", headers={"Content-Disposition": "attachment;filename=scan_results.csv"})

@app.route('/get_ip_info', methods=['POST'])
def get_ip_info_route():
    ip_address = request.form.get('ip_address', '').strip()
    if not ip_address:
        return jsonify({"error": "Missing ip_address field"}), 400
    if not is_valid_ip(ip_address):
        return jsonify({"ip_address": ip_address, "error": "Invalid IP address format"}), 400
    ip_info = get_ip_info(ip_address)
    return jsonify(ip_info)

@app.route('/export', methods=['POST'])
def export():
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data"}), 400
    output = io.StringIO()
    fieldnames = ["ip_address", "country_name", "country_code", "region", "city", "postal_code", "isp", "org_name", "latitude", "longitude", "whois_url", "error"]
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    for row in data:
        writer.writerow({k: row.get(k, "") for k in fieldnames})
    output.seek(0)
    return Response(output, mimetype="text/csv", headers={"Content-Disposition": "attachment;filename=scan_results.csv"})

if __name__ == "__main__":
    app.run(debug=False)
