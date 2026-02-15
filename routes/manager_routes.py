from datetime import datetime

from flask import render_template, request, redirect, url_for, flash, abort
from flask_login import current_user, login_required
from werkzeug.security import generate_password_hash

from models import db, Manager, Technician, Tenant, Ticket, TicketAssignment, TicketHistory, TicketStatus, Unit
from services import (
    to_ticket_status,
    can_transition,
    log_ticket_activity,
    notify_user,
    latest_notifications,
)


def register_manager_routes(app):
    @app.route('/manager/dashboard')
    @login_required
    def manager_dashboard():
        if not isinstance(current_user, Manager):
            abort(403)

        status_filter = request.args.get('status', '')
        priority_filter = request.args.get('priority', '')
        tech_filter = request.args.get('technician', '')

        query = Ticket.query.outerjoin(Unit)

        status_enum = to_ticket_status(status_filter)
        if status_enum:
            query = query.filter(Ticket.status == status_enum)
        if priority_filter:
            query = query.filter(Ticket.priority == priority_filter)
        if tech_filter and tech_filter.isdigit():
            query = query.join(TicketAssignment).filter(TicketAssignment.technician_id == int(tech_filter))

        tickets = query.order_by(Ticket.created_at.desc()).distinct().all()

        stats = {
            'open_tickets': Ticket.query.filter_by(status=TicketStatus.OPEN).count(),
            'high_priority': Ticket.query.filter(Ticket.priority.in_(['high', 'urgent'])).count(),
            'total_tickets': Ticket.query.count(),
        }

        technicians = Technician.query.order_by(Technician.name.asc()).all()
        notifications = latest_notifications('manager', current_user.id)

        return render_template(
            './manager/dashboard.html',
            tickets=tickets,
            stats=stats,
            technicians=technicians,
            status_filter=status_filter,
            priority_filter=priority_filter,
            tech_filter=tech_filter,
            notifications=notifications,
        )

    @app.route('/manager/add_technician', methods=['GET', 'POST'])
    @login_required
    def add_technician():
        if not isinstance(current_user, Manager):
            abort(403)

        if request.method == 'POST':
            existing = Technician.query.filter_by(email=request.form['email']).first()
            if existing:
                flash('Email already exists!')
                return render_template('manager/add_technician.html')

            technician = Technician(
                name=request.form['name'],
                email=request.form['email'],
                password_hash=generate_password_hash(request.form.get('password', 'default123')),
                skill=request.form.get('skill', 'General'),
            )
            db.session.add(technician)
            db.session.commit()
            flash('✅ Technician added successfully!')
            return redirect(url_for('manager_dashboard'))

        return render_template('manager/add_technician.html')

    @app.route('/manager/assign/<int:ticket_id>', methods=['POST'])
    @login_required
    def assign_ticket(ticket_id):
        if not isinstance(current_user, Manager):
            abort(403)

        ticket = Ticket.query.get_or_404(ticket_id)
        tech_id = request.form.get('technician_id', '').strip()
        if not tech_id.isdigit():
            flash('Please select a technician first.')
            return redirect(url_for('manager_dashboard'))

        technician = db.session.get(Technician, int(tech_id))
        if not technician:
            flash('Selected technician does not exist.')
            return redirect(url_for('manager_dashboard'))

        old_assignment = TicketAssignment.query.filter_by(ticket_id=ticket_id).order_by(TicketAssignment.assigned_at.desc()).first()
        TicketAssignment.query.filter_by(ticket_id=ticket_id).delete()

        assignment = TicketAssignment(ticket_id=ticket_id, technician_id=technician.id)
        old_status = ticket.status
        if old_status == TicketStatus.DONE:
            flash('Done tickets cannot be reassigned.')
            return redirect(url_for('manager_dashboard'))
        if old_status == TicketStatus.OPEN:
            ticket.status = TicketStatus.ASSIGNED

        previous_tech = old_assignment.technician_id if old_assignment else None
        log_ticket_activity(
            ticket_id=ticket_id,
            actor_role='manager',
            actor_id=current_user.id,
            action='assigned_to_tech',
            old_value=str(previous_tech) if previous_tech else 'unassigned',
            new_value=str(technician.id),
        )

        if old_status != ticket.status:
            log_ticket_activity(
                ticket_id=ticket_id,
                actor_role='manager',
                actor_id=current_user.id,
                action='status_changed',
                old_value=old_status.value,
                new_value=ticket.status.value,
            )

        db.session.add(assignment)
        notify_user('technician', technician.id, f'New ticket assigned: T{ticket.id} - {ticket.title}')
        notify_user('tenant', ticket.tenant_id, f'Your ticket T{ticket.id} has been assigned to {technician.name}.')
        db.session.commit()

        flash(f'✅ Assigned to {technician.name}')
        return redirect(url_for('manager_dashboard'))

    @app.route('/manager/tickets/<int:ticket_id>/update', methods=['POST'])
    @login_required
    def manager_update_ticket(ticket_id):
        if not isinstance(current_user, Manager):
            abort(403)

        ticket = Ticket.query.get_or_404(ticket_id)
        new_priority = request.form.get('priority', '').strip().lower()
        new_status_raw = request.form.get('status', '').strip()

        valid_priorities = {'low', 'medium', 'high', 'urgent'}
        changed = False

        if new_priority and new_priority in valid_priorities and new_priority != ticket.priority:
            old_priority = ticket.priority
            ticket.priority = new_priority
            log_ticket_activity(ticket.id, 'manager', current_user.id, 'priority_changed', old_priority, new_priority)
            notify_user('tenant', ticket.tenant_id, f'Ticket T{ticket.id} priority changed to {new_priority}.')
            changed = True

        new_status = to_ticket_status(new_status_raw)
        if new_status and new_status != ticket.status:
            if not can_transition(ticket.status, new_status):
                flash(f'Invalid status flow: {ticket.status.value} -> {new_status.value}')
                return redirect(url_for('manager_dashboard'))

            if new_status == TicketStatus.ASSIGNED:
                has_assignment = TicketAssignment.query.filter_by(ticket_id=ticket.id).first()
                if not has_assignment:
                    flash('Assign a technician before moving to Assigned.')
                    return redirect(url_for('manager_dashboard'))

            old_status = ticket.status
            ticket.status = new_status
            log_ticket_activity(ticket.id, 'manager', current_user.id, 'status_changed', old_status.value, new_status.value)
            notify_user('tenant', ticket.tenant_id, f'Ticket T{ticket.id} status is now {new_status.value.replace("_", " ").title()}.')
            changed = True

        if changed:
            db.session.commit()
            flash(f'✅ Ticket T{ticket.id} updated.')
        else:
            flash('No valid changes detected.')

        return redirect(url_for('manager_dashboard'))

    @app.route('/manager/export')
    @login_required
    def export_tickets():
        if not isinstance(current_user, Manager):
            abort(403)

        import csv
        from io import StringIO

        output = StringIO()
        writer = csv.writer(output)

        writer.writerow(['ID', 'Title', 'Status', 'Priority', 'Unit', 'Created'])
        for ticket in Ticket.query.all():
            writer.writerow([
                ticket.id,
                ticket.title,
                ticket.status.value,
                ticket.priority,
                getattr(ticket.unit, 'unit_number', '-'),
                ticket.created_at.strftime('%Y-%m-%d %H:%M'),
            ])

        return output.getvalue(), 200, {
            'Content-Type': 'text/csv',
            'Content-Disposition': 'attachment; filename=tickets.csv',
        }

    @app.route('/manager/tenants')
    @login_required
    def manage_tenants():
        if not isinstance(current_user, Manager):
            abort(403)

        status_filter = request.args.get('status', 'all')
        unit_filter = request.args.get('unit', '')

        query = Tenant.query

        if unit_filter:
            query = query.join(Ticket).join(Unit).filter(Unit.unit_number.ilike(f'%{unit_filter}%')).distinct()

        if status_filter != 'all':
            if status_filter == 'active':
                query = query.filter(Tenant.is_active.is_(True))
            elif status_filter == 'inactive':
                query = query.filter(Tenant.is_active.is_(False))

        tenants = query.order_by(Tenant.id.desc()).all()

        stats = {
            'total_tenants': Tenant.query.count(),
            'active_tenants': Tenant.query.filter_by(is_active=True).count(),
            'inactive_tenants': Tenant.query.filter_by(is_active=False).count(),
        }

        return render_template(
            'manager/tenants.html',
            tenants=tenants,
            stats=stats,
            status_filter=status_filter,
            unit_filter=unit_filter,
        )

    @app.route('/manager/add_tenant', methods=['GET', 'POST'])
    @login_required
    def add_tenant():
        if not isinstance(current_user, Manager):
            abort(403)

        if request.method == 'POST':
            tenant = Tenant(
                name=request.form['name'],
                email=request.form['email'],
                password_hash=generate_password_hash(request.form['password']),
            )
            db.session.add(tenant)
            db.session.commit()
            flash('✅ Tenant added successfully!')
            return redirect(url_for('manage_tenants'))

        return render_template('manager/add_tenant.html')

    @app.route('/manager/edit_tenant/<int:tenant_id>', methods=['GET', 'POST'])
    @login_required
    def edit_tenant(tenant_id):
        if not isinstance(current_user, Manager):
            abort(403)

        tenant = Tenant.query.get_or_404(tenant_id)

        if request.method == 'POST':
            if request.form['email'] != tenant.email and Tenant.query.filter_by(email=request.form['email']).first():
                flash('❌ Email already exists for another tenant!', 'error')
                return render_template('manager/edit_tenant.html', tenant=tenant)

            tenant.name = request.form['name']
            tenant.email = request.form['email']
            if request.form.get('password'):
                tenant.password_hash = generate_password_hash(request.form['password'])
            tenant.phone = request.form.get('phone', '')

            db.session.commit()
            flash('✅ Tenant updated successfully!', 'success')
            return redirect(url_for('manage_tenants'))

        return render_template('manager/edit_tenant.html', tenant=tenant)

    @app.route('/manager/deactivate_tenant/<int:tenant_id>', methods=['POST'])
    @login_required
    def deactivate_tenant(tenant_id):
        if not isinstance(current_user, Manager):
            abort(403)

        tenant = Tenant.query.get_or_404(tenant_id)

        tenant.is_active = False

        history = TicketHistory(
            ticket_id=None,
            actor_role='manager',
            actor_id=current_user.id,
            action='deactivated_tenant',
            old_value='active',
            new_value='inactive',
            timestamp=datetime.utcnow(),
        )
        db.session.add(history)

        db.session.commit()
        flash(f'✅ Tenant "{tenant.name}" has been deactivated!', 'success')
        return redirect(url_for('manage_tenants'))

    @app.route('/manager/activate_tenant/<int:tenant_id>', methods=['POST'])
    @login_required
    def activate_tenant(tenant_id):
        if not isinstance(current_user, Manager):
            abort(403)

        tenant = Tenant.query.get_or_404(tenant_id)
        tenant.is_active = True
        db.session.commit()
        flash(f'✅ Tenant "{tenant.name}" has been activated!', 'success')
        return redirect(url_for('manage_tenants'))

    @app.route('/manager/delete_tenant/<int:tenant_id>', methods=['POST'])
    @login_required
    def delete_tenant(tenant_id):
        if not isinstance(current_user, Manager):
            abort(403)

        tenant = Tenant.query.get_or_404(tenant_id)
        tenant_name = tenant.name

        Ticket.query.filter_by(tenant_id=tenant_id).delete()

        db.session.delete(tenant)
        db.session.commit()

        flash(f'✅ Tenant "{tenant_name}" and all their tickets have been deleted!', 'success')
        return redirect(url_for('manage_tenants'))
