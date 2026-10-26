# Templates

[English](templates.md) | [Русский](ru/templates.md)

Source: [template methods](https://godocs.unisender.ru/web-api-ref#template). Checked 2026-10-26.

| Method | Body | Behavior |
|---|---|---|
| `template/list` | `{"limit":50,"offset":0}` | List templates; paginate using `offset` |
| `template/get` | `{"id":"UUID"}` | Read a complete template |
| `template/set` | `{"template":{...}}` | Create without `template.id`; update with it |
| `template/delete` | `{"id":"UUID"}` | Delete a template |

A useful starting `template.json`:

```json
{
  "template": {
    "name": "Order confirmation",
    "from_email": "robot@example.com",
    "from_name": "Store",
    "subject": "Order {{order_number}} received",
    "body": {
      "html": "<p>Hello, {{to_name}}!</p>",
      "plaintext": "Hello, {{to_name}}!"
    },
    "template_engine": "simple"
  }
}
```

`name` and `from_email` are required. Subject and body can be omitted from the template, but must then be supplied when sending. The documented maximum is 10,000 templates and 10 MB per request.

Before updating, fetch the current template, prepare the intended JSON with its `id`, and retain the original for comparison/recovery. Do not assume omitted fields have guaranteed PATCH semantics; prepare the complete intended state. Visual-editor templates are created through the web UI; use HTML for a new API template.

```bash
python3 scripts/unisender_go.py call template/set --data-file template.json
python3 scripts/unisender_go.py call template/set --data-file template.json --execute
```

The first call previews the request. Creating a template sends no email. Sending requires a separate `email/send` call, using the returned `template.id` as `message.template_id`. Omitted message fields inherit values from the template.
