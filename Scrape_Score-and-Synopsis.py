import requests

class MALService:
    def __init__(self, clientId):
        self.clientId = clientId
        self.proxyUrl = 'https://corsproxy.io/?'
        self.apiBaseUrl = 'https://api.myanimelist.net/v2'

    def get_user_list(self, username, type):
        url = f'{self.apiBaseUrl}/users/{username}/{type}list?limit=1000'
        headers = {
            'X-MAL-CLIENT-ID': self.clientId,
            'Origin': 'window.location.href'
        }

        all_anime = []
        while True:
            response = requests.get(url, headers=headers)
            # with open(f'./response[{i}].json', 'w') as f: f.write(response.text)
            response_json = response.json()
            all_anime.extend(response_json['data'])

            if 'next' in response_json['paging']:
                url = response_json['paging']['next']
            else:
                break

        return all_anime

    def get_entry_details(self, entry_id, fields, type):
        url = f'{self.apiBaseUrl}/{type}/{entry_id}'
        params = { 
            'fields': fields
        }
        headers = {
            'X-MAL-CLIENT-ID': self.clientId,
            'Origin': 'window.location.href'
        }
        response = requests.get(url, params=params, headers=headers)
        return response.json()
    
def generate_template(entry, type):
    template = f'/* {entry["title"]} */ '
    # Replace newline characters with '\a' and escape double quotes.
    synopsis = entry["synopsis"].replace('\n', '\\a ').replace('"', '\\"')
    if 'mean' in entry:
        template += f'.list-table td.data.image > a[href^="/{type}/{entry["id"]}/"]::after ' \
                    f'{{ content: "{entry["mean"]}"; visibility: visible !important; }} '
    else:
        template += f'.list-table td.data.image > a[href^="/{type}/{entry["id"]}/"]::after ' \
                    f'{{ content: "N/A"; visibility: visible !important; }} '

    template += f'.list-table .list-table-data .data.title:hover ' \
                f'.link[href^="/{type}/{entry["id"]}/"]::before ' \
                f'{{ content: "Rank : {entry["rank"]}   |   ' \
                f'Popularity : {entry["popularity"]}   |   ' \
                f'Alt. Title : {entry["alternative_titles"]["en"]} \\a \\a ' \
                f'{synopsis}"; '

    template += f'background-image: url({entry["main_picture"]["medium"]}); ' \
                f'background-size: cover; ' \
                f'background-blend-mode: overlay; }}'

    return template

def discord_notify(content):
    discord_id = "1022735992014254183"
    discord_webhook = "https://ptb.discord.com/api/webhooks/1031955469998243962/UO379MCHeXTXwk9s86qeZedKKNOa5aDVMHInqGea_dUEOzfPZf66i00CPbGOA0lOkIxp"
    
    payload = {
        'username': 'MAL List Scraper',
        'avatar_url': 'https://i.imgur.com/TCNOflM.jpg',
        'content': f'<@{discord_id}> {content}',
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

    for type in types:
        list = mal_service.get_user_list(username, type)
        template = ""

        for i, entry in enumerate(list):
            entry = entry['node']
            params = "id, title, synopsis, alternative_titles, mean, rank, popularity"
            
            print(f'{i}] id:{entry["id"]} {entry["title"]}')

            details = mal_service.get_entry_details(entry['id'], params, type)

            template += generate_template(details, type) + '\n'

        with open(f'{type.capitalize()}-Score-and-Synopsis.css', 'w', encoding='utf-8') as f:
            f.write(template)
        
        discord_response += f'{type.capitalize()}-Score-and-Synopsis.css was updated.\n'

    discord_notify(discord_response)


if __name__ == "__main__":
    try: 
        main()
    except Exception as e:
        discord_notify("MAL List Scraper ran into an error.\nCheck https://github.com/jeryjs/Hosting/actions for more details.")
        e.with_traceback()