from datetime import datetime, timezone, timedelta
import requests
from bs4 import BeautifulSoup
from .base import BaseEventSource
import config

class YokoariSource(BaseEventSource):
    def fetch_events(self):
        # 今月のスケジュールページURLを生成
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

        # Playwright フォールバック
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
                "event_url": None,
            }
            data_rows.append(ev)
        return data_rows

    def _filter_events(self, events):
        # 必要に応じて日付で絞り込み（当日分だけなど）
        filtered = []
        now = datetime.now(timezone(timedelta(hours=9)))
        for ev in events:
            # 例: date_textが "12月20日" みたいな場合、今日と一致だけ通す
            dtxt = ev.get("date_text", "")
            if f"{now.month}月{now.day}日" in dtxt:
                filtered.append(ev)
        # もし全件欲しい場合は return events
        return filtered

    def create_message(self, events):
        if not events:
            return None
        blocks = [
            {"type": "header", "text": {"type": "plain_text", "text": "📍 横浜アリーナ 予定ピックアップ", "emoji": True}},
            {"type": "divider"}
        ]
        for ev in events[:10]:
            title = ev.get("title") or "タイトル不明"
            date_text = ev.get("date_text") or ""
            start_time = ev.get("start") or ""
            end_time = ev.get("end") or ""
            url = ev.get("event_url")
            time_parts = [p for p in (date_text, start_time and f"開演 {start_time}", end_time and f"終演 {end_time}") if p]
            time_text = " · ".join(time_parts) if time_parts else "日時不明"
            title_text = f"<{url}|{title}>" if url else title
            blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": f"*{time_text}*  {title_text}\n会場: 横浜アリーナ"}})
            blocks.append({"type": "divider"})
        return {"blocks": blocks}