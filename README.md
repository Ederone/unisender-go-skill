# UniSender Go Skill

[English](README.md) | [Русский](README.ru.md)

An agent skill and a small CLI for the **UniSender Go transactional email API**. It covers 36 methods for sending messages, managing templates, inspecting delivery events, configuring sender domains and webhooks, handling suppressions, and managing projects where account permissions allow.

Works with Codex and Claude Code. Requires Python 3.9+ on macOS or Linux; no third-party runtime packages. This is a community integration, independent of UniSender. The classic UniSender marketing API is outside its scope.

## Install

After cloning or extracting the repository, run from its root:

```bash
mkdir -p ~/.codex/skills
ln -s "$PWD/skills/unisender-go" ~/.codex/skills/unisender-go
```

For Claude Code, use `~/.claude/skills/unisender-go` instead. Inspect an existing destination before replacing it. A symlink requires this checkout to remain in place; alternatively, copy the entire `skills/unisender-go` directory, including its license, to your agent's skill directory.

Invoke `$unisender-go`, or describe a task mentioning UniSender Go. Example requests:

- “Show my sender domains and their verification status.”
- “Prepare an order-confirmation template without sending it.”
- “Send this test message to my address.”
- “Export delivery events for this job yesterday in my timezone.”

## Configure credentials

Create a file outside the repository:

```bash
mkdir -p ~/.config/unisender-go
touch ~/.config/unisender-go/api-key
chmod 600 ~/.config/unisender-go/api-key
```

Open `~/.config/unisender-go/api-key` in a text editor, paste the key as a single line, and save. Never include the key in a chat, command argument, or commit. The file must belong to the current user and have owner-only access. An existing note containing a single `api_key: value` line is also supported; this is a limited line parser, not a full YAML loader.

Credential precedence:

1. `--key-file PATH` supplied to a call.
2. Nonempty process variable `UNISENDER_GO_API_KEY`.
3. `key_file` from `~/.config/unisender-go/config.json`, if configured.
4. Otherwise `~/.config/unisender-go/api-key`.

A selected file that is missing, invalid, or accessible to other users causes a local error. There is no fallback to another credential after such an error. For multiple projects, keep separate files and select one explicitly:

```bash
python3 skills/unisender-go/scripts/unisender_go.py call system/info --key-file ~/.config/unisender-go/project-key
```

The optional config file stores only a path:

```json
{"key_file":"~/.config/unisender-go/project-key"}
```

File-based credentials work from a desktop agent without inheriting another terminal's environment. [.env.example](.env.example) documents optional environment variables; the CLI does not automatically load `.env` files.

## Try the CLI

Without credentials or network access:

```bash
python3 skills/unisender-go/scripts/unisender_go.py methods
python3 skills/unisender-go/scripts/unisender_go.py call system/info --dry-run
```

Check the account using a live read:

```bash
python3 skills/unisender-go/scripts/unisender_go.py call system/info
```

Prepare a JSON file using the [sending guide](skills/unisender-go/references/sending.md), then preview it:

```bash
python3 skills/unisender-go/scripts/unisender_go.py call email/send --data-file message.json
```

To **actually send** the message:

```bash
python3 skills/unisender-go/scripts/unisender_go.py call email/send --data-file message.json --execute
```

Read methods run live by default. All other methods preview unless `--execute` is supplied; `--dry-run` always disables network access. `--data-file -` accepts JSON from stdin. Run `call --help` for available flags.

The skill follows the user's authorization: drafting a message does not authorize sending it. An explicit request to send a specific message does not require a second approval merely because the CLI uses `--execute`.

## Behavior and limits

- HTTPS POST with `X-API-KEY`; only documented Go hosts are accepted, and redirects are refused.
- No automatic retries. A timed-out send may have succeeded. The documented `message.idempotence_key` deduplication window is only one minute.
- Exit codes: `0` success/preview, `1` local/network/API error, `2` invalid CLI arguments, `3` an accepted send with rejected recipients. Preserve `job_id` and never resend the entire batch after partial acceptance.
- Secret fields and the active API key are redacted from responses, including newly created project keys. Raw secret-bearing responses are not saved. Ordinary recipient data, message content, and export URLs can still be present.
- Domain `get-*` methods may register a domain or create a sandbox; checks may start asynchronous work. These are not classified as read-only.
- Preview performs basic validation, not full API-schema or account-capability validation. Free-tier recipient restrictions and disabled project features may still reject a live request.
- Pagination, export polling/downloads, DNS edits, webhook receivers, and scheduling are handled separately by the agent within the task.

Keep task JSON/CSV and responses outside the skill directory. `.local/` is ignored for local task files. API credentials belong in the user configuration directory, never in the repository or release archive.

## Documentation

| Topic | English | Русский |
|---|---|---|
| Agent instructions | [SKILL.md](skills/unisender-go/SKILL.md) | [Инструкция](skills/unisender-go/references/ru/usage.md) |
| API and method catalog | [API](skills/unisender-go/references/api.md) | [API](skills/unisender-go/references/ru/api.md) |
| Sending and retries | [Sending](skills/unisender-go/references/sending.md) | [Отправка](skills/unisender-go/references/ru/sending.md) |
| Templates | [Templates](skills/unisender-go/references/templates.md) | [Шаблоны](skills/unisender-go/references/ru/templates.md) |
| Delivery and statistics | [Delivery](skills/unisender-go/references/delivery.md) | [Доставка](skills/unisender-go/references/ru/delivery.md) |
| Account, domains, projects | [Account](skills/unisender-go/references/account.md) | [Аккаунт](skills/unisender-go/references/ru/account.md) |
| Webhooks and suppressions | [Webhooks](skills/unisender-go/references/webhooks-suppressions.md) | [Вебхуки](skills/unisender-go/references/ru/webhooks-suppressions.md) |

References were checked against [UniSender Go Web API v1.92](https://godocs.unisender.ru/web-api-ref) on October 26, 2026. The deprecated `unsubscribed/*` endpoints are omitted in favor of `suppression/*`.

## Development and packaging

```bash
python3 -m unittest discover -s tests -v
```

Tests isolate the home directory and environment and replace the HTTP boundary. They need no real key and never send mail. GitHub Actions runs them on Python 3.9 and 3.13. See [CONTRIBUTING.md](CONTRIBUTING.md) for the documentation and API-change workflow.

Build a portable skill from committed files:

```bash
mkdir -p dist
git archive --format=zip --prefix=unisender-go/ --output=dist/unisender-go.zip HEAD:skills/unisender-go
```

The archive contains the skill, both reference languages, CLI, UI metadata, and license. It excludes local requests, credentials, tests, and Python cache files.

## License

[MIT](LICENSE). The self-contained skill includes a copy of the license for redistribution.
