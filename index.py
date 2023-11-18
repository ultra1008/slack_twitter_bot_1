import requests
import os
import time

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from datetime import datetime, timedelta
from dotenv import load_dotenv
load_dotenv(".env")
bearer_token = os.getenv('BEARER_TOKEN')
slack_bot_token = os.getenv("SLACK_BOT_TOKEN")
search_url = "https://api.twitter.com/2/tweets/search/recent"

channel_names = ["questions-answer", "charts-analysis", "class-materials", "trading-room"]
channel_ids = []

def week_ago_time():
    # Get the current time
    now = datetime.now()

    # Subtract a week
    one_week_ago = now - timedelta(days=6)

    # Format the datetime objects
    one_week_ago_str = one_week_ago.strftime('%Y-%m-%dT%H:%M:%S.000Z')
    return one_week_ago_str

# Optional params: start_time,end_time,since_id,until_id,max_results,next_token,
# expansions,tweet.fields,media.fields,poll.fields,place.fields,user.fields
query_params = {
    'query': 'from:primeoptions02', # -is:retweet -is:reply
    'tweet.fields': 'author_id,created_at,conversation_id',
    'user.fields': 'username',
    'expansions': 'author_id',
    'start_time': week_ago_time(),
    'max_results': 10,
    'sort_order': 'recency'
}

def bearer_oauth(r):
    # Method required by bearer token authentication.
    r.headers["Authorization"] = f"Bearer {bearer_token}"
    r.headers["User-Agent"] = "v2RecentSearchPython"
    return r

def connect_to_endpoint(url, params):
    response = requests.get(url, auth=bearer_oauth, params=params)
    if response.status_code != 200:
        raise Exception(response.status_code, response.text)
    return response.json()

# Initialize a Web API client
slack_web_client = WebClient(token=slack_bot_token)

def post_msg(channel_id, message):
    # Send message to the channel
    try:
        # Call the chat.postMessage method using the WebClient
        # The text field is where you can write the message text
        response = slack_web_client.chat_postMessage(
            channel=channel_id,
            text=message
        )
    except SlackApiError as e:
        # You will get a SlackApiError if "ok" is False
        print(f"Error: {e}")
    time.sleep(1)

# Search the ID of channel name and return
def channel_name2id(channel_name):
    response = slack_web_client.conversations_list(types='public_channel,private_channel')
    channel_id = None
    for channel in response['channels']:
        if channel['name'] == channel_name:
            channel_id = channel['id']
            break

    return channel_id

def invite_user(token, email, channels):
    url = "https://slack.com/api/users.admin.invite"
    payload = {
        'token': token,
        'email': email,
        'channels': channels,
        'resend': True
    }
    response = requests.post(url, data=payload)
    return response.json()

def create_channel(channel_name):
    # Create a channel by given name in workspace
    if(channel_name2id(channel_name) != None):
        print("The name is already exist")
        return channel_name2id(channel_name)

    try:
    # call the conversations_create method using the WebClient
    # replace 'channel-name' with your desired channel name
        response = slack_web_client.conversations_create(
            name=channel_name
        )
        channel_id = response["channel"]["id"]
        print(f"{channel_name} channel is created")
        return channel_id
    except SlackApiError as e:
        print(f"Error creating channel: {e}")
        return False

def main():
    last_at = ""
    for channels_name in channel_names:
        item_id = create_channel(channels_name)
        channel_ids.append(item_id)
    
    channel_id_trading = channel_ids[3]
    channel_id_qa = channel_ids[0]

    if (channel_id_trading):
        while(True):
            json_response = connect_to_endpoint(search_url, query_params)
            if 'data' not in json_response:
                time.sleep(90)
                print("Success")
                continue
            tweets = json_response['data']
            users = json_response['includes']['users']
            user_map = {
                user["id"]: user["username"]
                for user in users
            }
            
            last_at = tweets[0]['created_at']

            for tweet in reversed(tweets):                  
                author_id = tweet["author_id"]
                id = tweet["id"]
                message = f"""https://twitter.com/{user_map[author_id]}/status/{id}"""
                post_msg(channel_id_trading, message)

                # replies_params = {
                #     'query': f'conversation_id:{id}',
                #     'tweet.fields': 'author_id,created_at',
                #     'max_results': 10,
                #     'expansions': 'author_id',
                #     'sort_order': 'recency',
                # }
                # reply_json_response = connect_to_endpoint(search_url, replies_params)
                # if 'data' in reply_json_response:
                #     reply_tweets = reply_json_response['data']

                #     reply_users = reply_json_response['includes']['users']
                #     reply_user_map = {
                #         user["id"]: user["username"]
                #         for user in reply_users
                #     }

                #     for reply_tweet in reply_tweets:
                #         reply_author_id = reply_tweet["author_id"]
                #         reply_id = reply_tweet["id"]
                #         reply_message = f"""https://twitter.com/{reply_user_map[reply_author_id]}/status/{reply_id}"""

                #         if channel_id_qa:
                #             say_hello(channel_id_qa, reply_message)

            last_at = datetime.strptime(last_at, '%Y-%m-%dT%H:%M:%S.%fZ') + timedelta(seconds=1)
            query_params['start_time'] = last_at.strftime('%Y-%m-%dT%H:%M:%S.000Z')
            print("Success")
            time.sleep(90)

if __name__ == "__main__":
    main()