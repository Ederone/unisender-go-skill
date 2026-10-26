# Webhooks, suppressions, and email validation

[English](webhooks-suppressions.md) | [Русский](ru/webhooks-suppressions.md)

Sources: [webhook](https://godocs.unisender.ru/web-api-ref#webhook), [callback-format](https://godocs.unisender.ru/web-api-ref#callback-format), [suppression](https://godocs.unisender.ru/web-api-ref#suppression), [email/subscribe](https://godocs.unisender.ru/web-api-ref#email-subscribe), [email-validation/single](https://godocs.unisender.ru/web-api-ref#email-validation-single). Checked 2026-10-26.

## Webhooks

- `webhook/list`: `{"limit":50,"offset":0}`; handle pagination.
- `webhook/get`: `{"url":"https://example.com/hooks/unisender"}`.
- `webhook/set`: create/update by URL; a complete example follows.
- `webhook/delete`: `{"url":"https://example.com/hooks/unisender"}`.

```json
{
  "url": "https://example.com/hooks/unisender",
  "status": "active",
  "event_format": "json_post",
  "delivery_info": 1,
  "single_event": 0,
  "events": {
    "email_status": ["delivered", "opened", "clicked", "soft_bounced", "hard_bounced", "spam", "unsubscribed"]
  }
}
```

The endpoint must respond **200 to GET without parameters** during registration: the API checks reachability. `events` is optional when changing an existing webhook's status. Read current settings first and subscribe only to the required events. A user request to connect this URL authorizes `webhook/set --execute`.

For a receiver implementation, read the complete [callback format](https://godocs.unisender.ru/web-api-ref#callback-format). Respond 200 within three seconds; queue longer processing. Notifications may repeat, so processing must be idempotent. `events_by_user` is an array whose entries contain an `events` array with `event_name` and `event_data`. Do not assume one event per HTTP request.

The `auth` signature is a provider-specific MD5 over the **original string body**, with the `auth` value replaced by the corresponding user/project key. It is not HMAC and must not be computed from reserialized JSON. Account for gzip (`json_post_gzip`), exact source bytes, the correct project key, and constant-time comparison. This client is not a webhook receiver and does not verify incoming signatures.

## Suppressions and resubscription

| Method | Example body | Effect |
|---|---|---|
| `suppression/get` | `{"email":"user@example.com"}` | Read reasons and removal eligibility |
| `suppression/list` | `{"limit":50}` | List; continue using the returned `cursor` |
| `suppression/set` | `{"email":"user@example.com","cause":"unsubscribed"}` | Add a suppression |
| `suppression/delete` | `{"email":"user@example.com"}` | Attempt removal where permitted |
| `email/subscribe` | `{"from_email":"robot@example.com","from_name":"Store","to_email":"user@example.com"}` | Send a resubscription-link email |

Inspect `cause`, `source`, and `is_deletable`. Removing system suppressions or unsubscribes is not guaranteed and should not bypass recipient choices. `email/subscribe` differs from marketing `subscribe`: the recipient must follow the link. Normally one resubscription email per day is allowed; do not work around limits through retries.

For `suppression/list`, pass the returned cursor to the next call. Stop on an empty page/no continuation and guard against repeated cursors. `start_time`/`created` use UTC. Deprecated `unsubscribed/*` methods are replaced by `suppression/*` and omitted from this client.

## Email validation

Call `email-validation/single` with `{"email":"user@example.com"}` and `--execute`: this performs an external check rather than local syntax validation. At most two concurrent requests are allowed. `result` can be `valid`, `invalid`, `suspicious`, or `unknown`; additional fields include `cause`, `validity`, and `did_you_mean`. Unknown does not mean invalid. Do not apply suggested address corrections automatically or validate a whole database without a user request.
