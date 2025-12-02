import warnings
import sys
import os

# importlib.metadataのエラーを抑制（Python 3.9の互換性問題）
warnings.filterwarnings('ignore', category=DeprecationWarning)
warnings.filterwarnings('ignore', message='.*importlib.metadata.*')

# google-generativeaiのインポート時のエラーメッセージを抑制
# エラーメッセージはprintで出力されるため、stdout/stderrを一時的にリダイレクト
class SuppressOutput:
    def __init__(self):
        self.stdout = sys.stdout
        self.stderr = sys.stderr
        
    def __enter__(self):
        sys.stdout = open(os.devnull, 'w')
        sys.stderr = open(os.devnull, 'w')
        return self
        
    def __exit__(self, *args):
        sys.stdout.close()
        sys.stderr.close()
        sys.stdout = self.stdout
        sys.stderr = self.stderr

# google-generativeaiのインポート時のエラーを抑制
with SuppressOutput():
    try:
        import google.generativeai as genai
    except:
        pass

import config
from sources.connpass import ConnpassSource
from sources.yokoari import YokoariSource

def main():
    print("--- Batch Start ---")
    
    # 実行するソースのリスト
    sources = [
        # データ系勉強会 -> Techチャンネル
        ConnpassSource(webhook_url=config.SLACK_WEBHOOK_TECH),
        
        # 横アリ混雑情報 -> Lifeチャンネル
        YokoariSource(webhook_url=config.SLACK_WEBHOOK_LIFE)
    ]

    for source in sources:
        try:
            print(f"Processing {source.__class__.__name__}...")
            events = source.fetch_events()
            
            if events:
                print(f"  -> Found {len(events)} events.")
                payload = source.create_message(events)
                source.send_notification(payload)
            else:
                print("  -> No events found.")
                
        except Exception as e:
            print(f"Error in {source.__class__.__name__}: {e}")
            
    print("--- Batch End ---")

if __name__ == "__main__":
    main()
