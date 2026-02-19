# SkyTrack API updates for Frontend (Feb 2026)

Scope: **Manufacturer** + **eSimProvider** create/update/filter, including **Manufacturer ↔ eSimProvider (M2M)** assignment and the newly added fields.

---

## General notes (important)

### Authentication
- **Non-public** endpoints require authentication (DRF auth). In practice this is typically:
  - `Authorization: Token <token>`
- Some endpoints also enforce roles (e.g. `superadmin`).

### Content-Type
- Endpoints that accept files should be sent as **`multipart/form-data`**.
- Text-only payloads can be JSON, but these specific create endpoints always include file uploads, so use multipart.

### File upload validation (via `save_file()`)
- Max size: **1 MB**
- Allowed types:
  - `image/png`, `image/jpeg`, `application/pdf`, `application/vnd.ms-excel`, `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`
- Executable-like files are rejected.
- Stored in DB as a **relative path string** (example: `fileuploads/man/<random>.pdf`).

### Array input format (for `telecomProviders`)
Backend accepts multiple formats:
- `telecomProviders[]` (recommended): repeat the key multiple times
  - `telecomProviders[]=Airtel`, `telecomProviders[]=Jio`
- `telecomProviders` as a JSON string
  - `"[\"Airtel\",\"Jio\"]"`
- `telecomProviders` as comma-separated string
  - `"Airtel,Jio"`
- Alternate key supported: `telecom_providers`

---

## eSimProvider APIs

### 1) Create eSimProvider (non-public)
- **URL**: `/eSimProvider/create_eSimProvider/`
- **Method**: `POST`
- **Auth**: required (`superadmin`)
- **Content-Type**: `multipart/form-data`

**New field added**
- `telecomProviders` (array of small strings)

**Request fields (common)**
- Company:
  - `company_name`
  - `gstnnumber`
  - `gstno` (optional)
  - `idProofno` (optional)
  - `stateId` (note the key is `stateId`)
- User creation (used by backend `create_user()`):
  - `email`
  - `mobile`
  - `name`
  - `dob`
- New:
  - `telecomProviders[]` (preferred) or `telecomProviders`

**Required files**
- `file_authLetter`
- `file_companRegCertificate`
- `file_GSTCertificate`
- `file_idProof`

**Response**
- Returns a full `eSimProvider` object (serializer: `eSimProviderSerializer`) including:
  - `telecomProviders: []`
  - `users: [...]`
  - `state: {...}`

---

### 2) Create eSimProvider (public)
- **URL**: `/pub/eSimProvider/create_eSimProvider/`
- **Method**: `POST`
- **Auth**: not required
- **Content-Type**: `multipart/form-data`

Same request/response contract as non-public create, including `telecomProviders`.

---

### 3) Update eSimProvider (non-public)
- **URL**: `/eSimProvider/update_eSimProvider/`
- **Method**: `POST`
- **Auth**: required (`superadmin` + must be creator)
- **Content-Type**: `multipart/form-data` (recommended if uploading replacement docs)

**Request fields**
- Required:
  - `esimprovider_id`
- Optional updates:
  - `company_name`, `gstnnumber`, `gstno`, `idProofno`
  - `email`, `mobile`, `name`, `dob`
  - `telecomProviders[]` or `telecomProviders` (replaces entire list)

**Optional replacement files** (if provided, they overwrite the stored path)
- `file_authLetter`
- `file_companRegCertificate`
- `file_GSTCertificate`
- `file_idProof`

---

### 4) Filter eSimProvider
- **URL**: `/eSimProvider/filter_eSimProvider/`
- **Method**: `POST`
- **Auth**: required
  - role behavior varies (stateadmin/devicemanufacture logic exists)

**Useful filter keys**
- `eSimProvider_id`, `email`, `company_name`, `name`, `phone_no`, `state`

**Response**
- List of eSimProviders; each item includes `telecomProviders`.

---

### 5) Delete eSimProvider
- **URL**: `/eSimProvider/delete_eSimProvider/<id>/`
- **Method**: `DELETE`
- **Auth**: required (`superadmin`)

---

## Manufacturer APIs

### 1) Create Manufacturer (non-public)
- **URL**: `/manufacturer/create_manufacturer/`
- **Method**: `POST`
- **Auth**: required (`superadmin`)
- **Content-Type**: `multipart/form-data`

**New fields added**
- `tac` (text)
- `device_model_details` (text)
- `file_affidavitNda` (file upload, optional)

**Request fields (common)**
- Company:
  - `company_name`
  - `gstnnumber`
  - `gstno` (optional)
  - `idProofno` (optional)
  - `state` (note the key is `state`, not `stateId`)
- User creation (used by backend `create_user()`):
  - `email`
  - `mobile`
  - `name`
  - `dob`
- New:
  - `tac`
  - `device_model_details`

**Required files**
- `file_authLetter`
- `file_companRegCertificate`
- `file_GSTCertificate`
- `file_idProof`

**Optional file**
- `file_affidavitNda`

**Manufacturer ↔ eSimProvider (Many-to-Many assignment)**
- Send eSimProvider IDs as a repeated multipart key:
  - `esimProvider[]=1`
  - `esimProvider[]=2`
- Backend validation:
  - each selected eSimProvider must have `eSimProvider.state.id == state`.
  - if none are valid, API returns `400`.

**Response**
- Returns `ManufacturerSerializer(manufacturer).data`, which includes:
  - `esim_provider: [...]` (nested eSimProvider objects)
    - each nested eSimProvider includes `telecomProviders`
  - `users: [...]`
  - `state: {...}`

---

### 2) Create Manufacturer (public)
- **URL**: `/pub/manufacturer/create_manufacturer/`
- **Method**: `POST`
- **Auth**: not required
- **Content-Type**: `multipart/form-data`

Same request/response contract as non-public create, including the new fields and `esimProvider[]` M2M assignment.

---

### 3) Update Manufacturer
- **URL**: `/manufacturer/update_manufacturer/`
- **Method**: `POST`
- **Auth**: required

Note: as of this change, only the **create** endpoints were updated to accept `tac`, `device_model_details`, and `file_affidavitNda`.
If the frontend needs to update these fields after creation, backend should extend the update endpoint similarly.

---

## Useful supporting endpoint (for dropdowns)

### eSimProvider list for Device Stock flows
- **URL**: `/devicestock/esim_provider_list/`
- **Method**: `GET`

Useful when you need a list of available eSimProviders to populate Manufacturer assignment UI; returned objects include `telecomProviders`.
