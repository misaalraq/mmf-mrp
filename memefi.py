import aiohttp
import asyncio
import json
import os
import pytz
import random
import string
import time
from datetime import datetime
from urllib.parse import unquote
from utils.headers import headers_set
from utils.queries import QUERY_USER, QUERY_LOGIN, MUTATION_GAME_PROCESS_TAPS_BATCH, QUERY_BOOSTER, QUERY_NEXT_BOSS
from utils.queries import QUERY_TASK_VERIF, QUERY_TASK_COMPLETED, QUERY_GET_TASK, QUERY_TASK_ID, QUERY_GAME_CONFIG

url = "https://api-gw-tg.memefi.club/graphql"

# URLs to fetch proxies
proxy_urls = [
    'https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt',
    'https://raw.githubusercontent.com/monosans/proxy-list/main/proxies_anonymous/http.txt',
    'https://raw.githubusercontent.com/Vann-Dev/proxy-list/main/proxies/http.txt',
    'https://raw.githubusercontent.com/elliottophellia/yakumo/master/results/http/global/http_checked.txt'
]

# Function to fetch proxies from the provided URLs
async def fetch_proxies():
    proxies = []
    async with aiohttp.ClientSession() as session:
        for proxy_url in proxy_urls:
            async with session.get(proxy_url) as response:
                if response.status == 200:
                    proxy_list = await response.text()
                    proxies.extend(proxy_list.splitlines())
    return proxies

# Function to get a random proxy
def get_random_proxy(proxies):
    return random.choice(proxies) if proxies else None

# Handle errors in a safe way
async def safe_post(session, url, headers, json_payload, proxy=None):
    retries = 5
    for attempt in range(retries):
        async with session.post(url, headers=headers, json=json_payload, proxy=proxy) as response:
            if response.status == 200:
                return await response.json()  # Return the JSON response if successful
            else:
                print(f"❌ Gagal dengan status {response.status}, mencoba lagi ")
                if attempt < retries - 1:  # Jika ini bukan percobaan terakhir, tunggu sebelum mencoba lagi
                    await asyncio.sleep(10)
                else:
                    print("❌ Gagal setelah beberapa percobaan. Memulai ulang...")
                    return None
    return None

def generate_random_nonce(length=52):
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for _ in range(length))

# Mendapatkan akses token
async def fetch(account_line, proxies):
    with open('query_id.txt', 'r') as file:
        lines = file.readlines()
        raw_data = lines[account_line - 1].strip()

    tg_web_data = unquote(unquote(raw_data))
    query_id = tg_web_data.split('query_id=', maxsplit=1)[1].split('&user', maxsplit=1)[0]
    user_data = tg_web_data.split('user=', maxsplit=1)[1].split('&auth_date', maxsplit=1)[0]
    auth_date = tg_web_data.split('auth_date=', maxsplit=1)[1].split('&hash', maxsplit=1)[0]
    hash_ = tg_web_data.split('hash=', maxsplit=1)[1].split('&', maxsplit=1)[0]

    user_data_dict = json.loads(unquote(user_data))

    headers = headers_set.copy()  # Membuat salinan headers_set agar tidak mengubah variabel global
    data = {
        "operationName": "MutationTelegramUserLogin",
        "variables": {
            "webAppData": {
                "auth_date": int(auth_date),
                "hash": hash_,
                "query_id": query_id,
                "checkDataString": f"auth_date={auth_date}\nquery_id={query_id}\nuser={unquote(user_data)}",
                "user": {
                    "id": user_data_dict["id"],
                    "allows_write_to_pm": user_data_dict["allows_write_to_pm"],
                    "first_name": user_data_dict["first_name"],
                    "last_name": user_data_dict["last_name"],
                    "username": user_data_dict.get("username", "Username gak diset"),
                    "language_code": user_data_dict["language_code"],
                    "version": "7.2",
                    "platform": "ios"
                }
            }
        },
        "query": QUERY_LOGIN
    }

    async with aiohttp.ClientSession() as session:
        proxy = get_random_proxy(proxies)
        async with session.post(url, headers=headers, json=data, proxy=proxy) as response:
            try:
                json_response = await response.json()
                if 'errors' in json_response:
                    return None
                else:
                    access_token = json_response['data']['telegramUserLogin']['access_token']
                    return access_token
            except aiohttp.ContentTypeError:
                print("Failed to decode JSON response")
                return None

# Cek akses token
async def cek_user(index, proxies):
    access_token = await fetch(index + 1, proxies)
    if access_token is None:
        return None

    headers = headers_set.copy()  # Membuat salinan headers_set agar tidak mengubah variabel global
    headers['Authorization'] = f'Bearer {access_token}'

    json_payload = {
        "operationName": "QueryTelegramUserMe",
        "variables": {},
        "query": QUERY_USER
    }

    async with aiohttp.ClientSession() as session:
        proxy = get_random_proxy(proxies)
        async with session.post(url, headers=headers, json=json_payload, proxy=proxy) as response:
            if response.status == 200:
                response_data = await response.json()
                if 'errors' in response_data:
                    print(f"❌ Gagal Query ID Salah")
                    return None
                else:
                    user_data = response_data['data']['telegramUserMe']
                    return user_data
            else:
                print(response)
                print(f"❌ Gagal dengan status {response.status}, mencoba lagi...")
                return None

async def activate_energy_recharge_booster(index, headers, proxies):
    access_token = await fetch(index + 1, proxies)
    if access_token is None:
        return None

    headers['Authorization'] = f'Bearer {access_token}'

    recharge_booster_payload = {
        "operationName": "telegramGameActivateBooster",
        "variables": {"boosterType": "Recharge"},
        "query": QUERY_BOOSTER
    }

    async with aiohttp.ClientSession() as session:
        proxy = get_random_proxy(proxies)
        async with session.post(url, headers=headers, json=recharge_booster_payload, proxy=proxy) as response:
            if response.status == 200:
                response_data = await response.json()
                if response_data and 'data' in response_data and response_data['data'] and 'telegramGameActivateBooster' in response_data['data']:
                    new_energy = response_data['data']['telegramGameActivateBooster']['currentEnergy']
                    print(f"\n🔋 Energi terisi. Energi saat ini: {new_energy}")
                else:
                    print("❌ Gagal mengaktifkan Recharge Booster: Data tidak lengkap atau tidak ada.")
            else:
                print(f"❌ Gagal dengan status {response.status}, mencoba lagi..." + response)
                return None

async def submit_taps(index, json_payload, proxies):
    access_token = await fetch(index + 1, proxies)
    if access_token is None:
        return None

    headers = headers_set.copy()
    headers['Authorization'] = f'Bearer {access_token}'

    async with aiohttp.ClientSession() as session:
        proxy = get_random_proxy(proxies)
        async with session.post(url, headers=headers, json=json_payload, proxy=proxy) as response:
            if response.status == 200:
                response_data = await response.json()
                return response_data
            else:
                print(f"❌ Gagal dengan status {response}, mencoba lagi...")
                return None

async def set_next_boss(index, headers, proxies):
    access_token = await fetch(index + 1, proxies)
    if access_token is None:
        return None

    headers['Authorization'] = f'Bearer {access_token}'

    boss_payload = {
        "operationName": "telegramGameSetNextBoss",
        "variables": {},
        "query": QUERY_NEXT_BOSS
    }

    async with aiohttp.ClientSession() as session:
        proxy = get_random_proxy(proxies)
        async with session.post(url, headers=headers, json=boss_payload, proxy=proxy) as response:
            if response.status == 200:
                print("✅ Berhasil ganti bos.", flush=True)
            else:
                print("❌ Gagal ganti bos.", flush=True)

# cek stat
async def cek_stat(index, headers, proxies):
    access_token = await fetch(index + 1, proxies)
    if access_token is None:
        return None

    headers['Authorization'] = f'Bearer {access_token}'

    json_payload = {
        "operationName": "QUERY_GAME_CONFIG",
        "variables": {},
        "query": QUERY_GAME_CONFIG
    }

    async with aiohttp.ClientSession() as session:
        proxy = get_random_proxy(proxies)
        async with session.post(url, headers=headers, json=json_payload, proxy=proxy) as response:
            if response.status == 200:
                response_data = await response.json()
                if 'errors' in response_data:
                    return None
                else:
                    user_data = response_data['data']['telegramGameGetConfig']
                    return user_data
            else:
                print(f"❌ Gagal dengan status {response.status}, mencoba lagi...")
                return None

async def main():
    while True:
        proxies = await fetch_proxies()
        with open('query_id.txt', 'r') as file:
            lines = file.readlines()

        headers = headers_set.copy()

        for index in range(len(lines)):
            user = await cek_user(index, proxies)
            if user is None:
                print(f"❌ Akun {index + 1} gagal diakses")
                continue

            current_energy = user['game']['currentEnergy']
            max_energy = user['game']['maxEnergy']
            recharge_energy = user['game']['rechargeEnergy']

            print(f"\n🔍 Akun {index + 1} - Energi saat ini: {current_energy}, Energi maksimal: {max_energy}, Energi recharge: {recharge_energy}", flush=True)

            if recharge_energy > 0:
                print("🔋 Recharge Booster aktif, mengisi energi...")
                await activate_energy_recharge_booster(index, headers, proxies)
                await asyncio.sleep(10)  # Tunggu sebentar untuk menghindari masalah rate limit

            taps = [
                {
                    "clientTs": int(time.time() * 1000),
                    "nonce": generate_random_nonce()
                }
                for _ in range(min(current_energy, max_energy))
            ]

            if current_energy > 0:
                json_payload = {
                    "operationName": "MutationTelegramGameProcessTapsBatch",
                    "variables": {"taps": taps},
                    "query": MUTATION_GAME_PROCESS_TAPS_BATCH
                }
                response = await submit_taps(index, json_payload, proxies)
                if response:
                    print("✅ Berhasil menyerang", flush=True)
                else:
                    print("❌ Gagal menyerang", flush=True)

            await set_next_boss(index, headers, proxies)
            await asyncio.sleep(2)  # Tunggu sebentar untuk menghindari masalah rate limit

        print("\n⏳ Menunggu untuk putaran berikutnya...", flush=True)
        await asyncio.sleep(60 * 15)  # Ulangi setiap 15 menit

asyncio.run(main())
