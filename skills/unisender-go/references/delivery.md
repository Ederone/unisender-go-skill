# Delivery and statistics

[English](delivery.md) | [Русский](ru/delivery.md)

Sources: [event-dump/create](https://godocs.unisender.ru/web-api-ref#event-dump-create), [event-dump/get](https://godocs.unisender.ru/web-api-ref#event-dump-get), [callback-format](https://godocs.unisender.ru/web-api-ref#callback-format). Checked 2026-10-26.

Go does not use the marketing API's `getCampaignStatus`. Use webhooks or asynchronous event dumps.

## Export events for a job

Establish the time range when it is not implicit in the request. API timestamps are **UTC**, formatted `YYYY-MM-DD HH:MM:SS`; `end_time` is exclusive. Interpret relative dates in the user's timezone. For example, October 25, 2026 in Europe/Moscow corresponds to `2026-10-24 21:00:00` through `2026-10-25 21:00:00` UTC.

```json
{
  "start_time": "2026-10-24 21:00:00",
  "end_time": "2026-10-25 21:00:00",
  "limit": 100000,
  "filter": {"job_id": "REPLACE_WITH_JOB_ID"},
  "format": "csv"
}
```

1. Save the JSON and call `event-dump/create --data-file events.json --execute`. Export preparation is a write, authorized by a user request to export those events.
2. Use the returned `dump_id` in `event-dump/get`, body `{"dump_id":"..."}`.
3. Read **`event_dump.dump_status`**: `queued`, `in_process`, `ready`, or `failed`. Top-level `status: success` only indicates API call success.
4. Poll with pauses, such as 5–10 seconds, and bound waiting to two minutes per task run. If still pending, return the ID and current state. Do not create another dump instead of waiting.
5. CSV/CSV.GZ links are in **`event_dump.files[].url`**. Process every file. Files may appear during `in_process`, but do not label partial output complete.

Run the export creation from the skill directory:

```bash
python3 scripts/unisender_go.py call event-dump/create --data-file events.json --execute
```

The client does not download files automatically. Download only HTTPS URLs returned for the requested export, without an `X-API-KEY` header or API key in the query string. Keep data in the task workspace, outside the skill. Export URLs may grant access to data; avoid unnecessary sharing.

The API defaults to only **50 events**: set an explicit `limit` appropriate to the task. Reaching the limit may indicate truncation. Establish completeness or split the time range into smaller intervals. Each file contains at most 100,000 events. Event retention is up to 45 days depending on tariff. At most ten dumps may exist/be in preparation; finished dumps expire after eight hours. Do not delete unrelated dumps to free a slot without authorization.

List existing exports with `event-dump/list`, body `{}`. Delete using `event-dump/delete`, body `{"dump_id":"..."}`, and `--execute`.

## Aggregates and interpretation

For overall daily statistics, `aggregate: "day_status"` is available. **A nonempty `filter`, including `job_id`, cannot be combined with it.** For one job, export filtered events and compute statistics locally. The column selector is `dump_fields`, despite a `dump_fileds` typo in one documentation paragraph.

Distinguish `accepted`, `sent`, `delivered`, `opened`, `clicked`, `soft_bounced`, `hard_bounced`, `unsubscribed`, `subscribed`, and `spam`. Soft bounces may be retried by the provider; hard bounces are final delivery failures.

Use `(job_id, email)` when identifying unique messages: one job may contain multiple recipients, and a message can produce multiple events. State the denominator for open rate/CTR, time range, account/project scope, and completeness. Do not add openings, clicks, and deliveries together as independent sends. An opening records tracking activity, not guaranteed human reading.
