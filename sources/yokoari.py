from datetime import datetime, timezone, timedelta
import requests
from bs4 import BeautifulSoup
from .base import BaseEventSource
import config

# YokoariSource: 横浜アリーナのスケジュール（/schedule/）を取得するソース
# - まず requests+BeautifulSoup で table#calbox を探す
# - 見つからない場合は Playwright でレンダリングして DOM を取得するフォールバックあり
class YokoariSource(BaseEventSource):
    LIST_URL = "https://www.yokohama-arena.co.jp/schedule/"

    def fetch_events(self):
        # 軽量にまず requests で試す
        try:
            res = requests.get(self.LIST_URL, timeout=15)
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

        # フォールバック: Playwright でレンダリングして取得
        try:
            from playwright.sync_api import sync_playwright
        except Exception as e:
            print("   ❌ Playwright をインポートできません。インストールしてください（pip install playwright）。詳細:", e)
            return []

        try:
            with sync_playwright() as pw:
                browser = pw.chromium.launch(headless=True)
                page = browser.new_page()
                page.goto(self.LIST_URL, wait_until="networkidle", timeout=30000)
                # 必要であればスクロールやボタン操作を追加
                content = page.content()
                browser.close()

            events = self._parse_table_from_html(content)
            if events:
                print(f"   ✅ Headless でレンダリングして取得: {len(events)}件")
                return self._filter_events(events)
            else:
                print("   ⚠️ レンダリング後でもイベント行が見つかりません。印刷で作られるコンテンツが別生成されている可能性があります。")
                return []
        except Exception as e:
            print(f"   ❌ Playwright 実行中にエラー: {e}")
            return []

    def _parse_table_from_html(self, html):
        """HTMLから<table id='calbox'> をパースしてイベントリストを返す。
           期待されるカラム: 日付, イベント名, 開場, 開演, 終演
        """
        soup = BeautifulSoup(html, "html.parser")
        table = soup.find("table", id="calbox")
        if not table:
            return []

        rows = table.find_all("tr")
        data_rows = []
        # ヘッダを除いてパース
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
        """簡易フィルタ。date_text から started_at を構築するロジックを追加してください。"""
        filtered = []
        now = datetime.now(timezone(timedelta(hours=9)))
        target_end = now + timedelta(days=config.TECH_CONFIG.get("DAYS_AHEAD", 7))

        for ev in events:
            # 現時点では started_at を作成していないため一旦全件含める。
            # 必要であれば date_text と start を解析して started_at を作成し、
            # 現在日時範囲でフィルタしてください。
            filtered.append(ev)

        return filtered