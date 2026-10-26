# Account, projects, and sender readiness

[English](account.md) | [Русский](ru/account.md)

Sources: [system](https://godocs.unisender.ru/web-api-ref#system), [domain](https://godocs.unisender.ru/web-api-ref#domain), [project](https://godocs.unisender.ru/web-api-ref#project), [confirmed-email](https://godocs.unisender.ru/web-api-ref#confirmed-email). Checked 2026-10-26.

## Connection and scope

`system/ping` with `{}` validates the key and returns `user_id`. `system/info` with `{}` also returns scope and accounting:

- `project_id`, `project_name`, `project_accounting`: a project key;
- `accounting`, with period and `emails_included`/`emails_sent`: a user key.

Use the intended project's key. Do not switch projects to work around access errors. Project management, sandbox creation, and confirmed-email methods require the main account key. Account restrictions may still return 403 even with a user key; report the actual error. An accounting field of zero alone does not establish the tariff or available sending allowance.

## Existing domain

Start with `domain/list`, body `{"domain":"example.com"}`. Sender readiness requires both:

- `domains[].verification-record.status` = `confirmed`;
- `domains[].dkim.status` = `active`.

A domain's presence, or successful initiation of a check, is insufficient.

## Prepare a domain

1. `domain/get-dns-records` with `{"domain":"example.com"}` returns records and **registers the domain/generates keys** when absent. It requires `--execute` within an authorized domain setup task.
2. Publish the `verification-record` value as a TXT record at the domain root. Publish DKIM at `us._domainkey`, with `k=rsa; p=` followed by the returned `dkim` public key. This is not the API key.
3. The recommended SPF mechanism is `include:spf.unisender.ru/go`. Merge it into an existing SPF record while preserving its meaning; do not create a second SPF record or replace existing configuration wholesale.
4. After publishing DNS, call `domain/validate-verification-record` and `domain/validate-dkim` with the same body and `--execute`. Success means the checks **started**.
5. Later read `domain/list` and verify both final states. Report pending DNS propagation rather than starting an unbounded loop of checks.

This client does not edit DNS at a registrar. Show requested records directly; changing DNS requires an appropriate tool and authorization for that change.

## Sandbox and confirmed addresses

`domain/get-sandbox-domain` with `{}` returns an existing sandbox or **creates** one. It is a `write` operation requiring `--execute`.

`confirmed-email/list` with `{}` lists confirmed and unconfirmed addresses. `confirmed-email/create` with `{"email":"..."}` **sends a confirmation link**; creation does not itself confirm ownership. The owner must follow the link. Check the resulting status through `confirmed-email/list`. `confirmed-email/delete` removes an address. Both mutating methods require `--execute`.

Free-tier restrictions may reject external recipients with API error 903. Address confirmation or a suitable paid tariff may be needed. Do not bypass restrictions or claim that sandbox creation removes them; use the actual API error and account conditions.

## Projects

| Method | Body |
|---|---|
| `project/list` | `{}` or `{"project_id":"..."}` |
| `project/create` | `{"project":{"name":"Transactional app"}}` |
| `project/update` | `{"project_id":"...","project":{"name":"Existing name","send_enabled":true}}` |
| `project/delete` | `{"project_id":"..."}` |

Prefer `project_id` over putting a project API key in JSON. `project/list` includes `projects[].api_key`; creation returns `project_api_key`. Both are redacted by the client. Obtain new credentials through the provider dashboard or the user's secret manager; the client intentionally does not save raw secret-bearing responses.

Updates require `project.name`; read current properties and preserve the intended name. Do not reset `email_counter`, remove `email_counter_limit`, or disable unsubscribe links by default. Delete only the specific project/domain requested by the user.
