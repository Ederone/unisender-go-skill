# Вебхуки, недоступные адреса и проверка email

[English](../webhooks-suppressions.md) | [Русский](webhooks-suppressions.md)

Источники: [webhook](https://godocs.unisender.ru/web-api-ref#webhook), [callback-format](https://godocs.unisender.ru/web-api-ref#callback-format), [suppression](https://godocs.unisender.ru/web-api-ref#suppression), [email/subscribe](https://godocs.unisender.ru/web-api-ref#email-subscribe), [email-validation/single](https://godocs.unisender.ru/web-api-ref#email-validation-single). Проверено 2026-10-26.

## Вебхуки

- `webhook/list`: `{"limit":50,"offset":0}`; учитывай страницы.
- `webhook/get`: `{"url":"https://example.com/hooks/unisender"}`.
- `webhook/set`: создание/изменение по URL; ниже пример полного запроса.
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

Перед регистрацией URL должен отвечать **200 на GET без параметров**: API проверяет доступность. Для смены статуса существующего вебхука `events` необязателен. Сначала читай его текущие настройки; не подписывай на лишние события автоматически. Создание через `webhook/set --execute` разрешено, когда пользователь поручил подключить этот URL.

Для разработки принимающего сервера читай полный [callback-format](https://godocs.unisender.ru/web-api-ref#callback-format). Обработчик должен ответить 200 в течение трёх секунд; обработку лучше передавать в очередь. Уведомления могут повторяться, обработка должна быть идемпотентной. Провайдер передаёт массив `events_by_user`, внутри — массив `events` с `event_name` и `event_data`. Не считай, что один HTTP-запрос содержит только одно событие.

Подпись `auth` — специфический MD5 от **исходного строкового тела**, где значение `auth` заменено ключом соответствующего пользователя/проекта. Это не HMAC и не MD5 от заново сериализованного JSON. При реализации учитывай gzip (`json_post_gzip`), точные исходные байты, правильный ключ проекта и сравнение без утечки по времени. Клиент скилла не является webhook-сервером и не проверяет входящие подписи.

## Недоступность и переподписка

| Метод | Пример тела | Эффект |
|---|---|---|
| `suppression/get` | `{"email":"user@example.com"}` | Прочитать причины и доступность удаления |
| `suppression/list` | `{"limit":50}` | Список; продолжать через возвращаемый `cursor` |
| `suppression/set` | `{"email":"user@example.com","cause":"unsubscribed"}` | Добавить блокировку |
| `suppression/delete` | `{"email":"user@example.com"}` | Попытка убрать допустимую к удалению запись |
| `email/subscribe` | `{"from_email":"robot@example.com","from_name":"Магазин","to_email":"user@example.com"}` | Отправить письмо со ссылкой переподписки |

Проверяй `cause`, `source`, `is_deletable`. Снятие системной недоступности или отписки не гарантируется и не должно использоваться как способ обойти действия получателя. `email/subscribe` не аналог маркетингового `subscribe`: пользователь сам переходит по ссылке. Обычно разрешено одно письмо переподписки в сутки; не обходи лимит повторами.

У `suppression/list` используй полученный `cursor` в следующем запросе, прекращая при пустой странице/отсутствии продолжения; защити цикл от повторяющегося cursor. Времена `start_time`/`created` — UTC. Устаревшие `unsubscribed/*` заменены на `suppression/*` и не включены в клиент.

## Проверка email

`email-validation/single` с `{"email":"user@example.com"}` выполняется с `--execute`: это реальная внешняя проверка, а не локальная проверка синтаксиса. Максимум два параллельных запроса. `result` может быть `valid`, `invalid`, `suspicious`, `unknown`; также есть `cause`, `validity`, `did_you_mean`. `unknown` не означает недействительный адрес; подсказку исправления не применяй автоматически. Не проверяй всю базу по собственной инициативе.
