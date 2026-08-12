# /// script
# requires-python = ">=3.11"
# dependencies = ["requests>=2.31"]
# ///
"""EDINET API v2 クライアント: 開示書類の一覧・企業検索・ダウンロード。

使い方:
  uv run scripts/edinet.py list 2026-08-12                # 指定日の提出書類一覧
  uv run scripts/edinet.py search 7203 --days 30          # 証券コード/社名で直近 N 日を検索
  uv run scripts/edinet.py get S100XXXX --type pdf        # 書類取得 (pdf | xbrl | csv)

API キーは .env の EDINET_API_KEY (https://api.edinet-fsa.go.jp で発行)。
四半期報告書は 2024 年の金商法改正で廃止済み。決算短信は TDnet の管轄で EDINET にはない。
"""

import argparse
import datetime
import os
import sys
from pathlib import Path

import requests

REPO = Path(__file__).resolve().parent.parent
BASE = "https://api.edinet-fsa.go.jp/api/v2"
DOWNLOAD_DIR = REPO / "downloads" / "edinet"

DOC_TYPE = {"xbrl": (1, "zip"), "pdf": (2, "pdf"), "csv": (5, "zip")}
FORM_NAMES = {
    "120": "有価証券報告書", "130": "訂正有価証券報告書",
    "160": "半期報告書", "170": "訂正半期報告書",
    "180": "臨時報告書",
    "350": "大量保有報告書", "360": "変更報告書(大量保有)",
}


def api_key():
    key = os.environ.get("EDINET_API_KEY")
    if not key:
        env_file = REPO / ".env"
        if env_file.exists():
            for line in env_file.read_text(encoding="utf-8").splitlines():
                if line.strip().startswith("EDINET_API_KEY="):
                    key = line.split("=", 1)[1].strip()
    if not key:
        sys.exit("EDINET_API_KEY が未設定。D:\\Claude-knowledge-bank\\.env に追記すること")
    return key


def fetch_day(date, key):
    r = requests.get(
        f"{BASE}/documents.json",
        params={"date": date, "type": 2, "Subscription-Key": key},
        timeout=30,
    )
    if r.status_code == 401:
        sys.exit("401: API キーが不正 (Subscription-Key を確認)")
    r.raise_for_status()
    body = r.json()
    # EDINET (APIM) はエラーを HTTP 200 + body 内 StatusCode で返すことがある
    if body.get("StatusCode") not in (None, 200):
        sys.exit(f"API エラー: {body.get('StatusCode')} {body.get('message')}")
    meta_status = (body.get("metadata") or {}).get("status")
    if meta_status not in (None, "200"):
        sys.exit(f"API エラー (metadata.status={meta_status}): {(body.get('metadata') or {}).get('message')}")
    return body.get("results") or []


def fmt(doc):
    sec = (doc.get("secCode") or "----")[:4]
    form = doc.get("docTypeCode") or "---"
    form_name = FORM_NAMES.get(form, "")
    return (
        f"{doc.get('docID')}  {sec}  {doc.get('filerName', ''):<30.30}  "
        f"[{form}{' ' + form_name if form_name else ''}] {doc.get('docDescription', '')}"
    )


def cmd_list(args):
    docs = fetch_day(args.date, api_key())
    for d in docs:
        if args.all or d.get("secCode"):  # デフォルトは上場企業 (secCode あり) のみ
            print(fmt(d))
    print(f"-- {args.date}: {len(docs)} 件 (全提出者)")


def cmd_search(args):
    key = api_key()
    query = args.query
    today = datetime.date.today()
    hits = 0
    for i in range(args.days):
        date = (today - datetime.timedelta(days=i)).isoformat()
        for d in fetch_day(date, key):
            sec = d.get("secCode") or ""
            if sec.startswith(query) or query in (d.get("filerName") or ""):
                print(f"{date}  {fmt(d)}")
                hits += 1
    print(f"-- 直近 {args.days} 日で {hits} 件")


def cmd_get(args):
    doc_type, ext = DOC_TYPE[args.type]
    r = requests.get(
        f"{BASE}/documents/{args.doc_id}",
        params={"type": doc_type, "Subscription-Key": api_key()},
        timeout=120,
    )
    r.raise_for_status()
    if "application/json" in r.headers.get("Content-Type", ""):
        sys.exit(f"取得失敗: {r.json()}")  # エラー時のみ JSON が返る
    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
    out = DOWNLOAD_DIR / f"{args.doc_id}.{ext}"
    out.write_bytes(r.content)
    print(out)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(required=True)

    p_list = sub.add_parser("list", help="指定日の提出書類一覧")
    p_list.add_argument("date", help="YYYY-MM-DD")
    p_list.add_argument("--all", action="store_true", help="非上場の提出者 (ファンド等) も表示")
    p_list.set_defaults(func=cmd_list)

    p_search = sub.add_parser("search", help="証券コード or 社名で直近 N 日を検索")
    p_search.add_argument("query", help="証券コード 4 桁 or 社名の部分一致")
    p_search.add_argument("--days", type=int, default=30)
    p_search.set_defaults(func=cmd_search)

    p_get = sub.add_parser("get", help="docID で書類を downloads/edinet/ に取得")
    p_get.add_argument("doc_id")
    p_get.add_argument("--type", choices=DOC_TYPE, default="pdf")
    p_get.set_defaults(func=cmd_get)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
