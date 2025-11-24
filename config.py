import os

# --- Slack Webhook URLs ---
SLACK_WEBHOOK_TECH = os.environ.get("SLACK_WEBHOOK_TECH")   # 勉強会用
SLACK_WEBHOOK_LIFE = os.environ.get("SLACK_WEBHOOK_LIFE")   # 混雑情報用

# --- Gemini API Key ---
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# --- データ系勉強会の設定 ---
TECH_CONFIG = {
    # 検索キーワード
    "KEYWORDS": ["データ分析", "機械学習", "Deep Learning", "Kaggle", "SQL", "Python", "生成AI"],
    # 開催場所フィルタ（これらが含まれるものを抽出）
    "LOCATIONS": ["東京都", "オンライン", "Zoom", "Youtube"],
    # 何日先まで検索するか
    "DAYS_AHEAD": 7,
}

# --- 横浜アリーナの設定 ---
YOKOARI_CONFIG = {
    "BASE_URL": "https://www.yokohama-arena.co.jp/event/",
}
