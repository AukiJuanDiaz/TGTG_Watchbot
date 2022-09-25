from tgtg import TgtgClient
from json import load, dump
import requests
import schedule
import time
import os
import traceback
import json
import maya
import datetime
import inspect
import sys
from urllib.parse import quote
import random
import string
import dateutil.parser

try:
    filename = inspect.getframeinfo(inspect.currentframe()).filename
    path = os.path.dirname(os.path.abspath(filename))
    # Load credentials from a file
    f = open(os.path.join(path, 'config.json'), mode='r+')
    config = load(f)
except FileNotFoundError:
    print("No files found for local credentials.")
    exit(1)
except:
    print("Unexpected error")
    print(traceback.format_exc())
    exit(1)

try:
    # Create the tgtg client with my credentials
    tgtg_client = TgtgClient(access_token=config['tgtg']['access_token'], refresh_token=config['tgtg']['refresh_token'], user_id=config['tgtg']['user_id'])
except KeyError:
    # print(f"Failed to obtain TGTG credentials.\nRun \"python3 {sys.argv[0]} <your_email>\" to generate TGTG credentials.")
    # exit(1)
    try:
        email = input("Type your TooGoodToGo email address: ")
        client = TgtgClient(email=email)
        tgtg_creds = client.get_credentials()
        print(tgtg_creds)
        config['tgtg'] = tgtg_creds
        f.seek(0)
        json.dump(config, f, indent = 4)
        f.truncate()
        tgtg_client = TgtgClient(access_token=config['tgtg']['access_token'], refresh_token=config['tgtg']['refresh_token'], user_id=config['tgtg']['user_id'])
    except:
        print(traceback.format_exc())
        exit(1)
except:
    print("Unexpected error")
    print(traceback.format_exc())
    exit(1)
try:
    bot_token = config['telegram']["bot_token"]
    if bot_token == "BOTTOKEN":
        raise KeyError
except KeyError:
    print(f"Failed to obtain Telegram bot token.\n Put it into config.json.")
    exit(1)
except:
    print(traceback.format_exc())
    exit(1)

try:
    bot_chatID = str(config['telegram']["bot_chatID"])
    if bot_chatID == "0":
        # Get chat ID
        pin = ''.join(random.choice(string.digits) for x in range(6))
        print("Please type \"" + pin + "\" to the bot.")
        while bot_chatID == "0":
            response = requests.get('https://api.telegram.org/bot' + bot_token + '/getUpdates?limit=1&offset=-1') 
            # print(response.json())
            if (response.json()['result'][0]['message']['text'] == pin):
                bot_chatID = str(response.json()['result'][0]['message']['chat']['id'])
                print("Your chat id:" + bot_chatID)
                config['telegram']['bot_chatID'] = int(bot_chatID)
                f.seek(0)
                json.dump(config, f, indent = 4)
                f.truncate()
            time.sleep(1)
except KeyError:
    print(f"Failed to obtain Telegram chat ID.")
    exit(1)
except:
    print(traceback.format_exc())
    exit(1)

try:
    f.close()
except:
    print(traceback.format_exc())
    exit(1)

# Init the favourites in stock list as a global variable
tgtg_in_stock = list()
foodsi_in_stock = list()


def telegram_bot_sendtext(bot_message, only_to_admin=True):
    """
    Helper function: Send a message with the specified telegram bot.
    It can be specified if both users or only the admin receives the message
    Follow this article to figure out a specific chatID: https://medium.com/@ManHay_Hong/how-to-create-a-telegram-bot-and-send-messages-with-python-4cf314d9fa3e
    """
    send_text = 'https://api.telegram.org/bot' + bot_token + '/sendMessage?chat_id=' + bot_chatID + '&parse_mode=Markdown&text=' + quote(bot_message)
    response = requests.get(send_text)
    return response.json()

def telegram_bot_sendimage(image_url, image_caption=None):
    """
    For sending an image in Telegram, that can also be accompanied by an image caption
    """
    # Prepare the url for an telegram API call to send a photo
    send_text = 'https://api.telegram.org/bot' + bot_token + '/sendPhoto?chat_id=' + bot_chatID + '&photo=' + image_url
    # If the argument gets passed, at a caption to the image
    if image_caption != None:
        send_text += '&parse_mode=Markdown&caption=' + quote(image_caption)
    response = requests.get(send_text)
    return response.json()

def telegram_bot_delete_message(message_id):
    """
    For deleting a Telegram message
    """
    send_text = 'https://api.telegram.org/bot' + bot_token + '/deleteMessage?chat_id=' + bot_chatID + '&message_id=' + str(message_id)
    response = requests.get(send_text)
    return response.json()

def parse_tgtg_api(api_result):
    """
    For fideling out the few important information out of the api response
    """
    result = list()
    # Go through all stores, that are returned with the api
    for store in api_result:
        current_item = dict()
        current_item['id'] = store['item']['item_id']
        current_item['store_name'] = store['store']['store_name']
        current_item['items_available'] = store['items_available']
        if current_item['items_available'] == 0:
            result.append(current_item)
            continue
        current_item['description'] = store['item']['description']
        current_item['category_picture'] = store['item']['cover_picture']['current_url']
        current_item['price_including_taxes'] = str(store['item']['price_including_taxes']['minor_units'])[:-(store['item']['price_including_taxes']['decimals'])] + "." + str(store['item']['price_including_taxes']['minor_units'])[-(store['item']['price_including_taxes']['decimals']):]+store['item']['price_including_taxes']['code']
        current_item['value_including_taxes'] = str(store['item']['value_including_taxes']['minor_units'])[:-(store['item']['value_including_taxes']['decimals'])] + "." + str(store['item']['value_including_taxes']['minor_units'])[-(store['item']['value_including_taxes']['decimals']):]+store['item']['value_including_taxes']['code']
        try:
            localPickupStart = datetime.datetime.strptime(store['pickup_interval']['start'],'%Y-%m-%dT%H:%M:%S%z').replace(tzinfo=datetime.timezone.utc).astimezone(tz=None)
            localPickupEnd = datetime.datetime.strptime(store['pickup_interval']['end'],'%Y-%m-%dT%H:%M:%S%z').replace(tzinfo=datetime.timezone.utc).astimezone(tz=None)
            current_item['pickup_start'] = maya.parse(localPickupStart).slang_date().capitalize() + " " + localPickupStart.strftime('%H:%M')
            current_item['pickup_end'] = maya.parse(localPickupEnd).slang_date().capitalize() + " " + localPickupEnd.strftime('%H:%M')
        except KeyError:
            current_item['pickup_start'] = None
            current_item['pickup_end'] = None
        try:
            current_item['rating'] = round(store['item']['average_overall_rating']['average_overall_rating'], 2)
        except KeyError:
            current_item['rating'] = None
        result.append(current_item)
    return result

def toogoodtogo():
    """
    Retrieves the data from tgtg API and selects the message to send.
    """

    # Get the global variable of items in stock
    global tgtg_in_stock

    # Get all favorite items
    api_response = tgtg_client.get_items(
        favorites_only=False,
        latitude=config['location']['lat'],
        longitude=config['location']['long'],
        radius=config['location']['range'],
        page_size=300
    )

    parsed_api = parse_tgtg_api(api_response)

    # Go through all favourite items and compare the stock
    for item in parsed_api:
        try:
            old_stock = [stock['items_available'] for stock in tgtg_in_stock if stock['id'] == item['id']][0]
        except IndexError:
            old_stock = 0
        try:
            item['msg_id'] = [stock['msg_id'] for stock in tgtg_in_stock if stock['id'] == item['id']][0]
        except:
            pass

        new_stock = item['items_available']

        # Check, if the stock has changed. Send a message if so.
        if new_stock != old_stock:
            # Check if the stock was replenished, send an encouraging image message
            if old_stock == 0 and new_stock > 0:
                message = f"🍽 There are {new_stock} new goodie bags at [{item['store_name']}](https://share.toogoodtogo.com/item/{item['id']})\n"\
                f"_{item['description']}_\n"\
                f"💰 *{item['price_including_taxes']}*/{item['value_including_taxes']}\n"
                if 'rating' in item:
                    message += f"⭐️ {item['rating']}/5\n"
                if 'pickup_start' and 'pickup_end' in item:
                    message += f"⏰ {item['pickup_start']} - {item['pickup_end']}\n"
                message += "ℹ️ toogoodtogo.com"
                tg = telegram_bot_sendimage(item['category_picture'], message)
                try: 
                    item['msg_id'] = tg['result']['message_id']
                except:
                    print(json.dumps(tg))
                    print(item['image']['url'])
                    print(message)
                    print(traceback.format_exc())
            elif old_stock > new_stock and new_stock != 0:
                # customer feedback: This message is not needed
                pass
                ## Prepare a generic string, but with the important info
                # message = f" 📉 Decrease from {old_stock} to {new_stock} available goodie bags at {[item['store_name'] for item in new_api_result if item['item_id'] == item_id][0]}."
                # telegram_bot_sendtext(message)
            elif old_stock > new_stock and new_stock == 0:
                # message = f" ⭕ Sold out! There are no more goodie bags available at {item['store_name']}."
                # telegram_bot_sendtext(message)
                telegram_bot_delete_message([stock['msg_id'] for stock in tgtg_in_stock if stock['id'] == item['id']][0])
            else:
                # Prepare a generic string, but with the important info
                message = f"There was a change of number of goodie bags in stock from {old_stock} to {new_stock} at {item['store_name']}."
                telegram_bot_sendtext(message)

    # Reset the global information with the newest fetch
    tgtg_in_stock = parsed_api

    # Print out some maintenance info in the terminal
    print(f"TGTG: API run at {time.ctime(time.time())} successful.")
    # for item in parsed_api:
    #     print(f"{item['store_name']}({item['id']}): {item['items_available']}")

def parse_foodsi_api(api_result):
    """
    For fideling out the few important information out of the api response
    """
    new_api_result = list()
    # Go through all favorites linked to the account,that are returned with the api
    for restaurant in api_result['data']:
        current_item = restaurant
        current_item['opened_at'] = dateutil.parser.parse(restaurant['package_day']['collection_day']['opened_at']).strftime('%H:%M')
        current_item['closed_at'] = dateutil.parser.parse(restaurant['package_day']['collection_day']['closed_at']).strftime('%H:%M')
        if (restaurant['package_day']['meals_left'] is None):
            current_item['package_day']['meals_left'] = 0
        new_api_result.append(current_item)

    return new_api_result
def foodsi():
    """
    Retrieves the data from foodsi API and selects the message to send.
    """
    items = list()
    page = 1
    totalpages = 1
    while page <= totalpages:
        req_json = {
            "page": page,
            "per_page": 15,
            "distance": {
                "lat": config['location']['lat'],
                "lng": config['location']['long'],
                "range": config['location']['range']*1000
            },
            "hide_unavailable": False,
            "food_type": [],
            "collection_time": {
                "from": "00:00:00",
                "to": "23:59:59"
            }
        }
        foodsi_api = requests.post('https://api.foodsi.pl/api/v2/restaurants', headers = {'Content-type':'application/json', 'system-version':'android_3.0.0', 'user-agent':'okhttp/3.12.0'}, data = json.dumps(req_json))
        items += parse_foodsi_api(foodsi_api.json())
        # print("Foodsi current page: " + str(foodsi_api.json()['current_page']))
        # print("Foodsi total pages: " + str(foodsi_api.json()['total_pages']))
        totalpages = foodsi_api.json()['total_pages']
        # print("Foodsi page count: " + str(len(foodsi_api.json()['data'])))
        page += 1
    print("Foodsi total items: " + str(len(items)))
    # Get the global variable of items in stock
    global foodsi_in_stock

    # Go through all favourite items and compare the stock
    for item in items:
        try:
            old_stock = [stock['package_day']['meals_left'] for stock in foodsi_in_stock if stock['id'] == item['id']][0]
        except IndexError:
            old_stock = 0
        try:
            item['msg_id'] = [stock['msg_id'] for stock in foodsi_in_stock if stock['id'] == item['id']][0]
        except:
            pass

        new_stock = item['package_day']['meals_left']

        # Check, if the stock has changed. Send a message if so.
        if new_stock != old_stock:
            # Check if the stock was replenished, send an encouraging image message
            if old_stock == 0 and new_stock > 0:
                #TODO: tommorrow date
                message = f"🍽 There are {new_stock} new goodie bags at [{item['name']}]({item['url']})\n"\
                f"_{item['meal']['description']}_\n"\
                f"💰 *{item['meal']['price']}PLN*/{item['meal']['original_price']}PLN\n"\
                f"⏰ {item['opened_at']}-{item['closed_at']}\n"\
                "ℹ️ foodsi.pl"
                # message += f"\ndebug id: {item['id']}"
                tg = telegram_bot_sendimage(item['image']['url'], message)
                try: 
                    item['msg_id'] = tg['result']['message_id']
                except:
                    print(json.dumps(tg))
                    print(item['image']['url'])
                    print(message)
                    print(traceback.format_exc())
            elif old_stock > new_stock and new_stock != 0:
                # customer feedback: This message is not needed
                pass
                ## Prepare a generic string, but with the important info
                # message = f" 📉 Decrease from {old_stock} to {new_stock} available goodie bags at {[item['store_name'] for item in new_api_result if item['id'] == item_id][0]}."
                # telegram_bot_sendtext(message)
            elif old_stock > new_stock and new_stock == 0:
                # message = f" ⭕ Sold out! There are no more goodie bags available at {item['store_name']}."
                # telegram_bot_sendtext(message)
                telegram_bot_delete_message([stock['msg_id'] for stock in foodsi_in_stock if stock['id'] == item['id']][0])
            else:
                # Prepare a generic string, but with the important info
                message = f"There was a change of number of goodie bags in stock from {old_stock} to {new_stock} at {item['store_name']}."
                telegram_bot_sendtext(message)

    # Reset the global information with the newest fetch
    foodsi_in_stock = items

    # Print out some maintenance info in the terminal
    print(f"Foodsi: API run at {time.ctime(time.time())} successful.")
    # for item in foodsi_in_stock:
    #     print(f"{item['name']}({item['id']}): {item['package_day']['meals_left']}")


def still_alive():
    """
    This function gets called every 24 hours and sends a 'still alive' message to the admin.
    """
    message = f"Current time: {time.ctime(time.time())}. The bot is still running. "
    telegram_bot_sendtext(message)

def refresh():
    """
    Function that gets called via schedule every 1 minute.
    Retrieves the data from services APIs and selects the messages to send.
    """
    try:
        toogoodtogo()
        foodsi()
    except:
        print(traceback.format_exc())
        telegram_bot_sendtext("Error occured: \n```" + str(traceback.format_exc()) + "```")

# Use schedule to set up a recurrent checking
schedule.every(1).minutes.do(refresh)
schedule.every(24).hours.do(still_alive)

# Description of the service, that gets send once
telegram_bot_sendtext("The bot script has started successfully. The bot checks every 1 minute, if there is something new at TooGoodToGo or Foodsi. Every 24 hours, the bots sends a \"still alive\" message.")
refresh()
while True:
    # run_pending
    schedule.run_pending()
    time.sleep(1)
