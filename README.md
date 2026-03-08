# Bulk IP Scanner

A web-based bulk IP scanner built with Flask that scans thousands of IPs and delivers detailed geolocation, ISP, organisation, and WHOIS data — with an interactive clustered map.

## Features

- **Single IP Scan** — Enter one IP and get instant results with a map
- **Bulk Scan** — Upload a `.txt` or `.csv` file with thousands of IPs
- **Background Processing** — Large files (100+ IPs) are scanned in the background with a live progress bar
- **Interactive Clustered Map** — All scanned IPs plotted on one map using Leaflet + MarkerCluster
- **Locate on Map** — Click 📍 on any IP card to zoom into its location on the map
- **CSV Export** — Download all scan results as a CSV file
- **IP Validation** — Invalid IPs are filtered out automatically
- **Batch API** — Uses ip-api.com batch endpoint for fast bulk scanning (100 IPs per request)
- **Retry Logic** — Failed requests are retried once before marking as error

## Tech Stack

- **Backend:** Python, Flask
- **Frontend:** HTML, CSS, JavaScript
- **Maps:** Leaflet.js + Leaflet.markercluster
- **API:** [ip-api.com](http://ip-api.com) (free tier, no API key required)

## Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/YOUR_USERNAME/Bulk-ip-scanner.git
   cd Bulk-ip-scanner
   ```

2. **Create a virtual environment**
   ```bash
   python3 -m venv venv
   source venv/bin/activate        # Linux/macOS
   venv\Scripts\activate           # Windows
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the app**
   ```bash
   python bulk_ip.py
   ```

5. **Open in browser**
   ```
   http://127.0.0.1:5000
   ```

## Usage

### Single IP
Enter an IP address (e.g. `8.8.8.8`) in the text field and click **Scan IP**.

### Bulk Scan
1. Prepare a `.txt` file (one IP per line) or `.csv` file (IP in first column)
2. Click **Upload and Scan**
3. Watch the progress bar — IP cards and map markers appear in real time
4. When done, click **Download CSV** to export results

A sample file is included: [`sample_ips.txt`](sample_ips.txt)

### File Format Examples

**TXT file** (one IP per line):
```
8.8.8.8
1.1.1.1
208.67.222.222
```

**CSV file** (IP in first column, other columns ignored):
```
8.8.8.8,Google DNS
1.1.1.1,Cloudflare
208.67.222.222,OpenDNS
```

## API Rate Limits

This tool uses the free tier of [ip-api.com](http://ip-api.com):
- **Single requests:** 45 per minute
- **Batch endpoint:** Up to 100 IPs per request
- The tool automatically adds delays between batch requests to stay within limits
- For 26,000 IPs, expect ~5-8 minutes total scan time

## Project Structure

```
├── bulk_ip.py           # Flask application (backend)
├── templates/
│   └── index.html       # Web interface (frontend)
├── requirements.txt     # Python dependencies
├── sample_ips.txt       # Sample IP list for testing
├── LICENSE              # MIT License
├── .gitignore           # Git ignore rules
└── README.md            # This file
```

## Screenshots

| Single IP Scan | Bulk Scan with Map |
|:-:|:-:|
| Enter one IP → instant results with map | Upload file → progress bar + clustered map |

## License

MIT License — see [LICENSE](LICENSE) for details.

