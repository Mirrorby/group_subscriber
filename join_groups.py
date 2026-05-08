import asyncio
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from telethon import TelegramClient
from telethon.errors import FloodWaitError, UserAlreadyParticipantError
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.tl.functions.messages import ImportChatInviteRequest
from datetime import datetime
import re

# === GOOGLE SHEETS ===
def get_sheet(name):
    scope = ['https://spreadsheets.google.com/feeds',
             'https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
    client = gspread.authorize(creds)
    spreadsheet_id = get_config_value(client, 'spreadsheet_id')
    ss = client.open_by_key(spreadsheet_id)
    return ss.worksheet(name)

def get_config_value(gc, key):
    # Читаем spreadsheet_id отдельно до инициализации sheet
    raise NotImplementedError

def load_config():
    scope = ['https://spreadsheets.google.com/feeds',
             'https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
    gc = gspread.authorize(creds)

    # Ищем таблицу по имени (альтернатива — вписать ID прямо в скрипт)
    # Проще: читаем spreadsheet_id из первой найденной таблицы с листом config
    # Для простоты — ID таблицы указываем здесь один раз
    ss = gc.open_by_key(SPREADSHEET_ID)
    config_sheet = ss.worksheet('config')
    rows = config_sheet.get_all_values()

    config = {}
    for row in rows[1:]:  # пропускаем заголовок
        if len(row) >= 2 and row[0].strip():
            config[row[0].strip()] = row[1].strip()
    return config, ss

def load_groups(ss, skip_done):
    sheet = ss.worksheet('groups')
    rows = sheet.get_all_values()
    links = []
    for i, row in enumerate(rows[1:], start=2):  # i = номер строки в таблице
        if not row or not row[0].strip():
            continue
        link = row[0].strip()
        status = row[1].strip() if len(row) > 1 else ''
        if skip_done and status in ('✅ Вступил', '⏭ Уже участник'):
            continue
        links.append((i, link))
    return sheet, links

def update_status(sheet, row_index, status):
    sheet.update_cell(row_index, 2, status)
    sheet.update_cell(row_index, 3, datetime.now().strftime('%d.%m.%Y %H:%M:%S'))

# === TELEGRAM ===
async def join(client, link):
    try:
        private = re.search(r't\.me/\+([a-zA-Z0-9_-]+)', link) or \
                  re.search(r't\.me/joinchat/([a-zA-Z0-9_-]+)', link)
        if private:
            await client(ImportChatInviteRequest(private.group(1)))
        else:
            await client(JoinChannelRequest(link))
        return 'ok'
    except UserAlreadyParticipantError:
        return 'already'
    except FloodWaitError as e:
        wait = e.seconds + 10
        print(f'  [!] FloodWait — жду {wait}s...')
        await asyncio.sleep(wait)
        return await join(client, link)
    except Exception as e:
        return f'error: {e}'

# === MAIN ===
# Единственная строка которую нужно заполнить вручную один раз:
SPREADSHEET_ID = 'ВСТАВЬ_ID_ТАБЛИЦЫ_СЮДА'

async def main():
    config, ss = load_config()

    api_id   = int(config['api_id'])
    api_hash = config['api_hash']
    phone    = config['phone']
    delay    = int(config.get('delay_sec', 20))
    skip     = config.get('skip_already_joined', 'TRUE').upper() == 'TRUE'

    groups_sheet, links = load_groups(ss, skip_done=skip)
    print(f'Ссылок к обработке: {len(links)}')

    async with TelegramClient('session', api_id, api_hash) as client:
        await client.start(phone=phone)

        for idx, (row_i, link) in enumerate(links, 1):
            print(f'[{idx}/{len(links)}] {link}')
            result = await join(client, link)

            if result == 'ok':
                status = '✅ Вступил'
            elif result == 'already':
                status = '⏭ Уже участник'
            else:
                status = f'❌ {result}'

            print(f'  → {status}')
            update_status(groups_sheet, row_i, status)

            if idx < len(links):
                await asyncio.sleep(delay)

    print('\nГотово!')

if __name__ == '__main__':
    asyncio.run(main())
