"""Lightweight notification helper used by API routes."""
from __future__ import annotations

from datetime import datetime
from typing import Dict, List


class NotificationService:
    """Simple notification dispatcher for push and email events."""

    def __init__(self) -> None:
        self.sent_notifications: List[Dict] = []

    def send_push_notification(self, user_id: str, title: str, body: str) -> None:
        payload = {
            'type': 'push',
            'user_id': user_id,
            'title': title,
            'body': body,
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        }
        self.sent_notifications.append(payload)
        print(f"[NotificationService] PUSH -> {user_id}: {title} - {body}")

    def send_email_notification(self, user_id: str, subject: str, body: str) -> None:
        payload = {
            'type': 'email',
            'user_id': user_id,
            'subject': subject,
            'body': body,
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        }
        self.sent_notifications.append(payload)
        print(f"[NotificationService] EMAIL -> {user_id}: {subject}")

    def notify_enrollment(self, user_id: str, mission_title: str) -> None:
        message = f"You're now enrolled in {mission_title}!"
        self.send_push_notification(user_id, 'Mission unlocked', message)
        self.send_email_notification(user_id, f'Welcome to {mission_title}', message)

    def notify_next_topic(self, user_id: str, mission_title: str, topic_title: str) -> None:
        body = f"Next up in {mission_title}: {topic_title}."
        self.send_push_notification(user_id, 'Next mission topic ready', body)

    def notify_mission_completed(self, user_id: str, mission_title: str) -> None:
        body = f"You completed {mission_title}! Celebrate your badge."
        self.send_push_notification(user_id, 'Mission complete 🎉', body)
        self.send_email_notification(user_id, f'{mission_title} complete', body)
