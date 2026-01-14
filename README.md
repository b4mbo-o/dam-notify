# 🎤 DAM Notify Bot

Club DAM の検索 API を叩いて **新曲が追加されたら X(Twitter) に自動ツイート** するボットです。  
指定したキーワードの総件数が初回より増えたら即ツイートして終了します。

---

## 🚀 Features

- ✅ Club DAM 公式 API に直接 POST  
- ✅ 初回の `totalCount` を基準に「増えた」タイミングで検出  
- ✅ 新曲タイトルを3件までプレビュー  
- ✅ OAuth1.0a (4キー方式) で自分の X アカウントに自動投稿  
- ✅ ツイートに **#DAM #カラオケ #KEYWORD** のハッシュタグを付与  
- ✅ キーワードを複数監視 & 検知したキーワードは自動でリストから削除  
- ✅ ツイート後はキーワードごとの状態ファイルを削除 → 次回は再度初期化から監視  

---

## 📦 Requirements

- Python 3.10+
- [requests](https://pypi.org/project/requests/)
- [python-dotenv](https://pypi.org/project/python-dotenv/)
- [tweepy](https://pypi.org/project/tweepy/)

インストール:

```bash
pip install -r requirements.txt
```

---

## ⚙️ Setup

### .env

```bash
# 監視キーワード: いずれかで指定
KEYWORDS=word1,word2  # カンマ or 改行区切り
# または KEYWORDS_FILE=keywords.txt  # 1行1キーワードで書く（デフォルト値）
# または KEYWORD=単一キーワード     # 後方互換

INTERVAL_SEC=600 # 何秒おきに検索か

# キーワードを検出したら keywords.txt から自動削除するか
# REMOVE_KEYWORD_ON_HIT=true

# X (OAuth1.0a) 4キー
TW_CONSUMER_KEY=xxxxxxxxxxxxxxxx
TW_CONSUMER_SECRET=xxxxxxxxxxxxxxxxxxxxxxxx
TW_ACCESS_TOKEN=xxxxxxxxxxxxxxxx-xxxxxxxxxxxxxxxxxxxxxxxx
TW_ACCESS_SECRET=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

---

## ▶️ Usage

起動:

```bash
python main.py
```

動作:
- 初回起動: 現在の件数を保存して監視開始  
- 件数が増加したら:  
  - 🎤 ツイート  
  - そのキーワードの状態ファイル (`state/<keyword>.json`) を削除  
  - `REMOVE_KEYWORD_ON_HIT=true` なら `keywords.txt` から該当キーワードを削除  
  - ループを続行（他キーワードの監視継続）  

### keywords.txt (デフォルトのキーワード管理)

リポジトリ直下の `keywords.txt` に 1行1キーワードで書くと、複数ワードを監視できます。  
`#` 始まりの行はコメント扱い。  
検知後に自動削除させたい場合は `.env` で `REMOVE_KEYWORD_ON_HIT=true` のままにしておきます（デフォルト）。

---

## 📝 Example Tweet

```
🎤 Club DAMに『iLiFE!』の新曲が追加されました！
22 → 25 件
• 会いにKiTE!
• #ラブコード
• アイドルライフスターターパック
#DAM #カラオケ #iLiFE
```

---

## 🛠️ systemd 常駐の例

リポジトリ内の `dam-notify.service` を `/etc/systemd/system/` に配置するか、以下をベースに作成します（パスは環境に合わせて調整してください）。

```
[Unit]
Description=DAM Notify Bot
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=/root/dam-notify
EnvironmentFile=/root/dam-notify/.env
ExecStart=/usr/bin/python3 /root/dam-notify/main.py
Restart=on-failure
RestartSec=30

[Install]
WantedBy=multi-user.target
```

反映と自動起動:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now dam-notify.service
```

ログ確認:

```bash
journalctl -u dam-notify.service -f
```

キーワードや .env を変えたら `sudo systemctl restart dam-notify.service` を実行してください。

---

## ⚠️ 注意

- X アプリ権限は必ず Read and Write に設定  
- サーバーの時刻が大きくズレていると認証エラーになる場合あり  

---

## 🖤 Author

ばんぶー
