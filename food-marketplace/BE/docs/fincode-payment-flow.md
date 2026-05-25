# Fincode Payment Integration

## Overview

Project uses [Fincode](https://fincode.jp/) for credit card payment processing.
**3D Secure is DISABLED** (`tds_type: "0"`) for simplified checkout flow.

Base URL: `https://api.test.fincode.jp` (test mode)
Auth: `Authorization: Bearer {FINCODE_SECRET_KEY}`

---

## API Endpoints Used

| Operation | Method | Fincode Endpoint |
|-----------|--------|------------------|
| Create customer | POST | `/v1/customers` |
| Get customer | GET | `/v1/customers/{customer_id}` |
| Create card session | POST | `/v1/card_sessions` |
| List cards | GET | `/v1/customers/{customer_id}/cards` |
| Set default card | PUT | `/v1/customers/{customer_id}/cards/{card_id}` |
| Delete card | DELETE | `/v1/customers/{customer_id}/cards/{card_id}` |
| Register payment | POST | `/v1/payments` |
| Execute payment | PUT | `/v1/payments/{order_id}` |
| Get payment | GET | `/v1/payments/{payment_id}` |
| Change payment (refund) | PUT | `/v1/payments/{order_id}/change` |

---

## Payment Flow

### 1. Customer Registration (idempotent)

```
POST /api/purchase/customers/register
```

- Registers user with Fincode using `user.id` as `customer_id`
- Safe to call multiple times (returns existing ID if already registered)
- Payload to Fincode: `{ id, email, name? }`

### 2. Card Registration

```
POST /api/purchase/card/register?combo_id={optional}
```

- Creates a Fincode card session → returns `card_registration_url`
- Frontend opens URL in popup/new tab
- User enters card info on Fincode hosted page
- After success, Fincode calls webhook → card saved to local DB
- `combo_id` is optional, only used for redirect URL after registration

### 3. List Cards

```
GET /api/purchase/cards/list
```

- Fetches cards **directly from Fincode API** (source of truth)
- Returns: `[{ id, fincode_card_id, card_number_masked, brand, expire, holder_name, is_default }]`

### 4. Payment Execution (2-step)

```
POST /api/purchase/payment
Body: { order_id, card_id }
```

**Important:** Fincode uses `order_number` (e.g. `ORD202501201234561234`) as the payment ID, NOT the UUID `order_id`. The `payments` table stores `order_number` in `fincode_payment_id`.

**Step 1 — Register payment intent:**
```json
POST /v1/payments
{
  "id": "{order_number}",
  "pay_type": "Card",
  "job_code": "CAPTURE",
  "amount": "{amount_as_string}",
  "tds_type": "0",
  "client_field_1": "{shop_id}"
}
```
Response includes `access_id` needed for step 2.

**Step 2 — Execute payment:**
```json
PUT /v1/payments/{order_number}
{
  "pay_type": "Card",
  "access_id": "{from_step_1}",
  "customer_id": "{user_id}",
  "card_id": "{fincode_card_id}",
  "method": "1"
}
```
Response `status`: `"CAPTURED"` = success.

### 5. Card Management

**Set default card:**
```
POST /api/purchase/cards/set-default/{fincode_card_id}
```
Calls Fincode: `PUT /v1/customers/{user_id}/cards/{card_id}` with `{ default_flag: "1" }`

**Delete card:**
```
DELETE /api/purchase/card/delete/{fincode_card_id}
```
Calls Fincode: `DELETE /v1/customers/{user_id}/cards/{card_id}`

---

## Key Design Decisions

| Decision | Detail |
|----------|--------|
| **3D Secure** | Disabled (`tds_type: "0"`) — no redirect/challenge flow |
| **Card ID** | All APIs use **Fincode card ID** directly (not local DB ID) |
| **Customer ID** | `user.id` = Fincode `customer_id` (1:1 mapping) |
| **Amount** | Stored as `int` in DB, sent as `string` to Fincode |
| **Card list source** | Fincode API (not local DB) — always up-to-date |
| **Job code** | `CAPTURE` — immediate capture, no separate auth+capture |

---

## Webhook Endpoints

| Webhook | Path | Purpose |
|---------|------|---------|
| Card registration | `POST /api/purchase-callbacks/webhook/card-registration` | Save card to local DB after user registers |
| Payment execute | `POST /api/purchase-callbacks/webhook/payment-execute` | Async payment confirmation |
| 3D Secure | `POST /api/purchase-callbacks/webhook/3d-secure` | 3D Secure callback (not used, tds disabled) |

---

## Environment Variables

```env
FINCODE_API_BASE_URL=https://api.test.fincode.jp
FINCODE_PUBLIC_KEY=p_test_...
FINCODE_SECRET_KEY=m_test_...
FINCODE_WEBHOOK_SECRET=...
```

---

## File Structure

```
apps/
  integrations/
    fincode_client.py    # FincodeClient class + fincode_client singleton
  payments/
    routers.py           # API endpoints (/purchase/*)
    services.py          # Business logic
    crud.py              # Local DB operations
    schemas.py           # Request/response models
    models.py            # SQLModel (Payment, FincodeUser, Card)
```
