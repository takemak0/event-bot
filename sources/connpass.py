from datetime import datetime, timedelta, timezone
import requests
from .base import BaseEventSource
import config

class ConnpassSource(BaseEventSource):
    def fetch_events(self):
        # v2エンドポイント
        url = "https://connpass.com/api/v2/event/"
        
        # ヘッダー設定
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

        # APIキーがある場合は認証ヘッダーを追加
        if config.CONNPASS_API_KEY:
            headers["Authorization"] = f"Bearer {config.CONNPASS_API_KEY}"
        else:
            print("Warning: CONNPASS_API_KEY is missing.")

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
        
        # 1. 東京都のイベントを取得
        params_tokyo = params.copy()
        params_tokyo["address"] = "東京都"
        events_tokyo = self._fetch_events_from_api(url, params_tokyo, headers, seen_event_ids)
        all_events.extend(events_tokyo)
        
        # 2. 神奈川県のイベントを取得
        params_kanagawa = params.copy()
        params_kanagawa["address"] = "神奈川県"
        events_kanagawa = self._fetch_events_from_api(url, params_kanagawa, headers, seen_event_ids)
        all_events.extend(events_kanagawa)
        
        # 3. オンラインイベントを取得
        params_online = params.copy()
        params_online["address"] = "オンライン"
        events_online = self._fetch_events_from_api(url, params_online, headers, seen_event_ids)
        all_events.extend(events_online)
        
        return self._filter_events(all_events)
    
    def _fetch_events_from_api(self, url, params, headers, seen_event_ids):
        """APIからイベントを取得し、重複を除外する"""
        try:
            res = requests.get(url, params=params, headers=headers, timeout=10)
            res.raise_for_status()
            
            raw_events = res.json().get("events", [])
            # 重複を除外
            unique_events = []
            for ev in raw_events:
                eid = ev.get("event_id")
                if eid and eid not in seen_event_ids:
                    seen_event_ids.add(eid)
                    unique_events.append(ev)
            
            return unique_events
        except Exception as e:
            print(f"Connpass API error (params: {params}): {e}")
            if 'res' in locals():
                print(f"Response content: {res.text[:200]}")
            return []

    def _filter_events(self, events):
        """日付範囲でフィルタリング"""
        filtered = []
        now = datetime.now(timezone(timedelta(hours=9)))
        target_end = now + timedelta(days=config.TECH_CONFIG["DAYS_AHEAD"])

        for ev in events:
            try:
                start = datetime.fromisoformat(ev["started_at"].replace("Z", "+00:00"))
                if now <= start <= target_end:
                    filtered.append(ev)
            except Exception as e:
                print(f"Error parsing date for event {ev.get('event_id')}: {e}")
                continue
        
        return filtered

    def create_message(self, events):
        if not events: return None
        
        blocks = [
            {"type": "header", "text": {"type": "plain_text", "text": "📚 データ系勉強会Pickup", "emoji": True}},
            {"type": "divider"}
        ]
        
        for ev in events[:10]:
            try:
                # 日付のパース処理を統一
                started_at = ev["started_at"].replace("Z", "+00:00")
                start = datetime.fromisoformat(started_at).strftime("%m/%d %H:%M")
            except Exception as e:
                print(f"Error parsing date in create_message for event {ev.get('event_id')}: {e}")
                start = "日時不明"
            
            limit = ev.get("limit")
            accepted = ev.get("accepted", 0)
            status = "🔴満席" if limit and accepted >= limit else "🟢"
            
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*{start}* {status} <{ev['event_url']}|{ev['title']}>\n主催: {ev.get('owner_display_name')}"
                }
            })
            blocks.append({"type": "divider"})
            
        return {"blocks": blocks}