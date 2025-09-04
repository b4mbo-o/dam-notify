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
- ✅ ツイート後に `state_api.json` を削除 → 次回は再度初期化から監視  

---

## 📦 Requirements

- Python 3.10+
- [requests](https://pypi.org/project/requests/)
- [python-dotenv](https://pypi.org/project/python-dotenv/)
- [tweepy](https://pypi.org/project/tweepy/)

インストール:

```bash
pip install -r requirements.txt```

⚙️ Setup

1. Twitter Developer Portal

	1.	アプリを作成
	2.	User authentication settings を有効化
	•	Type: OAuth1.0a
	•	Permissions: Read and Write
	3.	API Key / API Secret と Access Token / Access Token Secret を発行

2. .env
```bash
# 監視キーワード
KEYWORD=検索したいワード
INTERVAL_SEC=600 #何分置きに検索か

# DAM API 固定値（必要なら変更可）
MODEL_TYPE_CODE=1
SERIAL_NO=BA000001
COMP_ID=1
AUTH_KEY=2/Qb9R@8s*
CONTENTS_CODE=
SERVICE_CODE=
SORT=2
DISP_COUNT=100
PAGE_NO=1

# X (OAuth1.0a) 4キー
TW_CONSUMER_KEY=xxxxxxxxxxxxxxxx
TW_CONSUMER_SECRET=xxxxxxxxxxxxxxxxxxxxxxxx
TW_ACCESS_TOKEN=xxxxxxxxxxxxxxxx-xxxxxxxxxxxxxxxxxxxxxxxx
TW_ACCESS_SECRET=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```
▶️ Usage

起動:

python main.py

動作:
	•	初回起動: 現在の件数を保存して監視開始
	•	件数が増加したら:
	•	🎤 ツイート
	•	state_api.json を削除
	•	プロセス終了

📝 Example Tweet

🎤 Club DAMに『iLiFE!』の新曲が追加されました！
22 → 25 件
• 会いにKiTE!
• #ラブコード
• アイドルライフスターターパック
#DAM #カラオケ #iLiFE

⚠️ 注意

	•	Access Token/Secret を公開しないこと！
	•	X アプリ権限は必ず Read and Write に設定
	•	サーバーの時刻が大きくズレていると認証エラーになる場合あり

🖤 Author

つくった人: ばんぶー

---