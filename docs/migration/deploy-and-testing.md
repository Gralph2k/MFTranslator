# Деплой и тестирование — runbook

Практическая инструкция для агента и владельца: как проверить проект локально,
как выложить изменение на боевой VPS, как убедиться, что деплой прошёл, как
откатиться и что делать, когда что-то сломалось.

- Проект: `C:\Projects\MFTranslator` (Windows, основной инструмент — PowerShell).
- Прод: `root@48.102.186.191`, код в `/opt/mf-translator`, systemd-сервис `emotion-trainer`.
- **Канон порядка деплоя — [`deploy/DEPLOY.md`](../../deploy/DEPLOY.md) §7.** Этот файл
  повторяет его с ожидаемыми результатами и проверками, а не заменяет.
- Снимок фактов и проверок: **10.11.2026, ~13:45 МСК**. Сервер живёт в
  `Europe/Berlin` (CET, зимой МСК−2 ч) — время в `journalctl` и `cron` серверное,
  не московское.

> **Правило проекта.** Любое изменение кода, сценариев или конфигурации деплоится
> на VPS и перезапускает бота. «Локально работает» ничего не доказывает:
> пользователи ходят через сервер. Деплой и `systemctl restart` — только с явного
> согласия владельца; без согласия допустимы лишь read-only проверки (§4, §8).

---

## 0. Шпаргалка

| Что нужно | Команда | Ожидаемо |
|---|---|---|
| Тесты локально | `.\.venv\Scripts\python.exe -m pytest -q` | `216 passed` (~3.5 с) |
| Demo-прогон без сети | `.\.venv\Scripts\python.exe -m bot.cli --provider demo --scenario eva_message` | игра доходит до разбора, exit 0 |
| Проверка окружения | `.\.venv\Scripts\python.exe -m bot.doctor` | DeepSeek `OK`; Telegram локально — `ConnectTimeout` (сеть) |
| Прод жив? (read-only) | `ssh -o BatchMode=yes root@48.102.186.191 "systemctl is-active emotion-trainer"` | `active` |
| Строгая проверка прода | скрипт из §8.2 | `OK: active, PID …, Бот запущен + Run polling, без Traceback/Conflict` |
| Деплой | §3, шаги 0–9 | `active` + свежие `Бот запущен`/`Run polling` |
| Бэкап базы | `ssh root@48.102.186.191 "bash /opt/mf-translator/deploy/backup.sh"` | `Готово: /var/backups/emotion-trainer/bot-….db` |
| Откат | §5 | сервис `active`, лог чистый |

Ключевые пути: сервер — `/opt/mf-translator`, база — `data/bot.db` (на сервере
единственная копия диалогов), бэкапы — `/var/backups/emotion-trainer`, юнит —
`/etc/systemd/system/emotion-trainer.service`, архив обновления — `/opt/update.tgz`.

---

## 1. Локальная установка и окружение

### 1.1 Что где лежит

| Путь | Что это |
|---|---|
| `.venv\Scripts\python.exe` | интерпретатор проекта (Python 3.13.5 проверен 10.11.2026) |
| `.env` | секреты: токен Telegram, ключ DeepSeek (в `.gitignore`, **не печатать**) |
| `.env.example` | шаблон `.env` для новых машин |
| `data/bot.db` | локальная база истории (в `.gitignore`; на сервере своя) |
| `.tmp/` | временные файлы бота/тестов/деплоя (в `.gitignore`) |
| `.uv-cache/` | кэш `uv` (в `.gitignore`) |
| `pyproject.toml` | зависимости и настройки pytest; lock-файла нет |

### 1.2 Python, venv и зависимости

Проверка (из корня проекта):

```powershell
Test-Path .venv\Scripts\python.exe    # True
.\.venv\Scripts\python.exe --version  # Python 3.13.5
```

Ожидаемо: `True` и `Python 3.13.x`. Активировать venv не нужно — вызываем
`python.exe` напрямую.

Если `.venv` нет (новая машина):

```powershell
uv venv .venv --python 3.13
uv pip install --python .venv -e ".[dev]"
```

Нюанс `uv` (из `PROGRESS.md`, §«Важные особенности среды»): в DSH-песочнице `uv`
не мог писать кэш в `%LOCALAPPDATA%`. **В Claude Code песочницы нет** — обычно
ничего настраивать не надо. Если `uv` всё же ругается на кэш:

```powershell
$env:UV_CACHE_DIR='C:\Projects\MFTranslator\.uv-cache'
```

(В `.claude/settings.json` эта переменная уже прописана — отдельно делать не нужно.)

Зависимости ставятся из `pyproject.toml`: `pip install -e .` (на сервере — так же).
Требование `requires-python = ">=3.12"`: локально 3.13, на сервере 3.12.16 — это
норма, не расхождение.

### 1.3 `.env` и ключи

```powershell
Copy-Item .env.example .env
```

Заполнить в `.env`:

| Переменная | Обязательна | Что писать |
|---|---|---|
| `TELEGRAM_BOT_TOKEN` | да, для бота | токен от @BotFather |
| `DEEPSEEK_API_KEY` | да, для бота | ключ с platform.deepseek.com |
| `DEEPSEEK_BASE_URL` | нет | `https://api.deepseek.com` |
| `DEEPSEEK_MODEL` | нет | `deepseek-chat` |
| `TELEGRAM_PROXY` | нет | `http://…` или `socks5://…`, только если Telegram недоступен напрямую |
| `DB_PATH` | нет | `./data/bot.db` |
| `SAFETY_RESOURCES` | нет в `.env.example` | реальные контакты помощи; **пусто и локально, и в проде** (проверено 10.11.2026: `Settings.safety_resources is None`) — не выдумывать номера |

Правила: `.env` не читать «для проверки» (для этого есть `bot.doctor`), не печатать,
не коммитить, не подставлять значения в документацию/логи. `.env` на сервере
и `.env` локально — разные файлы, при деплое не перезаписываются.

`SAFETY_RESOURCES` в `.env.example` отсутствует (см. §9): если нужен локально,
добавить строку `SAFETY_RESOURCES=…` вручную.

### 1.4 Сеть: VPN/прокси и TLS

- **Telegram с рабочей машины недоступен** (`ConnectTimeout`) — это сеть, а не код.
  Фактический вывод `bot.doctor` 10.11.2026: DeepSeek `OK`, Telegram `ОШИБКА`. Так
  и должно быть без VPN: прод ходит в Telegram из Германии, поэтому прод от этого
  не страдает.
- Варианты для локального Telegram-теста: системный VPN (тогда `TELEGRAM_PROXY`
  пуст) или прокси в `.env` (`http://127.0.0.1:10809` / `socks5://127.0.0.1:1080`,
  для socks пакет `httpx[socks]` уже в зависимостях).
- **TLS**: соединения идут через `bot/tls.py` → `truststore`, то есть доверяют
  хранилищу Windows. Поэтому VPN/антивирус с перехватом HTTPS не роняет httpx
  с `CERTIFICATE_VERIFY_FAILED`, если корень посредника установлен в систему.
  Если ошибка сертификата всё же есть — разрешить программе-посреднику её
  сертификат, а не отключать проверку.

### 1.5 Консоль и кодировка

- В `.cmd`-файлах кодировка уже настроена (`chcp 65001`, `PYTHONIOENCODING=utf-8`);
  менять их на не-ASCII нельзя — `cmd.exe` читает в OEM-кодировке и ломает кириллицу.
- В Claude Code `PYTHONIOENCODING=utf-8` уже выставлен через `.claude/settings.json`
  (`env`), поэтому для команд агента отдельно задавать не нужно. Для запуска
  вручную в обычном PowerShell — задать:

```powershell
$env:PYTHONIOENCODING='utf-8'
```

### 1.6 Локальные запуски: что можно и что нельзя

| Команда | Что делает | Безопасно? |
|---|---|---|
| `.\.venv\Scripts\python.exe -m bot.cli --provider demo --scenario <id>` | игра в терминале без сети/ключей | да |
| `.\.venv\Scripts\python.exe -m bot.cli --provider deepseek --scenario <id>` | игра с живой моделью (тратит баланс DeepSeek) | да, но платно |
| `.\run-cli.cmd` | то же интерактивно, спросит провайдера и сценарий | да |
| `.\.venv\Scripts\python.exe -m bot.doctor` | проверка токена/прокси/ключа | да (только сеть) |
| `.\.venv\Scripts\python.exe -m bot.launcher status` | запущен ли локальный бот, PID | да |
| `.\sessions.cmd` | сессии локальной базы + копия серверной (scp) | да, сервер только читается |
| `.\run-bot.cmd` | **запуск Telegram-бота локально** | **НЕТ, пока прод работает** |

**Почему нельзя `run-bot.cmd`:** в локальном `.env` тот же боевой токен, что на
сервере. Второй процесс с тем же токеном даёт `Conflict: terminated by other
getUpdates`: прод-бот на время перестаёт получать сообщения. Если бот всё же
запустился локально: `Ctrl+C` (или `.\.venv\Scripts\python.exe -m bot.launcher stop`),
затем убедиться, что прод снова в порядке (§8.2). Для локального просмотра игры
использовать `run-cli.cmd` / `bot.cli --provider demo`.

`launcher status` может показать `Бот не запущен. PID-файл: 24444.` — это устаревший
`data/bot.pid` после аварийного завершения, он безвреден: `launcher` проверяет,
жив ли процесс, и не доверяет файлу.

### 1.7 Проверка окружения: `bot.doctor`

```powershell
.\.venv\Scripts\python.exe -m bot.doctor
```

Ожидаемо локально (без VPN): `[OK  ] DeepSeek: ключ работает…` и
`[ОШИБКА] Telegram: нет соединения с api.telegram.org (ConnectTimeout)` — это
состояние сети, а не повод что-то чинить. На сервере оба пункта должны быть `OK`.
Код возврата 1 при одной ошибке — нормально; `run-bot.cmd` в этом случае всё равно
пробует запустить бота.

---

## 2. Обязательные проверки перед любым изменением

Порядок железный: сначала проверки, потом правка/деплой. Baseline на 10.11.2026 —
**216 passed**.

### 2.1 Тесты

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Ожидаемо: строка `216 passed in ~3–4s` и exit code 0. Тесты не ходят в сеть
(FakeLLM, временная база), `%TEMP%` не используют.

Если упало: **не деплоить**. Смотреть первые FAILED и traceback; типичные причины —
сломанный контракт сценария (`tests/test_scenarios_contract.py`), изменённая схема
`scenario.json` без правки тестов, импорт нового модуля не в том месте. Если упал
один тест из-за правимого файла — починить код/тест, прогнать снова.

### 2.2 Demo-прогон изменённого сценария (и соседей)

```powershell
# прогон конкретного сценария: реплики в консоль, /finish — разбор, /state — состояние
.\.venv\Scripts\python.exe -m bot.cli --provider demo --scenario eva_message
.\.venv\Scripts\python.exe -m bot.cli --provider demo --scenario first_message
```

Ожидаемо: заголовок сценария, рамка «это тренажёр», описание/анкета, ответы
персонажа, в конце — `Разбор: «…»` и `Итог: N из 12`, exit 0. Проверено 10.11.2026:
`eva_message` → `Итог: 9 из 12`, `first_message` → разбор тоже печатается.

Неинтерактивный вариант для агента (stdin закрывается сам, exit 0):

```powershell
$env:PYTHONIOENCODING='utf-8'
@('Привет, как ты?','Понимаю, что устала.') | .\.venv\Scripts\python.exe -m bot.cli --provider demo --scenario first_message
```

Доступные сценарии: `first_message`, `first_call`, `first_date`, `eva_message`;
выключенные (`enabled: false`), но играбельные по id — `friday_evening`, `reunion_call`.
Правило: менял сценарий — прогоняй его; менял общий код — прогоняй минимум
`first_message` и `eva_message`.

### 2.3 Окружение и статус

```powershell
.\.venv\Scripts\python.exe -m bot.doctor
.\.venv\Scripts\python.exe -m bot.launcher status
```

Ожидаемо: см. §1.7; `launcher` — `Бот не запущен` (локальный бот не нужен).

### 2.4 Состояние репозитория

```powershell
git status --short
git diff --stat
```

Сейчас в рабочей копии много незакоммиченных изменений итерации «Героини: Вера
и Ева» (это нормально для текущего пакета передачи). Перед деплоем полезно
зафиксировать, какие файлы меняются именно этим деплоем: `git status` / `git diff`
— чтобы не выложить случайное. Локальные коммиты разрешены; `git push` — только
по явной команде владельца.

### 2.5 Чек-лист «готов к деплою»

- [ ] `pytest -q` → `216 passed` (или новый baseline, если тесты добавили осознанно).
- [ ] Demo-прогон затронутых сценариев доходит до разбора, exit 0.
- [ ] `bot.doctor`: DeepSeek `OK`; Telegram-ошибка локально ожидаема.
- [ ] Правки не касаются `.env`, `data/bot.db`, секретов в документации.
- [ ] Если правились `deploy/*.sh` / `*.service` / `*.cron` на Windows — у файлов
      остались **LF**-переводы строк (`.gitattributes` требует `eol=lf`):

```powershell
Get-ChildItem deploy\*.sh,deploy\*.cron,deploy\*.service | ForEach-Object {
  if ([IO.File]::ReadAllText($_.FullName) -match "`r") { "CRLF: $($_.Name)" }
}
```

Ожидаемо: пусто (ни одной строки `CRLF:`). Если есть — пересохранить файл с LF,
иначе на сервере bash/systemd споткнутся о `\r`.
- [ ] Известно, что именно меняем на сервере, и получено согласие владельца на деплой.

---

## 3. Деплой на VPS: шаг за шагом

Схема: **тесты → бэкап базы → архив → scp → распаковка → права → `pip install -e .`
→ restart → проверка**. Ни один шаг нельзя переставлять.

### 3.0 Предпосылки

- SSH по ключу уже настроен: `~/.ssh/id_ed25519` есть, сервер в `known_hosts`,
  вход под `root` работает без пароля. Проверка:

```powershell
ssh -o BatchMode=yes -o ConnectTimeout=10 root@48.102.186.191 "echo OK; hostname"
```

Ожидаемо: `OK` и `vm1496646.cloud.nuxt.network`. Если висит/просит пароль — ключ
не тот или сеть; без `OK` дальше не идти.

- Алиаса `trainer` из §0.5 `DEPLOY.md` в системе **нет** (`~/.ssh/config` не создан):
  во всех командах использовать полное `root@48.102.186.191`.
- Инструменты: `tar` = bsdtar 3.7.6 (Windows System32), `ssh`/`scp` = OpenSSH 9.5,
  при необходимости есть Git Bash (`C:\Program Files\Git\bin\bash.exe`).
- Прод живёт в `Europe/Berlin`; «сейчас» на сервере проверять `ssh … date`.
- Все команды ниже выполняются из `C:\Projects\MFTranslator`.
- **Первичная установка** (сервер с нуля, `.venv`, пользователь `trainer`, `.env`,
  юнит) — `deploy/DEPLOY.md` §0–§6, скрипт `deploy/setup.sh` идемпотентен. Этот
  runbook описывает обновления уже работающего сервера.

### 3.1 Шаг 0. Локальные проверки

Выполнить §2.1–2.2. Без `216 passed` деплой не начинать.

### 3.2 Шаг 1. Бэкап базы на сервере

Перед любым обновлением кода — снять консистентную копию базы. Это часть деплоя,
а не read-only проверка: `backup.sh` пишет файл в `/var/backups/emotion-trainer`.

```powershell
ssh -o BatchMode=yes root@48.102.186.191 "bash /opt/mf-translator/deploy/backup.sh"
```

Ожидаемо: `Готово: /var/backups/emotion-trainer/bot-2026-11-10_1131.db` (имя —
дата_ЧЧММ серверного времени). Если `Базы пока нет … бэкапить нечего` — это первый
деплой, можно продолжать.

Если упало: `Permission denied` — запускать от `root` (как выше); `sqlite3: not found`
— сломан `setup.sh`, поставить `sudo apt install -y sqlite3`.

### 3.3 Шаг 2. Собрать архив

Архив собирается **только из перечисленных путей**: так `.env` и `data/bot.db`
физически не попадают внутрь.

```powershell
# папка .tmp должна существовать; из неё же потом забираем архив
if (-not (Test-Path .tmp)) { New-Item -ItemType Directory .tmp | Out-Null }

tar -czf .tmp\update.tgz AGENTS.md README.md PROGRESS.md pyproject.toml .env.example .gitignore run-bot.cmd run-cli.cmd sessions.cmd bot deploy heroines scenarios prompts tests
```

Список проверен 10.11.2026: все 15 путей существуют. В архив **не входят**:
`.env`, `data/`, `.venv/`, `.git/`, `.tmp/`, `.uv-cache/`, `.idea/`, `.dsh/`,
`docs/`, `CLAUDE.md`, `.claude/`, `spike/` — ни секреты, ни база, ни локальная
история, ни миграционные документы.

Ожидаемо: команда без вывода, exit 0, файл `.tmp\update.tgz` появился (десятки МБ
из-за фото сценариев — это норма).

Если `tar: Can't open '.tmp\update.tgz'` — нет папки `.tmp` (создать, см. выше).

### 3.4 Шаг 3. Проверить, что в архиве нет секретов

```powershell
$names = tar -tzf .tmp\update.tgz
"записей: $($names.Count)"
if ($names -match '(^|/)\.env$' -or $names -match '(^|/)data/') { 'STOP: в архиве .env или data' } else { 'OK: .env и data не попали' }
```

Ожидаемо: `OK: .env и data не попали` (`.env.example` под проверку не попадает —
он не заканчивается на `.env`). Если `STOP` — пересобрать архив, на сервер **не
отправлять**.

### 3.5 Шаг 4. Отправить архив

```powershell
scp -o BatchMode=yes .tmp\update.tgz root@48.102.186.191:/opt/update.tgz
```

Ожидаемо: без вывода, exit 0. Проверка на сервере:

```powershell
ssh -o BatchMode=yes root@48.102.186.191 "ls -l /opt/update.tgz"
```

Ожидаемо: файл с сегодняшним временем и ненулевым размером. Если `Permission
denied` — идти под `root` (у `/opt` root-владелец). Если `Host key verification
failed` — изменился ключ хоста: уточнить у владельца/провайдера, не отключать
проверку вслепую.

### 3.6 Шаг 5. Распаковать и выставить права (на сервере)

Блок серверный: отправить его целиком через `bash -s` (надёжно, без проблем
с кавычками PowerShell) или выполнить после `ssh root@48.102.186.191`.

```powershell
@'
cd /opt
tar -xzf update.tgz -C /opt/mf-translator && rm update.tgz
chown -R trainer:trainer /opt/mf-translator
# Права: архив из Windows приносит файлы с 666 — без этого код writable для всех.
chmod -R u=rwX,go=rX /opt/mf-translator/bot /opt/mf-translator/deploy \
  /opt/mf-translator/scenarios /opt/mf-translator/tests /opt/mf-translator/prompts \
  /opt/mf-translator/heroines
find /opt/mf-translator -maxdepth 1 -type f -exec chmod 644 {} +
chmod 600 /opt/mf-translator/.env
chmod 750 /opt/mf-translator/data
chmod 600 /opt/mf-translator/data/bot.db 2>/dev/null || true
'@ | ssh -o BatchMode=yes -o ConnectTimeout=10 root@48.102.186.191 bash -s
```

Ожидаемо: без вывода (кроме возможного `chmod: … No such file` при первом деплое —
это норма). Список каталогов включает `heroines` дополнительно к §7 `DEPLOY.md`
(см. §9): иначе файлы героинь останутся с правами из Windows.

Проверка прав (read-only):

```powershell
ssh -o BatchMode=yes root@48.102.186.191 "stat -c '%a %U:%G %n' /opt/mf-translator/.env /opt/mf-translator/data /opt/mf-translator/data/bot.db; find /opt/mf-translator/heroines -type f | head -3 | xargs stat -c '%a %U:%G %n'"
```

Ожидаемо: `.env` → `600 trainer:trainer`, `data` → `750`, `bot.db` → `600`,
файлы героинь → `644 trainer:trainer`.

Важно: tar распаковывается «поверх» — файлы, **удалённые/переименованные** локально,
на сервере останутся. Если в этой итерации что-то удалялось/переименовывалось,
старый файл нужно убрать руками (осознанно, по списку) или не полагаться на
`import`-конфликты в тестах.

### 3.7 Шаг 6. Зависимости

```powershell
ssh -o BatchMode=yes root@48.102.186.191 "sudo -u trainer -H /opt/mf-translator/.venv/bin/pip install -q -e /opt/mf-translator"
```

Ожидаемо: без вывода при успехе. Если менялся `pyproject.toml`, pip скачает новую
зависимость (серверу нужен доступ к PyPI — он есть). Если упало — **не
перезапускать сервис**: сначала починить. Частая причина — новая зависимость не
добавлена в `pyproject.toml` или требует Python новее 3.12 (на сервере 3.12.16).

### 3.8 Шаг 7. Перезапустить бота

```powershell
ssh -o BatchMode=yes root@48.102.186.191 "systemctl restart emotion-trainer"
```

Ожидаемо: exit 0. Это единственное место, где сервис останавливается/запускается;
если `restart` вернул ошибку — смотреть `systemctl status` и журнал.
`Restart=always` и `RestartSec=5` поднимут бота, даже если процесс упадёт,
но это не заменяет проверку.

### 3.9 Шаг 8. Проверить, что деплой прошёл

Сразу выполнить §8.1/§8.2 (там точные команды и ожидаемые строки). Признак успеха:
`active`, в журнале текущего процесса `Бот запущен` + `Run polling`, без
`Traceback`/`Conflict`. Если проверка не прошла — §6 и §5 (откат), не «подождать
и посмотреть».

### 3.10 Шаг 9. Живая проверка в Telegram (владелец или по его просьбе)

`/start` → рамка «это тренажёр», описание сцены, карточки анкеты; `/menu` → героиня
→ сцена; после разбора — «Продолжить». Это единственная end-to-end проверка:
локально Telegram недоступен. Агент сам в Telegram не заходит.

### 3.11 Что не перезаписывается и почему

- `.env` и `data/bot.db` в архив не входят → на сервере остаются как были.
- Миграции схемы SQLite (`updated_at`, `ended_by_persona`, …) выполняются при
  старте: старые диалоги не теряются, но **обратная совместимость с очень старым
  кодом не гарантируется** — поэтому перед деплоем бэкап (шаг 1).
- `.venv` не в архиве: используется серверный Python 3.12.16.
- `.tmp/` сервера не перезаписывается, карточки перерисуются при необходимости.

### 3.12 Если менялся systemd-юнит или setup-скрипт

Если правился `deploy/emotion-trainer.service` (или `deploy/setup.sh`), после
распаковки пере-рендерить юнит и применить:

```powershell
ssh -o BatchMode=yes root@48.102.186.191 "bash /opt/mf-translator/deploy/setup.sh"
```

Скрипт идемпотентный: доставит зависимости, перезапишет юнит из шаблона,
`daemon-reload`, перезапустит сервис (если ключи в `.env` заполнены). Проверка
после — та же (§8).

---

## 4. Проверка боевого сервера (только чтение)

### 4.1 Инвентарь прода (проверено 10.11.2026)

| Параметр | Значение |
|---|---|
| Хост / IP | `vm1496646.cloud.nuxt.network` / `48.102.186.191` (Германия, nuxt.cloud) |
| ОС / ресурсы | Ubuntu 22.04, 1 vCPU, 2 GB RAM, 30 GB (занято 21%) |
| Часовой пояс | `Europe/Berlin` (CET): журнал и cron в нём, МСК = CET+2 зимой |
| Код | `/opt/mf-translator`, владелец `trainer:trainer`, каталог `750` |
| Сервис | `emotion-trainer`: `enabled`, `active`; `MainPID` = `data/bot.pid` |
| Python сервера | `/opt/mf-translator/.venv/bin/python` → 3.12.16 (deadsnakes) |
| База | `data/bot.db` — 81 920 байт (80 КБ), `600`, 3 users / 7 sessions / 4 debriefs |
| Бэкапы | `/var/backups/emotion-trainer`; cron `/etc/cron.d/emotion-trainer-backup` (04:17) |
| Сеть | long polling, входящие порты не нужны; `TELEGRAM_PROXY` пуст |

### 4.2 Разрешённые read-only команды

Можно выполнять без согласования (ничего не меняют):

```powershell
# сервис и юнит
ssh -o BatchMode=yes root@48.102.186.191 "systemctl is-active emotion-trainer"
ssh -o BatchMode=yes root@48.102.186.191 "systemctl is-enabled emotion-trainer"
ssh -o BatchMode=yes root@48.102.186.191 "systemctl show -p ActiveEnterTimestamp -p MainPID --value emotion-trainer"
ssh -o BatchMode=yes root@48.102.186.191 "systemctl cat emotion-trainer"

# журнал (последние строки; фильтр по PID — только текущий процесс, см. §8)
ssh -o BatchMode=yes root@48.102.186.191 "journalctl -u emotion-trainer -n 30 --no-pager"

# файлы
ssh -o BatchMode=yes root@48.102.186.191 "ls -la /opt/mf-translator /opt/mf-translator/data"
ssh -o BatchMode=yes root@48.102.186.191 "stat -c '%a %U:%G %s %y %n' /opt/mf-translator/data/bot.db"
ssh -o BatchMode=yes root@48.102.186.191 "cat /opt/mf-translator/data/bot.pid"

# процессы и база (чтение через read-only URI, без блокировок)
ssh -o BatchMode=yes root@48.102.186.191 "pgrep -af bot.telegram_bot"
ssh -o BatchMode=yes root@48.102.186.191 "sqlite3 'file:/opt/mf-translator/data/bot.db?mode=ro' 'select (select count(*) from users), (select count(*) from sessions);'"

# бэкапы и ресурсы
ssh -o BatchMode=yes root@48.102.186.191 "ls -lt /var/backups/emotion-trainer | head -5"
ssh -o BatchMode=yes root@48.102.186.191 "df -h /; free -m | head -2"
```

### 4.3 Что запрещено без явного разрешения владельца

- `systemctl restart|stop|start|daemon-reload`, `kill` процесса бота.
- `deploy/backup.sh` (пишет файл — это уже изменение состояния).
- `pip install`, `apt`, `chown`, `chmod`, `rm`, распаковка архивов на проде.
- Редактирование `.env` и любых файлов в `/opt/mf-translator`.
- `git pull`/коммиты на сервере (там нет git-клона).
- «Проверочный» запуск `python -m bot.telegram_bot` где-либо — это второй polling
  с боевым токеном (см. §6, `Conflict`).

### 4.4 Сверка кода: локально == на сервере

```powershell
foreach ($f in 'bot/telegram_bot.py','bot/config.py','scenarios/eva_message/scenario.json','heroines/eva/heroine.json') {
  $local  = (Get-FileHash -Algorithm SHA256 $f).Hash.ToLower()
  $remote = ((ssh -o BatchMode=yes root@48.102.186.191 "sha256sum /opt/mf-translator/$f") -split ' ')[0]
  "$f : $(if ($local -eq $remote) {'совпадает'} else {'РАСХОДИТСЯ'})"
}
```

Ожидаемо: все `совпадает` (проверено 10.11.2026 для `bot/telegram_bot.py`,
`bot/config.py`, `scenarios/eva_message/scenario.json`, `heroines/eva/heroine.json`,
`deploy/DEPLOY.md`, `pyproject.toml`). Расхождение после деплоя — либо архив не
доехал, либо файл на сервере правили руками: смотреть §6, не «чинить» на сервере.

### 4.5 Критерии «прод здоров»

| Признак | Как проверить | Норма |
|---|---|---|
| Сервис активен | `systemctl is-active` | `active` |
| Один процесс, тот же PID | `MainPID` vs `cat data/bot.pid` | совпадают, `pgrep` — одна строка |
| Бот опрашивает Telegram | журнал текущего PID | `Бот запущен` + `Run polling` |
| Нет ошибок | журнал текущего PID | нет `Traceback`, нет `Conflict` |
| База открывается | `sqlite3 … mode=ro` | числа без ошибок |
| Свежие сообщения обслуживаются | журнал | `Update id=… is handled`, `POST …/chat/completions … 200 OK` |
| Диск/память | `df`, `free` | диск < 80 %, память < 1.5 GB |

### 4.6 Просмотр диалогов (read-only по смыслу)

```powershell
.\sessions.cmd
```

`bot/session_sync.py` снимает **копию** серверной базы через `sqlite3.backup`,
забирает её `scp` в локальный `.tmp/` и сливает с локальной — боевая база не
изменяется. На сервере создаётся временный `/tmp/mf-bot-view-*.db` и удаляется
после; это допустимая read-only операция. Если сервер недоступен — показывается
последний кэш.

---

## 5. Бэкапы, восстановление, откат

### 5.1 Ручной бэкап

```powershell
ssh -o BatchMode=yes root@48.102.186.191 "bash /opt/mf-translator/deploy/backup.sh"
```

Что делает `deploy/backup.sh`: `sqlite3 .backup` (консистентный снимок на живой
базе; копировать `bot.db` файлом нельзя), имя `bot-YYYY-MM-DD_HHMM.db` в
`/var/backups/emotion-trainer`, хранение `KEEP_DAYS=14` дней, старые удаляются.

Ожидаемо: строка `Готово: /var/backups/emotion-trainer/bot-….db`.

### 5.2 Ежедневный cron

`/etc/cron.d/emotion-trainer-backup` (уже установлен; файл-шаблон —
`deploy/emotion-trainer-backup.cron`):

```
17 4 * * * root /opt/mf-translator/deploy/backup.sh >/dev/null 2>&1
```

Время — серверное (Berlin): 04:17 CET = 06:17 МСК зимой, 05:17 МСК летом.
Проверка, что cron на месте: `ls -l /etc/cron.d/emotion-trainer-backup`.
Если файла нет — поставить (это изменение, только с согласия владельца):

```powershell
ssh -o BatchMode=yes root@48.102.186.191 "cp /opt/mf-translator/deploy/emotion-trainer-backup.cron /etc/cron.d/emotion-trainer-backup && chmod 644 /etc/cron.d/emotion-trainer-backup"
```

### 5.3 Проверить, что бэкапы живые

```powershell
ssh -o BatchMode=yes root@48.102.186.191 "ls -lt /var/backups/emotion-trainer | head -5"
```

Проверка целостности последнего бэкапа одной командой (read-only: `pragma
quick_check` ничего не меняет; проверено 10.11.2026 → `ok` и число сессий):

```powershell
ssh -o BatchMode=yes root@48.102.186.191 'latest=$(ls -t /var/backups/emotion-trainer/bot-*.db | head -1); echo "$latest"; sqlite3 \"$latest\" \"pragma quick_check; select count(*) from sessions;\"'
```

Ожидаемо: путь к самому свежему бэкапу, `ok` и число сессий. Бэкапы принадлежат
`root:root` (cron пишет от root) — при восстановлении не забыть `chown trainer:trainer`.

### 5.4 Восстановление базы из бэкапа

Внимание: диалоги за время после снимка будут потеряны — сначала уточнить у
владельца, это осознанное решение. Блок серверный, отправляется через `bash -s`:

```powershell
@'
systemctl stop emotion-trainer
cp /var/backups/emotion-trainer/bot-2026-11-10_1131.db /opt/mf-translator/data/bot.db
chown trainer:trainer /opt/mf-translator/data/bot.db
chmod 600 /opt/mf-translator/data/bot.db
systemctl start emotion-trainer
'@ | ssh -o BatchMode=yes -o ConnectTimeout=10 root@48.102.186.191 bash -s
```

Проверка: §8.1/§8.2; дополнительно — что числа в базе соответствуют ожидаемым:
`sqlite3 'file:/opt/mf-translator/data/bot.db?mode=ro' 'select count(*) from sessions;'`.

### 5.5 Откат кода

Git-клона на сервере нет, деплой — архивом. Поэтому:

1. **Перед деплоем** сохранить прошлый архив локально — он остаётся в
   `.tmp\update.tgz` после `scp`; перед сборкой нового переименовать:
   `Move-Item .tmp\update.tgz .tmp\update-prev.tgz` (если файл есть).
   **Сейчас такого «known good» архива нет:** итерация героинь задеплоена
   владельцем, локальный `update.tgz` не сохранён. Пока не поздно, стоит собрать
   архив текущего (работающего) состояния по §3.3 и отложить его как
   `update-known-good.tgz` — он и будет базой отката, если следующий деплой сломает
   бота.
2. Откат = повторить §3.5–3.9 с `update-prev.tgz` (scp → распаковка → права →
   `pip install -e .` → restart → проверка). База при этом не трогается.
3. Если проблема в схеме/данных — дополнительно восстановить базу из бэкапа (§5.4).
4. После отката — обязательно §8 и запись в отчёт, что именно откатили.

Если правки ещё не задеплоены, локальный откат делается через git
(`git diff`/`git checkout -- <файл>`), но помнить: часть работы не закоммичена,
`git checkout` может уничтожить единственную копию — сначала спросить владельца.

### 5.6 Чего не делать

- Не копировать живой `data/bot.db` файлом (только `sqlite3 .backup` /
  `deploy/backup.sh`) — иначе получите битую копию.
- Не удалять `data/bot.db` «для чистого старта»: это все диалоги пользователей.
- Не «лечить» прод правкой файлов на сервере — следующий деплой перезапишет,
  а расхождение с локальным останется незамеченным.
- Не делать `git push` и не переписывать историю.

---

## 6. Типовые поломки

| Симптом | Причина | Что делать |
|---|---|---|
| `TelegramConflictError: … Conflict: terminated by other getUpdates` | запущен второй экземпляр с тем же токеном (локальный `run-bot.cmd` или старый процесс) | `pgrep -af bot.telegram_bot` на сервере; локальный бот остановить (`Ctrl+C` / `bot.launcher stop`), затем `systemctl restart emotion-trainer` и §8.2 |
| Прод перестал отвечать после локального `run-bot.cmd` | локальный бот с боевым токеном забрал getUpdates | остановить локальный, перезапустить прод, убедиться, что `Conflict` больше не появляется |
| `doctor`: «нет соединения с api.telegram.org» на **сервере** | сеть хостинга не видит Telegram | `TELEGRAM_PROXY` (socks5/http на зарубежный) или другой VPS; локально эта же ошибка — норма |
| `doctor`: 401 | токен перевыпущен/опечатка | обновить `.env` на сервере, `systemctl restart emotion-trainer` |
| `doctor`: 402 | кончился баланс DeepSeek | пополнить на platform.deepseek.com |
| `Permission denied` на `data/` | сервис/файлы не под `trainer` | `sudo chown -R trainer:trainer /opt/mf-translator/data`, права `750`/`600`, restart |
| Сервис `active`, но в логе нет `Run polling` | бот ещё стартует (2–6 с) | подождать 10 с, проверить §8.2; если так и нет — журнал |
| Сервис циклически рестартует, `Traceback` в журнале | забытая зависимость в `pyproject.toml` (так было с `Pillow`) или ошибка загрузки сценария | прочитать traceback; `pip install -e .`; если сценарий — проверить `tests/test_scenarios_contract.py`; откат по §5.5 |
| `pip install -e .` падает | нет сети до PyPI, нет новой зависимости в `pyproject.toml`, зависимость требует Python > 3.12 | исправить, повторить; **сервис не перезапускать** до успеха |
| «Бот не отвечает» после правки `.env` | забыт restart | `systemctl restart emotion-trainer`, проверка §8 |
| Бот пишет «Не получилось ответить» | сеть до DeepSeek или формат ответа модели | `journalctl -u emotion-trainer -n 100`; проверить `bot.doctor` на сервере |
| `Traceback` в журнале, но старый | в `journalctl -n 20` попадают прошлые падения (см. 09.11 и 00:57 в истории) | фильтровать по текущему PID/`--since`, §8.2 — не пугаться старого |
| `CERTIFICATE_VERIFY_FAILED` / `self-signed certificate in chain` | VPN/антивирус проверяет HTTPS | разрешить посреднику сертификат; `bot/tls.py` (truststore) уже включён |
| `tar: Can't open '.tmp\update.tgz'` | нет папки `.tmp` | `New-Item -ItemType Directory .tmp` |
| В архиве оказались `.env`/`data` | собрали не по списку §3.3 | пересобрать, на сервер не отправлять |
| Файлы на сервере с правами `666` / `Permission denied` | пропущен `chmod` после распаковки | повторить шаг 3.6 (включая `heroines`), проверить `stat` |
| `ssh: Permission denied (publickey)` | не тот ключ/пользователь | проверять `~/.ssh/id_ed25519`, `known_hosts`; не создавать новый ключ без владельца |
| `Host key verification failed` | сменился ключ хоста (переустановка VPS) | уточнить у владельца/провайдера; не отключать проверку вслепую |
| `data/bot.pid` есть, но бот «не запущен» (локально) | устаревший PID-файл после падения | безвредно; `launcher` проверяет живой процесс, файл можно не трогать |
| `sessions.cmd` не видит свежие сессии | сервер недоступен или кэш 2 мин | подождать/проверить SSH; кэш `.tmp/vps-bot.db` |
| `.tmp/` на сервере растёт | карточки анкеты/экран звонка | `rm -rf /opt/mf-translator/.tmp/*` (изменение — с согласия владельца; перегенерируется) |

---

## 7. Важно для Claude Code

1. **Правило деплоя не меняется.** Изменил код/сценарий/конфиг → тесты →
   деплой → restart → проверка (§3, §8). «Локально работает» — не доказательство.
   Деплой и перезапуск прода — только с явного подтверждения владельца
   (это же записано в `.claude/settings.json` и `CLAUDE.md`).
2. **Оболочка.** Основной вариант — PowerShell (так проверены все команды выше).
   В системе есть Git Bash (`C:\Program Files\Git\bin\bash.exe`): если Claude Code
   выполняет команды через него, те же `tar`/`scp`/`ssh` работают, только пути
   писать через `/` (`./.venv/Scripts/python.exe`). PowerShell-особенность:
   одинарные кавычки сохраняют `$(...)` для сервера, но вложенные двойные кавычки
   PowerShell «съедает». Поэтому многострочные проверки отправлять через stdin:

   ```powershell
   @'
   systemctl is-active emotion-trainer
   cat /opt/mf-translator/data/bot.pid
   '@ | ssh -o BatchMode=yes root@48.102.186.191 bash -s
   ```

   А в однострочниках, где нужен `grep` с пробелами, экранировать кавычки:
   `grep -E \"Бот запущен|Run polling\"` (проверено).
3. **SSH уже настроен.** `~/.ssh/id_ed25519` + `known_hosts`; пароль не нужен.
   Алиаса `trainer` нет — писать `root@48.102.186.191`; добавлять
   `-o BatchMode=yes -o ConnectTimeout=10`, чтобы команда падала, а не ждала ввода.
4. **Секреты.** Никогда не печатать `.env` (локальный и `/opt/mf-translator/.env`),
   не читать его «для проверки», не вставлять токены в документы/отчёты/команды.
   Проверка токенов — только `bot.doctor`. В `.claude/settings.json` чтение `.env`
   и `git push` уже запрещены правилами прав.
5. **Права Claude Code.** В `.claude/settings.json` авторазрешены только тесты,
   `bot.cli`, `bot.doctor`, `bot.launcher`, `git status/diff/log/…` и чтение
   каталогов. `ssh`, `scp`, `tar`, `systemctl`, `pip install`, `sudo` требуют
   подтверждения (ask) — это норма, а не поломка: перед деплоем значит, что владелец
   увидит запрос. Слэш-команды `.claude/commands/`: `/test`, `/smoke`, `/deploy`
   (деплой-команда останавливается дважды — перед `scp` и перед `restart`).
   Проверка после `/deploy` там короткая (`sleep 5; journalctl -n 20`); надёжнее
   дополнить её §8.2 этого runbook.
6. **Песочницы DSH больше нет.** Нюансы `%TEMP%`, `UV_CACHE_DIR`, сломанного `curl`
   по TLS из `PROGRESS.md` относились к DSH-песочнице; в Claude Code они обычно
   не проявляются. `pytest`-кэш всё равно отключён в `pyproject.toml` — включать
   обратно не нужно.
7. **Что не деплоится.** `docs/`, `docs/migration/`, `CLAUDE.md`, `.claude/`,
   `spike/`, `.dsh/` в боевой архив не входят и на бота не влияют — их правки
   деплой не требуют. Деплоя требуют `bot/`, `scenarios/`, `heroines/`, `prompts/`,
   `tests/`, `deploy/`, `pyproject.toml`, `AGENTS.md`/`README.md`/`PROGRESS.md`
   (последние три — только как документация на сервере, на работу не влияют).
8. **Не путать две базы.** Локальная `data/bot.db` и серверная
   `/opt/mf-translator/data/bot.db` — разные файлы; серверная — единственная копия
   диалогов.
9. **Чего не делать без просьбы:** не деплоить, не рестартовать сервис, не менять
   `.env`, не трогать `deploy/*.sh`, не удалять незакоммиченную работу,
   не «оживлять» выключенные сценарии, не делать `git push`.

---

## 8. Как проверить, что деплой прошёл

Это же — безопасная read-only проверка прода в любой момент (можно давать агенту).

### 8.1 Сразу после `systemctl restart` (первые 30 секунд)

```powershell
# 1) сервис поднялся
ssh -o BatchMode=yes root@48.102.186.191 'systemctl is-active emotion-trainer'
# ожидаемо: active

# 2) текущий процесс: те же PID в systemd и в bot.pid
ssh -o BatchMode=yes root@48.102.186.191 'main=$(systemctl show -p MainPID --value emotion-trainer); pid=$(cat /opt/mf-translator/data/bot.pid); echo MainPID=$main bot.pid=$pid; test $main = $pid && echo PID-совпал'
# ожидаемо: «MainPID=… bot.pid=…» и «PID-совпал»

# 3) журнал старта текущего процесса
ssh -o BatchMode=yes root@48.102.186.191 'main=$(systemctl show -p MainPID --value emotion-trainer); journalctl -u emotion-trainer _PID=$main --no-pager | grep -E \"Бот запущен|Run polling|Traceback|Conflict\"'
# ожидаемо: «Бот запущен, сценарий: …» и «Run polling for bot @…»
# НЕ должно быть строк Traceback/Conflict
```

Почему фильтр `_PID`: `journalctl -n 20` может показать старые ошибки (на сервере
есть исторические `Traceback` от 09.11 и `Conflict` от 10.11 00:57) либо, наоборот,
не показать строки старта, если бот уже активно обрабатывает апдейты. Фильтр по PID
текущего процесса даёт именно его журнал.

Если бот ещё стартует — повторить через 10 с (наблюдаемое время от `Started` до
`Бот запущен` — около 5 с). Если через 30 с `Run polling` нет — §6.

### 8.2 Строгая проверка (одна команда, PowerShell)

Проверяет за один заход: сервис активен, PID совпадает, старт в журнале текущего
процесса, `Run polling`, отсутствие `Traceback`/`Conflict`. Возвращает `OK` или
падает с ошибкой (exit ≠ 0). Проверено 10.11.2026 — вывела
`OK: active, PID 194620, Бот запущен + Run polling, без Traceback/Conflict`.

```powershell
@'
set -e
main=$(systemctl show -p MainPID --value emotion-trainer)
test -n "$main" && test "$main" != 0
pid=$(cat /opt/mf-translator/data/bot.pid)
test "$main" = "$pid"
logs=$(journalctl -u emotion-trainer _PID="$main" --no-pager)
echo "$logs" | grep -q "Бот запущен"
echo "$logs" | grep -q "Run polling"
! echo "$logs" | grep -q "Traceback"
! echo "$logs" | grep -q "Conflict"
echo "OK: active, PID $main, Бот запущен + Run polling, без Traceback/Conflict"
'@ | ssh -o BatchMode=yes -o ConnectTimeout=10 root@48.102.186.191 bash -s
```

Трактовка: `OK: …` — деплой прошёл и бот жив; любая другая строка/exit ≠ 0 —
смотреть §8.5. Скрипт ничего не меняет: только `systemctl show`, `cat`,
`journalctl`, `grep`.

### 8.3 Быстрая «жив ли» без строгого скрипта

```powershell
ssh -o BatchMode=yes root@48.102.186.191 'systemctl is-active emotion-trainer; systemctl show -p ActiveEnterTimestamp --value emotion-trainer; journalctl -u emotion-trainer -n 3 --no-pager'
```

Ожидаемо: `active`, серверное время последнего старта, 3 последние строки журнала
(признак жизни — `Update id=… is handled` или `POST …/chat/completions 200 OK`).

### 8.4 Проверка версии содержимого

Сверить хеши ключевых файлов (§4.4): `совпадает` для изменённых файлов. Дополнительно
читать журнал старта: там печатается сценарий по умолчанию — `Бот запущен, сценарий:
Первое сообщение` (первый доступный по `order`). Если менялся код, но хеш на сервере
старый — архив не доехал или распакован не туда.

### 8.5 Если проверка не прошла

1. `journalctl -u emotion-trainer -n 100 --no-pager` — искать `Traceback`.
2. `systemctl status emotion-trainer` — цикл рестартов, код выхода.
3. Если ошибка из-за нового кода/зависимости: `pip install -e .` (§3.7), затем
   restart и снова §8.1.
4. Если не помогает — откат кода (§5.5) и/или базы (§5.4), затем снова §8.2.
5. Доложить владельцу: что менялось, что в журнале (без `.env`), что откатили.

### 8.6 Шаблон отчёта о деплое

```
Деплой 10.11.2026 13:32 МСК (11:32 CET): <что изменилось>.
Бэкап: /var/backups/emotion-trainer/bot-2026-11-10_1131.db
Проверка: active, PID 194620 (=bot.pid), «Бот запущен, сценарий: …», «Run polling»,
Traceback/Conflict в журнале текущего процесса нет.
Хеши изменённых файлов на сервере совпадают с локальными.
.env и data/bot.db не перезаписывались.
```

---

## 9. Замечания к `deploy/DEPLOY.md` (не правил, на отчёт владельцу)

Найдено при сверке 10.11.2026; сам `DEPLOY.md` не менялся (это вне зоны задачи).

1. **Часовой пояс сервера.** Сервер в `Europe/Berlin` (CET). Запись в `PROGRESS.md`
   «деплой 10.11.2026 11:32 МСК» — это серверное `11:32 CET` из журнала (фактически
   `13:32 МСК`): время журнала записали как московское. `journalctl` и `cron` дают
   серверное время; при сверке с МСК прибавлять 2 часа (зимой). В runbook учтено.
2. **`heroines/` не в списке `chmod`.** §7 `DEPLOY.md` (и цикл в `deploy/setup.sh`)
   нормализует права только для `bot deploy scenarios tests prompts`; каталог
   `heroines/`, добавленный вместе с Евой и Верой, там отсутствует. Сейчас на проде
   файлы героинь всё равно `644`, но при другом наборе файлов в архиве могут
   приехать `666`. В §3.6 я добавил `heroines` в команду.
3. **`SAFETY_RESOURCES`.** §3 `DEPLOY.md` велит вписать её в `.env`, но в
   `.env.example` такой переменной нет — `setup.sh` создаёт `.env` из примера, и
   строку приходится добавлять вручную. В проде переменная присутствует, но
   фактически **пустая** (`SAFETY_RESOURCES=` + пробел → `Settings.safety_resources
   is None`): бот подставляет fallback-текст с 112. Публичный запуск без реальных
   контактов не начинать.
4. **`sleep 5` в §7.** Старт бота занимает ~5–6 с (наблюдение: `Started 11:32:17` →
   `Бот запущен 11:32:22`), поэтому `sleep 5` на грани. В runbook — проверка с
   повтором до 30 с и фильтром по PID.
5. **`journalctl -n 20 | grep` даёт ложные срабатывания.** В истории журнала есть
   старые `Traceback` (09.11) и `Conflict` (10.11 00:57); при коротком хвосте можно
   либо не увидеть строки старта, либо испугаться старой ошибки. В §8 — фильтр
   `_PID` текущего процесса.
6. **Алиас `trainer`** из §0.5 не создан в `~/.ssh/config`; все команды — с полным
   `root@48.102.186.191`. Не ошибка, но при копировании примеров с алиасом
   команды не сработают.
7. **Слэш-команда `/deploy` (`.claude/commands/deploy.md`) повторяет те же два
   места:** в её `chmod` тоже нет `heroines`, а проверка после restart —
   `sleep 5; journalctl -n 20 | grep`. Файл принадлежит другому пакету (конфиг
   Claude Code), здесь не правился; после деплоя опираться на §8.2 этого runbook.

---

## 10. Evidence — что проверено 10.11.2026

```
# локально
.\.venv\Scripts\python.exe -m pytest -q
  → 216 passed in 3.42s
.\.venv\Scripts\python.exe -m bot.cli --provider demo --scenario eva_message
  → «Разбор: «Первое сообщение»», «Итог: 9 из 12», exit 0
.\.venv\Scripts\python.exe -m bot.cli --provider demo --scenario first_message
  → разбор напечатан, exit 0 (в т.ч. неинтерактивно через stdin)
.\.venv\Scripts\python.exe -m bot.doctor
  → [OK] DeepSeek: ключ работает, модель по умолчанию — deepseek-chat
  → [ОШИБКА] Telegram: нет соединения с api.telegram.org (ConnectTimeout) — сеть
.\.venv\Scripts\python.exe -m bot.launcher status
  → «Бот не запущен. PID-файл: 24444.» (устаревший pid-файл, безвреден)

# прод (read-only)
ssh -o BatchMode=yes root@48.102.186.191 "systemctl is-active emotion-trainer"
  → active (enabled; старт 10.11 11:32:17 CET, MainPID 194620 = data/bot.pid)
journalctl -u emotion-trainer _PID=194620 | grep -E "Бот запущен|Run polling"
  → «Бот запущен, сценарий: Первое сообщение»
  → «Start polling», «Run polling for bot @gralmy_bot id=…»
  → Traceback/Conflict у текущего процесса нет
sqlite3 'file:/opt/mf-translator/data/bot.db?mode=ro' 'select …'
  → 3 users, 7 sessions, 4 debriefs; файл 81 920 байт
ls -lt /var/backups/emotion-trainer | head -5
  → последний bot-2026-11-10_1131.db; cron /etc/cron.d/emotion-trainer-backup на месте
sha256sum ключевых файлов на сервере == Get-FileHash локально
  → bot/telegram_bot.py, bot/config.py, scenarios/eva_message/scenario.json,
    heroines/eva/heroine.json, deploy/DEPLOY.md, pyproject.toml — совпадают
```

Связанные документы: [`deploy/DEPLOY.md`](../../deploy/DEPLOY.md) (канон деплоя),
[`docs/migration/README.md`](README.md) (пакет передачи), [`AGENTS.md`](../../AGENTS.md)
(правила), [`PROGRESS.md`](../../PROGRESS.md) (история решений).
