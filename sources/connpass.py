from datetime import datetime, timedelta, timezone
import requests
import time
from .base import BaseEventSource
import config

class ConnpassSource(BaseEventSource):
    def fetch_events(self):
        # v2エンドポイント（eventsは複数形）
        url = "https://connpass.com/api/v2/events/"
        
        # ヘッダー設定
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

        # APIキーがある場合は認証ヘッダーを追加
        # connpass APIは通常、X-API-Keyヘッダーまたはクエリパラメータで認証
        if config.CONNPASS_API_KEY:
            headers["X-API-Key"] = config.CONNPASS_API_KEY
            masked_key = config.CONNPASS_API_KEY[:8] + "..." if len(config.CONNPASS_API_KEY) > 8 else "***"
            print(f"🔑 APIキー設定済み: {masked_key}")
        else:
            print("⚠️  Warning: CONNPASS_API_KEY is missing.")

        # キーワード条件: ("データ") and ("メルカリ" or "LINE")
        # 場所条件: 東京都、神奈川県、オンラインの3つのOR条件
        # connpass APIではaddressパラメータを複数回指定することでOR条件で検索可能
        
        # パラメータを構築（addressを複数回指定するためリスト形式で準備）
        params = {
            "keyword": "データ",
            "keyword_or": "メルカリ,LINE",
            "count": 50,
            "order": 2,  # 更新日時順
        }
        
        # addressパラメータを複数回指定するため、URLを手動で構築
        # または、3つのリクエストに分けて実行してマージする方法を採用
        # （APIの仕様により、複数のaddressを一度に指定できない可能性があるため）
        
        all_events = []
        seen_event_ids = set()
        
        # リクエスト間隔（秒） - レート制限を避けるため
        REQUEST_DELAY = 2
        
        print(f"🔍 Connpass API検索開始: keyword='データ', keyword_or='メルカリ,LINE'")
        
        # 1. 東京都のイベントを取得
        print("📍 東京都のイベントを検索中...")
        params_tokyo = params.copy()
        params_tokyo["address"] = "東京都"
        events_tokyo = self._fetch_events_from_api(url, params_tokyo, headers, seen_event_ids)
        print(f"   取得件数: {len(events_tokyo)}件")
        all_events.extend(events_tokyo)
        time.sleep(REQUEST_DELAY)  # リクエスト間隔を空ける
        
        # 2. 神奈川県のイベントを取得
        print("📍 神奈川県のイベントを検索中...")
        params_kanagawa = params.copy()
        params_kanagawa["address"] = "神奈川県"
        events_kanagawa = self._fetch_events_from_api(url, params_kanagawa, headers, seen_event_ids)
        print(f"   取得件数: {len(events_kanagawa)}件")
        all_events.extend(events_kanagawa)
        time.sleep(REQUEST_DELAY)  # リクエスト間隔を空ける
        
        # 3. オンラインイベントを取得
        print("📍 オンラインイベントを検索中...")
        params_online = params.copy()
        params_online["address"] = "オンライン"
        events_online = self._fetch_events_from_api(url, params_online, headers, seen_event_ids)
        print(f"   取得件数: {len(events_online)}件")
        all_events.extend(events_online)
        
        print(f"📊 合計取得件数（フィルタ前）: {len(all_events)}件")
        filtered_events = self._filter_events(all_events)
        print(f"📅 日付フィルタ後: {len(filtered_events)}件")
        
        return filtered_events
    
    def _fetch_events_from_api(self, url, params, headers, seen_event_ids, max_retries=3):
        """APIからイベントを取得し、重複を除外する（リトライ機能付き）"""
        request_params = params.copy()
        if config.CONNPASS_API_KEY and "X-API-Key" in headers:
            # クエリパラメータとしても追加（APIの仕様により異なる可能性があるため）
            request_params["key"] = config.CONNPASS_API_KEY
        
        for attempt in range(max_retries):
            try:
                res = requests.get(url, params=request_params, headers=headers, timeout=10)
                
                # ステータスコードを確認
                if res.status_code == 404:
                    print(f"⚠️  404エラー: エンドポイントが見つかりません")
                    print(f"   URL: {url}")
                    print(f"   パラメータ: {request_params}")
                    print(f"   レスポンス: {res.text[:500]}")
                    return []
                
                # 429エラー（レート制限）の場合はリトライ
                if res.status_code == 429:
                    if attempt < max_retries - 1:
                        wait_time = (attempt + 1) * 5  # 5秒、10秒、15秒と段階的に待機
                        print(f"⚠️  429エラー（レート制限）: {wait_time}秒待機してリトライします... (試行 {attempt + 1}/{max_retries})")
                        time.sleep(wait_time)
                        continue
                    else:
                        print(f"❌ HTTPエラー (ステータスコード: 429) - リトライ上限に達しました")
                        print(f"   パラメータ: {params}")
                        print(f"   レスポンス: {res.text[:500]}")
                        return []
                
                res.raise_for_status()
                
                raw_events = res.json().get("events", [])
                print(f"   ✅ API成功: {len(raw_events)}件のイベントを取得")
                
                # 重複を除外
                unique_events = []
                duplicate_count = 0
                for ev in raw_events:
                    # connpass API v2では 'id' フィールドを使用
                    eid = ev.get("id") or ev.get("event_id")
                    if not eid:
                        print(f"   ⚠️  IDが存在しないイベント: {ev.get('title', 'N/A')[:30]}")
                        continue
                    
                    if eid not in seen_event_ids:
                        seen_event_ids.add(eid)
                        unique_events.append(ev)
                    else:
                        duplicate_count += 1
                        if duplicate_count <= 3:  # 最初の3件の重複のみ表示
                            print(f"   🔄 重複スキップ: id={eid}, title={ev.get('title', 'N/A')[:30]}")
                
                if duplicate_count > 0:
                    print(f"   ℹ️  重複除外: {len(raw_events)}件 → {len(unique_events)}件 (重複: {duplicate_count}件)")
                else:
                    print(f"   ℹ️  重複なし: {len(raw_events)}件")
                
                return unique_events
                
            except requests.exceptions.HTTPError as e:
                if res.status_code == 429 and attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 5
                    print(f"⚠️  429エラー（レート制限）: {wait_time}秒待機してリトライします... (試行 {attempt + 1}/{max_retries})")
                    time.sleep(wait_time)
                    continue
                else:
                    print(f"❌ HTTPエラー (ステータスコード: {res.status_code})")
                    print(f"   パラメータ: {params}")
                    print(f"   レスポンス: {res.text[:500]}")
                    return []
            except Exception as e:
                print(f"❌ Connpass API error (params: {params}): {e}")
                if 'res' in locals():
                    print(f"   レスポンス: {res.text[:200]}")
                return []
        
        return []  # すべてのリトライが失敗した場合

    def _filter_events(self, events):
        """日付範囲でフィルタリング"""
        filtered = []
        now = datetime.now(timezone(timedelta(hours=9)))
        target_end = now + timedelta(days=config.TECH_CONFIG["DAYS_AHEAD"])
        
        print(f"📅 日付フィルタ: 現在={now.strftime('%Y-%m-%d %H:%M:%S')}, 終了日={target_end.strftime('%Y-%m-%d %H:%M:%S')}")

        for ev in events:
            try:
                start = datetime.fromisoformat(ev["started_at"].replace("Z", "+00:00"))
                if now <= start <= target_end:
                    filtered.append(ev)
                else:
                    print(f"   ⏭️  除外: {ev.get('title', 'N/A')[:30]}... (開始日時: {start.strftime('%Y-%m-%d %H:%M')})")
            except Exception as e:
                print(f"   ❌ 日付パースエラー (id: {ev.get('id') or ev.get('event_id')}): {e}")
                continue
        
        return filtered

    def _get_event_url(self, ev):
        """イベントのURLを安全に取得する。なければ event_id から構築する。"""
        if not isinstance(ev, dict):
            return None
        # まず標準フィールド
        url = ev.get("event_url") or ev.get("eventUrl") or ev.get("url")
        if url:
            return url
        # フォールバック: id または event_id から構築
        eid = ev.get("id") or ev.get("event_id")
        if eid:
            try:
                return f"https://connpass.com/event/{int(eid)}/"
            except Exception:
                return f"https://connpass.com/event/{eid}/"
        return None

    def create_message(self, events):
        if not events: return None
        
        blocks = [
            {"type": "header", "text": {"type": "plain_text", "text": "📚 データ系勉強会Pickup", "emoji": True}},
            {"type": "divider"}
        ]
        
        for ev in events[:10]:
            try:
                # 日付のパース処理を統一
                started_at = ev.get("started_at", "").replace("Z", "+00:00")
                start = datetime.fromisoformat(started_at).strftime("%m/%d %H:%M") if started_at else "日時不明"
            except Exception as e:
                print(f"Error parsing date in create_message for event {ev.get('id') or ev.get('event_id')}: {e}")
                start = "日時不明"
            
            limit = ev.get("limit")
            accepted = ev.get("accepted", 0)
            status = "🔴満席" if limit and accepted >= limit else "🟢"

            title = ev.get('title', 'タイトル不明')
            url = self._get_event_url(ev)
            if url:
                title_text = f"<{url}|{title}>"
            else:
                title_text = title

            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*{start}* {status} {title_text}\n主催: {ev.get('owner_display_name') or '不明'}"
                }
            })
            blocks.append({"type": "divider"})
            
        return {"blocks": blocks}