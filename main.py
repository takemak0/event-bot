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
