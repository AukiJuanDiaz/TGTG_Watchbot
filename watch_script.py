from tgtg import TgtgClient
from json import load, dump
import requests
import schedule
import time
import os

# For remote deployment, the credentials are stored as environment variables in Heroku
# Try to load the credentials remotely first. If this false, look for a local file
# Try to first load credentials from environment
credentials_remote_loaded = False

try:
    # Credential handling heroku
    credentials = dict()
    credentials['email'] = os.environ['TGTG_EMAIL']
    print(f"tgtg_email: {credentials['email']}")
    credentials['password'] = os.environ['TGTG_PW']
    print(f"tgtg_pw: {credentials['password']}")

    telegram = dict()
    telegram['bot_chatID1'] = os.environ['TELEGRAM_BOT_CHATID1']
    print(f"TELEGRAM_BOT_CHATID1: {telegram['bot_chatID1']}")
    telegram['bot_chatID2'] = os.environ['TELEGRAM_BOT_CHATID2']
    print(f"TELEGRAM_BOT_CHATID2: {telegram['bot_chatID2']}")
    telegram['bot_token'] = os.environ['TELEGRAM_BOT_TOKEN']
    print(f"TELEGRAM_BOT_TOKEN: {telegram['bot_token']}")

    credentials_remote_loaded = True
except:
    print("No credentials found in Heroku environment")

if credentials_remote_loaded == False:
    try:
        # Credential handling local version
        # Load tgtg account credentials from a hidden file
        f = open('telegram.json',)
        telegram = load(f)
        f.close()

        # Load tgtg account credentials from a hidden file
        f = open('credentials.json',)
        credentials = load(f)
        f.close()
    except:
        print("No files found for local credentials.")

# Create the tgtg client with my credentials
client = TgtgClient(email=credentials['email'], password=credentials['password'])

# Init the favourites in stock list as a global variable
favourites_in_stock = list()


def telegram_bot_sendtext(bot_message, only_to_admin=False):
    """
    Helper function: Send a message with the specified telegram bot.
    It can be specified if both users or only the admin receives the message
    Follow this article to figure out a specific chatID: https://medium.com/@ManHay_Hong/how-to-create-a-telegram-bot-and-send-messages-with-python-4cf314d9fa3e
    """

    if only_to_admin:
        # ChadID1 is the admin
        chatIDlist = [telegram["bot_chatID1"]]
    else:
        chatIDlist = [telegram["bot_chatID1"], telegram["bot_chatID2"]]

    for id in chatIDlist:
        bot_token = telegram["bot_token"]
        send_text = 'https://api.telegram.org/bot' + bot_token + '/sendMessage?chat_id=' + id + '&parse_mode=Markdown&text=' + bot_message
        response = requests.get(send_text)

    return response.json()

def telegram_bot_sendimage(image_url, image_caption=None):
    """
    For sending an image in Telegram, that can also be accompanied by an image caption
    """
    # Send the message to both users
    chatIDlist = [telegram["bot_chatID1"], telegram["bot_chatID2"]]
    for id in chatIDlist:
        bot_token = telegram["bot_token"]
        # Prepare the url for an telegram API call to send a photo
        send_text = 'https://api.telegram.org/bot' + bot_token + '/sendPhoto?chat_id=' + id + '&photo=' + image_url

        # If the argument gets passed, at a caption to the image
        if image_caption != None:
            send_text += '&caption=' + image_caption
        response = requests.get(send_text)

    return response.json()

def fetch_stock_from_api(api_result):
    """
    For fideling out the few important information out of the api response
    """
    new_api_result = list()
    # Go through all favorites linked to the account,that are returned with the api
    for i in range(len(api_result)):
        current_fav = dict()
        current_fav['item_id'] = api_result[i]['item']['item_id']
        current_fav['store_name'] = api_result[i]['store']['store_name']
        current_fav['items_available'] = api_result[i]['items_available']
        current_fav['category_picture'] = api_result[i]['store']['cover_picture']['current_url']
        new_api_result.append(current_fav)

    return new_api_result

def routine_check():
    """
    Function that gets called via schedule every 3 minutes.
    Retrieves the data from TGTG API and selects the message to send.
    """

    # Get the global variable of items in stock
    global favourites_in_stock

    # Get all favorite items
    api_response = client.get_items()
    new_api_result = fetch_stock_from_api(api_response)

    # Go through all favourite items and compare the stock
    list_of_item_ids = [fav['item_id'] for fav in new_api_result]
    for item_id in list_of_item_ids:
        try:
            old_stock = [item['items_available'] for item in favourites_in_stock if item['item_id'] == item_id][0]
        except:
            old_stock = 0
            print("An exception occurred: The item_id was not known as a favorite before")

        new_stock = [item['items_available'] for item in new_api_result if item['item_id'] == item_id][0]

        # Check, if the stock has changed. Send a message if so.
        if new_stock != old_stock:
            # Check if the stock was replenished, send an encouraging image message
            if old_stock == 0 and new_stock > 0:
                message = f"There are {new_stock} new goodie bags at {[item['store_name'] for item in new_api_result if item['item_id'] == item_id][0]}"
                image = [item['category_picture'] for item in new_api_result if item['item_id'] == item_id][0]
                telegram_bot_sendimage(image, message)
            elif old_stock > new_stock and new_stock != 0:
                # customer feedback: This message is not needed
                pass
                ## Prepare a generic string, but with the important info
                # message = f" 📉 Decrease from {old_stock} to {new_stock} available goodie bags at {[item['store_name'] for item in new_api_result if item['item_id'] == item_id][0]}."
                # telegram_bot_sendtext(message)
            elif old_stock > new_stock and new_stock == 0:
                message = f" ⭕ Sold out! There are no more goodie bags available at {[item['store_name'] for item in new_api_result if item['item_id'] == item_id][0]}."
                telegram_bot_sendtext(message)
            else:
                # Prepare a generic string, but with the important info
                message = f"There was a change of number of goodie bags in stock from {old_stock} to {new_stock} at {[item['store_name'] for item in new_api_result if item['item_id'] == item_id][0] }."
                telegram_bot_sendtext(message)

    # Reset the global information with the newest fetch
    favourites_in_stock = new_api_result

    # Print out some maintenance info in the terminal
    print(f"API run at {time.ctime(time.time())} successful. Current stock:")
    for item_id in list_of_item_ids:
        print(f"{[item['store_name'] for item in new_api_result if item['item_id'] == item_id][0]}:\
         {[item['items_available'] for item in new_api_result if item['item_id'] == item_id][0]}")

def still_alive():
    """
    This function gets called every 24 hours and sends a 'still alive' message to the admin.
    """
    message = f"Current time: {time.ctime(time.time())}. The bot is still running. "

    global favourites_in_stock

    list_of_item_ids = [fav['item_id'] for fav in favourites_in_stock]
    for item_id in list_of_item_ids:
        message += (f"{[item['store_name'] for item in favourites_in_stock if item['item_id'] == item_id][0]}: {[item['items_available'] for item in favourites_in_stock if item['item_id'] == item_id][0]} items available")

    telegram_bot_sendtext(message, only_to_admin = True)

# Use schedule to set up a recurrent checking
schedule.every(3).minutes.do(routine_check)
schedule.every(24).hours.do(still_alive)

# Description of the sercive, that gets send once
telegram_bot_sendtext("The bot script has started successfully. The bot checks every 3 minutes, if there is something new at TooGoodToGo. Every 24 hours, the bots sends a 'still alive'-message.", only_to_admin=True)

while True:
    # run_pending
    schedule.run_pending()
    time.sleep(1)
