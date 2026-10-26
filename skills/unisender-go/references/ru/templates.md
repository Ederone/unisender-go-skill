# Шаблоны

[English](../templates.md) | [Русский](templates.md)

Источник: [template методы](https://godocs.unisender.ru/web-api-ref#template). Проверено 2026-10-26.

| Метод | Запрос | Поведение |
|---|---|---|
| `template/list` | `{"limit":50,"offset":0}` | Список; следующие страницы через `offset` |
| `template/get` | `{"id":"UUID"}` | Полный шаблон |
| `template/set` | `{"template":{...}}` | Создание без `template.id`, обновление с ним |
| `template/delete` | `{"id":"UUID"}` | Удаление |

Минимальная полезная заготовка `template.json`:

```json
{
  "template": {
    "name": "Подтверждение заказа",
    "from_email": "robot@example.com",
    "from_name": "Магазин",
    "subject": "Заказ {{order_number}} принят",
    "body": {
      "html": "<p>Здравствуйте, {{to_name}}!</p>",
      "plaintext": "Здравствуйте, {{to_name}}!"
    },
    "template_engine": "simple"
  }
}
```

У шаблона обязательны `name` и `from_email`. Тело и тема могут отсутствовать, но тогда их надо передавать при отправке. Максимум 10 000 шаблонов, запрос до 10 MB.

Перед обновлением прочитай текущий шаблон, подготовь новый JSON с его `id` и сохрани исходник для сравнения/восстановления. Не рассчитывай на сохранение пропущенных полей как на гарантированный PATCH: подготовь полный нужный вариант. `editor_type=visual` создаётся в веб-интерфейсе; для нового API-шаблона используй HTML.

```bash
python3 scripts/unisender_go.py call template/set --data-file template.json
python3 scripts/unisender_go.py call template/set --data-file template.json --execute
```

Первый вызов только показывает запрос. Создание шаблона не отправляет письмо. Для реальной отправки нужен отдельный `email/send`; перенеси в него полученный `template.id` как `message.template_id`. Непереданные поля сообщения наследуются из шаблона.
