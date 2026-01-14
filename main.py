import hashlib
import os
import time
import sys
import json
import unicodedata
import re
from pathlib import Path

import requests
from dotenv import load_dotenv
import tweepy

load_dotenv()

# ===== 設定 =====
INTERVAL_SEC = int(os.getenv("INTERVAL_SEC", "600"))
KEYWORDS_FILE = Path(os.getenv("KEYWORDS_FILE", "keywords.txt"))


def env_flag(name: str, default: bool = False) -> bool:
    val = os.getenv(name)
    if val is None:
        return default
    return str(val).strip().lower() not in {"0", "false", "no", "off"}


REMOVE_KEYWORD_ON_HIT = env_flag("REMOVE_KEYWORD_ON_HIT", True)

STATE_DIR = Path("state")
STATE_DIR.mkdir(exist_ok=True)

DAM_API = "https://www.clubdam.com/dkwebsys/search-api/SearchVariousByKeywordApi"
BASE_PAYLOAD = {
    "modelTypeCode": os.getenv("MODEL_TYPE_CODE", "1"),
    "serialNo": os.getenv("SERIAL_NO", "BA000001"),
    "compId": os.getenv("COMP_ID", "1"),
    "authKey": os.getenv("AUTH_KEY", "2/Qb9R@8s*"),
    "contentsCode": os.getenv("CONTENTS_CODE") or None,
    "serviceCode": os.getenv("SERVICE_CODE") or None,
    "sort": os.getenv("SORT", "2"),
    "dispCount": os.getenv("DISP_COUNT", "100"),
    "pageNo": os.getenv("PAGE_NO", "1"),
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

def normalize_keywords(raw: str) -> list[str]:
    """
    改行 or カンマ区切りの文字列をキーワード配列にする。
    空行/コメント(#)はスキップ。順序は維持しつつ重複は除外。
    """
    items: list[str] = []
    for line in raw.replace(",", "\n").splitlines():
        kw = line.strip()
        if not kw or kw.startswith("#"):
            continue
        items.append(kw)

    seen = set()
    uniq: list[str] = []
    for kw in items:
        if kw not in seen:
            uniq.append(kw)
            seen.add(kw)
    return uniq

def load_keywords() -> list[str]:
    if KEYWORDS_FILE.exists():
        return normalize_keywords(KEYWORDS_FILE.read_text(encoding="utf-8"))

    env_keywords = os.getenv("KEYWORDS")
    if env_keywords:
        return normalize_keywords(env_keywords)

    # 後方互換: KEYWORD を 1 件だけ見る
    fallback = os.getenv("KEYWORD", "MEGAFON")
    return normalize_keywords(fallback)

def slugify_keyword(keyword: str) -> str:
    norm = unicodedata.normalize("NFKC", keyword)
    norm = re.sub(r"[^A-Za-z0-9_-]+", "-", norm).strip("-") or "kw"
    digest = hashlib.sha256(keyword.encode("utf-8")).hexdigest()[:8]
    return f"{norm}-{digest}"

# ===== DAM呼び出し =====
def build_payload(keyword: str) -> dict:
    payload = {**BASE_PAYLOAD, "keyword": keyword}
    return {k: v for k, v in payload.items() if v is not None}

# ===== DAM呼び出し =====
def call_dam_api(keyword: str) -> dict:
    r = requests.post(DAM_API, headers=HEADERS, json=build_payload(keyword), timeout=30)
    r.raise_for_status()
    js = r.json()
    if str(js.get("result", {}).get("statusCode")) != "0000":
        raise RuntimeError(f"DAM API status != 0000: {js.get('result')}")
    return js

# ===== 状態管理 =====
def state_file(keyword: str) -> Path:
    return STATE_DIR / f"{slugify_keyword(keyword)}.json"

def load_initial_total(keyword: str) -> int | None:
    path = state_file(keyword)
    if path.exists():
        try:
            return int(json.loads(path.read_text(encoding="utf-8")).get("initial_total"))
        except Exception:
            return None
    return None

def save_initial_total(keyword: str, n: int):
    path = state_file(keyword)
    path.write_text(json.dumps({"initial_total": int(n)}, ensure_ascii=False, indent=2), encoding="utf-8")

def delete_state_file(keyword: str):
    try:
        path = state_file(keyword)
        if path.exists():
            path.unlink()
            print(f"[state] state/{path.name} を削除しました")
    except Exception as e:
        print("[state] 削除失敗:", e)

def remove_keyword_from_file(keyword: str) -> bool:
    if not KEYWORDS_FILE.exists():
        return False

    lines = KEYWORDS_FILE.read_text(encoding="utf-8").splitlines()
    keep: list[str] = []
    removed = False
    for line in lines:
        if not line.strip() or line.strip().startswith("#"):
            keep.append(line)
            continue

        if line.strip() == keyword:
            removed = True
            continue

        keep.append(line)

    if removed:
        new_body = "\n".join(keep).rstrip() + ("\n" if keep else "")
        KEYWORDS_FILE.write_text(new_body, encoding="utf-8")
    return removed

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
    print("== DAM watch via API (multiple keywords) ==")
    while True:
        keywords = load_keywords()
        if not keywords:
            print("[warn] キーワードが設定されていません (keywords.txt か KEYWORDS/KEYWORD を設定してね)")

        for keyword in keywords:
            try:
                js = call_dam_api(keyword)
                total = int(js.get("data", {}).get("totalCount", 0))
                titles = [it.get("title") for it in (js.get("list") or []) if it.get("title")]

                baseline = load_initial_total(keyword)
                if baseline is None:
                    save_initial_total(keyword, total)
                    print(f"[init] '{keyword}' baseline totalCount = {total}")
                    continue

                print(f"[poll] '{keyword}': total={total} (baseline={baseline})")
                if total > baseline:
                    tweet(format_tweet(keyword, baseline, total, titles))
                    delete_state_file(keyword)

                    if REMOVE_KEYWORD_ON_HIT:
                        if remove_keyword_from_file(keyword):
                            print(f"[keywords] '{keyword}' を keywords.txt から削除しました")
                        elif not KEYWORDS_FILE.exists():
                            print("[keywords] KEYWORDS_FILE 未設定のためキーワード削除はスキップ")

                    print(f"[done] '{keyword}' で変化を検出")
                    # 他のキーワードは続行
            except tweepy.TweepyException as e:
                print(f"[error] '{keyword}' tweet失敗:", e)
                print("ヒント: アプリ権限がRead & Writeか / 4キーが同一アプリ由来か / 時刻ズレがないか")
            except Exception as e:
                print(f"[error] '{keyword}'", e)

        time.sleep(INTERVAL_SEC)

if __name__ == "__main__":
    main_loop()
