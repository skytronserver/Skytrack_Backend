# Complaint Management System — Full API Documentation

> **Version:** 1.0 | **Base path:** `/api/` | **Date:** 2026-06-08
> This document is intended for the frontend development team.
> All endpoints live under the same base URL as the rest of the Skytrack backend API.

---

## Table of Contents

1. [Overview](#1-overview)
2. [Authentication](#2-authentication)
3. [Reference Data (Enums)](#3-reference-data-enums)
4. [Status Transition Rules](#4-status-transition-rules)
5. [File Upload Rules](#5-file-upload-rules)
6. [API Endpoints](#6-api-endpoints)
   - [6.1 Create Ticket (Public / HelpDesk)](#61-create-ticket)
   - [6.2 List Tickets](#62-list-tickets)
   - [6.3 Ticket Detail](#63-ticket-detail)
   - [6.4 Update Status](#64-update-status)
   - [6.5 Submit Final Report](#65-submit-final-report)
   - [6.6 Add Comment](#66-add-comment)
   - [6.7 Activity Log](#67-activity-log)
   - [6.8 Public Ticket Tracker (No Login)](#68-public-ticket-tracker)
7. [Error Response Format](#7-error-response-format)
8. [Frontend Pages — Full Specification](#8-frontend-pages--full-specification)
   - [Page A: Public Complaint Submission Form](#page-a-public-complaint-submission-form)
   - [Page B: Public Ticket Status Tracker](#page-b-public-ticket-status-tracker)
   - [Page C: HelpDesk Dashboard](#page-c-helpdesk-dashboard)
   - [Page D: Create Ticket on Behalf of Public (HelpDesk)](#page-d-create-ticket-on-behalf-of-public-helpdesk)
   - [Page E: Ticket Detail & Management (Staff)](#page-e-ticket-detail--management-staff)
   - [Page F: Staff Ticket List (TeamLead / SOS Executive)](#page-f-staff-ticket-list-teamlead--sos-executive)
   - [Page G: Admin Ticket List (StateAdmin / SuperAdmin)](#page-g-admin-ticket-list-stateadmin--superadmin)
9. [Role-to-Page Access Matrix](#9-role-to-page-access-matrix)

---

## 1. Overview

The Complaint Management System allows:
- **Public users** (anonymous or logged-in) to submit complaint tickets via the app/website.
- **HelpDesk users** to create tickets on behalf of public callers or emailers.
- **Staff roles** (HelpDesk, TeamLead, SOS Executive, StateAdmin, SuperAdmin) to view, manage, and resolve all tickets.
- **Anyone** to track their ticket status using a reference number — no login required.

### Ticket Reference Number Format
Every ticket gets a unique reference number on creation:
```
TKT-YYYY-NNNNN
Example: TKT-2026-00001
```
This is returned on creation and used for public tracking.

---

## 2. Authentication

### Authenticated Endpoints
Send the JWT token in the `Authorization` header:
```
Authorization: Bearer <your_jwt_token>
```

### Public Endpoints
Endpoints marked **"No auth required"** do not need any header.

### Optional Auth Endpoint
`POST /api/complaint/create/` accepts both anonymous and authenticated requests.
- If no token is sent → ticket is created as anonymous public submission.
- If a valid token is sent → ticket is linked to that user account.

---

## 3. Reference Data (Enums)

### Ticket Status Values

| Value | Display Label | Description |
|-------|--------------|-------------|
| `created` | Created | Ticket just submitted, not yet reviewed |
| `in_review` | In Review | Staff is actively reviewing |
| `pending` | Pending | Awaiting additional info or action |
| `closed` | Closed | Issue resolved and closed |
| `canceled` | Canceled | Ticket canceled (invalid / duplicate / withdrawn) |

### Ticket Source Values

| Value | Display Label | Who Sets It |
|-------|--------------|-------------|
| `public_app` | Public App | Auto-set for all public submissions |
| `helpdesk_call` | HelpDesk Call | HelpDesk user sets this when creating on behalf of a phone caller |
| `helpdesk_email` | HelpDesk Email | HelpDesk user sets this when creating on behalf of an email sender |

### Activity Action Types (Audit Trail)

| Value | Meaning |
|-------|---------|
| `created` | Ticket was created |
| `status_change` | Status was changed |
| `comment` | A comment was added by staff |
| `final_report` | Final report text or file was submitted |
| `attachment` | A file was attached |

---

## 4. Status Transition Rules

Not all status changes are allowed. The backend enforces this matrix:

| Current Status | Allowed Next Status |
|---------------|---------------------|
| `created` | `in_review`, `canceled` |
| `in_review` | `pending`, `closed`, `canceled` |
| `pending` | `in_review`, `closed`, `canceled` |
| `closed` | _(no further changes allowed)_ |
| `canceled` | _(no further changes allowed)_ |

**Frontend implication:** When showing the status change dropdown on the detail page, only show the allowed next statuses based on the current status. Disable the status change UI entirely when the ticket is `closed` or `canceled`.

---

## 5. File Upload Rules

Applies to both **creation attachments** and **final report upload**.

| Rule | Value |
|------|-------|
| Max file size | **10 MB** per file |
| Allowed types | `image/png`, `image/jpeg`, `application/pdf`, `application/vnd.ms-excel` (.xls), `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet` (.xlsx) |
| Upload method | `multipart/form-data` |
| Files stored in | MinIO object storage (server-managed) |

The `file_path` returned in responses is the internal MinIO object key. To display/download a file, pass the `file_path` value to the existing Skytrack file download endpoint (same as other file downloads in the system).

---

## 6. API Endpoints

---

### 6.1 Create Ticket

**`POST /api/complaint/create/`**

**Auth:** Optional (no auth = anonymous public submission; with auth token = linked to account)

**Content-Type:** `multipart/form-data` (required if attaching files) or `application/json` (if no files)

#### Request Body

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `applicant_name` | string | ✅ Yes | Full name of the person making the complaint |
| `applicant_phone` | string | ✅ Yes | Phone number of the applicant |
| `applicant_email` | string | No | Email address of the applicant |
| `title` | string | ✅ Yes | Short title/subject of the complaint (max 500 chars) |
| `details` | string | ✅ Yes | Full description of the complaint |
| `source` | string | No | One of: `helpdesk_call`, `helpdesk_email`, `public_app`. Only honoured when sent by a HelpDesk/staff user. Public users always get `public_app` regardless. |
| `file_0` | file | No | First attachment (image/pdf/xls/xlsx, max 10 MB) |
| `file_1` | file | No | Second attachment |
| `file_2` | file | No | Third attachment (add more as `file_3`, `file_4`, etc.) |

> **Note on files:** Use keys `file_0`, `file_1`, `file_2`, ... for multiple files. All file keys starting with `file` are processed. Invalid files (wrong type, too large) are silently skipped.

#### Success Response — `201 Created`

```json
{
  "message": "Ticket created successfully",
  "ticket_ref": "TKT-2026-00001",
  "id": 1
}
```

| Field | Type | Description |
|-------|------|-------------|
| `message` | string | Confirmation message |
| `ticket_ref` | string | Human-readable reference number — show this to the user |
| `id` | integer | Internal ticket ID (used in other API calls) |

#### Error Responses

| HTTP Code | Body | When |
|-----------|------|------|
| `400` | `{"error": "applicant_name is required"}` | Missing required field |
| `400` | `{"error": "applicant_phone is required"}` | Missing required field |
| `400` | `{"error": "title is required"}` | Missing required field |
| `400` | `{"error": "details is required"}` | Missing required field |

#### Example — Anonymous (Public App)

```
POST /api/complaint/create/
Content-Type: multipart/form-data

applicant_name = "Rahul Sharma"
applicant_phone = "9876543210"
applicant_email = "rahul@example.com"
title = "Broken street light near bus stand"
details = "The street light on NH-37 near Central Bus Stand has been non-functional for 2 weeks."
file_0 = [image.jpg]
```

#### Example — HelpDesk creating on behalf of caller

```
POST /api/complaint/create/
Authorization: Bearer <helpdesk_token>
Content-Type: multipart/form-data

applicant_name = "Priya Devi"
applicant_phone = "9123456789"
title = "Vehicle harassment complaint"
details = "Caller reported that vehicle MH-12-AB-1234 was driving recklessly."
source = "helpdesk_call"
```

---

### 6.2 List Tickets

**`GET /api/complaint/list/`**

**Auth:** Required — roles: `helpdesk`, `teamleader`, `sosexecutive`, `stateadmin`, `superadmin`

#### Query Parameters (all optional)

| Parameter | Type | Description |
|-----------|------|-------------|
| `status` | string | Filter by status. One of: `created`, `in_review`, `pending`, `closed`, `canceled` |
| `source` | string | Filter by source. One of: `public_app`, `helpdesk_call`, `helpdesk_email` |
| `search` | string | Search across: ticket_ref, applicant_name, applicant_phone, applicant_email, title |
| `page` | integer | Page number (default: `1`) |
| `page_size` | integer | Results per page (default: `20`, max: `100`) |

#### Success Response — `200 OK`

```json
{
  "total": 150,
  "page": 1,
  "page_size": 20,
  "results": [
    {
      "id": 1,
      "ticket_ref": "TKT-2026-00001",
      "applicant_name": "Rahul Sharma",
      "applicant_phone": "9876543210",
      "applicant_email": "rahul@example.com",
      "title": "Broken street light near bus stand",
      "details": "The street light on NH-37 near Central Bus Stand has been non-functional for 2 weeks.",
      "status": "created",
      "source": "public_app",
      "solution": null,
      "final_report_file": null,
      "entry_date": "2026-06-08",
      "created_at": "2026-06-08T10:30:00.000000Z",
      "updated_at": "2026-06-08T10:30:00.000000Z",
      "created_by": null,
      "attachments": [
        {
          "id": 1,
          "file_name": "image.jpg",
          "file_path": "fileuploads/complaints/abc123def456.jpg",
          "uploaded_at": "2026-06-08T10:30:00.000000Z"
        }
      ]
    }
  ]
}
```

#### Response Field Reference

| Field | Type | Description |
|-------|------|-------------|
| `total` | integer | Total number of matching tickets |
| `page` | integer | Current page number |
| `page_size` | integer | Number of results in this page |
| `results` | array | Array of ticket objects (see below) |

**Ticket Object Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `id` | integer | Internal ID — use in other API URLs |
| `ticket_ref` | string | Human-readable reference, e.g. `TKT-2026-00001` |
| `applicant_name` | string | Full name of complainant |
| `applicant_phone` | string | Phone number |
| `applicant_email` | string \| null | Email (null if not provided) |
| `title` | string | Ticket title |
| `details` | string | Full complaint description |
| `status` | string | Current status (see enum) |
| `source` | string | How ticket was created (see enum) |
| `solution` | string \| null | Resolution text (null until submitted) |
| `final_report_file` | string \| null | MinIO path of final report file (null until uploaded) |
| `entry_date` | string | Date of ticket creation (`YYYY-MM-DD`) |
| `created_at` | string | Full datetime of creation (ISO 8601 UTC) |
| `updated_at` | string | Full datetime of last update (ISO 8601 UTC) |
| `created_by` | integer \| null | User ID of creator (null for anonymous) |
| `attachments` | array | List of attached files (see below) |

**Attachment Object Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `id` | integer | Attachment ID |
| `file_name` | string | Original filename |
| `file_path` | string | MinIO object key (use with file download endpoint) |
| `uploaded_at` | string | ISO 8601 datetime |

#### Error Responses

| HTTP Code | Body | When |
|-----------|------|------|
| `401` | `{"detail": "Authentication credentials were not provided."}` | No token |
| `403` | `{"error": "Access denied"}` | Role not permitted |

---

### 6.3 Ticket Detail

**`GET /api/complaint/<id>/`**

**Auth:** Required — roles: `helpdesk`, `teamleader`, `sosexecutive`, `stateadmin`, `superadmin`

#### URL Parameter

| Parameter | Type | Description |
|-----------|------|-------------|
| `id` | integer | The ticket's internal ID |

#### Success Response — `200 OK`

Returns a single ticket object. Identical structure to one item in the `results` array from [List Tickets](#62-list-tickets).

```json
{
  "id": 1,
  "ticket_ref": "TKT-2026-00001",
  "applicant_name": "Rahul Sharma",
  "applicant_phone": "9876543210",
  "applicant_email": "rahul@example.com",
  "title": "Broken street light near bus stand",
  "details": "The street light on NH-37 near Central Bus Stand has been non-functional for 2 weeks.",
  "status": "in_review",
  "source": "public_app",
  "solution": null,
  "final_report_file": null,
  "entry_date": "2026-06-08",
  "created_at": "2026-06-08T10:30:00.000000Z",
  "updated_at": "2026-06-08T11:00:00.000000Z",
  "created_by": null,
  "attachments": [
    {
      "id": 1,
      "file_name": "image.jpg",
      "file_path": "fileuploads/complaints/abc123def456.jpg",
      "uploaded_at": "2026-06-08T10:30:00.000000Z"
    }
  ]
}
```

#### Error Responses

| HTTP Code | Body | When |
|-----------|------|------|
| `401` | `{"detail": "Authentication credentials were not provided."}` | No token |
| `403` | `{"error": "Access denied"}` | Role not permitted |
| `404` | `{"error": "Ticket not found"}` | Invalid ID |

---

### 6.4 Update Status

**`PATCH /api/complaint/<id>/update-status/`**

**Auth:** Required — roles: `helpdesk`, `teamleader`, `sosexecutive`, `stateadmin`, `superadmin`

**Content-Type:** `application/json`

#### URL Parameter

| Parameter | Type | Description |
|-----------|------|-------------|
| `id` | integer | Ticket internal ID |

#### Request Body

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `status` | string | ✅ Yes | New status value. Must be a valid transition from current status (see [Section 4](#4-status-transition-rules)) |
| `comment` | string | No | Optional note explaining the status change (logged in activity trail) |
| `solution` | string | No | Resolution text. Only used when moving to `closed` and no solution exists yet |

#### Example Request

```json
{
  "status": "in_review",
  "comment": "Ticket has been picked up for investigation."
}
```

#### Example — Closing with solution

```json
{
  "status": "closed",
  "solution": "Street light repaired by PWD team on 10 June 2026.",
  "comment": "Issue resolved and verified."
}
```

#### Success Response — `200 OK`

```json
{
  "message": "Status updated",
  "status": "in_review"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `message` | string | Confirmation |
| `status` | string | The new current status of the ticket |

#### Special Case — No Change

If `status` sent equals the current status:

```json
{
  "message": "Status unchanged",
  "status": "in_review"
}
```

#### Error Responses

| HTTP Code | Body | When |
|-----------|------|------|
| `400` | `{"error": "Invalid status. Choices: [...]"}` | Unknown status value |
| `400` | `{"error": "Cannot move from \"created\" to \"closed\"."}` | Invalid transition |
| `401` | `{"detail": "Authentication credentials were not provided."}` | No token |
| `403` | `{"error": "Access denied"}` | Role not permitted |
| `404` | `{"error": "Ticket not found"}` | Invalid ID |

---

### 6.5 Submit Final Report

**`POST /api/complaint/<id>/final-report/`**

**Auth:** Required — roles: `helpdesk`, `teamleader`, `sosexecutive`, `stateadmin`, `superadmin`

**Content-Type:** `multipart/form-data`

> At least one of `solution` (text) or `final_report` (file) must be provided.

#### URL Parameter

| Parameter | Type | Description |
|-----------|------|-------------|
| `id` | integer | Ticket internal ID |

#### Request Body

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `solution` | string | No* | Resolution text summary |
| `final_report` | file | No* | Final report file (PDF, image, XLS, XLSX — max 10 MB) |

> *At least one of these is required.

#### Example Request (multipart)

```
POST /api/complaint/1/final-report/
Authorization: Bearer <token>
Content-Type: multipart/form-data

solution = "Street light repaired by PWD on 10 June 2026. Work order #PWD-2026-441."
final_report = [report.pdf]
```

#### Success Response — `200 OK`

```json
{
  "message": "Final report submitted"
}
```

#### Error Responses

| HTTP Code | Body | When |
|-----------|------|------|
| `400` | `{"error": "Provide solution text and/or a final_report file."}` | Both fields missing |
| `401` | `{"detail": "Authentication credentials were not provided."}` | No token |
| `403` | `{"error": "Access denied"}` | Role not permitted |
| `404` | `{"error": "Ticket not found"}` | Invalid ID |

---

### 6.6 Add Comment

**`POST /api/complaint/<id>/comment/`**

**Auth:** Required — roles: `helpdesk`, `teamleader`, `sosexecutive`, `stateadmin`, `superadmin`

**Content-Type:** `application/json`

#### URL Parameter

| Parameter | Type | Description |
|-----------|------|-------------|
| `id` | integer | Ticket internal ID |

#### Request Body

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `comment` | string | ✅ Yes | The comment text to add to the activity trail |

#### Example Request

```json
{
  "comment": "Called applicant — confirmed issue is still ongoing. Escalating to field team."
}
```

#### Success Response — `201 Created`

```json
{
  "message": "Comment added"
}
```

#### Error Responses

| HTTP Code | Body | When |
|-----------|------|------|
| `400` | `{"error": "comment is required"}` | Empty comment |
| `401` | `{"detail": "Authentication credentials were not provided."}` | No token |
| `403` | `{"error": "Access denied"}` | Role not permitted |
| `404` | `{"error": "Ticket not found"}` | Invalid ID |

---

### 6.7 Activity Log

**`GET /api/complaint/<id>/activity/`**

**Auth:** Required — roles: `helpdesk`, `teamleader`, `sosexecutive`, `stateadmin`, `superadmin`

#### URL Parameter

| Parameter | Type | Description |
|-----------|------|-------------|
| `id` | integer | Ticket internal ID |

#### Success Response — `200 OK`

```json
{
  "ticket_ref": "TKT-2026-00001",
  "activities": [
    {
      "id": 1,
      "actor_name": "Anonymous",
      "action_type": "created",
      "old_value": null,
      "new_value": "TKT-2026-00001",
      "comment": null,
      "timestamp": "2026-06-08T10:30:00.000000Z"
    },
    {
      "id": 2,
      "actor_name": "Ananya Das",
      "action_type": "status_change",
      "old_value": "created",
      "new_value": "in_review",
      "comment": "Picked up for review.",
      "timestamp": "2026-06-08T11:05:00.000000Z"
    },
    {
      "id": 3,
      "actor_name": "Ananya Das",
      "action_type": "comment",
      "old_value": null,
      "new_value": null,
      "comment": "Called applicant. Confirmed the light is still broken.",
      "timestamp": "2026-06-08T11:20:00.000000Z"
    },
    {
      "id": 4,
      "actor_name": "Ananya Das",
      "action_type": "final_report",
      "old_value": null,
      "new_value": "report.pdf",
      "comment": "Street light repaired by PWD on 10 June 2026.",
      "timestamp": "2026-06-10T15:00:00.000000Z"
    }
  ]
}
```

**Activity Object Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `id` | integer | Activity record ID |
| `actor_name` | string | Name of the person who performed the action (`"Anonymous"` for public) |
| `action_type` | string | One of: `created`, `status_change`, `comment`, `final_report`, `attachment` |
| `old_value` | string \| null | Previous value (used for `status_change`: the old status) |
| `new_value` | string \| null | New value (for `status_change`: new status; for `attachment`/`final_report`: filename) |
| `comment` | string \| null | Free-text note (present for `comment` and optionally for `status_change`, `final_report`) |
| `timestamp` | string | ISO 8601 UTC datetime of the action |

#### Error Responses

| HTTP Code | Body | When |
|-----------|------|------|
| `401` | `{"detail": "Authentication credentials were not provided."}` | No token |
| `403` | `{"error": "Access denied"}` | Role not permitted |
| `404` | `{"error": "Ticket not found"}` | Invalid ID |

---

### 6.8 Public Ticket Tracker

**`GET /api/complaint/track/<ticket_ref>/`**

**Auth:** None required — fully public endpoint

#### URL Parameter

| Parameter | Type | Description |
|-----------|------|-------------|
| `ticket_ref` | string | The ticket reference number (case-insensitive), e.g. `TKT-2026-00001` |

#### Success Response — `200 OK`

```json
{
  "ticket_ref": "TKT-2026-00001",
  "title": "Broken street light near bus stand",
  "status": "closed",
  "entry_date": "2026-06-08",
  "updated_at": "2026-06-10T15:00:00.000000Z",
  "solution": "Street light repaired by PWD on 10 June 2026.",
  "activities": [
    {
      "action_type": "created",
      "new_value": "TKT-2026-00001",
      "comment": null,
      "timestamp": "2026-06-08T10:30:00.000000Z"
    },
    {
      "action_type": "status_change",
      "new_value": "in_review",
      "comment": null,
      "timestamp": "2026-06-08T11:05:00.000000Z"
    },
    {
      "action_type": "comment",
      "new_value": null,
      "comment": "Called applicant. Confirmed the light is still broken.",
      "timestamp": "2026-06-08T11:20:00.000000Z"
    },
    {
      "action_type": "status_change",
      "new_value": "closed",
      "comment": null,
      "timestamp": "2026-06-10T15:00:00.000000Z"
    }
  ]
}
```

> **Note:** This response intentionally omits internal-only fields: `applicant_phone`, `applicant_email`, `details`, `final_report_file`, `created_by`, and attachment paths. Only `created`, `status_change`, and `comment` activities are shown (not `attachment` or `final_report` actions).

**Response Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `ticket_ref` | string | Reference number |
| `title` | string | Ticket title/subject |
| `status` | string | Current status |
| `entry_date` | string | Date filed (`YYYY-MM-DD`) |
| `updated_at` | string | Last updated datetime (ISO 8601 UTC) |
| `solution` | string \| null | Resolution summary (null until resolved) |
| `activities` | array | Public-safe activity timeline |

#### Error Responses

| HTTP Code | Body | When |
|-----------|------|------|
| `404` | `{"error": "Ticket not found"}` | Invalid or non-existent ticket_ref |

---

## 7. Error Response Format

All error responses follow one of two formats:

**Application errors (field validation, access control, business logic):**
```json
{
  "error": "Human-readable error message"
}
```

**Framework-level auth errors (DRF default):**
```json
{
  "detail": "Authentication credentials were not provided."
}
```

### HTTP Status Codes Used

| Code | Meaning |
|------|---------|
| `200` | Success (GET, PATCH) |
| `201` | Created (POST — ticket created, comment added) |
| `400` | Bad Request — validation error or invalid input |
| `401` | Unauthorized — missing or invalid token |
| `403` | Forbidden — valid token but role not allowed |
| `404` | Not Found — ticket ID/ref does not exist |

---

## 8. Frontend Pages — Full Specification

---

### Page A: Public Complaint Submission Form

**URL suggestion:** `/complaint/submit`
**Access:** Public (no login required)
**Purpose:** Allows any citizen to file a complaint.

#### UI Elements

| Element | Details |
|---------|---------|
| Form title | "Submit a Complaint" |
| Applicant Name field | Text input, required |
| Phone Number field | Text input, required, numeric validation |
| Email field | Email input, optional |
| Complaint Title field | Text input, required, max 500 chars |
| Complaint Details textarea | Multi-line text, required |
| File Attachment section | Multiple file upload, accept: `.jpg,.jpeg,.png,.pdf,.xls,.xlsx`, max 10 MB each. Show file name + remove button for each selected file. Keys: `file_0`, `file_1`, etc. |
| Submit button | Triggers API call |
| Success state | Hide form, show success card with ticket reference number prominently displayed. Show message: "Your complaint has been registered. Reference number: **TKT-2026-00001**. Save this number to track your complaint status." Include link to Page B. |
| Error state | Show inline field errors |

#### API Used
- **Submit:** `POST /api/complaint/create/` (no auth header)

#### Notes
- Use `multipart/form-data` when files are attached; `application/json` otherwise (or always use multipart for simplicity).
- After success, prominently show `ticket_ref` — the user has no other way to track without this.

---

### Page B: Public Ticket Status Tracker

**URL suggestion:** `/complaint/track`
**Access:** Public (no login required)
**Purpose:** Allows anyone to check the status of their complaint using the reference number.

#### UI Elements

| Element | Details |
|---------|---------|
| Search bar | Text input labelled "Enter your ticket reference number (e.g. TKT-2026-00001)" |
| Track button | Triggers API call |
| Result card (on success) | Show: Reference No., Title, Status badge (colour-coded), Date Filed, Last Updated, Resolution/Solution text (if present) |
| Timeline section | Show activity log as a vertical timeline. For each entry: icon by action_type, timestamp, short label. For `comment` entries, show the comment text. |
| Status badge colours | `created` = grey, `in_review` = blue, `pending` = orange, `closed` = green, `canceled` = red |
| Error state | "No ticket found with this reference number." |

#### API Used
- **Lookup:** `GET /api/complaint/track/<ticket_ref>/`

#### Notes
- Case-insensitive: accept lowercase input from user, the API handles uppercase matching.
- Pre-fill the search field if `?ref=TKT-2026-00001` query param is in the URL (deep-linkable from Page A success state).

---

### Page C: HelpDesk Dashboard

**URL suggestion:** `/helpdesk/complaints`
**Access:** Authenticated — role: `helpdesk` only
**Purpose:** Central workspace for HelpDesk staff to see all tickets and take action.

#### UI Elements

| Element | Details |
|---------|---------|
| "New Ticket" button | Navigates to Page D |
| Stats bar (top) | Counts of tickets by status: Total, Created, In Review, Pending, Closed, Canceled. Each clickable to filter. |
| Filter bar | Dropdowns: Status (all/created/in_review/pending/closed/canceled), Source (all/helpdesk_call/helpdesk_email/public_app). Search box. |
| Ticket table/list | Columns: Ref No., Applicant Name, Phone, Title, Source badge, Status badge, Date Filed, Last Updated, Actions |
| Actions per row | "View" button → Page E |
| Pagination | page / page_size controls |
| Empty state | "No tickets found." |

#### APIs Used
- **Load list:** `GET /api/complaint/list/` with query params for filters + pagination
- **Navigate to create:** goes to Page D

---

### Page D: Create Ticket on Behalf of Public (HelpDesk)

**URL suggestion:** `/helpdesk/complaints/new`
**Access:** Authenticated — role: `helpdesk` only
**Purpose:** HelpDesk staff creates a ticket for a public user who called or emailed.

#### UI Elements

| Element | Details |
|---------|---------|
| Source selector | Required. Radio/dropdown: "Phone Call" (`helpdesk_call`) / "Email" (`helpdesk_email`) |
| Applicant Name field | Text input, required |
| Phone Number field | Text input, required |
| Email field | Email input, optional |
| Complaint Title field | Text input, required |
| Complaint Details textarea | Multi-line text, required |
| File Attachment section | Multiple file upload (same rules as Page A). Label: "Attach photos or documents shared by applicant" |
| Submit button | |
| Cancel button | Navigate back to Page C |
| Success state | Show success message with ticket ref. Offer: "Create Another Ticket" or "View Ticket" (→ Page E) |

#### API Used
- **Submit:** `POST /api/complaint/create/` with `Authorization: Bearer <token>` and `source` field set to `helpdesk_call` or `helpdesk_email`

---

### Page E: Ticket Detail & Management (Staff)

**URL suggestion:** `/helpdesk/complaints/<id>` (or `/complaints/<id>` shared across roles)
**Access:** Authenticated — roles: `helpdesk`, `teamleader`, `sosexecutive`, `stateadmin`, `superadmin`
**Purpose:** Full view of a single ticket with all management actions.

#### Sections

**1. Ticket Header**
- Ticket Ref (bold, prominent), Status badge, Source badge
- Entry Date, Last Updated

**2. Applicant Information Panel**
- Name, Phone, Email

**3. Complaint Details Panel**
- Title, Full Details text

**4. Attachments Panel**
- List all attachments with filename, upload date, and a download/view link
- Link built using `file_path` via the system's file download endpoint

**5. Status Management Panel**

> Show only if ticket is not `closed` or `canceled`.

| Element | Details |
|---------|---------|
| Current status display | Status badge |
| Change Status dropdown | Only show valid next statuses based on current (see [Section 4](#4-status-transition-rules)) |
| Comment field | Optional text field "Add a note for this status change" |
| Solution field | Only show when moving to `closed`. Label: "Resolution Summary" |
| Update Status button | Calls update-status API |

**6. Final Report Panel**

| Element | Details |
|---------|---------|
| Solution text display | Show if `solution` is set, otherwise show "Not submitted yet" |
| Final Report File | Show download link if `final_report_file` is set |
| Submit/Update Report form | Text area for solution, file upload for report file. Button: "Submit Final Report" |

**7. Add Comment Panel**
- Textarea labelled "Add internal note/comment"
- "Add Comment" button

**8. Activity Timeline**
- Full chronological timeline showing all actions
- Each entry: avatar/icon, actor name, action description, timestamp
- For `status_change`: show "Status changed from **X** to **Y**" + comment if present
- For `comment`: show comment text in a speech-bubble style
- For `final_report`: show "Final report submitted" + filename if present
- For `attachment`: show "File attached: filename"
- For `created`: show "Ticket created"

#### APIs Used

| Action | API |
|--------|-----|
| Load ticket data | `GET /api/complaint/<id>/` |
| Load activity log | `GET /api/complaint/<id>/activity/` |
| Change status | `PATCH /api/complaint/<id>/update-status/` |
| Submit final report | `POST /api/complaint/<id>/final-report/` |
| Add comment | `POST /api/complaint/<id>/comment/` |

#### Notes
- Load ticket detail and activity log in parallel on page mount.
- After any write action (status change, comment, report), reload both the ticket detail and activity log to reflect changes.
- Disable the "Update Status" button if the new status is the same as current.

---

### Page F: Staff Ticket List (TeamLead / SOS Executive)

**URL suggestion:** `/complaints` (shared route, same component as Page C but adapted by role)
**Access:** Authenticated — roles: `teamleader`, `sosexecutive`
**Purpose:** Read + manage access to all tickets. Identical to HelpDesk Dashboard but without the "New Ticket" button (these roles don't create tickets).

#### UI Elements
Same as Page C but:
- No "New Ticket" button
- No source filter needed (can include for filtering only)

#### APIs Used
- **Load list:** `GET /api/complaint/list/`
- **Navigate to detail:** Page E

---

### Page G: Admin Ticket List (StateAdmin / SuperAdmin)

**URL suggestion:** `/admin/complaints`
**Access:** Authenticated — roles: `stateadmin`, `superadmin`
**Purpose:** Full oversight view. All tickets visible. Can take all actions.

#### UI Elements

Same as Page C, plus:
- Additional stats: breakdown by source (call/email/public)
- Export button (optional, future)
- No "New Ticket" button

#### Additional Recommended Metrics Row

| Stat | Calculation |
|------|-------------|
| Total Tickets | count all |
| Open (unresolved) | count status in `created`, `in_review`, `pending` |
| Resolved Today | count `closed`, `entry_date` = today |
| Canceled | count `canceled` |

#### APIs Used
- **Load list:** `GET /api/complaint/list/` (all filters available)
- **Navigate to detail:** Page E (full action access)

---

## 9. Role-to-Page Access Matrix

| Role | Page A | Page B | Page C | Page D | Page E | Page F | Page G |
|------|--------|--------|--------|--------|--------|--------|--------|
| **Public (anonymous)** | ✅ Submit | ✅ Track | ❌ | ❌ | ❌ | ❌ | ❌ |
| **Owner / App user** | ✅ Submit (with token) | ✅ Track | ❌ | ❌ | ❌ | ❌ | ❌ |
| **HelpDesk** | — | ✅ | ✅ Dashboard | ✅ Create | ✅ Full detail | — | — |
| **TeamLead** | — | — | — | — | ✅ Full detail | ✅ List | — |
| **SOS Executive** | — | — | — | — | ✅ Full detail | ✅ List | — |
| **StateAdmin** | — | — | — | — | ✅ Full detail | — | ✅ Admin list |
| **SuperAdmin** | — | — | — | — | ✅ Full detail | — | ✅ Admin list |

> **Note:** Page E (Ticket Detail) is a shared page. The same component is used by all staff roles. Only the navigation entry point differs. All five staff roles can perform all write actions on Page E (update status, submit report, add comment).

---

## Appendix: Quick Reference — All Endpoints

| # | Method | Endpoint | Auth | Roles |
|---|--------|----------|------|-------|
| 1 | POST | `/api/complaint/create/` | Optional | Anyone |
| 2 | GET | `/api/complaint/list/` | Required | helpdesk, teamleader, sosexecutive, stateadmin, superadmin |
| 3 | GET | `/api/complaint/<id>/` | Required | Same as above |
| 4 | PATCH | `/api/complaint/<id>/update-status/` | Required | Same as above |
| 5 | POST | `/api/complaint/<id>/final-report/` | Required | Same as above |
| 6 | POST | `/api/complaint/<id>/comment/` | Required | Same as above |
| 7 | GET | `/api/complaint/<id>/activity/` | Required | Same as above |
| 8 | GET | `/api/complaint/track/<ticket_ref>/` | **None** | Public |
