# API, методы и ошибки

[English](../api.md) | [Русский](api.md)

Источник: [официальный Web API v1.92](https://godocs.unisender.ru/web-api-ref), проверено 2026-10-26.

## Протокол

Все методы используют **HTTPS POST**, тело и ответ JSON, путь `/{группа}/{действие}.json`. Ключ передаётся заголовком `X-API-KEY`. Он загружается из `~/.config/unisender-go/api-key` (права `600`), с возможностью переопределения через переменную `UNISENDER_GO_API_KEY` или явный `--key-file PATH`. Явный файл имеет высший приоритет. Файл может содержать сам ключ или одну строку `api_key: value`. Preview файл с ключом не открывает. Клиент не помещает ключ в URL или тело и не переходит по редиректам.

По умолчанию `https://goapi.unisender.ru/ru/transactional/api/v1` маршрутизирует запросы. Документированные прямые адреса: `https://go1.unisender.ru/ru/transactional/api/v1` и `https://go2.unisender.ru/ru/transactional/api/v1`. Можно задать `UNISENDER_GO_BASE_URL` или `--base-url`. Иные хосты/пути запрещены; данные и ключ не попадут на произвольный сервер через этот параметр.

Это **Go**, а не `api.unisender.com/ru/api`. Нет списков рассылки, `createCampaign`, `getCampaignStatus` или авторизации через параметр `api_key` как в маркетинговом API. `callback-format` — описание входящих уведомлений, а не вызываемый метод.

Необязательный `~/.config/unisender-go/config.json` может содержать только путь к выбранному файлу:

```json
{"key_file":"~/.config/unisender-go/project-key"}
```

Приоритет: явный `--key-file` → непустая переменная `UNISENDER_GO_API_KEY` → файл из настройки → стандартный `~/.config/unisender-go/api-key`. Ошибка выбранного файла не вызывает подстановку другого ключа. Поддерживается строка `api_key: value` с кавычками/комментариями, а не произвольный YAML.

## Каталог клиента

`read` выполняется сразу. `write`, `send`, `check` требуют `--execute`; без него получается локальный preview. `check` здесь означает реальную проверку email внешним сервисом. `--dry-run` отключает сеть у любого метода. Поле `required` перечисляет только верхний уровень; для вложенных полей смотри профильный справочник и текущую документацию.

| Метод и документация | Эффект | Обязательные поля верхнего уровня |
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

У `project/update` и `project/delete` дополнительно требуется один из `project_id`/`project_api_key`; предпочитай ID. У `project/update` требуется `project.name`. Методы `confirmed-email/*`, `domain/get-sandbox-domain` и `project/*` требуют ключ основного аккаунта. При прочих ограничениях доступа используй фактическую ошибку API, не подменяй ключ самовольно.

## Вывод и ошибки

Вывод CLI — JSON. Живой ответ находится в `response`, preview содержит `body`, `effect`, `url`, `request_bytes`. Читай `response.status` как результат API, не как состояние доставки или дампа.

- Код выхода 0: успешный ответ или preview (проверяй `dry_run`).
- Код 1: локальная, сетевая или API-ошибка; JSON в stderr.
- Код 2: неверные аргументы CLI.
- Код 3: API принял задание, но `failed_emails` непустой. Сохрани `job_id`, не повторяй весь запрос.

API-ошибки возвращают `status: error`, `message`, `code`. Клиент сохраняет их в `response` ошибки и добавляет `http_status` для HTTP-ошибок. HTTP 401 — проверь ключ; 403 — права/ограничения; 413 — размер; 429 — частота; 5xx — серверная ошибка. HTTP 200 с `status: error` тоже ошибка. Не выводи неизвестные HTML-тела ошибок.

Сеть и неоднозначные ответы на изменяющие запросы отмечаются `outcome_unknown: true`. Клиент не делает автоматических повторов даже при 429/5xx. Для повторного чтения можно подождать и повторить вручную; для отправки сначала сверяй состояние. Тело ответа с `project_api_key` или вложенным `api_key` редактируется до печати. Клиент не имеет режима вывода сырых секретов.

## Границы проверки

Клиент проверяет известность метода, объект JSON, отсутствие API-ключа в теле, обязательные поля верхнего уровня, 1–500 получателей, основу письма без шаблона, длину `idempotence_key`, несовместимость `aggregate=day_status` с фильтром и общий размер запроса. Он не проверяет полностью адреса, UUID, содержимое HTML, все вложенные схемы, возможности тарифа или фактическую готовность домена. Не называй preview подтверждением того, что API примет письмо.

Нет автоматического постраничного чтения, ожидания дампа, скачивания CSV, изменения DNS, HTTP-сервера вебхуков или расписания отправок. Эти действия агент выполняет отдельно в рамках задачи и подходящими инструментами.
