import time
import traceback
import requests

class MALService:
    def __init__(self, clientId):
        self.clientId = clientId
        self.proxyUrl = 'https://corsproxy.io/?'
        self.apiBaseUrl = 'https://api.myanimelist.net/v2'

    def get_user_list(self, username, type):
        try:
            url = f'{self.apiBaseUrl}/users/{username}/{type}list?limit=1000'
            headers = {
                'X-MAL-CLIENT-ID': self.clientId,
                'Origin': 'window.location.href'
            }

            all_anime = []
            while True:
                response = requests.get(url, headers=headers)
                # with open(f'./response.json', 'w') as f: f.write(response.text)
                if response.status_code != 200:
                    print(f"An error occurred: {response.status_code} {response.text}\nYou might be rate limited.")
                    response.raise_for_status()
                response_json = response.json()
                all_anime.extend(response_json['data'])

                if 'next' in response_json['paging']:
                    url = response_json['paging']['next']
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
            headers = {
                'X-MAL-CLIENT-ID': self.clientId,
                'Origin': 'window.location.href'
            }
            response = requests.get(url, params=params, headers=headers)

            if response.status_code == 200:
                return response.json()
            else:
                response.raise_for_status()
        except Exception as e:
            print(f"An error occurred: {e}")
            traceback.print_exc()
            return None
    
def generate_template(entry, type):
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

        template += f'.list-table td.data.image > a[href^="/{type}/{entry["id"]}/"]::after ' \
                    f'{{ content: "{mean}"; visibility: visible !important; }} '

        template += f'.list-table .list-table-data .data.title:hover ' \
                    f'.link[href^="/{type}/{entry["id"]}/"]::before ' \
                    f'{{ content: "Rank : {rank}   |   ' \
                    f'Popularity : {popularity}   |   ' \
                    f'Alt. Title : {alt_title} \\a \\a ' \
                    f'{synopsis}"; '

        template += f'background-image: url({entry["main_picture"]["medium"]}); ' \
                    f'background-size: cover; ' \
                    f'background-blend-mode: overlay; }}'

        return template
    except Exception as e:
        print(f"An error occurred: {e}")
        traceback.print_exc()
        return None

def discord_notify(content, error=False):
    discord_id = "1022735992014254183"
    discord_webhook = "https://ptb.discord.com/api/webhooks/1031955469998243962/UO379MCHeXTXwk9s86qeZedKKNOa5aDVMHInqGea_dUEOzfPZf66i00CPbGOA0lOkIxp"
    
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


def main():
    clientId = 'cfdd50f8037e9e8cf489992df497c761'
    username = 'jery_js'
    types = ['anime', 'manga']

    mal_service = MALService(clientId)
    discord_response = ""
    start_time = time.time()

    for type in types:
        list = mal_service.get_user_list(username, type)
        template = "/*List generated by MAL List Scraper (https://github.com/jeryjs/Hosting/blob/main/Scrape_Score-and-Synopsis.py)*/\n\n"

        print(f'Generating {type.capitalize()}-Score-and-Synopsis.css...')
        for i, entry in enumerate(list):
            entry = entry['node']
            params = "id, title, synopsis, alternative_titles, mean, rank, popularity"
            
            print(f'{i+1}] id:{entry["id"]} {entry["title"]}')

            details = mal_service.get_entry_details(entry['id'], params, type)

            if details is not None:
                template += generate_template(details, type) + '\n'

            time.sleep(0.5)   # Rate limiting requests to every 500ms

        with open(f'{type.capitalize()}-Score-and-Synopsis.css', 'w', encoding='utf-8') as f:
            f.write(template)
        
        discord_response += f'`{type.capitalize()}-Score-and-Synopsis.css` was updated.\n'

    discord_response += f'Time taken: {time.time() - start_time:.2f} seconds.'

    discord_notify(discord_response)


if __name__ == "__main__":
    try: 
        main()
    except Exception as e:
        discord_notify("MAL List Scraper ran into an error.", True)
        traceback.print_exc()
