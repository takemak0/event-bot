import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta, timezone
import re
import google.generativeai as genai
from .base import BaseEventSource
import config

class YokoariSource(BaseEventSource):
    def __init__(self, webhook_url):
        super().__init__(webhook_url)
        # Gemini APIの初期化
        if config.GEMINI_API_KEY:
            genai.configure(api_key=config.GEMINI_API_KEY)
            self.model = genai.GenerativeModel('gemini-2.0-flash')
        else:
            self.model = None
            print("Warning: GEMINI_API_KEY is not set.")

    def fetch_events(self):
        # JSTで現在時刻を取得
        jst = timezone(timedelta(hours=9))
        now = datetime.now(jst)
        
        # URL生成 (例: .../event/2025-11)
        target_url = f"{config.YOKOARI_CONFIG['BASE_URL']}{now.strftime('%Y-%m')}"
        
        try:
            res = requests.get(target_url)
            res.raise_for_status()
            soup = BeautifulSoup(res.content, 'lxml')
            
            events = []
            rows = soup.find_all('tr')
            
            for row in rows:
                cells = row.find_all(['td', 'th'])
                if len(cells) < 4: continue
                
                date_text = cells[0].get_text(strip=True)
                title_text = cells[1].get_text(strip=True)
                open_time = cells[2].get_text(strip=True)
                start_time = cells[3].get_text(strip=True)
                
                if "設営日" in title_text or "イベント名" in title_text: continue
                
                # 日付の一致確認 "22(土)" -> 22
                day_match = re.search(r'(\d+)', date_text)
                if not day_match: continue
                
                event_day = int(day_match.group(1))
                
                # 今日ならリストに追加
                if event_day == now.day:
                    events.append({
                        "date": now.strftime("%Y-%m-%d"),
                        "title": title_text,
                        "open_time": open_time,
                        "start_time": start_time,
                        "url": target_url
                    })
            return events

        except Exception as e:
            print(f"Yokoari Scraping Error: {e}")
            return []

    def _analyze_congestion_ai(self, event_title, start_time):
        if not self.model: return None

        prompt = f"""
        あなたはイベント会場（横浜アリーナ）の混雑予測AIです。
        以下のイベント情報に基づいて、新横浜駅周辺の混雑レベルと予測理由を簡潔に答えてください。
        
        イベント名: {event_title}
        開演時間: {start_time}
        
        出力フォーマット（JSONのみ、Markdownなどの装飾なし）:
        {{
            "level": "Lv.1(閑散)〜Lv.5(激混み)のいずれか",
            "peak_time": "混雑のピーク時間帯（文字列）",
            "reason": "予測の理由（30文字以内）"
        }}
        """
        try:
            response = self.model.generate_content(prompt)
            import json
            text = response.text.strip()
            text = re.sub(r'^```json\s*', '', text)
            text = re.sub(r'^```\s*', '', text)
            text = re.sub(r'\s*```$', '', text)
            return json.loads(text)
        except Exception as e:
            print(f"Gemini API Error: {e}")
            return None

    def create_message(self, events):
        if not events: return None

        blocks = [
            {"type": "header", "text": {"type": "plain_text", "text": "🏟️ 今日の横浜アリーナ イベント情報", "emoji": True}},
            {"type": "divider"}
        ]

        for ev in events:
            ai_prediction = self._analyze_congestion_ai(ev['title'], ev['start_time'])
            
            if ai_prediction:
                congestion_info = (
                    f"🤖 *AI混雑予測*: `{ai_prediction['level']}`\n"
                    f"⏰ *ピーク予想*: {ai_prediction['peak_time']}\n"
                    f"📝 *理由*: {ai_prediction['reason']}"
                )
            else:
                congestion_info = "AI予測: 利用不可 (APIキー未設定など)"

            text = (
                f"🎤 *{ev['title']}*\n"
                f"🚪 開場: {ev['open_time']} / 🎸 開演: {ev['start_time']}\n"
                f"----------------------------\n"
                f"{congestion_info}\n"
                f"----------------------------\n"
                f"🔗 <{ev['url']}|公式サイトで確認>"
            )
            
            blocks.append({
                "type": "section",
                "text": {"type": "mrkdwn", "text": text}
            })
        
        return {"blocks": blocks}
