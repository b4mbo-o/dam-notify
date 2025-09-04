import os, time, sys, json, unicodedata, re
from pathlib import Path
import requests
from dotenv import load_dotenv
import tweepy

load_dotenv()

# ===== 設定 =====
KEYWORD      = os.getenv("KEYWORD", "MEGAFON")
INTERVAL_SEC = int(os.getenv("INTERVAL_SEC", "600"))

DAM_API = "https://www.clubdam.com/dkwebsys/search-api/SearchVariousByKeywordApi"
PAYLOAD = {
    "modelTypeCode": os.getenv("MODEL_TYPE_CODE", "1"),
    "serialNo":      os.getenv("SERIAL_NO", "BA000001"),
    "keyword":       KEYWORD,
    "compId":        os.getenv("COMP_ID", "1"),
    "authKey":       os.getenv("AUTH_KEY", "2/Qb9R@8s*"),
    "contentsCode":  os.getenv("CONTENTS_CODE") or None,
    "serviceCode":   os.getenv("SERVICE_CODE") or None,
    "sort":          os.getenv("SORT", "2"),
    "dispCount":     os.getenv("DISP_COUNT", "100"),
    "pageNo":        os.getenv("PAGE_NO", "1"),
}
HEADERS = {"User-Agent": "dam-watch/0.1", "Content-Type": "application/json"}

CK = os.getenv("TW_CONSUMER_KEY")
CS = os.getenv("TW_CONSUMER_SECRET")
AT = os.getenv("TW_ACCESS_TOKEN")
AS = os.getenv("TW_ACCESS_SECRET")

if not all([CK, CS, AT, AS]):
    print("❌ OAuth1.0aの4キー(TW_CONSUMER_KEY/SECRET, TW_ACCESS_TOKEN/SECRET)を .env に入れてね")
    sys.exit(1)

# Tweepy v2クライアント（OAuth1.0aの4キーでユーザー文脈）
client = tweepy.Client(
    consumer_key=CK,
    consumer_secret=CS,
    access_token=AT,
    access_token_secret=AS,
)

STATE_FILE = Path("state_api.json")

# ===== ユーティリティ =====
def sanitize_hashtag(s: str) -> str:
    """
    ハッシュタグ用に記号除去。
    - NFKC正規化（全角→半角など）
    - 許可: [A-Za-z0-9_], ひらがな, カタカナ, 漢字, 長音「ー」
    - それ以外は削る
    """
    s = unicodedata.normalize("NFKC", s)
    allowed = re.compile(r"[A-Za-z0-9_\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF\u30FC]+")
    return "".join(allowed.findall(s))

# ===== DAM呼び出し =====
def call_dam_api() -> dict:
    r = requests.post(DAM_API, headers=HEADERS, json=PAYLOAD, timeout=30)
    r.raise_for_status()
    js = r.json()
    if str(js.get("result", {}).get("statusCode")) != "0000":
        raise RuntimeError(f"DAM API status != 0000: {js.get('result')}")
    return js

# ===== 状態管理 =====
def load_initial_total() -> int | None:
    if STATE_FILE.exists():
        try:
            return int(json.loads(STATE_FILE.read_text(encoding="utf-8")).get("initial_total"))
        except Exception:
            return None
    return None

def save_initial_total(n: int):
    STATE_FILE.write_text(json.dumps({"initial_total": int(n)}, ensure_ascii=False, indent=2), encoding="utf-8")

def delete_state_file():
    try:
        if STATE_FILE.exists():
            STATE_FILE.unlink()
            print("[state] state_api.json を削除しました")
    except Exception as e:
        print("[state] 削除失敗:", e)

# ===== ツイート =====
def tweet(text: str):
    if len(text) > 260:  # 文字数保険
        text = text[:257] + "..."
    client.create_tweet(text=text)
    print("[tweet] posted")

def format_tweet(keyword: str, before: int, after: int, titles: list[str]) -> str:
    hashtag_kw = sanitize_hashtag(keyword)
    tags = f"#DAM #カラオケ #{hashtag_kw}" if hashtag_kw else "#DAM #カラオケ"
    lines = [
        f"🎤 Club DAMに『{keyword}』の新曲が追加されました！",
        f"{before} → {after} 件"
    ]
    for t in titles[:3]:
        lines.append(f"• {t}")
    lines.append(tags)
    return "\n".join(lines)

# ===== メインループ =====
def main_loop():
    print(f"== DAM watch via API (keyword={KEYWORD}) ==")
    baseline = load_initial_total()

    while True:
        try:
            js = call_dam_api()
            total = int(js.get("data", {}).get("totalCount", 0))
            titles = [it.get("title") for it in (js.get("list") or []) if it.get("title")]

            if baseline is None:
                save_initial_total(total)
                baseline = total
                print(f"[init] baseline totalCount = {baseline}")
            else:
                print(f"[poll] total={total} (baseline={baseline})")
                if total > baseline:
                    tweet(format_tweet(KEYWORD, baseline, total, titles))
                    delete_state_file()  # ★使い終わったら毎回消す
                    print("[done] 変化を検出 → 終了")
                    sys.exit(0)
                # 減少/同じはスルー
        except tweepy.TweepyException as e:
            print("[error] tweet失敗:", e)
            print("ヒント: アプリ権限がRead & Writeか / 4キーが同一アプリ由来か / 時刻ズレがないか")
        except Exception as e:
            print("[error]", e)

        time.sleep(INTERVAL_SEC)

if __name__ == "__main__":
    main_loop()