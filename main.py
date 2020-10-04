from flask import Flask, request, abort
import os

from linebot import (LineBotApi, WebhookHandler)
from linebot.exceptions import (InvalidSignatureError)
from linebot.models import (MessageEvent, TextMessage, TextSendMessage,)

import spotipy
import json
import pandas as pd
import matplotlib.pyplot as plt
import networkx as nx
# from community import community_louvain
from spotipy.oauth2 import SpotifyClientCredentials 

app = Flask(__name__)

# 環境変数取得
YOUR_CHANNEL_ACCESS_TOKEN = os.environ["YOUR_CHANNEL_ACCESS_TOKEN"]
YOUR_CHANNEL_SECRET = os.environ["YOUR_CHANNEL_SECRET"]
line_bot_api = LineBotApi(YOUR_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(YOUR_CHANNEL_SECRET)

client_id = os.environ["client_id"]
client_secret = os.environ["client_secret"]
client_credentials_manager = spotipy.oauth2.SpotifyClientCredentials(client_id, client_secret)
spotify = spotipy.Spotify(client_credentials_manager=client_credentials_manager)

# Webで開いたとき
@app.route("/")
def hello_world():
    return "hello world!"

# LINEで開いたとき
@app.route("/callback", methods=['POST'])
def callback():
    # get X-Line-Signature header value
    signature = request.headers['X-Line-Signature']

    # get request body as text
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    # handle webhook body
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return 'OK'

# 友だち追加時の関数
@handler.add(FollowEvent)
def handle_follow(event):
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text='好きなアーティスト名を教えてくれ')
    )

# テキストを送ったときの関数
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    txt = event.message.text
    # artist_df = pd.DataFrame(
    #     columns=['artist_name','artist_ID','genre','popularity','related_artist_names']
    # )
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=txt+'が好きなんだ~')
    )


if __name__ == "__main__":
#    app.run()
    port = int(os.getenv("PORT"))
    app.run(host="0.0.0.0", port=port)