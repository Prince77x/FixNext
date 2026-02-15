from flask import render_template, abort
from flask_login import current_user, login_required

from models import Manager, Technician, Tenant, Ticket, TicketAssignment, TicketHistory


def register_shared_routes(app):
    @app.route('/tickets/<int:ticket_id>')
    @login_required
    def ticket_detail(ticket_id):
        ticket = Ticket.query.get_or_404(ticket_id)

        if isinstance(current_user, Tenant):
            if ticket.tenant_id != current_user.id:
                abort(403)
        elif isinstance(current_user, Technician):
            assigned = TicketAssignment.query.filter_by(ticket_id=ticket.id, technician_id=current_user.id).first()
            if not assigned:
                abort(403)
        elif not isinstance(current_user, Manager):
            abort(403)

        history = TicketHistory.query.filter_by(ticket_id=ticket.id).order_by(TicketHistory.timestamp.desc()).all()
        return render_template('ticket_detail.html', ticket=ticket, history=history)
