# Деплой на VPS

Сервер под этот бот: **Ubuntu 22.04, 1 vCPU, 2 GB RAM, 30 GB**, IP **138.124.229.233**,
хостинг `nuxt.cloud` (Германия, AS216127). Для России это важно: Telegram там не
блокируется, поэтому `TELEGRAM_PROXY` скорее всего не понадобится — проверит `bot.doctor`.

Домен `vm1496646.cloud.nuxt.network` сейчас **не резолвится** (A-записи нет). Для long
polling домен не нужен вообще: бот сам ходит в Telegram, входящие порты не открываются.
Работаем по IP; если хочешь имя для SSH — добавь A-запись в DNS у провайдера.

## 0. Как устроен бот на сервере

- **long polling**, не webhook: ни nginx, ни сертификатов, ни домена не нужно;
- **SQLite** в `data/bot.db` — единственные данные, которые надо беречь; `.tmp/` (карточки
  анкеты, экран звонка) перегенерируется;
- **один процесс на токен**: второй экземпляр даст `Conflict: terminated by other
  getUpdates`, поэтому перезапуском занимается systemd, а не ручной запуск;
- зависимости ставятся из `pyproject.toml` (`pip install -e .`), lock-файла нет.

## 0.5. SSH-доступ

Деплой идёт по SSH под `root`. Публичный ключ (`~/.ssh/id_ed25519.pub`) должен попасть
в `~/.ssh/authorized_keys` на сервере. Два пути:

1. **Панель провайдера** (nuxt.cloud): раздел SSH keys / cloud-init — вставить содержимое
   `id_ed25519.pub` и применить к серверу. Удобнее всего, если доступ есть.
2. **Если у root есть пароль** — одной командой из PowerShell (подставь свой ключ; кавычки
   обязательны, иначе ключ разобьётся на аргументы и запишется битым):

   ```powershell
   ssh root@138.124.229.233 "mkdir -p ~/.ssh && chmod 700 ~/.ssh && echo 'ssh-ed25519 AAAA...ТВОЙ_КЛЮЧ... you@pc' >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys"
   ```

   Пароль спросится один раз. Публичный ключ не секретен, но приватный
   (`id_ed25519`, без `.pub`) в репозиторий и в чат не попадает никогда.

Проверка — без пароля:

```powershell
ssh -o BatchMode=yes root@138.124.229.233 "echo OK; hostname"
```

Если вывело `OK` — ключ работает, и `scp`/`tar` из раздела 1 пойдут без пароля.

Удобный алиас: `C:\Users\<ты>\.ssh\config` (на Linux — `~/.ssh/config`):

```
Host trainer
    HostName 138.124.229.233
    User root
    IdentityFile ~/.ssh/id_ed25519
    IdentitiesOnly yes
```

Дальше: `ssh trainer`, `scp ..\mf-translator.tgz trainer:/opt/`.

Если ssh ругается `UNPROTECTED PRIVATE KEY FILE`, у файла ключа слишком широкие права.
Windows-следующий вариант оставляет доступ только тебе (и системе):

```powershell
icacls "$env:USERPROFILE\.ssh\id_ed25519" /inheritance:r
icacls "$env:USERPROFILE\.ssh\id_ed25519" /grant:r "$env:USERNAME:(R)"
```

Харденинг — **только после того, как вход по ключу проверен** (иначе можно закрыть себе
доступ; консоль провайдера держи под рукой). Создать `/etc/ssh/sshd_config.d/99-hardening.conf`:

```
PasswordAuthentication no
KbdInteractiveAuthentication no
PermitRootLogin prohibit-password
```

```bash
sudo sshd -t && sudo systemctl reload ssh
```

Плюс `ufw` (раздел 5) и при желании `fail2ban`. После этого пароль от root больше не
работает — вход только по ключу, как и у сервиса `trainer` (у него пароля нет).

## 1. Перенести код с рабочей машины

В PowerShell из `C:\Projects\MFTranslator`:

```powershell
# архив кладём рядом с папкой проекта: внутри tree tar записал бы в него сам себя
tar -czf ..\mf-translator.tgz --exclude=.venv --exclude=.git --exclude=data --exclude=.tmp --exclude=.env --exclude=.uv-cache --exclude=.idea --exclude=.dsh --exclude=.tmp-dsh-ui* --exclude=pytest-cache-files-* --exclude="^dsh" .
scp ..\mf-translator.tgz root@138.124.229.233:/opt/
```

На сервере:

```bash
mkdir -p /opt/mf-translator
tar -xzf /opt/mf-translator.tgz -C /opt/mf-translator
rm /opt/mf-translator.tgz
```

Переносить историю диалогов с рабочей машины не обязательно. Если нужна — снимай
снимок, а не копируй живой файл: `sqlite3 data/bot.db ".backup data/bot-copy.db"`,
затем `scp data\bot-copy.db root@138.124.229.233:/opt/mf-translator/data/bot.db`
(папку `data` создать заранее).

Альтернатива — git: закоммитить и запушить, на сервере `git clone`. Git у репозитория
ходит по SSH, поэтому понадобится deploy key. Пушить можно только с явного разрешения
владельца — надёжнее и быстрее перенос архивом.

## 2. Установка

```bash
sudo bash /opt/mf-translator/deploy/setup.sh
```

Скрипт идемпотентный:
1) ставит Python 3.12 из deadsnakes (в Ubuntu 22.04 по умолчанию только 3.10, а проекту
нужен ≥ 3.12), `sqlite3`, `software-properties-common`;
2) создаёт системного пользователя `trainer` и отдаёт ему `/opt/mf-translator`;
3) собирает `.venv` и ставит зависимости;
4) создаёт `.env` из `.env.example` с правами `600`;
5) рендерит и включает `/etc/systemd/system/emotion-trainer.service`;
6) гоняет `bot.doctor`.

Первый запуск **остановится на шаге 6**, пока в `.env` пустые ключи — это ожидаемо.
Заполни `.env` (шаг 3) и запусти скрипт ещё раз: он доставит всё и стартует сервис.

### Те же шаги вручную (если скрипт не хочешь)

```bash
sudo apt update
sudo apt install -y software-properties-common ca-certificates sqlite3
sudo add-apt-repository -y ppa:deadsnakes/ppa
sudo apt update && sudo apt install -y python3.12 python3.12-venv

sudo useradd --system --home-dir /opt/mf-translator --shell /usr/sbin/nologin --no-create-home trainer
sudo chown -R trainer:trainer /opt/mf-translator

sudo -u trainer -H python3.12 -m venv /opt/mf-translator/.venv
sudo -u trainer -H /opt/mf-translator/.venv/bin/pip install -U pip
sudo -u trainer -H /opt/mf-translator/.venv/bin/pip install -e /opt/mf-translator

sudo -u trainer -H cp /opt/mf-translator/.env.example /opt/mf-translator/.env
sudo chmod 600 /opt/mf-translator/.env
```

Без PPA (например, если Launchpad недоступен) — `uv`, как на рабочей машине:

```bash
sudo apt install -y curl
sudo -u trainer -H bash -c 'curl -LsSf https://astral.sh/uv/install.sh | sh'
sudo -u trainer -H bash -c 'cd /opt/mf-translator && ~/.local/bin/uv venv .venv --python 3.13 && ~/.local/bin/uv pip install --python .venv -e .'
```

## 3. `.env`

```bash
sudo -u trainer nano /opt/mf-translator/.env
```

| Переменная | Что писать |
|---|---|
| `TELEGRAM_BOT_TOKEN` | токен от @BotFather (`/newbot`) |
| `DEEPSEEK_API_KEY` | ключ с platform.deepseek.com |
| `DEEPSEEK_BASE_URL` | `https://api.deepseek.com` — можно не менять |
| `DEEPSEEK_MODEL` | `deepseek-chat` — можно не менять |
| `TELEGRAM_PROXY` | оставить пустым: VPS в Германии, Telegram открыт |
| `DB_PATH` | `./data/bot.db` — можно не менять |
| `SAFETY_RESOURCES` | **вписать реальные контакты помощи** до публичного запуска: код их не выдумывает |

Права: `sudo chmod 600 /opt/mf-translator/.env` и владелец `trainer`. Файл в `.gitignore`.

Проверка:

```bash
sudo -u trainer /opt/mf-translator/.venv/bin/python -m bot.doctor
```

Должно быть два `OK`. Если Telegram — «нет соединения», это значит, что хостинг всё-таки
фильтрует: тогда `TELEGRAM_PROXY` (socks5/http на зарубежный прокси) или другой VPS.

## 4. systemd

Юнит уже установлен скриптом: `/etc/systemd/system/emotion-trainer.service`.
Если ставил вручную — отрендери шаблон:

```bash
sudo sed "s|__APP_DIR__|/opt/mf-translator|g; s|__SERVICE_USER__|trainer|g" \
  /opt/mf-translator/deploy/emotion-trainer.service \
  | sudo tee /etc/systemd/system/emotion-trainer.service
sudo systemctl daemon-reload
sudo systemctl enable --now emotion-trainer
```

Управление:

```bash
sudo systemctl status emotion-trainer
sudo systemctl restart emotion-trainer
sudo journalctl -u emotion-trainer -f        # живой лог
sudo journalctl -u emotion-trainer -n 100    # последние 100 строк
```

Сервис перезапускается сам (`Restart=always`, пауза 5 с). Остановка по `SIGTERM`
безопасна: SQLite коммитит каждый ход, миграции схемы выполняются при старте.

## 5. Файрвол

Входящие порты боту не нужны — только SSH. Если включаешь ufw, сначала разреши SSH
(и свой порт, если он нестандартный), потом включай:

```bash
sudo ufw allow OpenSSH
sudo ufw enable
sudo ufw status
```

## 6. Проверка после установки

```bash
sudo -u trainer /opt/mf-translator/.venv/bin/python -m bot.doctor
sudo systemctl status emotion-trainer --no-pager
sudo journalctl -u emotion-trainer -n 50 --no-pager
```

В Telegram: `/start` → должен прийти первый сценарий (переписка), `/scenario first_call`
→ экран звонка и «Алло. О. Ты правда позвонил.». Если это работает — деплой готов.

## 7. Обновления

**Правило: любое изменение кода или сценариев деплоится и перезапускает бота.**
Локальный прогон ничего не доказывает: пользователи ходят через VPS.

Порядок — тесты, бэкап, архив, распаковка, зависимости, перезапуск, проверка:

```powershell
# 0. локально: тесты и demo-прогон изменённого сценария
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe -m bot.cli --provider demo --scenario <id>

# 1. бэкап базы на сервере (данные не трогаем)
ssh root@138.124.229.233 "bash /opt/mf-translator/deploy/backup.sh"

# 2. архив только из нужных путей: .env, data, .git, .venv в него не попадают
tar -czf .tmp\update.tgz AGENTS.md README.md PROGRESS.md pyproject.toml .env.example .gitignore run-bot.cmd run-cli.cmd sessions.cmd bot deploy scenarios prompts tests
scp .tmp\update.tgz root@138.124.229.233:/opt/update.tgz
```

```bash
# на сервере
cd /opt
tar -xzf update.tgz -C /opt/mf-translator && rm update.tgz
chown -R trainer:trainer /opt/mf-translator
# Права: архив из Windows приносит файлы с 666 — без этого код writable для всех.
chmod -R u=rwX,go=rX /opt/mf-translator/bot /opt/mf-translator/deploy \
  /opt/mf-translator/scenarios /opt/mf-translator/tests /opt/mf-translator/prompts
find /opt/mf-translator -maxdepth 1 -type f -exec chmod 644 {} +
chmod 600 /opt/mf-translator/.env
chmod 750 /opt/mf-translator/data
chmod 600 /opt/mf-translator/data/bot.db 2>/dev/null || true
sudo -u trainer -H /opt/mf-translator/.venv/bin/pip install -q -e /opt/mf-translator
systemctl restart emotion-trainer
sleep 5
systemctl is-active emotion-trainer
journalctl -u emotion-trainer -n 20 --no-pager | grep -E "Бот запущен|Run polling|Traceback|Conflict" || true
```

Если менялся `deploy/emotion-trainer.service` (например, добавлен `UMask=0077`),
юнит нужно пере-рендерить и применить:

```bash
bash /opt/mf-translator/deploy/setup.sh
```

Успех — `active` и в логе `Бот запущен` + `Run polling`, без `Traceback` и `Conflict`.
Если сервис падает — `journalctl -u emotion-trainer -n 100`: чаще всего забытая
зависимость в `pyproject.toml` (так было с `Pillow`) или ошибка загрузки сценария.

Git-вариант (если на сервере клон): `git pull` под `trainer`, затем
`pip install -e .` и `systemctl restart emotion-trainer`.

`.env` и `data/bot.db` при обновлении не перезаписываются: их нет в архиве.
Миграции БД (`updated_at`, `ended_by_persona`) накатываются автоматически, старые
диалоги не теряются.

## 8. Резервная копия

Скрипт `deploy/backup.sh` снимает консистентную копию через `sqlite3 .backup`
(копировать `bot.db` на живую нельзя).

```bash
sudo bash /opt/mf-translator/deploy/backup.sh   # /var/backups/emotion-trainer
```

Поставить на ежедневный запуск:

```bash
sudo cp /opt/mf-translator/deploy/emotion-trainer-backup.cron /etc/cron.d/emotion-trainer-backup
sudo chmod 644 /etc/cron.d/emotion-trainer-backup
```

Восстановление:

```bash
sudo systemctl stop emotion-trainer
sudo cp /var/backups/emotion-trainer/bot-2026-11-09_0417.db /opt/mf-translator/data/bot.db
sudo chown trainer:trainer /opt/mf-translator/data/bot.db
sudo systemctl start emotion-trainer
```

## 9. Неполадки

| Симптом | Причина и что делать |
|---|---|
| `Conflict: terminated by other getUpdates` | запущен второй экземпляр с тем же токеном: `sudo pgrep -af bot.telegram_bot`, лишний убить, `sudo systemctl restart emotion-trainer`; на рабочей машине бот с тем же токеном должен быть выключен |
| `doctor`: «нет соединения с api.telegram.org» | сеть VPS не видит Telegram: `TELEGRAM_PROXY` или другой хостинг |
| `doctor`: 401 | токен перевыпущен/с опечаткой — обновить `.env` |
| `doctor`: 402 | кончился баланс DeepSeek — пополнить |
| `Permission denied` на `data/` | сервис запущен не под `trainer`: `sudo chown -R trainer:trainer /opt/mf-translator/data` |
| Бот пишет «Не получилось ответить» | `sudo journalctl -u emotion-trainer -n 100` — сеть до DeepSeek или формат ответа модели |
| ssh: `Permission denied, please try again` на пароле | Пароль из панели не применён или скопирован с лишним символом. Проверь вход **консолью провайдера**; если и там не пускает — Reset root password, перезагрузка сервера; если пускает — ставь ключ из консоли (раздел 0.5). `PermitRootLogin prohibit-password` тут ни при чём: `ssh -v` показывает, что сервер предлагает `publickey,password` |
| «Бот не отвечает» после обновления `.env` | забыл `sudo systemctl restart emotion-trainer` |

## 10. Мелочи

- Ресурсы: ~150 MB RAM (лимит 2 GB с запасом), диск занят в основном фотографиями
  сценариев (проект ~26 MB) и базой; 30 GB хватит надолго.
- `.tmp/` растёт медленно (карточки и экран звонка), чистится `rm -rf .tmp/*`.
- Windows-скрипты `run-bot.cmd`, `sessions.cmd`, `run-cli.cmd` и `bot.launcher` на сервере
  не нужны: сессии смотреть через `sudo -u trainer /opt/mf-translator/.venv/bin/python
  -m bot.session_view`.
- Для публичного запуска дочитай README: `SAFETY_RESOURCES`, приватность (стенограммы
  в `bot.db`), лимиты DeepSeek.
