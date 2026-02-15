from models import TicketStatus


STATUS_FLOW = {
    TicketStatus.OPEN: {TicketStatus.ASSIGNED},
    TicketStatus.ASSIGNED: {TicketStatus.IN_PROGRESS},
    TicketStatus.IN_PROGRESS: {TicketStatus.DONE},
    TicketStatus.DONE: set(),
}


def to_ticket_status(value):
    if not value:
        return None
    normalized = str(value).strip().lower()
    for item in TicketStatus:
        if item.value == normalized:
            return item
    return None


def can_transition(old_status, new_status):
    return new_status in STATUS_FLOW.get(old_status, set())
