# Sending transactional email

[English](sending.md) | [Русский](ru/sending.md)

Source: [email/send](https://godocs.unisender.ru/web-api-ref#email-send). Checked 2026-10-26, Web API v1.92.

## Send without a template

Save the request to a task JSON file. Replace example addresses and the operation ID with actual task inputs. Addresses under `*.invalid` are deliberately unsuitable for sending.

```json
{
  "message": {
    "from_email": "robot@example.com",
    "from_name": "Store",
    "recipients": [
      {"email": "buyer@example.invalid", "substitutions": {"to_name": "Alex"}}
    ],
    "subject": "Order received",
    "body": {
      "html": "<p>Hello, {{to_name}}! We received your order.</p>",
      "plaintext": "Hello, {{to_name}}! We received your order."
    },
    "idempotence_key": "REPLACE_WITH_STABLE_OPERATION_ID"
  }
}
```

Without `template_id`, provide `from_email`, `subject`, and at least one of `body.html` or `body.plaintext`. The sender domain must be ready; inspect `domain/list` when its readiness is unknown. Each request has 1–500 recipients. Each recipient object contains `email`; `substitutions` and `metadata` are optional. The recipient array is not automatically exposed to everyone as a shared `To` list.

Preview first:

```bash
python3 scripts/unisender_go.py call email/send --data-file message.json
```

When the user has explicitly requested this send to these recipients, execute the same file with `--execute`. Do not substitute test recipients on your own or send a test when the request was only to prepare a draft.

## Existing template

```json
{
  "message": {
    "template_id": "REPLACE_WITH_TEMPLATE_UUID",
    "recipients": [
      {"email": "first@example.invalid", "substitutions": {"to_name": "Alex"}},
      {"email": "second@example.invalid", "substitutions": {"to_name": "Sam"}}
    ],
    "global_substitutions": {"order_number": "42"},
    "idempotence_key": "REPLACE_WITH_STABLE_OPERATION_ID"
  }
}
```

Omitted fields inherit template values; supplied values override them. The client permits template-only sends without duplicate sender/subject/body fields. If template contents are unknown, read `template/get` first and check that the required values exist.

The default `template_engine` is `simple`; `velocity`, `liquid`, and `none` are also available. Per-recipient substitutions override global ones. Variable names start with a Latin letter, followed by Latin letters, digits, or `_`. Escape untrusted values appropriately for the selected template engine rather than inserting them as HTML markup.

## Attachments and options

- `attachments`: objects containing `type` (MIME), `name`, and base64 `content`. Names must be unique and contain no `/`. The documented individual-file limit is 7 MB; account for base64 expansion and total JSON size.
- `inline_attachments`: the same fields; use `cid:NAME` in HTML to reference `name`.
- Total request size is at most 10 MB. The client uses a conservative 10,000,000-byte UTF-8 limit, including base64 and JSON.
- `tags`: at most four unique strings of up to 100 characters each.
- `global_metadata` and `recipients[].metadata` can identify an application operation. For grouping, `campaign_id` accepts a nonnegative decimal integer up to 128 bits or a UUID, not an arbitrary name.
- Do not add `bypass_*` or `skip_unsubscribe=1` by default. These alter suppression/unsubscribe behavior; some require provider support approval.
- Do not copy `track_links=0`/`track_read=0` from provider examples by default: disabling tracking may require support to enable the capability. Use them only when requested and available.

## Result and retry handling

A successful response contains `status: success`, `job_id`, and possibly `emails` and `failed_emails` (address-to-rejection-reason mapping). Distinguish accepted and rejected recipients in the report. The CLI returns exit code **3** for nonempty `failed_emails`, preserving the response and `job_id`. Accepted messages may already be processing; do not resend the complete batch. If all recipients fail, the API may return error code 204.

Generate one `message.idempotence_key` of up to 64 characters per logical send and save it **before the call**, for example as a UUID. Reuse both the key and original payload for the same operation; do not generate a fresh key after a network failure.

The documented deduplication window is **one minute**. Reusing a key does not provide indefinite idempotency. After a timeout, reconcile using any available `job_id`, metadata, webhooks, or the dashboard. If reconciliation is impossible, report the uncertain outcome and do not resend automatically. A new send after resolving the issue requires a deliberate user decision.

`success` and `job_id` establish acceptance, not delivery. Check [delivery events](delivery.md) before claiming delivery.
