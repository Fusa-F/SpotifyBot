from flask import Flask, request, abort
import os

from linebot import (LineBotApi, WebhookHandler)
from linebot.exceptions import (InvalidSignatureError)
from linebot.models import (FollowEvent, MessageEvent, TextMessage, TextSendMessage, ImageSendMessage)

import spotipy
import json
import pandas as pd
import matplotlib.pyplot as plt
import networkx as nx
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
    # DataFrameを定義
    artist_df = pd.DataFrame(
        columns=['artist_name','artist_ID','genre','popularity','related_artist_names']
    )
    # 入力されたアーティスト名から情報を取得
    name = event.message.text
    spotapi_out = spotify.search(q='artist:' + name, type='artist')
    try:
        artist_items = spotapi_out['artists']['items'][0]
        artist_id = artist_items['id']
        artid_list = [artist_id]
        artname_related_list = []
        spotapi_out_related = spotify.artist_related_artists(artist_id)
        for artname_related in spotapi_out_related['artists']:
            artname_related_list.append(artname_related['name'])
        s = pd.Series([artist_items['name'], artist_items['id'], artist_items['genres'],artist_items['popularity'],artname_related_list],index=artist_df.columns)
        artist_df = artist_df.append(s,ignore_index=True)

        # 関連アーティストを探す
        artid_list_tail = 0
        for i in range(1):
            artid_list_head = artid_list_tail
            artid_list_tail = len(artid_list)
            for artid in artid_list[artid_list_head:artid_list_tail]:
                spotapi_out = spotify.artist_related_artists(artid)
                for artid_related in spotapi_out['artists']:
                    artist_df_bool = artist_df['artist_ID']==artid_related['id']
                    if artist_df_bool.sum()==0 and artid_related['popularity']>=10:
                        # 類似のアーティストリストを作成
                        spotapi_out_related = spotify.artist_related_artists(artid_related['id'])
                        artname_related2_list = []
                        for artname_related2 in spotapi_out_related['artists']:
                            artname_related2_list.append(artname_related2['name'])
                        artid_list.append(artid_related['id'])
                        s = pd.Series([artid_related['name'], artid_related['id'], artid_related['genres'], 
                                    artid_related['popularity'], artname_related2_list], index=artist_df.columns)
                        artist_df = artist_df.append(s,ignore_index=True)
        
        # アーティストの関係の辞書を作る
        plt.figure(figsize = (16, 16))
        artdic = {}
        for i in range(len(artid_list)):
            artdic[artist_df.iloc[i,0]] = []
        for i in range(len(artid_list)):
            for artname_related in artist_df.iloc[i,4]:
                artdic[artist_df.iloc[i,0]].append(artname_related)

        # 図の書き出し
        G = nx.DiGraph()
        nx.add_path(G, artdic)
        # pos = nx.spring_layout(G, k=0.3)
        pos = nx.circular_layout(G)
        pr = nx.pagerank(G)
        def calc_inverse(n):
            return 1/n

        font_path = "static/fonts/NotoSansJP-Bold.otf"
        nx.draw_networkx_nodes(G, pos, alpha=.6, node_color=list(map(calc_inverse,list(pr.values()))), cmap=plt.cm.GnBu, node_size=[200*(1/v) for v in pr.values()])
        nx.draw_networkx_labels(G, pos, font_size=14, font_family=font_path, font_weight="bold")
        nx.draw_networkx_edges(G, pos, alpha=1, edge_color="c")
        plt.axis("off")

        image_path = "static/images/image.jpg"
        plt.savefig(image_path)

        image_message = ImageSendMessage(
            original_content_url=f"https://fusafmusicbot.herokuapp.com/{image_path}",
            preview_image_url=f"https://fusafmusicbot.herokuapp.com/{image_path}"
        )
        
        genres = ', '.join(artist_items['genres'])

        line_bot_api.reply_message(
            event.reply_token,
            [
                TextSendMessage(text=name+'が好きなんだ~'),
                TextSendMessage(text='ジャンルは'+genres+'だね'),
                image_message,
                TextSendMessage(text='関連性の高いアーティストはこんな感じ!')
            ]
        )
    except IndexError:
        line_bot_api.reply_message(
            event.reply_token,
            [
                TextSendMessage(text=name+'ってアーティストは登録されていないみたい\n(英語で登録されている場合もあるよ)'),
                TextSendMessage(text='ほかには何が好き?'),
            ]
        )


if __name__ == "__main__":
#    app.run()
    port = int(os.getenv("PORT"))
    app.run(host="0.0.0.0", port=port)