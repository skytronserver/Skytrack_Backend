# Complaint Management System — Full API Documentation

> **Version:** 2.0 | **Base path:** `/api/` | **Date:** 2026-06-12
> This document is intended for the frontend development team.
> All endpoints live under the same base URL as the rest of the Skytrack backend API.

---

## Table of Contents

1. [Overview](#1-overview)
2. [Authentication](#2-authentication)
3. [Reference Data (Enums)](#3-reference-data-enums)
4. [Status Transition Rules](#4-status-transition-rules)
5. [Escalation Rules](#5-escalation-rules)
6. [File Upload Rules](#6-file-upload-rules)
7. [API Endpoints](#7-api-endpoints)
   - [7.1 Create Ticket (Public / HelpDesk)](#71-create-ticket)
   - [7.2 List Tickets](#72-list-tickets)
   - [7.3 Device / IMEI Lookup](#73-device--imei-lookup)
   - [7.4 Ticket Detail](#74-ticket-detail)
   - [7.5 Update Status](#75-update-status)
   - [7.6 Escalate Ticket](#76-escalate-ticket)
   - [7.7 Submit Final Report](#77-submit-final-report)
   - [7.8 Add Comment](#78-add-comment)
   - [7.9 Activity Log](#79-activity-log)
   - [7.10 Public Ticket Tracker (No Login)](#710-public-ticket-tracker)
8. [Error Response Format](#8-error-response-format)
9. [Role Access Matrix](#9-role-access-matrix)
10. [Frontend Pages — Full Specification](#10-frontend-pages--full-specification)
    - [Page A: Public Complaint Submission Form](#page-a-public-complaint-submission-form)
    - [Page B: Public Ticket Status Tracker](#page-b-public-ticket-status-tracker)
    - [Page C: HelpDesk Dashboard](#page-c-helpdesk-dashboard)
    - [Page D: Create Ticket on Behalf of Public (HelpDesk)](#page-d-create-ticket-on-behalf-of-public-helpdesk)
    - [Page E: Ticket Detail & Management (Staff)](#page-e-ticket-detail--management-staff)
    - [Page F: Staff Ticket List (TeamLead / SOS Executive / StateAdmin / SuperAdmin)](#page-f-staff-ticket-list)
    - [Page G: Manufacturer Ticket View](#page-g-manufacturer-ticket-view)

---

## 1. Overview

The Complaint Management System allows:
- **Public users** (anonymous or logged-in) to submit complaint tickets via the app/website.
- **HelpDesk users** to create tickets on behalf of public callers/emailers, manage ticket statuses, and escalate to higher roles.
- **Staff roles** (TeamLead, SOS Executive, StateAdmin, SuperAdmin) to view, manage, resolve, and escalate all tickets.
- **Manufacturer users** (`devicemanufacture` role) to view only tickets that have been explicitly escalated to their manufacturer account.
- **Anyone** to track their ticket status using a reference number — no login required.

### Ticket Reference Number Format
Every ticket gets a unique reference number on creation:
```
TKT-YYYY-NNNNN
Example: TKT-2026-00001
```

---

## 2. Authentication

All staff endpoints require a Bearer token in the `Authorization` header:

```
Authorization: Bearer <your-jwt-token>
```

Only two endpoints work without authentication:
- `POST /api/complaint/create/` — anonymous ticket creation is allowed
- `GET /api/complaint/track/<ticket_ref>/` — public status lookup

---

## 3. Reference Data (Enums)

### Ticket Status values
| Value | Label | Meaning |
|---|---|---|
| `created` | Created | Newly submitted, no action yet |
| `in_review` | In Review | Staff is actively investigating |
| `pending` | Pending | Awaiting external input or response |
| `closed` | Closed | Resolved |
| `canceled` | Canceled | Withdrawn or duplicate |

### Source values
| Value | Label | When used |
|---|---|---|
| `public_app` | Public App | Submitted by a member of the public |
| `helpdesk_call` | HelpDesk Call | Created by helpdesk on behalf of a caller |
| `helpdesk_email` | HelpDesk Email | Created by helpdesk from an email |

### Escalation target values (`escalated_to`)
| Value | Label | Who can set it |
|---|---|---|
| `null` | Not escalated | (default) |
| `teamlead` | Team Lead | helpdesk |
| `sosadmin` | SOS Admin | helpdesk, teamleader |
| `manufacturer` | Manufacturer | teamleader, sosexecutive, stateadmin, superadmin |

### Activity action types
| Value | Meaning |
|---|---|
| `created` | Ticket was submitted |
| `status_change` | Status was changed |
| `comment` | A comment was added |
| `final_report` | Final report or solution was submitted |
| `attachment` | A file was attached |
| `escalation` | Ticket was escalated to a higher level |

---

## 4. Status Transition Rules

```
created   →  in_review, canceled
in_review →  pending, closed, canceled
pending   →  in_review, closed, canceled
closed    →  (terminal — no further transitions)
canceled  →  (terminal — no further transitions)
```

The API enforces these transitions — attempting an invalid transition returns HTTP 400.

---

## 5. Escalation Rules

Escalation is a separate action from status changes (use the `/escalate/` endpoint).

| Actor role | Can escalate to |
|---|---|
| `helpdesk` | `teamlead`, `sosadmin` |
| `teamleader` | `sosadmin`, `manufacturer` |
| `sosexecutive` | `manufacturer` |
| `stateadmin` | `teamlead`, `sosadmin`, `manufacturer` |
| `superadmin` | `teamlead`, `sosadmin`, `manufacturer` |

When escalating to `manufacturer`, a `manufacturer_id` must be provided. Only tickets with `escalated_to = "manufacturer"` are visible to manufacturer users, and only for their own manufacturer account.

**Device / IMEI linkage:** A ticket can optionally be linked to a specific device at creation time via `device_imei`. This is informational — escalation to the correct manufacturer must still be done explicitly via the `/escalate/` endpoint.

---

## 6. File Upload Rules

- **Allowed types:** PNG, JPEG, PDF, XLS, XLSX
- **Maximum size:** 10 MB per file
- Files are stored in MinIO object storage; the response returns the internal storage path.
- Executable binary formats are rejected regardless of extension.

---

## 7. API Endpoints

### 7.1 Create Ticket

```
POST /api/complaint/create/
Auth: Optional (anonymous or Bearer token)
Content-Type: multipart/form-data
```

Creates a new complaint ticket. Accessible by anonymous users (public) and authenticated staff (helpdesk creates on behalf of public).

**Request body (form-data):**

| Field | Type | Required | Notes |
|---|---|---|---|
| `applicant_name` | string | Yes | Full name of the complainant |
| `applicant_phone` | string | Yes | Phone number of the complainant |
| `applicant_email` | string | No | Email of the complainant |
| `title` | string | Yes | Short summary of the complaint |
| `details` | string | Yes | Full description of the problem |
| `source` | string | No | One of `helpdesk_call`, `helpdesk_email`, `public_app`. Only honoured for staff; defaults to `public_app`. |
| `device_imei` | string | No | If provided (staff only), links the ticket to a DeviceStock record by exact IMEI. Returns 400 if IMEI not found. |
| `file`, `file_0`, `file_1` … | file | No | Attachments (up to file upload rules above) |

**Success response (HTTP 201):**
```json
{
  "message": "Ticket created successfully",
  "ticket_ref": "TKT-2026-00001",
  "id": 42
}
```

**Error responses:**
- `400` — Missing required field or invalid IMEI
- `400` — `applicant_name is required` / `applicant_phone is required` / `title is required` / `details is required`

---

### 7.2 List Tickets

```
GET /api/complaint/list/
Auth: Required (Bearer token)
Roles: helpdesk, teamleader, sosexecutive, stateadmin, superadmin, devicemanufacture
```

Returns a paginated, filtered list of tickets.

**Scoping by role:**
- Staff roles (`helpdesk` through `superadmin`): all tickets.
- `devicemanufacture`: only tickets where `escalated_to = "manufacturer"` and `escalated_to_manufacturer` is one of the manufacturer accounts the user belongs to.

**Default ordering:** Active tickets (`created`, `pending`) appear first, then all others — all sorted newest-first within each group.

**Query parameters:**

| Param | Type | Description |
|---|---|---|
| `status` | string | Filter by status value (e.g. `pending`) |
| `source` | string | Filter by source (e.g. `helpdesk_call`) |
| `escalated_to` | string | Filter by escalation target. Use `none` for non-escalated. Staff only (ignored for manufacturer role). |
| `search` | string | Search ticket_ref, applicant_name, phone, email, title |
| `page` | int | Page number (default 1) |
| `page_size` | int | Results per page (default 20, max 100) |

**Success response (HTTP 200):**
```json
{
  "total": 150,
  "page": 1,
  "page_size": 20,
  "results": [
    {
      "id": 42,
      "ticket_ref": "TKT-2026-00001",
      "applicant_name": "John Doe",
      "applicant_phone": "9876543210",
      "applicant_email": "john@example.com",
      "title": "Device not connecting",
      "details": "My device stopped connecting after the last update.",
      "status": "pending",
      "source": "helpdesk_call",
      "escalated_to": "manufacturer",
      "escalated_to_manufacturer": {
        "id": 7,
        "company_name": "Acme Devices Ltd."
      },
      "device_stock": {
        "id": 101,
        "imei": "490154203237518",
        "device_esn": "ESN-00123",
        "model_name": "SkyTrack Pro v2"
      },
      "solution": null,
      "final_report_file": null,
      "entry_date": "2026-06-12",
      "created_at": "2026-06-12T09:30:00Z",
      "updated_at": "2026-06-12T11:15:00Z",
      "created_by": 5,
      "attachments": []
    }
  ]
}
```

**Notes for frontend:**
- To build the "highlighted tickets" table for elevated roles, call this endpoint again with `?escalated_to=teamlead` (or `sosadmin` / `manufacturer`) to get only the tickets relevant to that role's queue.

---

### 7.3 Device / IMEI Lookup

```
GET /api/complaint/device-imei/?q=<partial_imei>
Auth: Required (Bearer token)
Roles: helpdesk, teamleader, sosexecutive, stateadmin, superadmin
```

Search for a device by partial IMEI. Use this for autocomplete when creating a ticket or for the escalation form to pre-fill device context. Returns up to 20 matches.

**Query parameters:**

| Param | Type | Required | Description |
|---|---|---|---|
| `q` | string | Yes | At least 4 characters of the IMEI |

**Success response (HTTP 200):**
```json
{
  "results": [
    {
      "id": 101,
      "imei": "490154203237518",
      "device_esn": "ESN-00123",
      "model_name": "SkyTrack Pro v2",
      "stock_status": "Fitted"
    }
  ]
}
```

**Error responses:**
- `400` — `Query must be at least 4 characters.`
- `403` — Non-staff role

---

### 7.4 Ticket Detail

```
GET /api/complaint/<id>/
Auth: Required (Bearer token)
Roles: helpdesk, teamleader, sosexecutive, stateadmin, superadmin, devicemanufacture
```

Returns the full ticket with all fields and attachments.

**Scoping:**
- Staff roles: any ticket.
- `devicemanufacture`: only tickets escalated to their manufacturer.

**Success response (HTTP 200):** Same structure as a single item in the list response (see §7.2), with `attachments` always included.

**Error responses:**
- `403` — Not in an allowed role, or manufacturer trying to access a ticket not escalated to them
- `404` — Ticket not found

---

### 7.5 Update Status

```
PATCH /api/complaint/<id>/update-status/
Auth: Required (Bearer token)
Roles: helpdesk, teamleader, sosexecutive, stateadmin, superadmin
Content-Type: application/json
```

Changes the status of a ticket, subject to allowed transitions.

**Request body:**
```json
{
  "status": "in_review",
  "comment": "Starting investigation.",
  "solution": "Issue resolved by..."
}
```

| Field | Type | Required | Notes |
|---|---|---|---|
| `status` | string | Yes | New status value (must be a valid transition) |
| `comment` | string | No | Optional comment logged to activity trail |
| `solution` | string | No | Only applied if new status is `closed` and no solution exists yet |

**Success response (HTTP 200):**
```json
{ "message": "Status updated", "status": "in_review" }
```

**Error responses:**
- `400` — Invalid status value
- `400` — Transition not allowed (e.g. `Cannot move from "closed" to "pending"`)
- `404` — Ticket not found

---

### 7.6 Escalate Ticket

```
PATCH /api/complaint/<id>/escalate/
Auth: Required (Bearer token)
Roles: helpdesk, teamleader, sosexecutive, stateadmin, superadmin
Content-Type: application/json
```

Escalates a ticket to a higher level. Each role can only escalate to certain targets (see §5).

**Request body:**
```json
{
  "escalate_to": "manufacturer",
  "manufacturer_id": 7,
  "comment": "Hardware defect suspected — escalating to device manufacturer."
}
```

| Field | Type | Required | Notes |
|---|---|---|---|
| `escalate_to` | string | Yes | One of `teamlead`, `sosadmin`, `manufacturer` |
| `manufacturer_id` | int | Conditional | Required when `escalate_to = "manufacturer"` |
| `comment` | string | No | Reason for escalation (logged to activity trail) |

**Success response (HTTP 200):**
```json
{
  "message": "Ticket escalated",
  "escalated_to": "manufacturer",
  "manufacturer_id": 7
}
```

**Error responses:**
- `400` — Invalid `escalate_to` value
- `400` — `manufacturer_id` missing when escalating to manufacturer
- `400` — Manufacturer not found
- `403` — Role not permitted to escalate to the requested level
- `404` — Ticket not found

**Activity log entry:** An `escalation` activity is appended automatically with `old_value` = previous escalation state and `new_value` = new escalation target (e.g. `manufacturer:Acme Devices Ltd.`).

---

### 7.7 Submit Final Report

```
POST /api/complaint/<id>/final-report/
Auth: Required (Bearer token)
Roles: helpdesk, teamleader, sosexecutive, stateadmin, superadmin
Content-Type: multipart/form-data
```

Uploads a final report file and/or records the solution text. At least one of `solution` or `final_report` must be provided.

**Request body (form-data):**

| Field | Type | Required | Notes |
|---|---|---|---|
| `solution` | string | Conditional | Resolution text (at least one of solution/file required) |
| `final_report` | file | Conditional | Report file (PNG/JPEG/PDF/XLS/XLSX, max 10 MB) |

**Success response (HTTP 200):**
```json
{ "message": "Final report submitted" }
```

---

### 7.8 Add Comment

```
POST /api/complaint/<id>/comment/
Auth: Required (Bearer token)
Roles: helpdesk, teamleader, sosexecutive, stateadmin, superadmin
Content-Type: application/json
```

Appends a free-text comment to the ticket audit trail.

**Request body:**
```json
{ "comment": "Called back the customer — issue persists." }
```

**Success response (HTTP 201):**
```json
{ "message": "Comment added" }
```

---

### 7.9 Activity Log

```
GET /api/complaint/<id>/activity/
Auth: Required (Bearer token)
Roles: helpdesk, teamleader, sosexecutive, stateadmin, superadmin, devicemanufacture
```

Returns the full audit trail for a ticket. Manufacturer users can only view logs for tickets escalated to their manufacturer.

**Success response (HTTP 200):**
```json
{
  "ticket_ref": "TKT-2026-00001",
  "activities": [
    {
      "id": 1,
      "actor_name": "Jane Smith",
      "action_type": "created",
      "old_value": null,
      "new_value": "TKT-2026-00001",
      "comment": null,
      "timestamp": "2026-06-12T09:30:00Z"
    },
    {
      "id": 2,
      "actor_name": "Helpdesk User",
      "action_type": "escalation",
      "old_value": "none",
      "new_value": "manufacturer:Acme Devices Ltd.",
      "comment": "Hardware defect suspected.",
      "timestamp": "2026-06-12T11:00:00Z"
    }
  ]
}
```

---

### 7.10 Public Ticket Tracker

```
GET /api/complaint/track/<ticket_ref>/
Auth: None required
```

Allows any member of the public to look up the current status of their ticket by reference number. Internal fields (file paths, staff names, etc.) are never returned.

**URL parameter:** `ticket_ref` — e.g. `TKT-2026-00001` (case-insensitive)

**Success response (HTTP 200):**
```json
{
  "ticket_ref": "TKT-2026-00001",
  "title": "Device not connecting",
  "status": "in_review",
  "entry_date": "2026-06-12",
  "updated_at": "2026-06-12T11:15:00Z",
  "solution": null,
  "activities": [
    {
      "action_type": "created",
      "new_value": "TKT-2026-00001",
      "comment": null,
      "timestamp": "2026-06-12T09:30:00Z"
    },
    {
      "action_type": "status_change",
      "new_value": "in_review",
      "comment": null,
      "timestamp": "2026-06-12T11:15:00Z"
    }
  ]
}
```

**Error response:**
- `404` — `{ "error": "Ticket not found" }`

---

## 8. Error Response Format

All error responses follow this structure:

```json
{ "error": "Human-readable message explaining what went wrong." }
```

Standard HTTP status codes used:
- `400 Bad Request` — Invalid input or business rule violation
- `401 Unauthorized` — No token or expired token
- `403 Forbidden` — Role not allowed to perform this action
- `404 Not Found` — Resource does not exist

---

## 9. Role Access Matrix

| Endpoint | public | helpdesk | teamleader | sosexecutive | stateadmin | superadmin | devicemanufacture |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| `POST /complaint/create/` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |
| `GET /complaint/list/` | ❌ | ✅ all | ✅ all | ✅ all | ✅ all | ✅ all | ✅ scoped* |
| `GET /complaint/device-imei/` | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |
| `GET /complaint/<id>/` | ❌ | ✅ any | ✅ any | ✅ any | ✅ any | ✅ any | ✅ scoped* |
| `PATCH /complaint/<id>/update-status/` | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |
| `PATCH /complaint/<id>/escalate/` | ❌ | ✅ limited** | ✅ limited** | ✅ limited** | ✅ | ✅ | ❌ |
| `POST /complaint/<id>/final-report/` | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |
| `POST /complaint/<id>/comment/` | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |
| `GET /complaint/<id>/activity/` | ❌ | ✅ any | ✅ any | ✅ any | ✅ any | ✅ any | ✅ scoped* |
| `GET /complaint/track/<ref>/` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |

\* **scoped** — manufacturer role only sees tickets explicitly escalated to their manufacturer account.  
\*\* **limited** — subject to per-role escalation target restrictions (see §5).

---

## 10. Frontend Pages — Full Specification

### Page A: Public Complaint Submission Form

**Route:** `/complaint/new` (public, no login required)

**Purpose:** Allow any member of the public to file a complaint.

**Form fields:**
- Full Name (`applicant_name`) — required
- Phone Number (`applicant_phone`) — required
- Email (`applicant_email`) — optional
- Complaint Title (`title`) — required
- Description (`details`) — required, multiline text
- Attachments — optional, multi-file (PNG/JPEG/PDF/XLS/XLSX, max 10 MB each)

**On submit:** Call `POST /api/complaint/create/`

**On success:** Display a success screen with the `ticket_ref`. The user should be instructed to save this reference to track their complaint later. Provide a link to Page B pre-filled with the reference number.

---

### Page B: Public Ticket Status Tracker

**Route:** `/complaint/track` (public, no login required)

**Purpose:** Allow anyone to check the status of their ticket.

**Input:** Ticket reference field (e.g. `TKT-2026-00001`)

**On submit:** Call `GET /api/complaint/track/<ticket_ref>/`

**Display:**
- Ticket reference, title, current status (as a labelled badge)
- Date filed (`entry_date`), last updated (`updated_at`)
- Solution text (if ticket is closed)
- Timeline of public activities (`created`, `status_change`, `comment` events)

---

### Page C: HelpDesk Dashboard

**Route:** `/helpdesk/tickets` (requires `helpdesk` role)

**Purpose:** Main working screen for helpdesk agents.

**Layout:**
- Filter bar: status, source, search, escalated_to, date range
- Ticket table (newest active on top):
  - Columns: Ticket Ref | Applicant | Title | Status | Source | Escalated To | Created | Last Updated
  - Badges: status colour-coded; escalated tickets shown with an arrow/flag icon
  - Pagination controls

**API calls:**
- Load: `GET /api/complaint/list/`
- Refresh: same endpoint with current filter state
- Click row: navigate to Page E (Ticket Detail)

**Quick actions from table row:**
- "Create Ticket" button → Page D
- Status update dropdown (inline)

---

### Page D: Create Ticket on Behalf of Public (HelpDesk)

**Route:** `/helpdesk/tickets/new` (requires `helpdesk` role)

**Purpose:** HelpDesk agent creates a ticket from a phone call or email.

**Form fields:**
- Same as Page A, plus:
- Source (`source`) — dropdown: `helpdesk_call` / `helpdesk_email`
- Device IMEI (`device_imei`) — optional, with autocomplete:
  - As the agent types (≥ 4 chars), call `GET /api/complaint/device-imei/?q=<input>`
  - Show results: IMEI, ESN, model name, stock status
  - On selection, store the chosen IMEI for submission

**On submit:** Call `POST /api/complaint/create/` with `source` and optionally `device_imei`.

---

### Page E: Ticket Detail & Management (Staff)

**Route:** `/helpdesk/tickets/<id>` (all staff roles; manufacturer role: scoped)

**Purpose:** View full ticket and take actions.

**Sections:**

1. **Header** — Ticket ref, title, status badge, escalation badge, created date
2. **Applicant info** — name, phone, email
3. **Device info** — (if linked) IMEI, ESN, model name, stock status
4. **Complaint details** — details text, attached files
5. **Solution / Final Report** — solution text, final report file download
6. **Activity Timeline** — full audit trail from `GET /api/complaint/<id>/activity/`
7. **Action Panel:**
   - **Update Status** → `PATCH /api/complaint/<id>/update-status/`
   - **Escalate** (staff only, not manufacturer) → opens a modal:
     - Dropdown: Escalate to `teamlead` / `sosadmin` / `manufacturer`
     - If `manufacturer`: manufacturer search/select dropdown + populated from system
     - Comment field
     - Submit → `PATCH /api/complaint/<id>/escalate/`
   - **Add Comment** → `POST /api/complaint/<id>/comment/`
   - **Submit Final Report** → `POST /api/complaint/<id>/final-report/`

**Manufacturer view:** Only steps 1–6 visible, no action panel (read-only).

---

### Page F: Staff Ticket List

**Route:** `/staff/tickets` (requires `teamleader`, `sosexecutive`, `stateadmin`, or `superadmin`)

**Purpose:** Full overview for elevated staff roles.

**Layout — two tables:**

1. **Main table** (all tickets, newest on top):
   - Same columns as Page C
   - Full filter bar: status, source, escalated_to, search, pagination
   - API: `GET /api/complaint/list/`

2. **"Escalated to me" table** (highlighted queue):
   - Shows only tickets escalated to this user's role level
   - Mapping: `teamleader` → `?escalated_to=teamlead`, `sosexecutive/stateadmin/superadmin` → `?escalated_to=sosadmin`
   - API: `GET /api/complaint/list/?escalated_to=<role_level>`
   - Empty state: "No tickets escalated to your level."

Both tables link to Page E for detail/action.

---

### Page G: Manufacturer Ticket View

**Route:** `/manufacturer/tickets` (requires `devicemanufacture` role)

**Purpose:** Device manufacturer sees only tickets escalated to their company.

**Layout:**
- Single table with all tickets escalated to their manufacturer (API automatically scopes)
- Columns: Ticket Ref | Applicant | Title | Device IMEI | Status | Escalated Date | Last Updated
- Search and pagination
- API: `GET /api/complaint/list/`
- Click row: navigate to read-only ticket detail (Page E, manufacturer mode)
- No action buttons (read-only)
