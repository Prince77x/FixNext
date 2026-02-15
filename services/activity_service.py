from datetime import datetime

from models import TicketHistory, db


def log_ticket_activity(ticket_id, actor_role, actor_id, action, old_value=None, new_value=None):
    db.session.add(
        TicketHistory(
            ticket_id=ticket_id,
            actor_role=actor_role,
            actor_id=actor_id,
            action=action,
            old_value=old_value,
            new_value=new_value,
            timestamp=datetime.utcnow(),
        )
    )
