# UniSender Go Skill

[English](README.md) | [Русский](README.ru.md)

Скилл и небольшой CLI для **транзакционного API UniSender Go**. Поддерживает 36 методов: отправку писем, шаблоны, события доставки, домены отправителя, вебхуки, блокировки адресов и проекты при наличии прав аккаунта.

Работает с Codex и Claude Code. Требует Python 3.9+ на macOS или Linux; внешних библиотек для работы не нужно. Независимая интеграция сообщества. Маркетинговый API обычного UniSender в неё не входит.

## Установка

После клонирования или распаковки репозитория выполни из его корня:

```bash
mkdir -p ~/.codex/skills
ln -s "$PWD/skills/unisender-go" ~/.codex/skills/unisender-go
```

Для Claude Code используй `~/.claude/skills/unisender-go`. Если путь занят, сначала проверь существующий скилл. При установке ссылкой каталог проекта должен оставаться на месте. Можно также скопировать всю папку `skills/unisender-go`, включая лицензию, в каталог скиллов своего агента.

Вызов: `$unisender-go` или задача с упоминанием UniSender Go. Примеры:

- «Покажи домены отправителя и их статусы проверки».
- «Подготовь шаблон подтверждения заказа без отправки».
- «Отправь это тестовое письмо на мой адрес».
- «Выгрузи события доставки по этому заданию за вчера в моём часовом поясе».

## Ключ

Создай файл вне репозитория:

```bash
mkdir -p ~/.config/unisender-go
touch ~/.config/unisender-go/api-key
chmod 600 ~/.config/unisender-go/api-key
```

Открой `~/.config/unisender-go/api-key` в редакторе, вставь ключ одной строкой и сохрани. Не вставляй секрет в чат, аргументы команды или коммит. Файл должен принадлежать текущему пользователю и быть доступен только ему. Также поддерживается заметка с единственной строкой `api_key: value`; это ограниченный разбор строки, а не полноценный загрузчик YAML.

Порядок выбора:

1. Явный `--key-file PATH`.
2. Непустая переменная процесса `UNISENDER_GO_API_KEY`.
3. Файл из `key_file` в `~/.config/unisender-go/config.json`, если настроен.
4. Иначе `~/.config/unisender-go/api-key`.

Если выбранный файл отсутствует, повреждён или доступен другим пользователям, клиент вернёт локальную ошибку без подстановки другого ключа. Для нескольких проектов храни отдельные файлы и выбирай нужный явно:

```bash
python3 skills/unisender-go/scripts/unisender_go.py call system/info --key-file ~/.config/unisender-go/project-key
```

Необязательная настройка хранит только путь:

```json
{"key_file":"~/.config/unisender-go/project-key"}
```

Чтение из файла работает и из desktop-агента без наследования окружения другого терминала. [.env.example](.env.example) описывает необязательные переменные; автоматической загрузки `.env` нет.

## Первые вызовы

Без ключа и сети:

```bash
python3 skills/unisender-go/scripts/unisender_go.py methods
python3 skills/unisender-go/scripts/unisender_go.py call system/info --dry-run
```

Проверка аккаунта живым запросом чтения:

```bash
python3 skills/unisender-go/scripts/unisender_go.py call system/info
```

Подготовь JSON по [справочнику отправки](skills/unisender-go/references/ru/sending.md) и проверь preview:

```bash
python3 skills/unisender-go/scripts/unisender_go.py call email/send --data-file message.json
```

Чтобы **действительно отправить** письмо:

```bash
python3 skills/unisender-go/scripts/unisender_go.py call email/send --data-file message.json --execute
```

Методы чтения сразу выполняют живые запросы. Остальные без `--execute` только показывают preview; `--dry-run` всегда отключает сеть. Через `--data-file -` можно подать JSON на stdin. Доступные флаги: `call --help`.

Скилл следует поручению пользователя: подготовка черновика не разрешает отправку. Явное поручение отправить конкретное письмо не требует повторного согласования только из-за наличия флага `--execute`.

## Поведение и ограничения

- HTTPS POST и заголовок `X-API-KEY`; разрешены только документированные хосты Go, редиректы запрещены.
- Автоматических повторов нет. После таймаута письмо могло быть принято. Документированное окно защиты через `message.idempotence_key` — одна минута.
- Коды выхода: `0` — успех/preview; `1` — локальная, сетевая или API-ошибка; `2` — неверные аргументы CLI; `3` — принятое задание с отклонёнными адресатами. Сохрани `job_id` и не повторяй всю отправку при частичном успехе.
- Секретные поля и текущий API-ключ скрываются в ответах, включая ключи новых проектов. Сырые ответы с ключами не сохраняются. При этом данные получателей, тексты и ссылки на выгрузки могут присутствовать.
- Некоторые `domain/get-*` регистрируют домен или создают sandbox; проверки могут запускать асинхронную работу. Эти методы не считаются чтением.
- Preview проверяет базовые условия, но не всю схему API и возможности аккаунта. Бесплатный тариф может ограничивать адресатов, а функции проектов — быть недоступными.
- Постраничное чтение, ожидание/скачивание выгрузок, изменение DNS, приём вебхуков и расписание агент выполняет отдельно в рамках задачи.

Храни рабочие JSON/CSV и ответы вне папки скилла. `.local/` игнорируется Git и подходит для локальных запросов. Ключи должны оставаться в пользовательском каталоге настроек и не попадать в репозиторий или архив.

## Документация

| Тема | English | Русский |
|---|---|---|
| Инструкции агента | [SKILL.md](skills/unisender-go/SKILL.md) | [Инструкция](skills/unisender-go/references/ru/usage.md) |
| API и каталог методов | [API](skills/unisender-go/references/api.md) | [API](skills/unisender-go/references/ru/api.md) |
| Отправка и повторы | [Sending](skills/unisender-go/references/sending.md) | [Отправка](skills/unisender-go/references/ru/sending.md) |
| Шаблоны | [Templates](skills/unisender-go/references/templates.md) | [Шаблоны](skills/unisender-go/references/ru/templates.md) |
| Доставка и статистика | [Delivery](skills/unisender-go/references/delivery.md) | [Доставка](skills/unisender-go/references/ru/delivery.md) |
| Аккаунт, домены, проекты | [Account](skills/unisender-go/references/account.md) | [Аккаунт](skills/unisender-go/references/ru/account.md) |
| Вебхуки и блокировки | [Webhooks](skills/unisender-go/references/webhooks-suppressions.md) | [Вебхуки](skills/unisender-go/references/ru/webhooks-suppressions.md) |

Справочники сверены с [официальным Web API v1.92](https://godocs.unisender.ru/web-api-ref) 26 октября 2026. Устаревшие `unsubscribed/*` заменены на `suppression/*`.

## Разработка и архив

```bash
python3 -m unittest discover -s tests -v
```

Тесты изолируют домашний каталог и окружение, подменяя сетевую границу. Реальный ключ им не нужен, писем они не отправляют. GitHub Actions запускает их на Python 3.9 и 3.13. Порядок внесения изменений описан в [CONTRIBUTING.md](CONTRIBUTING.md).

Архив скилла из закоммиченных файлов:

```bash
mkdir -p dist
git archive --format=zip --prefix=unisender-go/ --output=dist/unisender-go.zip HEAD:skills/unisender-go
```

В архив входят скилл, справочники на обоих языках, CLI, метаданные и лицензия. Локальные запросы, ключи, тесты и Python-кеши не включаются.

## Лицензия

[MIT](LICENSE). В папке скилла есть копия лицензии для распространения отдельно от репозитория.
