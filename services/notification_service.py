from datetime import datetime

from models import Notification, db
from repositories.user_repository import get_active_managers


def notify_user(user_role, user_id, message):
    db.session.add(
        Notification(
            user_role=user_role,
            user_id=user_id,
            message=message,
            is_read=False,
            created_at=datetime.utcnow(),
        )
    )


def notify_all_managers(message):
    for manager in get_active_managers():
        notify_user('manager', manager.id, message)


def latest_notifications(user_role, user_id, limit=5):
    return (
        Notification.query.filter_by(user_role=user_role, user_id=user_id)
        .order_by(Notification.created_at.desc())
        .limit(limit)
        .all()
    )
