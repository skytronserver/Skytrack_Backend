# Device Tagging Step 4: SMS Checks

Added 2026-11-05. Code: `skytron_api/tagging_sms_views.py`, `skytron_api/device_sms.py`.

During tagging step 4, after the packet check, the dealer runs three SMS checks:

1. **Health check on profile 1.** `@SET SENDHCHK-1*` is SMSed to the primary SIM number. The device replies by SMS with
   `HCHKR,000000,<vendor>,<fw>,<imei>,1,<lat>,N,<lon>,E,<fix>,<date time>,<heading>,<speed>,<csq>,<mcc>,<mnc>,<lac>,<mainpwr>,<ign>,<vin>,<frame>,<mode>`.
2. **Health check on profile 2.** Send `@SETPROF-2*` and wait 2–5 minutes for the device to re-register. Then the same request goes to the secondary SIM number. Switching back to profile 1 afterwards is recommended.
3. **Activation (last).** `ACTV,<6-digit code>,9181016496` is SMSed. The device replies with `ACTVR,<same code>,<vendor>,<fw>,<imei>,...`. Activation unlocks only after both health checks have passed. If no reply arrives, a new code can be sent 30 minutes after the last one.

## How messages are sent and matched

- **Sending.** SMS leave from our Airtel VMN; see `DEVICE_SMS_VIA` in `device_sms.py`.
- **Receiving.** Replies are read from `AirtelSmsInLog` and `SmppSmsIn`.
- **SIM numbers.** These come from the step 2 M2M check (`m2m_primary_msisdn` / `m2m_fallback_msisdn`), falling back to `DeviceStock.msisdn1/2`.
- **Profile of a health reply.** It counts for profile n when it came from SIM number n. Otherwise it counts for the profile the device was on: the last SETPROF the device acknowledged, or the last one sent from tagging.

## Gating

By default (`TAGGING_SMS_CHECKS_REQUIRED` unset or 1) step 4 completes, and the entry moves to step 5, only when all packets are received **and** all three SMS checks have passed. With `TAGGING_SMS_CHECKS_REQUIRED=0` the checks are shown and recorded but do not block step 4.

`POST /api/device-tagging/step4/` now also returns `data.sms_checks` (the status object below).

## APIs (dealer, entry must be at step 4)

### POST `/api/device-tagging/step4/sms/send/`

```json
{"id": 12, "action": "set_profile", "profile": 2}
{"id": 12, "action": "health", "profile": 1}
{"id": 12, "action": "activation"}
```

| action | SMS | sent to | limits |
|---|---|---|---|
| `set_profile` | `@SETPROF-<n>*` | SIM of the profile the device is on now | 1 per minute |
| `health` | `@SET SENDHCHK-1*` | SIM of `profile` | 1 per 2 minutes per profile; refused once passed |
| `activation` | `ACTV,<code>,9181016496` | SIM of the current profile | needs both health checks; resend 30 min after the last; refused once passed |

- **200:** `{"status": "success", "message": "...", "command": {...}, "data": <status>}`.
- **400:** a bad action or profile, a check already passed, or activation still locked.
- **429:** a resend came too early; the body includes `retry_at`.
- **502:** the SMS could not be sent; the body includes `data`.

### POST `/api/device-tagging/step4/sms/status/`

```json
{"id": 12}
```

```json
{
  "status": "success",
  "data": {
    "required": true,
    "all_passed": false,
    "msisdn1": "5754206414333",
    "msisdn2": "5754206414944",
    "reply_number": "9181016496",
    "current_profile": 2,
    "profile_cooldown_until": null,
    "steps": [
      {"key": "health_p1", "profile": 1, "sms_to": "5754206414333", "passed": true,
       "result": {"passed": true, "passed_at": "...", "network": "405/56", "sms": {"sender": "...", "text": "HCHKR,...", "received_at": "..."}},
       "last_sent_at": "...", "next_send_at": null, "device_on_profile": false},
      {"key": "health_p2", "...": "..."},
      {"key": "activation", "sms_to": "...", "passed": false, "codes_sent": ["654321"], "can_send": false,
       "next_send_at": "<last send + 30 min>", "blocked_reason": null}
    ],
    "commands": [{"id": 3, "kind": "activation", "command_sent": "ACTV,654321,9181016496", "sms_to": "...", "send_status": "queued", "sms_status": "delivered", "sent_at": "..."}]
  }
}
```

Checks that have passed are stored on `DeviceStockMaster.sms_checks` and stay passed.

Every command sent is stored in `DeviceTaggingSmsCommand` (table `device_tagging_sms_command`).
