# Frontend Integration Document: DeviceModel Technical Onboarding Flow

## Base Setup
- Base URL: `https://api.gromed.in`
- Auth: `Authorization: Bearer <token>`
- Roles:
  - Manufacturer user (`devicemanufacture`)
  - Superadmin user (`superadmin`)

---

## Business Flow (End-to-End)
1. Manufacturer creates a technical onboarding request for one DeviceModel.
2. Manufacturer can view own submitted requests and statuses.
3. Superadmin views all requests.
4. Superadmin marks request as **ongoing evaluation**.
5. Superadmin uploads compatibility report, adds final comment, and sets final decision (**accepted** or **rejected**).
6. Manufacturer sees updated status and final output in own request listing.

---

## Status Lifecycle
`submitted` → `ongoing_evaluation` → `accepted` or `rejected`

- Default on creation: `submitted`
- Only superadmin can move to `ongoing_evaluation`
- Only superadmin can finalize (`accepted`/`rejected`)

---

## 1) Manufacturer: Create Technical Onboarding Request
**Endpoint**
- `POST /devicemodel/technical-onboarding/create/`

**Role Access**
- Manufacturer only

**Important Validation Rules**
- Request can be created only by the same manufacturer user who created the selected DeviceModel.
- Required inputs:
  - `device_model_id`
  - `user_manual_pdf` (PDF file)
  - `ot_command_list_pdf` (PDF file)
  - `demo_devices` (JSON array; minimum 1 item)
- Each `demo_devices` item requires:
  - `device_serial_no`
  - `imei`
  - `ccid1`
  - `ccid2`
  - `msisdn1`
  - `msisdn2`

**Body Type**
- `multipart/form-data`

**Form Data Example**
- `device_model_id`: `12`
- `user_manual_pdf`: `<file.pdf>`
- `ot_command_list_pdf`: `<file.pdf>`
- `demo_devices`:
```json
[
  {
    "device_serial_no": "SN-1001",
    "imei": "356938035643809",
    "ccid1": "8991101200003204512",
    "ccid2": "8991101200003204513",
    "msisdn1": "919876543210",
    "msisdn2": "919876543211"
  }
]
```

---

## 2) Manufacturer: List Own Technical Onboarding Requests
**Endpoint**
- `POST /devicemodel/technical-onboarding/manufacturer/list/`

**Role Access**
- Manufacturer only

**Body Type**
- `application/json`

**Request Body**
```json
{}
```

**Frontend Usage**
- Show request table/list with:
  - request date-time
  - current status
  - device model details
  - report/comment when finalized

---

## 3) Superadmin: List All Technical Onboarding Requests
**Endpoint**
- `POST /devicemodel/technical-onboarding/superadmin/list/`

**Role Access**
- Superadmin only

**Body Type**
- `application/json`

**Request Body**
```json
{}
```

**Frontend Usage**
- Admin dashboard queue of all requests across manufacturers.
- Include manufacturer + device model + demo devices in detail view.

---

## 4) Superadmin: Mark Request as Ongoing Evaluation
**Endpoint**
- `POST /devicemodel/technical-onboarding/superadmin/mark-ongoing/`

**Role Access**
- Superadmin only

**Allowed Current Status**
- Only `submitted` requests

**Body Type**
- `application/json`

**Request Body Example**
```json
{
  "onboarding_request_id": 1,
  "evaluation_datetime": "2026-02-25T12:30:00Z"
}
```

**Notes**
- `evaluation_datetime` is optional; backend sets current time if omitted.

---

## 5) Superadmin: Finalize Request (Accept/Reject + Report + Comment)
**Endpoint**
- `POST /devicemodel/technical-onboarding/superadmin/finalize/`

**Role Access**
- Superadmin only

**Allowed Current Status**
- Only `ongoing_evaluation` requests

**Required Inputs**
- `onboarding_request_id`
- `status` (`accepted` or `rejected`)
- `final_comment`
- `compatibility_report_pdf` (PDF file)

**Body Type**
- `multipart/form-data`

**Form Data Example**
- `onboarding_request_id`: `1`
- `status`: `accepted`
- `final_comment`: `Device model passed technical onboarding checks.`
- `compatibility_report_pdf`: `<file.pdf>`

---

## Common Error Cases (Frontend Handling)
- `400 Bad Request` with `{ "error": "..." }`
  - Invalid role (wrong user type)
  - Invalid or missing required fields
  - Wrong status transition (e.g., finalize before ongoing_evaluation)
  - Non-PDF file upload for required PDF fields
  - Invalid `device_model_id` or `onboarding_request_id`

---

## Suggested Frontend Screens

### Manufacturer
1. **Create Technical Onboarding**
   - Form: DeviceModel selector, User Manual PDF, OT Command PDF, Demo Device list (repeatable rows)
2. **My Onboarding Requests**
   - List with status badges (`submitted`, `ongoing_evaluation`, `accepted`, `rejected`)
   - Detail drawer/modal for report/comment

### Superadmin
1. **Onboarding Request Queue**
   - All requests with filters by status/manufacturer/device model
2. **Evaluation Action**
   - Button: “Mark Ongoing Evaluation”
3. **Final Decision Action**
   - Upload compatibility report PDF
   - Enter final comment
   - Select decision: Accept/Reject

---

## API Sequence Example
1. Manufacturer calls `create`
2. Superadmin calls `superadmin/list`
3. Superadmin calls `mark-ongoing`
4. Superadmin calls `finalize`
5. Manufacturer calls `manufacturer/list` to view updated status and final decision

---

## Reference
- Import-ready collection file is available at:
  - `DeviceModel_Technical_Onboarding_APIs_Postman_Collection.json`
