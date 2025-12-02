import os

# --- Slack Webhook URLs ---
SLACK_WEBHOOK_TECH = os.environ.get("SLACK_WEBHOOK_TECH")
SLACK_WEBHOOK_LIFE = os.environ.get("SLACK_WEBHOOK_LIFE")

# --- API Keys ---
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
CONNPASS_API_KEY = os.environ.get("CONNPASS_API_KEY") # 追加

# --- データ系勉強会の設定 ---
TECH_CONFIG = {
    "KEYWORDS": ["データ分析", "機械学習", "Deep Learning", "Kaggle", "SQL", "Python", "生成AI"],
    "LOCATIONS": ["東京都", "オンライン", "Zoom", "Youtube"],
    "DAYS_AHEAD": 7,
}

# --- 横浜アリーナの設定 ---
YOKOARI_CONFIG = {
    "BASE_URL": "https://www.yokohama-arena.co.jp/event/",
}
