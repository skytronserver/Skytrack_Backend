# Project 2 — Integration Guide for Shared Skytrack Models

## Overview

This guide explains how to set up Project 2 to use the database models from **Skytrack_Backend (Project 1)** without managing any migrations. All schema changes are owned by Project 1. The `skytron_api` app is delivered as a **zip file** — you simply extract it into your project root.

---

## What You Will Get Access To

All models from `skytron_api`, including:

| Category | Models |
|---|---|
| Users & Auth | `User`, `Session`, `TempUser`, `Confirmation`, `TokenBlacklist`, `LoginSettings` |
| Devices | `DeviceModel`, `DeviceStock`, `DeviceTag`, `DeviceCOP`, `Device` |
| GPS & Tracking | `GPSData`, `EMGPSLocation`, `GPSDataLog`, `GPSemDataLog` |
| Organisations | `Manufacturer`, `Dealer`, `VehicleOwner`, `StateAdmin`, `eSimProvider` |
| Emergency | `EMCall`, `EMCallAssignment`, `EMCallBroadcast`, `EMTeams`, `EM_ex`, `EM_admin` |
| School Module | `School`, `SchoolApplication`, `SchoolRoute`, `SchoolBusStop`, `RouteStop`, `SchoolBusTrip`, `SchoolBusTag`, `SchoolBusDocument`, `SchoolHoliday`, `Student`, `ParentProfile`, `StudentBusAllocation`, `StudentAttendance`, `RouteBusAssignment`, `BusAlert` |
| Alerts & Logs | `AlertsLog`, `RequestLog`, `RegNoLookupLog`, `Notice` |
| Settings | `Settings_State`, `Settings_District`, `Settings_VehicleCategory`, `Settings_firmware`, `Settings_ip` |
| Other | `Driver`, `BleKey`, `BusStand`, `OTASettings`, `IncidentRegister`, `Holiday`, `Trip` |

---

## Files Shared by Project 1 Team (via zip)

The zip file `skytron_api.zip` will contain the following files:

```
skytron_api/
├── __init__.py                  # Required — Python package marker
├── apps.py                      # Required — app config, loaded on startup
├── models.py                    # Required — all database models
├── login_settings_cache.py      # Required — imported by apps.py on startup
├── middleware.py                # Optional — request logging middleware
├── authentication.py            # Optional — custom auth backend
├── jwt_authentication.py        # Optional — JWT token authentication
├── serializers.py               # Optional — DRF serializers
├── throttles.py                 # Optional — API rate limiting
├── utils.py                     # Optional — shared utility functions
└── keys/
    ├── jwt_private_key.pem      # Optional — only if Project 2 issues tokens
    └── jwt_public_key.pem       # Required — for verifying tokens from Project 1
```

> The `migrations/` folder is **not included** — Project 2 does not run migrations for this app.

---

## Step 1 — Extract the zip into Project Root

```
your_project2/               ← Django project root (where manage.py lives)
├── manage.py
├── your_project2/           ← Django settings module folder
│   ├── settings.py
│   ├── urls.py
│   └── ...
├── skytron_api/             ← Extract zip here  ✅
│   ├── __init__.py
│   ├── apps.py
│   ├── models.py
│   └── ...
└── keys/
    └── jwt_public_key.pem   ← Place JWT key here (or configure path in settings)
```

No changes to `manage.py`, `wsgi.py`, or `asgi.py` are needed. Django automatically finds apps in the project root.

---

## Step 2 — No sys.path Changes Needed

Since `skytron_api/` is placed directly in your project root (same level as `manage.py`), Django will find it automatically. **Do not modify `manage.py`, `wsgi.py`, or `asgi.py`.**

---

## Step 3 — Install Required Packages

Install these in Project 2's virtual environment. These are the minimum packages required by `skytron_api`:

 
```bash
pip install -r requirements.txt
```

---

## Step 4 — Configure `settings.py` in Project 2

Add/update the following sections in your Project 2 `settings.py`:

```python
import os

# -------------------------------------------------------
# INSTALLED APPS — add skytron_api and its dependencies
# -------------------------------------------------------
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'rest_framework.authtoken',
    'corsheaders',
    'csp',
    'drf_spectacular',
    'django_extensions',
    'bootstrap4',
    'bootstrap_datepicker_plus',

    'skytron_api',        # <-- shared from Project 1

    # ... your own Project 2 apps below
]

# -------------------------------------------------------
# DATABASE — connects to the same PostgreSQL as Project 1
# -------------------------------------------------------
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('DB_NAME', 'skytrondb_main'),
        'USER': os.environ.get('DB_USER', 'dbadmin'),
        'PASSWORD': os.environ.get('DB_PASSWORD', '<ask_project1_team>'),
        'HOST': os.environ.get('DB_HOST', '135.235.166.209'),
        'PORT': os.environ.get('DB_PORT', '5432'),
    }
}

# -------------------------------------------------------
# AUTH USER MODEL — must match Project 1
# -------------------------------------------------------
AUTH_USER_MODEL = 'skytron_api.User'

# -------------------------------------------------------
# CRITICAL — disable migrations for the shared app
# Project 1 owns all table creation/changes
# -------------------------------------------------------
MIGRATION_MODULES = {
    'skytron_api': None,
}

# -------------------------------------------------------
# JWT RSA keys — get these files from Project 1 team
# -------------------------------------------------------
JWT_PRIVATE_KEY_PATH = os.path.join(BASE_DIR, 'keys', 'jwt_private_key.pem')
JWT_PUBLIC_KEY_PATH  = os.path.join(BASE_DIR, 'keys', 'jwt_public_key.pem')

# REST Framework — needed by skytron_api
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
}
```

---

## Step 5 — JWT Key Files

The `skytron_api` app uses RSA keys to sign/verify JWT tokens. You need the **public key** at minimum (for verification). Get these from the Project 1 team:

```
keys/jwt_private_key.pem   ← only needed if Project 2 also issues tokens
keys/jwt_public_key.pem    ← required for verifying tokens from Project 1
```

Place them in your Project 2 root under a `keys/` folder:
```
your_project2/
    keys/
        jwt_private_key.pem
        jwt_public_key.pem
    manage.py
    ...
```

---

## Step 6 — Run Migrations (Project 2 apps only)

```bash
# This will only migrate your own Project 2 apps
# skytron_api is completely skipped
python manage.py migrate
```

Expected output will NOT include any `skytron_api` migrations.

---

## Step 7 — Using the Models

```python
# Import any model you need
from skytron_api.models import (
    User,
    DeviceTag,
    GPSData,
    School,
    Student,
    ParentProfile,
    SchoolBusTrip,
    StudentAttendance,
    EMCall,
)

# Example queries
active_vehicles = DeviceTag.objects.filter(status='Device_Active')
schools         = School.objects.filter(is_active=True)
students        = Student.objects.filter(school=some_school)
gps_points      = GPSData.objects.filter(device_tag=some_tag).order_by('-entry_time')[:10]
```

---

## Rules to Follow

| Rule | Detail |
|---|---|
| ✅ Import & query freely | Read/write any `skytron_api` model |
| ✅ Add your own models | Create models in your own Project 2 apps |
| ✅ Add ForeignKeys to `skytron_api` models | e.g. `ForeignKey('skytron_api.School', ...)` |
| ❌ Never run `makemigrations skytron_api` | Will conflict with Project 1 |
| ❌ Never run `migrate skytron_api` | Tables are owned by Project 1 |
| ❌ Never modify `skytron_api/models.py` locally | All model changes go through Project 1 team |

---


