from flask import render_template, request, redirect, url_for, flash, abort
from flask_login import current_user, login_required

from models import db, Tenant, Ticket, TicketStatus, Unit
from services import (
    to_ticket_status,
    log_ticket_activity,
    latest_notifications,
    notify_all_managers,
    save_ticket_attachments,
)


def register_tenant_routes(app):
    @app.route('/tenants/dashboard')
    @login_required
    def tenant_dashboard():
        if not isinstance(current_user, Tenant):
            abort(403)

        tenant_id = current_user.id
        status_filter = request.args.get('status', '')

        query = Ticket.query.filter_by(tenant_id=tenant_id).outerjoin(Unit)

        status_enum = to_ticket_status(status_filter)
        if status_enum:
            query = query.filter(Ticket.status == status_enum)

        my_tickets = query.order_by(Ticket.created_at.desc()).all()

        latest_unit = my_tickets[0].unit.unit_number if (my_tickets and my_tickets[0].unit) else 'Not assigned'
        stats = {
            'open_tickets': Ticket.query.filter_by(tenant_id=tenant_id, status=TicketStatus.OPEN).count(),
            'in_progress': Ticket.query.filter_by(tenant_id=tenant_id, status=TicketStatus.IN_PROGRESS).count(),
            'completed': Ticket.query.filter_by(tenant_id=tenant_id, status=TicketStatus.DONE).count(),
            'unit_number': latest_unit,
        }
        notifications = latest_notifications('tenant', tenant_id)

        return render_template(
            './tenants/dashboard.html',
            tickets=my_tickets,
            stats=stats,
            status_filter=status_filter,
            notifications=notifications,
        )

    @app.route('/tenants/new_ticket', methods=['GET', 'POST'])
    @login_required
    def new_ticket():
        if not isinstance(current_user, Tenant):
            abort(403)

        if request.method == 'POST':
            selected_unit = request.form.get('unit_id', '').strip()
            unit_id = int(selected_unit) if selected_unit.isdigit() else None

            requested_priority = request.form.get('priority', 'medium').strip().lower()
            if requested_priority not in {'low', 'medium', 'high', 'urgent'}:
                requested_priority = 'medium'

            ticket = Ticket(
                title=request.form.get('title', '').strip(),
                description=request.form.get('description', '').strip(),
                priority=requested_priority,
                tenant_id=current_user.id,
                status=TicketStatus.OPEN,
                unit_id=unit_id,
            )

            if not ticket.title or not ticket.description:
                flash('Title and description are required.')
                return redirect(url_for('new_ticket'))

            db.session.add(ticket)
            db.session.flush()

            save_ticket_attachments(app, ticket, request.files.getlist('photos'))

            log_ticket_activity(ticket.id, 'tenant', current_user.id, 'ticket_created', None, TicketStatus.OPEN.value)
            notify_all_managers(f'New ticket submitted: T{ticket.id} - {ticket.title}')
            db.session.commit()

            flash('✅ Maintenance request submitted successfully! Ticket #T' + str(ticket.id))
            return redirect(url_for('tenant_dashboard'))

        tenant_units = Unit.query.join(Ticket).filter(Ticket.tenant_id == current_user.id).distinct().all()
        if not tenant_units:
            tenant_units = Unit.query.order_by(Unit.unit_number.asc()).all()

        return render_template('tenants/new_ticket.html', tenant_units=tenant_units)
