# GeoServer Systemd Service Setup

This guide explains how to run GeoServer as a systemd service on a Linux server, ensuring it starts automatically on boot and restarts if it fails.

## Prerequisites
- GeoServer installed in `/opt/bin/` with `startup.sh` script.
- Sudo/root access to the server.

## Steps

### 1. Create the systemd Service File

Open a terminal and run:

```bash
sudo nano /etc/systemd/system/geoserver.service
```

Paste the following content:

```ini
[Unit]
Description=GeoServer Service
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/bin
ExecStart=/opt/bin/startup.sh
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

- Save and exit (Ctrl+O, Enter, Ctrl+X).

### 2. Reload systemd and Enable the Service

```bash
sudo systemctl daemon-reload
sudo systemctl enable geoserver
sudo systemctl start geoserver
```

### 3. Check Service Status

```bash
sudo systemctl status geoserver
```

## Service Management Commands
- **Start:** `sudo systemctl start geoserver`
- **Stop:** `sudo systemctl stop geoserver`
- **Restart:** `sudo systemctl restart geoserver`
- **Status:** `sudo systemctl status geoserver`

## Notes
- The service will start GeoServer automatically on every boot, even if no user logs in.
- For better security, you can change `User=root` to another user (e.g., `azureuser`) if all permissions are set correctly.
- Adjust paths as needed for your installation.

---

**Author:** skytronserver
**Date:** December 1, 2025
