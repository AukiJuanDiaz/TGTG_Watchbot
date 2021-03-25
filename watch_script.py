from tgtg import TgtgClient
from json import load, dump
import requests

# Load tgtg account credentials from a hidden file
f = open('telegram.json',)
telegram = load(f)
f.close()


def telegram_bot_sendtext(bot_message):

    bot_token = telegram["bot_token"]
    bot_chatID = telegram["bot_chatID"]
    send_text = 'https://api.telegram.org/bot' + bot_token + '/sendMessage?chat_id=' + bot_chatID + '&parse_mode=Markdown&text=' + bot_message

    response = requests.get(send_text)

    return response.json()

# Load tgtg account credentials from a hidden file
f = open('credentials.json',)
credentials = load(f)
f.close()

# Create the client
client = TgtgClient(email=credentials['email'], password=credentials['password'])

# Get all favorite items
check_result = client.get_items()
print(len(check_result))

message = f"You have {len(check_result)} favorites"
telegram_bot_sendtext(message)
