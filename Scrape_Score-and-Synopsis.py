import time
import traceback
import requests
import os
import re
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from html import unescape

class MALService:
    def __init__(self, clientId, proxy_url=None, min_request_interval=3.0):
        self.clientId = clientId
        self.apiBaseUrl = 'https://api.myanimelist.net/v2'
        self.error_count = 0
        self.min_request_interval = min_request_interval
        self.last_request_at = 0.0
        self.last_retry_triggered = False

        self.session = requests.Session()
        self.session.headers.update({
            'X-MAL-CLIENT-ID': self.clientId,
            'Origin': 'window.location.href'
        })

        retry = Retry(
            total=5,
            connect=5,
            read=5,
            status=5,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST"],
            respect_retry_after_header=True,
        )
        adapter = HTTPAdapter(max_retries=retry)
        self.session.mount('http://', adapter)
        self.session.mount('https://', adapter)

        if proxy_url:
            self.session.proxies.update({
                "http": proxy_url,
                "https": proxy_url,
            })

    def _throttled_get(self, url, params=None):
        elapsed = time.monotonic() - self.last_request_at
        if elapsed < self.min_request_interval:
            time.sleep(self.min_request_interval - elapsed)
        response = self.session.get(url, params=params, timeout=45)
        self.last_request_at = time.monotonic()
        self.last_retry_triggered = response.status_code in [429, 500, 502, 503, 504]
        return response

    def get_user_list(self, username, type):
        try:
            url = f'{self.apiBaseUrl}/users/{username}/{type}list?limit=1000'

            all_anime = []
            while True:
                response = self._throttled_get(url)
                if response.status_code != 200:
                    print(f"An error occurred: {response.status_code} {response.text}\nYou might be rate limited.")
                    response.raise_for_status()
                response_json = response.json()
                all_anime.extend(response_json['data'])

                next_url = response_json.get('paging', {}).get('next')
                if next_url:
                    url = next_url
                else:
                    break

            return all_anime
        
        except Exception as e:
            print(f"An error occurred: {e}")
            traceback.print_exc()
            return None

    def get_entry_details(self, entry_id, fields, type):
        try:
            url = f'{self.apiBaseUrl}/{type}/{entry_id}'
            params = { 
                'fields': fields
            }
            response = self._throttled_get(url, params=params)

            if response.status_code == 200:
                return response.json()
            else:
                response.raise_for_status()
        except Exception as e:
            print(f"[get details] An error occurred: {e}")
            self.error_count += 1
            traceback.print_exc()
            return None

    def get_entry_info(self, entry_id, type):
        try:
            t = 65 if type == 'manga' else 64   # 65 for manga, 64 for anime
            url = f'https://myanimelist.net/includes/ajax.inc.php?t={t}&id={entry_id}'
            html = self._throttled_get(url).text
            # find every `<span class="dark_text">Label:</span> value`
            data = { lbl.lower().strip(':') : unescape(val.strip())
                    for lbl, val in re.findall(r'<span class="dark_text">(.*?):</span>\s*([^<]+)', html) }
            return data
        except Exception as e:
            print(f"[get info] An error occurred: {e}")
            self.error_count += 1
            traceback.print_exc()
            return None

def generate_template(entry, info, type):
    try:
        template = f'/* {entry.get("title", "N/A")} */ '
        # Replace newline characters with '\a' and escape double quotes.
        synopsis = entry.get("synopsis", "N/A").replace('\n', '\\a ').replace('"', '\\"')
        
        mean = entry.get("mean", "N/A")
        if mean != "N/A":
            mean = f"{float(mean):.2f}"
        rank = entry.get("rank", "N/A")
        popularity = entry.get("popularity", "N/A")
        alt_title = entry.get("alternative_titles", {}).get("en", "N/A")
        genres = info.get("genres", "N/A")

        template += f'.list-table .list-table-data .data.title:hover ' \
                    f'.link[href^="/{type}/{entry["id"]}/"]::before ' \
                    f'{{ content: "Rank : {rank}   |   ' \
                    f'Popularity : {popularity}   |   ' \
                    f'Alt. Title : {alt_title} \\a ' \
                    f'Genres : {genres} \\a \\a ' \
                    f'{synopsis}"; '

        main_picture = entry.get("main_picture", {}).get("medium", "")
        template += f'background-image: url({main_picture}); ' \
                    f'background-size: cover; ' \
                    f'background-blend-mode: overlay; ' \
                    f'background-position: center center; }}'

        return template
    except Exception as e:
        print(f"An error occurred: {e}")
        traceback.print_exc()
        return None

def discord_notify(content, error=False):
    discord_id = "1022735992014254183"
    discord_webhook = os.getenv("DISCORD_WEBHOOK")
    if not discord_webhook:
        print("DISCORD_WEBHOOK is not set. Unable to send Discord notification.")
        return
    
    if error:
        content = f"<@{discord_id}> {content}\nCheck https://github.com/jeryjs/Hosting/actions/workflows/actions.yml for more details."

    payload = {
        'username': 'MAL List Scraper',
        'avatar_url': 'https://i.imgur.com/TCNOflM.jpg',
        'content': content,
    }
    
    headers = {
        "Content-Type": "application/json"
    }
    
    response = requests.post(discord_webhook, json=payload, headers=headers)
    
    if response.status_code == 204:
        print("Successfully notified via Discord.")
    else:
        print(f"Failed to notify via Discord. Status code: {response.status_code}")


def load_cache(type):
    path = f'.cache/{type}-Score-and-Synopsis.cache.json'
    if not os.path.exists(path):
        return {'entries': {}, 'updated_at': 0}, path
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f), path


def save_cache(cache, path):
    os.makedirs('.cache', exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(cache, f, ensure_ascii=False)


def should_refresh_info(cache_entry, now_ts, info_refresh_seconds, entry_id):
    info = cache_entry.get('info')
    if not info:
        return True
    last_info_fetch = cache_entry.get('last_info_fetch', 0)
    stagger_seconds = (int(entry_id) % 7) * 86400
    return (now_ts - last_info_fetch) >= (info_refresh_seconds + stagger_seconds)


def process_chunk(service, chunk, type, params, cache_entries, now_ts, info_refresh_seconds, worker_id):
    lines = []
    updates = {}
    stats = {
        'details_calls': 0,
        'info_calls': 0,
    }

    for index, node in chunk:
        entry_id = node['id']
        entry_key = str(entry_id)
        title = node["title"]
        
        cache_entry = cache_entries.get(entry_key, {})
        is_new = not cache_entry
        
        details = service.get_entry_details(entry_id, params, type)
        stats['details_calls'] += 1
        details_changed = details and details != cache_entry.get('details')
        details_retry = service.last_retry_triggered
        if details is None:
            details = cache_entry.get('details')

        info = cache_entry.get('info', {})
        refresh_info = should_refresh_info(cache_entry, now_ts, info_refresh_seconds, entry_id)
        info_changed = False
        info_retry = False
        if refresh_info:
            fetched_info = service.get_entry_info(entry_id, type)
            stats['info_calls'] += 1
            info_retry = service.last_retry_triggered
            if fetched_info is not None:
                info_changed = fetched_info != cache_entry.get('info')
                info = fetched_info

        if details is None:
            continue

        line = generate_template(details, info or {}, type)
        if line is None:
            continue

        change_flags = []
        if is_new:
            change_flags.append('new')
        if details_changed:
            change_flags.append('details')
        if info_changed:
            change_flags.append('info')
        change_str = ','.join(change_flags) if change_flags else 'unchanged'
        
        retry_notes = []
        if details_retry:
            retry_notes.append('d-retry')
        if info_retry:
            retry_notes.append('i-retry')
        retry_str = f" [{','.join(retry_notes)}]" if retry_notes else ""
        
        print(f'w{worker_id+1}-{index+1}] id:{entry_id} -> {title} -> {change_str}{retry_str}')
        
        lines.append((index, line))

        updates[entry_key] = {
            'details': details,
            'info': info or {},
            'last_details_fetch': now_ts,
            'last_info_fetch': now_ts if refresh_info else cache_entry.get('last_info_fetch', now_ts),
        }

    return lines, updates, stats


def build_proxy_urls():
    host = os.getenv('OXYLABS_PROXY_HOST', 'dc.oxylabs.io')
    ports = [p.strip() for p in os.getenv('OXYLABS_PROXY_PORTS', '').split(',') if p.strip()]
    user = os.getenv('OXYLABS_PROXY_USER')
    password = os.getenv('OXYLABS_PROXY_PASS')

    if not ports or not user or not password:
        return []

    return [f'http://{user}:{password}@{host}:{port}' for port in ports]


def main():
    # load .env file into environment variables if it exists
    if os.path.exists('.env'):
        with open('.env', 'r') as f:
            for line in f:
                if line.strip() and not line.startswith('#'):
                    key, value = line.strip().split('=', 1)
                    os.environ[key] = value

    clientId = os.getenv("MAL_APP_CLIENTID")
    if not clientId:
        raise RuntimeError('MAL_APP_CLIENTID is required')

    username = 'jery_js'
    types = ['anime', 'manga']
    params = "id, title, synopsis, alternative_titles, mean, rank, popularity, main_picture"

    request_interval = float(os.getenv('MAL_REQUEST_INTERVAL_SECONDS', '1.5'))
    info_refresh_days = int(os.getenv('MAL_INFO_REFRESH_DAYS', '28'))
    info_refresh_seconds = info_refresh_days * 86400
    max_workers = int(os.getenv('MAL_MAX_WORKERS', '5'))

    proxy_urls = build_proxy_urls()
    if proxy_urls:
        worker_proxy_urls = proxy_urls[:max_workers]
    else:
        worker_proxy_urls = [None]

    workers = [
        MALService(clientId, proxy_url=proxy_url, min_request_interval=request_interval)
        for proxy_url in worker_proxy_urls
    ]

    list_service = workers[0]
    discord_response = ""
    start_time = time.time()
    now_ts = int(time.time())

    for type in types:
        list_data = list_service.get_user_list(username, type)
        if list_data is None:
            raise RuntimeError(f'Unable to fetch {type} list for {username}')

        cache, cache_path = load_cache(type)
        cache_entries = cache.get('entries', {})

        current_ids = {str(x['node']['id']) for x in list_data}
        cache_entries = {k: v for k, v in cache_entries.items() if k in current_ids}

        chunks = [[] for _ in workers]
        for index, entry in enumerate(list_data):
            chunks[index % len(workers)].append((index, entry['node']))

        print(f'Generating {type.capitalize()}-Score-and-Synopsis.css...')
        lines = []
        aggregated_stats = {
            'details_calls': 0,
            'info_calls': 0,
        }

        with ThreadPoolExecutor(max_workers=len(workers)) as executor:
            futures = [
                executor.submit(
                    process_chunk,
                    workers[i],
                    chunks[i],
                    type,
                    params,
                    cache_entries,
                    now_ts,
                    info_refresh_seconds,
                    i,
                )
                for i in range(len(workers))
                if chunks[i]
            ]

            for future in as_completed(futures):
                worker_lines, worker_updates, worker_stats = future.result()
                lines.extend(worker_lines)
                cache_entries.update(worker_updates)
                aggregated_stats['details_calls'] += worker_stats['details_calls']
                aggregated_stats['info_calls'] += worker_stats['info_calls']

        template_lines = [
            "/*List generated by MAL List Scraper (https://github.com/jeryjs/Hosting/blob/main/Scrape_Score-and-Synopsis.py)*/",
            ""
        ]
        for _, line in sorted(lines, key=lambda x: x[0]):
            template_lines.append(line)
        template = '\n'.join(template_lines) + '\n'

        with open(f'{type.capitalize()}-Score-and-Synopsis.css', 'w', encoding='utf-8') as f:
            f.write(template)

        cache['entries'] = cache_entries
        cache['updated_at'] = now_ts
        save_cache(cache, cache_path)
        
        discord_response += f'`{type.capitalize()}-Score-and-Synopsis.css` was updated. '
        discord_response += (
            f'[*{aggregated_stats["details_calls"]} detail calls, '
            f'{aggregated_stats["info_calls"]} info-scrape calls*]\n'
        )
        
    elapsed_time = time.time() - start_time
    minutes = int(elapsed_time / 60)
    seconds = int(elapsed_time % 60)
    discord_response += f'> Time taken: {minutes} minutes and {seconds} seconds\n'
    discord_response += f'> Errors Counted: {sum(x.error_count for x in workers)}'

    discord_notify(discord_response)


if __name__ == "__main__":
    try: 
        main()
    except Exception as e:
        discord_notify("MAL List Scraper ran into an error.", True)
        traceback.print_exc()
