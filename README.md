# Daily Event Notification Bot
データ系勉強会情報と横浜アリーナのイベント・混雑予測をSlackに通知するBotです。

# 機能
- Connpass: データ分析、機械学習関連の勉強会を検索
- 横浜アリーナ: 公式サイトから本日のイベントを取得し、Gemini APIで混雑レベルを予測

# 設定

## GitHub Secrets（本番環境）
以下のシークレットを設定してください。
- SLACK_WEBHOOK_TECH: 勉強会用チャンネルのWebhook URL
- SLACK_WEBHOOK_LIFE: 雑談・生活用チャンネルのWebhook URL
- GEMINI_API_KEY: Google Gemini APIキー
- CONNPASS_API_KEY: connpass APIキー（オプション）

## ローカル環境での設定

### 方法1: .envファイルを使用（推奨）

プロジェクトルートに`.env`ファイルを作成し、以下のように設定してください：

```bash
# .envファイル
SLACK_WEBHOOK_TECH=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
SLACK_WEBHOOK_LIFE=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
GEMINI_API_KEY=your_gemini_api_key_here
CONNPASS_API_KEY=your_connpass_api_key_here
```

`.env`ファイルは`.gitignore`に含まれているため、Gitにコミットされません。

### 方法2: 環境変数として直接設定

```bash
# macOS/Linux
export CONNPASS_API_KEY="your_connpass_api_key_here"
export GEMINI_API_KEY="your_gemini_api_key_here"
export SLACK_WEBHOOK_TECH="https://hooks.slack.com/services/YOUR/WEBHOOK/URL"
export SLACK_WEBHOOK_LIFE="https://hooks.slack.com/services/YOUR/WEBHOOK/URL"

# Windows (PowerShell)
$env:CONNPASS_API_KEY="your_connpass_api_key_here"
$env:GEMINI_API_KEY="your_gemini_api_key_here"
$env:SLACK_WEBHOOK_TECH="https://hooks.slack.com/services/YOUR/WEBHOOK/URL"
$env:SLACK_WEBHOOK_LIFE="https://hooks.slack.com/services/YOUR/WEBHOOK/URL"
```

# ローカルでの実行

```bash
# 依存関係のインストール
pip install -r requirements.txt

# メインスクリプトの実行
python main.py

# 検証スクリプトの実行（connpass APIの動作確認）
python test_connpass_api.py
```
