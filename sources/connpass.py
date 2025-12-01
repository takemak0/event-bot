from datetime import datetime, timedelta, timezone
import requests
from .base import BaseEventSource
import config

class ConnpassSource(BaseEventSource):
    def fetch_events(self):
        # ここにAPIのURLを明示的に記述します
        url = "https://connpass.com/api/v1/event/"
        
        keywords = config.TECH_CONFIG["KEYWORDS"]
        params = {
            "keyword": ",".join(keywords),
            "count": 50,
            "order": 2, # 開催日時順
        }
        
        try:
            # APIリクエストを実行
            res = requests.get(url, params=params)
            res.raise_for_status()
            
            # レスポンスからイベントリストを取得
            raw_events = res.json().get("events", [])
            
            # フィルタリング処理へ
            return self._filter_events(raw_events)
        except Exception as e:
            print(f"Connpass error: {e}")
            return []

    def _filter_events(self, events):
        filtered = []
        # JST (日本標準時) で現在時刻を取得
        now = datetime.now(timezone(timedelta(hours=9)))
        target_end = now + timedelta(days=config.TECH_CONFIG["DAYS_AHEAD"])
        locations = config.TECH_CONFIG["LOCATIONS"]

        seen = set()
        for ev in events:
            eid = ev["event_id"]
            if eid in seen: continue
            
            # 日付チェック
            try:
                start = datetime.fromisoformat(ev["started_at"])
                # 開催期間外ならスキップ
                if not (now <= start <= target_end): continue
            except: continue

            # 場所チェック (設定がある場合のみ)
            if locations:
                place = str(ev.get("place") or "")
                addr = str(ev.get("address") or "")
                # 設定された場所キーワードが、場所名か住所のどちらかに含まれているか確認
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
        
        # Slackの見やすさのため最大10件に絞る
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
