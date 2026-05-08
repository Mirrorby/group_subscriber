import asyncio
import os
import re
from datetime import datetime

import gspread
from oauth2client.service_account import ServiceAccountCredentials
from telethon import TelegramClient
from telethon.errors import FloodWaitError, UserAlreadyParticipantError
from telethon.sessions import StringSession
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.tl.functions.messages import ImportChatInviteRequest

# === КОНСТАНТА ===
SPREADSHEET_ID = '187fYAAQ1vHuaMTaUY6Pi_ucUXM4NXbH-dE_BsU6Rzt8'


# === GOOGLE SHEETS ===

def load_config():
    scope = [
        'https://spreadsheets.google.com/feeds',
        'https://www.googleapis.com/auth/drive'
    ]
    creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
    gc = gspread.authorize(creds)
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
    for i, row in enumerate(rows[1:], start=2):
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

MAX_FLOOD_WAIT = 300  # если Telegram просит ждать дольше — останавливаемся

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
        if wait > MAX_FLOOD_WAIT:
            print(f'  [!] FloodWait {wait}s > {MAX_FLOOD_WAIT}s — останавливаемся.')
            return f'flood_stop:{wait}'
        print(f'  [!] FloodWait — жду {wait}s...')
        waited = 0
        while waited < wait:
            chunk = min(30, wait - waited)
            await asyncio.sleep(chunk)
            waited += chunk
            print(f'  [!] FloodWait — прошло {waited}s из {wait}s...')
        return await join(client, link)
    except Exception as e:
        return f'error: {e}'


# === MAIN ===

async def main():
    # Читаем SESSION_STRING из переменной окружения (GitHub Secret)
    session_string = os.environ.get('TG_SESSION', '')
    if not session_string:
        raise RuntimeError(
            'Переменная TG_SESSION не задана. '
            'Сгенерируй её локально и добавь в GitHub Secrets.'
        )

    config, ss = load_config()

    api_id   = int(config['api_id'])
    api_hash = config['api_hash']
    delay    = int(config.get('delay_sec', 20))
    skip     = config.get('skip_already_joined', 'TRUE').upper() == 'TRUE'

    groups_sheet, links = load_groups(ss, skip_done=skip)
    print(f'Ссылок к обработке: {len(links)}')

    async with TelegramClient(StringSession(session_string), api_id, api_hash) as client:
        for idx, (row_i, link) in enumerate(links, 1):
            print(f'[{idx}/{len(links)}] {link}')
            result = await join(client, link)

            if result == 'ok':
                status = '✅ Вступил'
            elif result == 'already':
                status = '⏭ Уже участник'
            elif result.startswith('flood_stop:'):
                wait = result.split(':')[1]
                print(f'\n⛔ Остановлено по FloodWait ({wait}s). Запусти снова через ~{int(wait)//60} мин.')
                update_status(groups_sheet, row_i, f'⏳ FloodWait {wait}s')
                break
            else:
                status = f'❌ {result}'

            print(f'  → {status}')
            update_status(groups_sheet, row_i, status)

            if idx < len(links):
                await asyncio.sleep(delay)

    print('\nГотово!')


if __name__ == '__main__':
    asyncio.run(main())
