# Deployment Portability Guide

## Overview

All Skytrack_Backend scripts have been updated to use **dynamic path resolution** instead of hardcoded paths. This allows the system to be deployed anywhere without modifying script paths.

## Path Resolution Strategy

### Python Scripts

All Python scripts now use this pattern:

```python
import os
import sys

# Get script's directory dynamically
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DJANGO_PATH = os.path.join(SCRIPT_DIR, 'Skytronsystem')
sys.path.append(DJANGO_PATH)
```

**Benefits:**
- Works regardless of deployment location
- No hardcoded `/home/azureuser/Skytrack_Backend/` paths
- Relative to script location, not current working directory
- Safe for Docker containers and different VMs

### Bash Scripts

All shell scripts now use this pattern:

```bash
#!/bin/bash
# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Use relative paths from script location
cd "$SCRIPT_DIR"
source .env
```

**Benefits:**
- Works from any directory
- Doesn't rely on `pwd` or current working directory
- Portable across different server configurations

## Updated Files

### Python Scripts (Dynamic Paths)

1. **`mqtt_acl_check.py`**
   - Old: `sys.path.append('/home/azureuser/Skytrack_Backend/Skytronsystem')`
   - New: Uses `SCRIPT_DIR` and relative paths

2. **`mqtt_unified_auth.py`**
   - Old: `sys.path.append('/home/azureuser/Skytrack_Backend/Skytronsystem')`
   - New: Uses `SCRIPT_DIR` and relative paths

3. **`mqtt_auth_wrapper_service.py`**
   - Old: `sys.path.append('/home/azureuser/Skytrack_Backend/Skytronsystem')`
   - New: Uses `SCRIPT_DIR` and relative paths

4. **`mqtt_jwt_preauth_service.py`**
   - Old: `sys.path.append('/home/azureuser/Skytrack_Backend/Skytronsystem')`
   - New: Uses `SCRIPT_DIR` and relative paths

5. **`mqtt_dual_auth_hook.py`**
   - Old: `sys.path.append('/home/azureuser/Skytrack_Backend/Skytronsystem')`
   - New: Uses `SCRIPT_DIR` and relative paths

6. **`mqtt_db_auth_hook.py`**
   - Old: `sys.path.append('/home/azureuser/Skytrack_Backend/Skytronsystem')`
   - New: Uses `SCRIPT_DIR` and relative paths

7. **`test_mqtt_jwt_auth.py`**
   - Old: `sys.path.append('/home/azureuser/Skytrack_Backend/Skytronsystem')`
   - New: Uses `SCRIPT_DIR` and relative paths

8. **`inspect_jwt_token_data.py`**
   - Old: `sys.path.insert(0, '/home/azureuser/Skytrack_Backend/Skytronsystem')`
   - New: Uses `SCRIPT_DIR` and relative paths

### Bash Scripts (Dynamic Paths)

1. **`mqtt_auth_wrapper.sh`**
   - Old: `/usr/bin/python3 /home/azureuser/Skytrack_Backend/mqtt_unified_auth.py`
   - New: Uses `$SCRIPT_DIR/mqtt_unified_auth.py`

2. **`build_run_mqtt.sh`**
   - Old: `cd /home/azureuser/Skytrack_Backend`
   - New: Uses `SCRIPT_DIR` from `BASH_SOURCE[0]`

## Deployment Instructions

### For New VM/Server

1. **Clone or copy Skytrack_Backend to any location:**
   ```bash
   # Can be anywhere - examples:
   /opt/skytrack/Skytrack_Backend
   /srv/applications/Skytrack_Backend
   /var/www/skytrack/Skytrack_Backend
   /home/username/projects/Skytrack_Backend
   ```

2. **No path modifications needed** - scripts automatically detect their location

3. **Run setup scripts as normal:**
   ```bash
   cd /your/custom/path/Skytrack_Backend
   sudo ./setup_mosquitto_jwt_auth.sh
   ./run_with_host_storage.sh
   ```

### For Docker Deployment

Docker containers already use `/app` as the working directory, which is mapped correctly:

```dockerfile
WORKDIR /app
COPY . /app
```

Scripts inside container automatically resolve paths relative to `/app`.

### For Migration Between Servers

1. **Stop services:**
   ```bash
   sudo docker stop skytron-backend-api-container
   sudo systemctl stop mosquitto
   ```

2. **Copy entire directory to new location:**
   ```bash
   rsync -avz /home/azureuser/Skytrack_Backend/ /new/location/Skytrack_Backend/
   ```

3. **Update configuration files with server-specific values:**
   - `.env` - Database host, domain names, etc.
   - Mosquitto configs if TLS cert paths changed
   - Docker network settings if needed

4. **Restart services:**
   ```bash
   cd /new/location/Skytrack_Backend
   ./run_with_host_storage.sh
   sudo systemctl start mosquitto
   ```

**No script modifications required!**

## Configuration Files That May Need Updates

While scripts are now portable, some configuration files contain server-specific values:

### Environment Variables (`.env`)

Update for your environment:
```env
DB_HOST=your.database.host
DB_PORT=5432
ALLOWED_HOSTS=your.domain.com,127.0.0.1
```

### Mosquitto Configurations

Update if TLS certificate paths change:
- `/etc/mosquitto/conf.d/tls.conf` - Certificate paths
- `/etc/mosquitto/conf.d/go-auth.conf` - Django API endpoint URL

### Django Settings

If deploying to different domain:
- `ALLOWED_HOSTS` in `.env`
- `CORS_ALLOWED_ORIGINS` if using CORS

## Testing Portability

Test that scripts work from different locations:

```bash
# Test 1: Run from script directory
cd /path/to/Skytrack_Backend
./build_run_mqtt.sh

# Test 2: Run from different directory
cd /tmp
/path/to/Skytrack_Backend/build_run_mqtt.sh

# Test 3: Test Python path resolution
python3 /path/to/Skytrack_Backend/inspect_jwt_token_data.py
```

All should work without modifications.

## Troubleshooting

### Issue: "No module named 'skytron_api'"

**Cause:** Script trying to import Django modules before path is set

**Solution:** Ensure script has dynamic path resolution at the top:
```python
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DJANGO_PATH = os.path.join(SCRIPT_DIR, 'Skytronsystem')
sys.path.append(DJANGO_PATH)
```

### Issue: ".env file not found"

**Cause:** Bash script not using SCRIPT_DIR

**Solution:** Ensure script uses:
```bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"
```

### Issue: "Django settings module not found"

**Cause:** DJANGO_SETTINGS_MODULE not set correctly

**Solution:** Check that script has:
```python
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Skytronsystem.settings')
```

## Best Practices

1. **Never use hardcoded absolute paths** in scripts
2. **Always use `SCRIPT_DIR` pattern** for path resolution
3. **Keep environment-specific values in `.env`** file
4. **Document any manual configuration changes** needed for deployment
5. **Test scripts from different working directories** before deploying

## Docker Considerations

For Docker deployments:

1. **Paths inside container are fixed** (`/app`) but that's correct
2. **Volume mounts may have different host paths** - that's fine
3. **Scripts inside container use `/app` relative paths** automatically
4. **No changes needed** for different host mount points

Example:
```bash
# Host path can be anything
docker run -v /opt/skytrack/data:/app/data skytrack-api

# Inside container, scripts see /app/data regardless of host path
```

## Summary

✅ **All scripts now portable** - no hardcoded paths
✅ **Deploy anywhere** - works in any directory location
✅ **Docker compatible** - uses relative paths inside containers
✅ **Migration friendly** - copy and run, no modifications needed
✅ **VM independent** - not tied to specific user home directories

You can now deploy Skytrack_Backend to any server, any path, any VM configuration without modifying script paths!
