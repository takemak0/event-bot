from datetime import datetime, timezone, timedelta
import requests
from bs4 import BeautifulSoup
from .base import BaseEventSource
import config
import re
import google.generativeai as genai  # ★ 追加


class YokoariSource(BaseEventSource):
    def __init__(self, webhook_url):
        # BaseEventSource 側の初期化（webhook_url 保持）
        super().__init__(webhook_url)

        # ★ Gemini API の初期化（旧実装を復活）
        if getattr(config, "GEMINI_API_KEY", None):
            genai.configure(api_key=config.GEMINI_API_KEY)
            # モデル名は旧コードと同じ
            self.model = genai.GenerativeModel("gemini-2.5-flash")
        else:
            self.model = None
            print("Warning: GEMINI_API_KEY is not set.")

    def fetch_events(self):
        # 今月のスケジュールページURLを生成（現行ロジックをそのまま利用）
        now = datetime.now(timezone(timedelta(hours=9)))
        schedule_url = f"https://www.yokohama-arena.co.jp/event/{now.year}-{now.month:02d}"
        print(f"横浜アリーナスケジュールURL: {schedule_url}")

        # まず requests で取得
        try:
            res = requests.get(schedule_url, timeout=15)
            res.raise_for_status()
            html = res.text
            events = self._parse_table_from_html(html)
            if events:
                print(f"   ✅ ページソースから取得: {len(events)}件")
                return self._filter_events(events)
            else:
                print("   ⚠️ ページソースにイベント行が見つかりません。JSで描画されている可能性があります。")
        except Exception as e:
            print(f"   ❌ requests でページ取得失敗: {e}")

        # Playwright フォールバック（現行ロジックをそのまま利用）
        try:
            from playwright.sync_api import sync_playwright
        except Exception as e:
            print("   ❌ Playwright をインポートできません。pip install playwright が必要です。詳細:", e)
            return []

        try:
            with sync_playwright() as pw:
                browser = pw.chromium.launch(headless=True)
                page = browser.new_page()
                page.goto(schedule_url, wait_until="networkidle", timeout=30000)
                content = page.content()
                browser.close()

            events = self._parse_table_from_html(content)
            if events:
                print(f"   ✅ Headless でレンダリングして取得: {len(events)}件")
                return self._filter_events(events)
            else:
                print("   ⚠️ レンダリング後でもイベント行が見つかりません。")
                return []
        except Exception as e:
            print(f"   ❌ Playwright 実行中にエラー: {e}")
            return []

    def _parse_table_from_html(self, html):
        soup = BeautifulSoup(html, "html.parser")
        table = soup.find("table", id="calbox")
        if not table:
            return []

        rows = table.find_all("tr")
        data_rows = []
        for tr in rows[1:]:
            cols = [td.get_text(strip=True) for td in tr.find_all(["td", "th"])]
            if not cols or len(cols) < 2:
                continue
            date_text = cols[0] if len(cols) > 0 else ""
            title = cols[1] if len(cols) > 1 else ""
            open_time = cols[2] if len(cols) > 2 else ""
            start_time = cols[3] if len(cols) > 3 else ""
            end_time = cols[4] if len(cols) > 4 else ""

            ev = {
                "title": title,
                "date_text": date_text,
                "open": open_time,
                "start": start_time,
                "end": end_time,
                "event_url": None,  # 公式URLが取れるならここに詰める
            }
            data_rows.append(ev)
        return data_rows

    def _filter_events(self, events):
        """date_text が「7(日)」や「12/7(日)」などでも、今日 (JST) のイベントを抽出できるようにする"""
        filtered = []
        now = datetime.now(timezone(timedelta(hours=9)))
        today_day = now.day
        for ev in events:
            dtxt = ev.get("date_text", "")
            # 「7(日)」や「12/7(日)」などから先頭の数字（=日）を抽出
            m = re.match(r"(?:(\d{1,2})/)?(\d{1,2})[（(]?", dtxt)  # 12/7(日)や 7(日)
            if m:
                month, day = m.groups()
                if not month or int(month) == now.month:  # 月指定なければ今月想定
                    if int(day) == today_day:
                        filtered.append(ev)
        return filtered

    # ★ ここから混雑予測（旧実装の復活＋キー名だけ現行に合わせている）
    def _analyze_congestion_ai(self, event_title: str, start_time: str):
        """Gemini にイベント名と開演時間を渡して混雑レベルなどを予測させる。"""
        if not self.model:
            return None

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
            # モデルが ```json で囲って返してしまうパターンに対応
            text = re.sub(r"^```json\s*", "", text)
            text = re.sub(r"^```\s*", "", text)
            text = re.sub(r"\s*```$", "", text)

            return json.loads(text)
        except Exception as e:
            print(f"Gemini API Error: {e}")
            return None

    def create_message(self, events):
        if not events:
            return None

        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "📍 横浜アリーナ 予定ピックアップ",
                    "emoji": True,
                },
            },
            {"type": "divider"},
        ]

        for ev in events[:10]:
            title = ev.get("title") or "タイトル不明"
            date_text = ev.get("date_text") or ""
            start_time = ev.get("start") or ""
            end_time = ev.get("end") or ""
            url = ev.get("event_url")

            # ★ ここで AI 混雑予測を呼ぶ（旧 create_message のロジックを移植）
            ai_prediction = self._analyze_congestion_ai(title, start_time)

            if ai_prediction:
                congestion_info = (
                    f"*AI混雑予測*: `{ai_prediction['level']}`\n"
                    f"⏰ *ピーク予想*: {ai_prediction['peak_time']}\n"
                    f"*理由*: {ai_prediction['reason']}"
                )
            else:
                congestion_info = "AI予測: 利用不可 (APIキー未設定など)"

            time_parts = [
                p
                for p in (
                    date_text,
                    start_time and f"開演 {start_time}",
                    end_time and f"終演 {end_time}",
                )
                if p
            ]
            time_text = " · ".join(time_parts) if time_parts else "日時不明"
            title_text = f"<{url}|{title}>" if url else title

            # 本文に混雑予測を追加
            body_lines = [
                f"*{time_text}*  {title_text}",
                "会場: 横浜アリーナ",
                "----------------------------",
                congestion_info,
            ]
            body_text = "\n".join(body_lines)

            blocks.append(
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": body_text},
                }
            )
            blocks.append({"type": "divider"})

        return {"blocks": blocks}