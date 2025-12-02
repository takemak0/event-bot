from datetime import datetime, timedelta, timezone
import requests
from .base import BaseEventSource
import config

class ConnpassSource(BaseEventSource):
    def fetch_events(self):
        # v2エンドポイントに変更
        url = "https://connpass.com/api/v2/event/"
        
        keywords = config.TECH_CONFIG["KEYWORDS"]
        params = {
            "keyword": ",".join(keywords),
            "count": 50,
            "order": 2,
        }
        
        # ヘッダー設定
        headers = {
            # 一般的なブラウザ偽装（念の為残します）
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

        # APIキーがある場合は認証ヘッダーを追加
        if config.CONNPASS_API_KEY:
            # 【重要】ドキュメントの指定に合わせて "Bearer" の部分を調整してください
            headers["Authorization"] = f"Bearer {config.CONNPASS_API_KEY}"
        else:
            print("Warning: CONNPASS_API_KEY is missing.")

        try:
            res = requests.get(url, params=params, headers=headers)
            res.raise_for_status()
            
            raw_events = res.json().get("events", [])
            return self._filter_events(raw_events)
        except Exception as e:
            print(f"Connpass error: {e}")
            if 'res' in locals():
                 print(f"Response content: {res.text[:200]}")
            return []

    def _filter_events(self, events):
        filtered = []
        now = datetime.now(timezone(timedelta(hours=9)))
        target_end = now + timedelta(days=config.TECH_CONFIG["DAYS_AHEAD"])
        locations = config.TECH_CONFIG["LOCATIONS"]

        seen = set()
        for ev in events:
            eid = ev["event_id"]
            if eid in seen: continue
            
            try:
                start = datetime.fromisoformat(ev["started_at"])
                if not (now <= start <= target_end): continue
            except: continue

            if locations:
                place = str(ev.get("place") or "")
                addr = str(ev.get("address") or "")
                if not any(loc in place or loc in addr for loc in locations):
                    continue
            
            seen.add(eid)
            filtered.append(ev)
        return filtered

    def create_message(self, events):
        if not events: return None
        
        blocks = [
            {"type": "header", "text": {"type": "plain_text", "text": "📚 データ系勉強会Pickup", "emoji": True}},
            {"type": "divider"}
        ]
        
        for ev in events[:10]:
            start = datetime.fromisoformat(ev["started_at"]).strftime("%m/%d %H:%M")
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