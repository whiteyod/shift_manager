# API cURL Test Playbook

This document is a copy/paste-friendly collection of `curl` commands to test the backend API end-to-end.

## Assumptions

- API base URL: `http://127.0.0.1:8000`
- You run `curl` from a shell that supports environment variables.
- OTP codes are printed in the backend console (dev-only).

## 0) Prerequisites

### Start Postgres

```bash
docker compose up -d
```

### Run migrations (Alembic)

```bash
cd backend
poetry run alembic upgrade head
```

### Start the API

```bash
cd backend
poetry run uvicorn app.main:app --reload
```

### Helpful base URL variable

```bash
API_URL="http://127.0.0.1:8000"
```

## 1) OTP Auth (phone registration/login)

### 1.1 Request OTP (dev prints OTP code in server logs)

```bash
curl -X POST "$API_URL/v1/auth/otp/request?phone_national=500100200"
```

Expected response:

```json
{"status":"ok"}
```

### 1.2 Verify OTP -> get access token

Replace `CODE_FROM_SERVER_LOGS` with the printed 6-digit OTP.

```bash
curl -X POST "$API_URL/v1/auth/otp/verify?phone_national=500100200&code=CODE_FROM_SERVER_LOGS"
```

Set `OWNER_TOKEN` (paste token from response):

```bash
OWNER_TOKEN="PASTE_ACCESS_TOKEN_HERE"
```

### 1.3 Who am I? (sanity check)

```bash
curl "$API_URL/v1/me" \
  -H "Authorization: Bearer $OWNER_TOKEN"
```

## 2) Restaurants (workspace / tenant)

### 2.1 Create restaurant

```bash
curl -X POST "$API_URL/v1/restaurants?name=TestRestaurant" \
  -H "Authorization: Bearer $OWNER_TOKEN"
```

Set `RESTAURANT_ID` from response JSON:

```bash
RESTAURANT_ID="PASTE_RESTAURANT_UUID_HERE"
```

### 2.2 List my restaurants

```bash
curl "$API_URL/v1/restaurants" \
  -H "Authorization: Bearer $OWNER_TOKEN"
```

## 3) Invites (owner invites staff)

### 3.1 Create invite (employee)

Notes:
- `role_to_assign` must match your enum values (typically `employee`, `manager`, `owner`).
- This returns a raw invite token only once.

```bash
curl -X POST "$API_URL/v1/restaurants/$RESTAURANT_ID/invites?role_to_assign=employee" \
  -H "Authorization: Bearer $OWNER_TOKEN"
```

Set `INVITE_TOKEN` from response JSON:

```bash
INVITE_TOKEN="PASTE_INVITE_TOKEN_HERE"
```

### 3.2 Create a second user (employee) via OTP

Request OTP:

```bash
curl -X POST "$API_URL/v1/auth/otp/request?phone_national=600100200"
```

Verify OTP (replace `CODE_FROM_SERVER_LOGS`):

```bash
curl -X POST "$API_URL/v1/auth/otp/verify?phone_national=600100200&code=CODE_FROM_SERVER_LOGS"
```

Set `EMPLOYEE_TOKEN` from response:

```bash
EMPLOYEE_TOKEN="PASTE_EMPLOYEE_ACCESS_TOKEN_HERE"
```

### 3.3 Accept invite (employee joins restaurant)

```bash
curl -X POST "$API_URL/v1/invites/accept?token=$INVITE_TOKEN" \
  -H "Authorization: Bearer $EMPLOYEE_TOKEN"
```

### 3.4 Verify employee can see restaurant

```bash
curl "$API_URL/v1/restaurants" \
  -H "Authorization: Bearer $EMPLOYEE_TOKEN"
```

## 4) Shifts (MVP scheduling)

### 4.1 Create shift for a user

Notes:
- Only `OWNER/MANAGER` can create shifts (MVP).
- Use full ISO datetimes.
- Backend stores UTC; UI can convert to Warsaw for display.

You need a `USER_ID` to assign a shift. You can use your own `/v1/me` id, or the employee’s `/v1/me` id.

Get employee user id:

```bash
curl "$API_URL/v1/me" \
  -H "Authorization: Bearer $EMPLOYEE_TOKEN"
```

Set `USER_ID`:

```bash
USER_ID="PASTE_TARGET_USER_UUID_HERE"
```

Create a cross-midnight shift example:

```bash
curl -X POST "$API_URL/v1/restaurants/$RESTAURANT_ID/shifts?user_id=$USER_ID&start_at=2026-01-06T22:00:00Z&end_at=2026-01-07T06:00:00Z" \
  -H "Authorization: Bearer $OWNER_TOKEN"
```

### 4.2 Overlap test (should fail with conflict)

This overlaps the previous shift (starts before it ends).

```bash
curl -X POST "$API_URL/v1/restaurants/$RESTAURANT_ID/shifts?user_id=$USER_ID&start_at=2026-01-07T05:00:00Z&end_at=2026-01-07T10:00:00Z" \
  -H "Authorization: Bearer $OWNER_TOKEN"
```

Expected: HTTP `409` with something like `Shift overlaps existing shift`.

### 4.3 List shifts by date range

Notes:
- Any restaurant member can list shifts (MVP).

```bash
curl "$API_URL/v1/restaurants/$RESTAURANT_ID/shifts?start=2026-01-01T00:00:00Z&end=2026-02-01T00:00:00Z" \
  -H "Authorization: Bearer $EMPLOYEE_TOKEN"
```

## Troubleshooting

### "Not authenticated"

- Usually means you forgot the `Authorization: Bearer ...` header.
- On macOS, be careful with line continuations. Prefer:

```bash
curl -X GET "$API_URL/v1/me" -H "Authorization: Bearer $OWNER_TOKEN"
```

### "incorrect access token"

Common causes:
- You changed `JWT_SECRET` or restarted with a different `.env` value.
- Token expired.

Fix:
- Re-run OTP verify and update your `*_TOKEN` variables.

### DB schema mismatch / missing tables

Fix:

```bash
cd backend
poetry run alembic upgrade head
```
