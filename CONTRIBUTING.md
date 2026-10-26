# Contributing

The skill and CLI live in `skills/unisender-go/`. The CLI runs on Python 3.9+ without third-party packages.

Run the offline suite from the repository root:

```bash
python3 -m unittest discover -s tests -v
python3 skills/unisender-go/scripts/unisender_go.py call system/info --dry-run
```

Tests isolate the home directory and environment and replace the HTTP boundary. They must never use real credentials, send email, or alter a provider account. Cover observable behavior when changing request handling, credential precedence, redaction, or retry behavior.

Keep `README.md` and `README.ru.md` aligned. English references live in `skills/unisender-go/references/`; corresponding Russian files are in `references/ru/`, including the Russian usage guide. Update both versions when changing behavior. Prefer the smallest reference needed for a task instead of expanding every entrypoint.

Check new methods and parameter rules against the [official Go API documentation](https://godocs.unisender.ru/web-api-ref). Classify side effects explicitly: method names beginning with `get` do not guarantee read-only behavior. Update both API catalogs when changing the CLI method registry.

Use example domains and synthetic keys in fixtures. Keep credentials, `.local/` requests, recipient lists, and raw account exports out of commits and issues. The code redacts credential fields, but ordinary API responses may still contain personal data.

CI also scans public files with `detect-secrets==1.5.0`. Synthetic credentials required by negative/redaction tests have line-specific `pragma: allowlist secret` comments; do not exempt an entire file. To repeat the scan locally without changing runtime dependencies:

```bash
uvx --from detect-secrets==1.5.0 detect-secrets scan --all-files --exclude-files '(^|/)(\.git|dist|__pycache__|\.local)/'
```

The scanner prints a JSON report; `results` must be empty. Review findings locally without pasting suspected secret values into issues. A clean scanner result does not replace reviewing account identifiers, local paths, archives, or Git author metadata.

Use purpose-based branch names such as `docs/english-reference` or `fix/key-file-parsing`.
