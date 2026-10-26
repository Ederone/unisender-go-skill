# API, methods, and errors

[English](api.md) | [Русский](ru/api.md)

Source: [official Web API v1.92](https://godocs.unisender.ru/web-api-ref), checked 2026-10-26.

## Protocol and credentials

All methods use **HTTPS POST**, JSON request/response bodies, and `/{group}/{action}.json` paths. Authentication uses `X-API-KEY`. The client never sends authentication keys in request bodies or URLs, and refuses redirects.

Credential precedence:

1. Explicit `--key-file PATH`.
2. Nonempty process variable `UNISENDER_GO_API_KEY`.
3. The file named by `key_file` in `~/.config/unisender-go/config.json`, if configured.
4. Otherwise `~/.config/unisender-go/api-key`.

A key file must be owned by the current user with owner-only permissions (`chmod 600`). It can contain a bare key or one `api_key: value` line, with optional quotes/comments. The parser supports that line format, not arbitrary YAML. Invalid/missing selected files fail locally without falling back to a different key. Preview does not open credential files. Optional path-only configuration:

```json
{"key_file":"~/.config/unisender-go/project-key"}
```

The default base, `https://goapi.unisender.ru/ru/transactional/api/v1`, handles routing. Documented direct bases are `https://go1.unisender.ru/ru/transactional/api/v1` and `https://go2.unisender.ru/ru/transactional/api/v1`. Override through `UNISENDER_GO_BASE_URL` or `--base-url`. Other hosts/paths are rejected.

This is the Go transactional API. Classic marketing endpoints on `api.unisender.com/ru/api`, including `createCampaign`, `getCampaignStatus`, and list management, are outside its scope. `callback-format` describes incoming notifications and is not a callable API method.

## Method catalog

`read` runs live. `write`, `send`, and `check` require `--execute`; otherwise they produce a local preview. Here `check` means an external address validation. `--dry-run` disables network access for every method. Required fields below cover only the top level; use task references and provider documentation for nested fields.

| Method and documentation | Effect | Required top-level fields |
|---|---|---|
| [email/send](https://godocs.unisender.ru/web-api-ref#email-send) | send | `message` |
| [email/subscribe](https://godocs.unisender.ru/web-api-ref#email-subscribe) | send | `from_email`, `from_name`, `to_email` |
| [email-validation/single](https://godocs.unisender.ru/web-api-ref#email-validation-single) | check | `email` |
| [confirmed-email/create](https://godocs.unisender.ru/web-api-ref#confirmed-email-create) | send | `email` |
| [confirmed-email/list](https://godocs.unisender.ru/web-api-ref#confirmed-email-list) | read | — |
| [confirmed-email/delete](https://godocs.unisender.ru/web-api-ref#confirmed-email-delete) | write | `email` |
| [template/set](https://godocs.unisender.ru/web-api-ref#template-set) | write | `template` |
| [template/get](https://godocs.unisender.ru/web-api-ref#template-get) | read | `id` |
| [template/list](https://godocs.unisender.ru/web-api-ref#template-list) | read | — |
| [template/delete](https://godocs.unisender.ru/web-api-ref#template-delete) | write | `id` |
| [webhook/set](https://godocs.unisender.ru/web-api-ref#webhook-set) | write | `url` |
| [webhook/get](https://godocs.unisender.ru/web-api-ref#webhook-get) | read | `url` |
| [webhook/list](https://godocs.unisender.ru/web-api-ref#webhook-list) | read | — |
| [webhook/delete](https://godocs.unisender.ru/web-api-ref#webhook-delete) | write | `url` |
| [suppression/set](https://godocs.unisender.ru/web-api-ref#suppression-set) | write | `email`, `cause` |
| [suppression/get](https://godocs.unisender.ru/web-api-ref#suppression-get) | read | `email` |
| [suppression/list](https://godocs.unisender.ru/web-api-ref#suppression-list) | read | — |
| [suppression/delete](https://godocs.unisender.ru/web-api-ref#suppression-delete) | write | `email` |
| [domain/get-dns-records](https://godocs.unisender.ru/web-api-ref#domain-get-dns-records) | write | `domain` |
| [domain/validate-verification-record](https://godocs.unisender.ru/web-api-ref#domain-validate-verification-record) | write | `domain` |
| [domain/validate-dkim](https://godocs.unisender.ru/web-api-ref#domain-validate-dkim) | write | `domain` |
| [domain/list](https://godocs.unisender.ru/web-api-ref#domain-list) | read | — |
| [domain/get-sandbox-domain](https://godocs.unisender.ru/web-api-ref#domain-get-sandbox-domain) | write | — |
| [domain/delete](https://godocs.unisender.ru/web-api-ref#domain-delete) | write | `domain` |
| [event-dump/create](https://godocs.unisender.ru/web-api-ref#event-dump-create) | write | `start_time` |
| [event-dump/get](https://godocs.unisender.ru/web-api-ref#event-dump-get) | read | `dump_id` |
| [event-dump/list](https://godocs.unisender.ru/web-api-ref#event-dump-list) | read | — |
| [event-dump/delete](https://godocs.unisender.ru/web-api-ref#event-dump-delete) | write | `dump_id` |
| [tag/list](https://godocs.unisender.ru/web-api-ref#tag-list) | read | — |
| [tag/delete](https://godocs.unisender.ru/web-api-ref#tag-delete) | write | `tag_id` |
| [project/create](https://godocs.unisender.ru/web-api-ref#project-create) | write | `project` |
| [project/update](https://godocs.unisender.ru/web-api-ref#project-update) | write | `project` |
| [project/list](https://godocs.unisender.ru/web-api-ref#project-list) | read | — |
| [project/delete](https://godocs.unisender.ru/web-api-ref#project-delete) | write | — |
| [system/ping](https://godocs.unisender.ru/web-api-ref#system-ping) | read | — |
| [system/info](https://godocs.unisender.ru/web-api-ref#system-info) | read | — |

`project/update` and `project/delete` also require one of `project_id`/`project_api_key`; prefer the ID. `project/update` requires `project.name`. `confirmed-email/*`, `domain/get-sandbox-domain`, and `project/*` require the main account key. Report actual access restrictions rather than switching credentials on your own.

## Output and errors

CLI output is JSON. Live results are under `response`; preview contains `body`, `effect`, `url`, and `request_bytes`. `response.status` describes API-call success, not delivery or export readiness.

| Exit code | Meaning |
|---|---|
| 0 | Success or preview; inspect `dry_run` |
| 1 | Local, network, or API error; JSON on stderr |
| 2 | Invalid CLI arguments |
| 3 | Accepted job with nonempty `failed_emails`; preserve `job_id`, do not resend the batch |

API errors contain `status: error`, `message`, and `code`. The client preserves these under the error's `response` and adds `http_status` for HTTP errors. HTTP 401 indicates authentication, 403 access/restrictions, 413 request size, 429 request frequency, and 5xx server errors. HTTP 200 with `status: error` is also a failure. Unknown HTML error bodies are omitted.

Network failures and ambiguous responses to mutating calls are marked `outcome_unknown: true`. There are no automatic retries, including for 429/5xx. Reads may be retried manually after waiting; reconcile sends before retrying. Response fields such as `project_api_key` and nested `api_key` are redacted. There is no raw-secret output mode.

## Validation boundaries

The client checks known methods, JSON object shape, absence of authentication keys in payloads, required top-level fields, 1–500 recipients, basic message content without a template, idempotence-key length, aggregate/filter incompatibility, and request size. It does not fully validate addresses, UUIDs, HTML, every nested schema, account capabilities, or sender-domain readiness. Preview does not prove provider acceptance.

Pagination, waiting for exports, CSV downloads, DNS edits, webhook receivers, and scheduled sends are not built into the client. The agent uses appropriate tools for those actions within the user's task.
