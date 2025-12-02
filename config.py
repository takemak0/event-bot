import os
from pathlib import Path

# .envファイルを読み込む（ローカル開発用）
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent / '.env'
    if env_path.exists():
        load_dotenv(env_path, override=True)  # override=Trueで環境変数を上書き
    # .envファイルが存在しない場合は環境変数のみを使用
except ImportError:
    # python-dotenvがインストールされていない場合はスキップ
    # 環境変数のみを使用
    pass

# --- Slack Webhook URLs ---
SLACK_WEBHOOK_TECH = os.environ.get("SLACK_WEBHOOK_TECH")
SLACK_WEBHOOK_LIFE = os.environ.get("SLACK_WEBHOOK_LIFE")

# --- API Keys ---
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
CONNPASS_API_KEY = os.environ.get("CONNPASS_API_KEY")

# --- データ系勉強会の設定 ---
TECH_CONFIG = {
    "KEYWORDS": ["データ分析", "機械学習", "Deep Learning", "Kaggle", "SQL", "Python", "生成AI"],
    "LOCATIONS": ["東京都", "オンライン", "神奈川県"],
    "DAYS_AHEAD": 31,
}

# --- 横浜アリーナの設定 ---
YOKOARI_CONFIG = {
    "BASE_URL": "https://www.yokohama-arena.co.jp/event/",
}
