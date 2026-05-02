"""
Firebase Cloud Messaging — push notifications to Flutter app.
Requires firebase_credentials.json in ml/ directory.
"""
import json
from pathlib import Path
from app.config import settings


class NotificationService:
    def __init__(self):
        self._app = None

    def init(self):
        cred_path = Path(settings.FIREBASE_CREDENTIALS_PATH)
        if not cred_path.exists():
            print("⚠️  Firebase credentials not found. Push notifications disabled.")
            return
        try:
            import firebase_admin
            from firebase_admin import credentials
            cred = credentials.Certificate(str(cred_path))
            self._app = firebase_admin.initialize_app(cred)
            print("✅ Firebase initialized")
        except Exception as e:
            print(f"⚠️  Firebase init failed: {e}")

    async def send_alert(self, fcm_token: str, title: str, body: str, data: dict = None):
        if self._app is None or not fcm_token:
            return
        try:
            from firebase_admin import messaging
            message = messaging.Message(
                notification=messaging.Notification(title=title, body=body),
                data={k: str(v) for k, v in (data or {}).items()},
                token=fcm_token,
                android=messaging.AndroidConfig(priority="high"),
                apns=messaging.APNSConfig(
                    payload=messaging.APNSPayload(
                        aps=messaging.Aps(sound="default", badge=1)
                    )
                ),
            )
            messaging.send(message)
        except Exception as e:
            print(f"Push notification failed: {e}")

    async def broadcast_alert(self, fcm_tokens: list[str], title: str, body: str, data: dict = None):
        if self._app is None:
            return
        try:
            from firebase_admin import messaging
            message = messaging.MulticastMessage(
                notification=messaging.Notification(title=title, body=body),
                data={k: str(v) for k, v in (data or {}).items()},
                tokens=fcm_tokens,
            )
            messaging.send_each_for_multicast(message)
        except Exception as e:
            print(f"Broadcast failed: {e}")


notification_service = NotificationService()
