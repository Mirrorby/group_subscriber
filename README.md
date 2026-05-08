# tg-group-joiner

Скрипт для вступления в Telegram-группы. Настройки и ссылки хранятся в Google Таблице.

## Подготовка

### 1. Клонировать репозиторий
git clone https://github.com/ТВО_ИМЯ/tg-group-joiner
cd tg-group-joiner
pip install -r requirements.txt

### 2. Google Sheets
- Google Cloud Console → новый проект
- Включить Google Sheets API + Google Drive API
- IAM → Service Accounts → создать → скачать JSON → переименовать в `credentials.json`
- Поделиться таблицей с email сервис-аккаунта

### 3. Telegram API
- my.telegram.org → API development tools → скопировать api_id и api_hash

### 4. Таблица
Запусти GAS-скрипт `setupSheets()` в таблице — он создаст листы config и groups.
Заполни лист config, добавь ссылки в groups.
Вставь ID таблицы в `SPREADSHEET_ID` в скрипте.

### 5. Запуск
python join_groups.py

При первом запуске введи номер телефона и код из Telegram.
Сессия сохраняется в `session.session` — повторная авторизация не нужна.

## Лист config

| Параметр | Значение |
|---|---|
| api_id | 123456 |
| api_hash | abc123... |
| phone | +79001234567 |
| spreadsheet_id | id из URL таблицы |
| delay_sec | 20 |
| skip_already_joined | TRUE |

## Файлы в .gitignore
- `credentials.json` — никогда не пушить
- `session.session` — файл сессии Telegram
