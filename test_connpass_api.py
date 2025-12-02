#!/usr/bin/env python3
"""
connpass API検証用スクリプト
様々なパラメータの組み合わせを試して、最適な検索条件を確認できます。
"""

import os
import sys
import requests
import json
from datetime import datetime, timedelta, timezone

# .envファイルを直接読み込む（config.pyより先に）
try:
    from dotenv import load_dotenv
    from pathlib import Path
    env_path = Path(__file__).parent / '.env'
    if env_path.exists():
        load_dotenv(env_path)
        print(f"✓ .envファイルを読み込みました: {env_path}")
    else:
        print(f"⚠️  .envファイルが見つかりません: {env_path}")
except ImportError:
    print("⚠️  python-dotenvがインストールされていません。pip install python-dotenv を実行してください。")

# config.pyから設定を読み込む
try:
    import config
    API_KEY = config.CONNPASS_API_KEY
    if API_KEY:
        # APIキーが設定されている場合、最初の数文字だけ表示（セキュリティのため）
        masked_key = API_KEY[:8] + "..." if len(API_KEY) > 8 else "***"
        print(f"✓ CONNPASS_API_KEYを読み込みました: {masked_key}")
    else:
        print("⚠️  CONNPASS_API_KEYが設定されていません。")
        print("   .envファイルまたは環境変数で設定してください。")
except ImportError:
    print("Warning: config.pyが見つかりません。環境変数から読み込みます。")
    API_KEY = os.environ.get("CONNPASS_API_KEY")

def test_endpoint(url, params, headers, test_name, api_key=None):
    """APIエンドポイントをテストする"""
    print(f"\n{'='*60}")
    print(f"テスト: {test_name}")
    print(f"URL: {url}")
    print(f"パラメータ: {json.dumps(params, ensure_ascii=False, indent=2)}")
    print(f"{'='*60}")
    
    try:
        # APIキーをクエリパラメータとしても試す
        request_params = params.copy()
        if api_key:
            request_params["key"] = api_key
        
        res = requests.get(url, params=request_params, headers=headers, timeout=10)
        print(f"ステータスコード: {res.status_code}")
        
        if res.status_code == 200:
            data = res.json()
            events = data.get("events", [])
            print(f"取得件数: {len(events)}件")
            
            if events:
                print("\n最初の3件のイベント:")
                for i, ev in enumerate(events[:3], 1):
                    print(f"\n{i}. {ev.get('title', 'タイトルなし')}")
                    print(f"   開催日時: {ev.get('started_at', '不明')}")
                    print(f"   場所: {ev.get('place', '不明')} / {ev.get('address', '不明')}")
                    print(f"   URL: {ev.get('event_url', '不明')}")
            else:
                print("イベントが見つかりませんでした。")
            
            return events
        else:
            print(f"エラー: {res.status_code}")
            print(f"レスポンス: {res.text[:500]}")
            return []
            
    except Exception as e:
        print(f"例外が発生しました: {e}")
        return []

def main():
    """メイン処理"""
    print("="*60)
    print("connpass API 検証スクリプト")
    print("="*60)
    
    if not API_KEY:
        print("\n⚠️  Warning: CONNPASS_API_KEYが設定されていません。")
        print("   環境変数またはconfig.pyで設定してください。")
        print("   一部のテストはAPIキーなしで実行されます。\n")
    
    # ヘッダー設定（複数の認証方法を試すため、テストごとに設定）
    base_headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    # v2エンドポイント（eventsは複数形）
    url_v2 = "https://connpass.com/api/v2/events/"
    
    # テスト1: v2エンドポイント（基本的な検索）- APIキーなし
    print("\n【テスト1】v2エンドポイント - 基本的な検索（APIキーなし）")
    params_v2 = {
        "keyword": "データ",
        "count": 10,
        "order": 2,
    }
    test_endpoint(url_v2, params_v2, base_headers.copy(), "v2 - キーワード: データ（APIキーなし）", None)
    
    # テスト1-2: v2エンドポイント（APIキーあり - X-API-Keyヘッダー）
    if API_KEY:
        print("\n【テスト1-2】v2エンドポイント - 基本的な検索（X-API-Keyヘッダー）")
        headers_with_key = base_headers.copy()
        headers_with_key["X-API-Key"] = API_KEY
        test_endpoint(url_v2, params_v2, headers_with_key, "v2 - キーワード: データ（X-API-Key）", None)
    
    # テスト1-3: v2エンドポイント（APIキーあり - クエリパラメータ）
    if API_KEY:
        print("\n【テスト1-3】v2エンドポイント - 基本的な検索（クエリパラメータkey）")
        test_endpoint(url_v2, params_v2, base_headers.copy(), "v2 - キーワード: データ（key=API_KEY）", API_KEY)
    
    # テスト2: keyword_orパラメータのテスト
    print("\n【テスト2】keyword_orパラメータのテスト")
    params_v2_or = {
        "keyword": "データ",
        "keyword_or": "メルカリ,LINE",
        "count": 10,
        "order": 2,
    }
    test_headers = base_headers.copy()
    if API_KEY:
        test_headers["X-API-Key"] = API_KEY
    test_endpoint(url_v2, params_v2_or, test_headers, "v2 - データ AND (メルカリ OR LINE)", API_KEY)
    
    # テスト3: 東京都の検索
    print("\n【テスト3】東京都の検索")
    params_tokyo = {
        "keyword": "データ",
        "keyword_or": "メルカリ,LINE",
        "address": "東京都",
        "count": 10,
        "order": 2,
    }
    test_endpoint(url_v2, params_tokyo, test_headers, "v2 - 東京都", API_KEY)
    
    # テスト4: 神奈川県の検索
    print("\n【テスト4】神奈川県の検索")
    params_kanagawa = {
        "keyword": "データ",
        "keyword_or": "メルカリ,LINE",
        "address": "神奈川県",
        "count": 10,
        "order": 2,
    }
    test_endpoint(url_v2, params_kanagawa, test_headers, "v2 - 神奈川県", API_KEY)
    
    # テスト5: オンラインの検索
    print("\n【テスト5】オンラインの検索")
    params_online = {
        "keyword": "データ",
        "keyword_or": "メルカリ,LINE",
        "address": "オンライン",
        "count": 10,
        "order": 2,
    }
    test_endpoint(url_v2, params_online, test_headers, "v2 - オンライン", API_KEY)
    
    # テスト6: より広いキーワードで検索（検証用）
    print("\n【テスト6】より広いキーワードで検索（検証用）")
    params_broad = {
        "keyword": "データ",
        "count": 10,
        "order": 2,
    }
    test_endpoint(url_v2, params_broad, test_headers, "v2 - キーワード: データのみ", API_KEY)
    
    # テスト7: メルカリまたはLINEのみ
    print("\n【テスト7】メルカリまたはLINEのみ")
    params_mercari_line = {
        "keyword_or": "メルカリ,LINE",
        "count": 10,
        "order": 2,
    }
    test_endpoint(url_v2, params_mercari_line, test_headers, "v2 - メルカリ OR LINE", API_KEY)
    
    # テスト8: prefパラメータのテスト（都道府県コード）
    print("\n【テスト8】prefパラメータのテスト（都道府県コード）")
    params_pref = {
        "keyword": "データ",
        "keyword_or": "メルカリ,LINE",
        "pref": "13",  # 東京都の都道府県コード
        "count": 10,
        "order": 2,
    }
    test_endpoint(url_v2, params_pref, test_headers, "v2 - pref=13 (東京都)", API_KEY)
    
    # テスト9: 複数のaddressパラメータ（URLに直接追加）
    print("\n【テスト9】複数のaddressパラメータ（URLに直接追加）")
    # requestsでは同じキーを複数回指定できないため、URLを手動で構築
    manual_params = {
        "keyword": "データ",
        "keyword_or": "メルカリ,LINE",
        "count": 10,
        "order": 2,
    }
    # addressパラメータを複数回追加するため、URLを手動構築
    url_with_addresses = url_v2 + "?" + "&".join([f"{k}={v}" for k, v in manual_params.items()])
    url_with_addresses += "&address=東京都&address=神奈川県&address=オンライン"
    if API_KEY:
        url_with_addresses += f"&key={API_KEY}"
    print(f"手動構築URL: {url_with_addresses}")
    try:
        res = requests.get(url_with_addresses, headers=test_headers, timeout=10)
        print(f"ステータスコード: {res.status_code}")
        if res.status_code == 200:
            data = res.json()
            events = data.get("events", [])
            print(f"取得件数: {len(events)}件")
        else:
            print(f"エラー: {res.status_code}")
            print(f"レスポンス: {res.text[:500]}")
    except Exception as e:
        print(f"例外が発生しました: {e}")
    
    print("\n" + "="*60)
    print("検証完了")
    print("="*60)
    print("\n推奨事項:")
    print("1. v2エンドポイントの動作を確認")
    print("2. 最適なパラメータの組み合わせを確認")
    print("3. 検索結果が0件の場合は、キーワードを緩和して再検証")
    print("4. 認証方法（X-API-Keyヘッダー or クエリパラメータ）を確認")
    print("="*60)

if __name__ == "__main__":
    main()

