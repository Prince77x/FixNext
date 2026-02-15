from datetime import datetime, date

from flask import render_template, request, redirect, url_for, flash, abort
from flask_login import current_user, login_required

from models import db, Technician, Ticket, TicketAssignment, TicketStatus, Unit
from services import to_ticket_status, log_ticket_activity, latest_notifications, notify_user


def register_worker_routes(app):
    @app.route('/worker/dashboard')
    @login_required
    def worker_dashboard():
        if not isinstance(current_user, Technician):
            abort(403)

        tech_id = current_user.id
        status_filter = request.args.get('status', '')
        priority_filter = request.args.get('priority', '')

        query = Ticket.query.join(TicketAssignment).filter(TicketAssignment.technician_id == tech_id).outerjoin(Unit)

        status_enum = to_ticket_status(status_filter)
        if status_enum:
            query = query.filter(Ticket.status == status_enum)
        if priority_filter:
            query = query.filter(Ticket.priority == priority_filter)

        my_tickets = query.order_by(TicketAssignment.assigned_at.desc()).all()

        stats = {
            'assigned_count': TicketAssignment.query.filter_by(technician_id=tech_id).count(),
            'in_progress': Ticket.query.join(TicketAssignment)
            .filter(TicketAssignment.technician_id == tech_id, Ticket.status == TicketStatus.IN_PROGRESS)
            .count(),
            'completed_today': Ticket.query.join(TicketAssignment)
            .filter(
                TicketAssignment.technician_id == tech_id,
                Ticket.status == TicketStatus.DONE,
                Ticket.created_at >= datetime.combine(date.today(), datetime.min.time()),
            )
            .count(),
        }
        notifications = latest_notifications('technician', tech_id)

        return render_template(
            './worker/dashboard.html',
            tickets=my_tickets,
            stats=stats,
            status_filter=status_filter,
            priority_filter=priority_filter,
            notifications=notifications,
        )

    @app.route('/worker/tickets/<int:ticket_id>/update', methods=['POST'])
    @login_required
    def worker_update_ticket(ticket_id):
        if not isinstance(current_user, Technician):
            abort(403)

        ticket = Ticket.query.get_or_404(ticket_id)
        assignment = TicketAssignment.query.filter_by(ticket_id=ticket_id, technician_id=current_user.id).first()
        if not assignment:
            abort(403)

        new_status = to_ticket_status(request.form.get('status', ''))
        if not new_status:
            flash('Invalid status selected.')
            return redirect(url_for('worker_dashboard'))

        if ticket.status == TicketStatus.ASSIGNED and new_status != TicketStatus.IN_PROGRESS:
            flash('Assigned tickets can only move to In Progress.')
            return redirect(url_for('worker_dashboard'))
        if ticket.status == TicketStatus.IN_PROGRESS and new_status != TicketStatus.DONE:
            flash('In Progress tickets can only move to Done.')
            return redirect(url_for('worker_dashboard'))
        if ticket.status == TicketStatus.DONE:
            flash('Done tickets cannot be changed.')
            return redirect(url_for('worker_dashboard'))

        old_status = ticket.status
        ticket.status = new_status
        log_ticket_activity(ticket.id, 'technician', current_user.id, 'status_changed', old_status.value, new_status.value)
        notify_user('tenant', ticket.tenant_id, f'Ticket T{ticket.id} updated to {new_status.value.replace("_", " ").title()} by technician.')
        db.session.commit()

        flash(f'✅ Ticket T{ticket.id} moved to {new_status.value.replace("_", " ").title()}.')
        return redirect(url_for('worker_dashboard'))
