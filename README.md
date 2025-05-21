# Blackbox Target Manager

A web application for managing monitoring targets for Prometheus Blackbox Exporter. This tool provides a modern UI and API for managing HTTP, ICMP, and TCP monitoring targets.

## Features

- Modern web interface for target management
- RESTful API for CRUD operations
- Support for HTTP, ICMP, and TCP monitoring targets
- Prometheus service discovery integration
- Batch operations (enable/disable/delete multiple targets)
- Advanced search capabilities with Splunk-like query language

## Installation

1. Clone the repository:

```bash
git clone https://github.com/yourusername/blackbox-httpsd.git
cd blackbox-httpsd
```

2. Create a virtual environment and install dependencies:

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

3. Run the application:

```bash
python run.py
```

## API Endpoints

### Target Management

- `GET /api/targets` - Get all targets or search with query parameter
- `GET /api/targets/<id>` - Get a specific target
- `POST /api/targets` - Create a new target
- `PUT /api/targets/<id>` - Update a target
- `DELETE /api/targets/<id>` - Delete a target
- `POST /api/targets/batch` - Perform batch operations on targets

### Prometheus Service Discovery

- `GET /api/sd/<protocol>` - Get targets for a specific protocol (icmp, http, tcp)
- `GET /api/sd/test` - Test endpoint that returns a sample target

### Other Endpoints

- `GET /api/probes` - Get all monitoring probes
- `GET /api/statistics` - Get system statistics

## Prometheus Configuration

Example Prometheus configuration for using this tool as a service discovery mechanism:

```yaml
global:
  scrape_interval: 30s

scrape_configs:
  # ICMP checks
  - job_name: "blackbox_icmp"
    metrics_path: /probe
    params:
      module: [icmp]
    http_sd_configs:
      - url: http://your-server:80/api/sd/icmp
        refresh_interval: 30s
    relabel_configs:
      - source_labels: [__address__]
        target_label: __param_target
      - source_labels: [__param_target]
        target_label: instance
      - target_label: __address__
        replacement: 127.0.0.1:9115  # Blackbox exporter

  # HTTP checks
  - job_name: "blackbox_http"
    metrics_path: /probe
    params:
      module: [http_2xx]
    http_sd_configs:
      - url: http://your-server:80/api/sd/http
        refresh_interval: 30s
    relabel_configs:
      - source_labels: [__address__]
        target_label: __param_target
      - source_labels: [__param_target]
        target_label: instance
      - target_label: __address__
        replacement: 127.0.0.1:9115

  # TCP checks
  - job_name: "blackbox_tcp"
    metrics_path: /probe
    params:
      module: [tcp_connect]
    http_sd_configs:
      - url: http://your-server:80/api/sd/tcp
        refresh_interval: 30s
    relabel_configs:
      - source_labels: [__address__]
        target_label: __param_target
      - source_labels: [__param_target]
        target_label: instance
      - target_label: __address__
        replacement: 127.0.0.1:9115
```

## Production Deployment

For production deployment, it's recommended to use a WSGI server like Gunicorn:

```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:80 "app:create_app()"
```

Or use with a reverse proxy like Nginx.

## License

This project is licensed under the MIT License - see the LICENSE file for details.