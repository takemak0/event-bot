# Daily Event Notification Bot
データ系勉強会情報と横浜アリーナのイベント・混雑予測をSlackに通知するBotです。

# 機能
- Connpass: データ分析、機械学習関連の勉強会を検索
- 横浜アリーナ: 公式サイトから本日のイベントを取得し、Gemini APIで混雑レベルを予測

# 設定 (GitHub Secrets)
以下のシークレットを設定してください。
- SLACK_WEBHOOK_TECH: 勉強会用チャンネルのWebhook URL
- SLACK_WEBHOOK_LIFE: 雑談・生活用チャンネルのWebhook URL
- GEMINI_API_KEY: Google Gemini APIキー

# ローカルでの実行
```
pip install -r requirements.txt
python main.py
```
