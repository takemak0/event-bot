from abc import ABC, abstractmethod
import requests
import json

class BaseEventSource(ABC):
    def __init__(self, webhook_url):
        self.webhook_url = webhook_url

    @abstractmethod
    def fetch_events(self):
        """イベント情報を取得してリストで返す"""
        pass

    @abstractmethod
    def create_message(self, events):
        """Slack送信用のメッセージペイロードを作成する"""
        pass

    def send_notification(self, payload):
        """Slackに通知を送る共通メソッド"""
        if not payload:
            return

        if not self.webhook_url:
            print(f"Warning: Webhook URL not set for {self.__class__.__name__}")
            return

        try:
            response = requests.post(
                self.webhook_url,
                data=json.dumps(payload),
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            print(f"Message sent from {self.__class__.__name__}")
        except requests.exceptions.RequestException as e:
            print(f"Error sending to Slack: {e}")
