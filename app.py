import os
from datetime import datetime, date
from uuid import uuid4
from flask import Flask, render_template, request, redirect, url_for, flash, abort
from models import db, Manager, Technician, Tenant, Ticket, TicketAssignment, TicketHistory, TicketStatus, Unit, Property, Attachment, Notification
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from flask_login import LoginManager, current_user, login_user, logout_user, login_required
from flask_migrate import Migrate
app = Flask(__name__, static_folder='statics', static_url_path='/statics')

#app configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SECRET_KEY'] = 'FixNext'
app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'statics', 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024  # 10MB
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

#Flask_login configuration 
loginmanager = LoginManager()
loginmanager.init_app(app)
loginmanager.login_view = "login"

# database initialization
db.init_app(app)
migrate = Migrate(app,db)
with app.app_context():
    db.create_all()


STATUS_FLOW = {
    TicketStatus.OPEN: {TicketStatus.ASSIGNED},
    TicketStatus.ASSIGNED: {TicketStatus.IN_PROGRESS},
    TicketStatus.IN_PROGRESS: {TicketStatus.DONE},
    TicketStatus.DONE: set(),
}
ALLOWED_UPLOAD_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp', 'gif'}


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


def log_ticket_activity(ticket_id, actor_role, actor_id, action, old_value=None, new_value=None):
    db.session.add(TicketHistory(
        ticket_id=ticket_id,
        actor_role=actor_role,
        actor_id=actor_id,
        action=action,
        old_value=old_value,
        new_value=new_value,
        timestamp=datetime.utcnow(),
    ))


def notify_user(user_role, user_id, message):
    db.session.add(Notification(
        user_role=user_role,
        user_id=user_id,
        message=message,
        is_read=False,
        created_at=datetime.utcnow(),
    ))


def notify_all_managers(message):
    for manager in Manager.query.filter_by(is_active=True).all():
        notify_user('manager', manager.id, message)


def latest_notifications(user_role, user_id, limit=5):
    return Notification.query.filter_by(
        user_role=user_role, user_id=user_id
    ).order_by(Notification.created_at.desc()).limit(limit).all()


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_UPLOAD_EXTENSIONS

# user loader
@loginmanager.user_loader
def load_user(user_id):
    """Load user with role-aware IDs to prevent cross-table ID collisions."""
    if not user_id:
        return None

    # New format: "<role>:<id>", e.g. "tenant:1"
    if ":" in user_id:
        role, raw_id = user_id.split(":", 1)
        if not raw_id.isdigit():
            return None

        lookup = {
            "manager": Manager,
            "tenant": Tenant,
            "technician": Technician,
        }
        model = lookup.get(role)
        if not model:
            return None

        user = db.session.get(model, int(raw_id))
        return user if user and user.is_active else None

    # Backward compatibility for old sessions that stored only numeric IDs.
    if user_id.isdigit():
        raw_id = int(user_id)
        for model in (Manager, Tenant, Technician):
            user = db.session.get(model, raw_id)
            if user and user.is_active:
                return user

    return None

# home route 
@app.route('/')
def home():
    return render_template('index.html')

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        # ---------- Check Tenant ----------
        tenant = Tenant.query.filter_by(email=email).first()
        if tenant and check_password_hash(tenant.password_hash, password):
            login_user(tenant)
            return redirect(url_for("tenant_dashboard"))

        # ---------- Check Manager ----------
        manager = Manager.query.filter_by(email=email).first()
        if manager and check_password_hash(manager.password_hash, password):
            login_user(manager)
            return redirect(url_for("manager_dashboard"))

        # ---------- Check Technician ----------
        technician = Technician.query.filter_by(email=email).first()
        if technician and check_password_hash(technician.password_hash, password):
            login_user(technician)
            return redirect(url_for("worker_dashboard"))

        flash("Invalid credentials")

    return render_template("login.html")

@app.route('/logout')
@login_required
def logout():
    """Logout any user (Manager/Tenant/Technician) and redirect to login"""
    logout_user()
    flash('You have been logged out successfully!')
    return redirect(url_for('login'))


# manager route
@app.route('/manager/dashboard')
@login_required
def manager_dashboard():
    if not isinstance(current_user, Manager):
        abort(403)
    
    # Filters from query params
    status_filter = request.args.get('status', '')
    priority_filter = request.args.get('priority', '')
    tech_filter = request.args.get('technician', '')
    
    query = Ticket.query.outerjoin(Unit)
    
    # Apply filters
    status_enum = to_ticket_status(status_filter)
    if status_enum:
        query = query.filter(Ticket.status == status_enum)
    if priority_filter:
        query = query.filter(Ticket.priority == priority_filter)
    if tech_filter:
        if tech_filter.isdigit():
            query = query.join(TicketAssignment).filter(TicketAssignment.technician_id == int(tech_filter))
    
    tickets = query.order_by(Ticket.created_at.desc()).distinct().all()
    
    # Stats
    stats = {
        'open_tickets': Ticket.query.filter_by(status=TicketStatus.OPEN).count(),
        'high_priority': Ticket.query.filter(Ticket.priority.in_(['high', 'urgent'])).count(),
        'total_tickets': Ticket.query.count()
    }
    
    technicians = Technician.query.order_by(Technician.name.asc()).all()
    notifications = latest_notifications('manager', current_user.id)
    
    return render_template('./manager/dashboard.html', 
                         tickets=tickets, stats=stats, 
                         technicians=technicians,
                         status_filter=status_filter,
                         priority_filter=priority_filter,
                         tech_filter=tech_filter,
                         notifications=notifications)


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
            skill=request.form.get('skill', 'General')
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
    
    # Remove old assignment
    old_assignment = TicketAssignment.query.filter_by(ticket_id=ticket_id).order_by(TicketAssignment.assigned_at.desc()).first()
    TicketAssignment.query.filter_by(ticket_id=ticket_id).delete()
    
    # New assignment
    assignment = TicketAssignment(
        ticket_id=ticket_id,
        technician_id=technician.id
    )
    old_status = ticket.status
    if old_status == TicketStatus.DONE:
        flash('Done tickets cannot be reassigned.')
        return redirect(url_for('manager_dashboard'))
    if old_status == TicketStatus.OPEN:
        ticket.status = TicketStatus.ASSIGNED
    
    # History log
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
    import sys
    
    output = StringIO()
    writer = csv.writer(output)
    
    writer.writerow(['ID', 'Title', 'Status', 'Priority', 'Unit', 'Created'])
    for ticket in Ticket.query.all():
        writer.writerow([
            ticket.id, ticket.title, ticket.status.value,
            ticket.priority, getattr(ticket.unit, 'unit_number', '-'),
            ticket.created_at.strftime('%Y-%m-%d %H:%M')
        ])
    
    return output.getvalue(), 200, {
        'Content-Type': 'text/csv',
        'Content-Disposition': 'attachment; filename=tickets.csv'
    }

@app.route('/manager/tenants')
@login_required
def manage_tenants():
    if not isinstance(current_user, Manager):
        abort(403)
    
    # Filters
    status_filter = request.args.get('status', 'all')
    unit_filter = request.args.get('unit', '')
    
    query = Tenant.query
    
    # Filter by unit if provided (through tenant's tickets)
    if unit_filter:
        query = query.join(Ticket).join(Unit).filter(Unit.unit_number.ilike(f'%{unit_filter}%')).distinct()
    
    # Filter by status if requested
    if status_filter != 'all':
        if status_filter == 'active':
            query = query.filter(Tenant.is_active.is_(True))
        elif status_filter == 'inactive':
            query = query.filter(Tenant.is_active.is_(False))

    tenants = query.order_by(Tenant.id.desc()).all()

    # Stats
    stats = {
        'total_tenants': Tenant.query.count(),
        'active_tenants': Tenant.query.filter_by(is_active=True).count(),
        'inactive_tenants': Tenant.query.filter_by(is_active=False).count(),
    }
    
    return render_template('manager/tenants.html', tenants=tenants, stats=stats,
                           status_filter=status_filter, unit_filter=unit_filter)

@app.route('/manager/add_tenant', methods=['GET', 'POST'])
@login_required
def add_tenant():
    if not isinstance(current_user, Manager):
        abort(403)
    
    if request.method == 'POST':
        tenant = Tenant(
            name=request.form['name'],
            email=request.form['email'],
            password_hash=generate_password_hash(request.form['password'])
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
        # Check email conflict (excluding current tenant)
        if request.form['email'] != tenant.email and Tenant.query.filter_by(email=request.form['email']).first():
            flash('❌ Email already exists for another tenant!', 'error')
            return render_template('manager/edit_tenant.html', tenant=tenant)
        
        # Update tenant details
        tenant.name = request.form['name']
        tenant.email = request.form['email']
        if request.form.get('password'):  # Only update if password provided
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
    
    # Deactivate tenant
    tenant.is_active = False
    
    # Optional: Log the action
    history = TicketHistory(
        ticket_id=None,  # No specific ticket
        actor_role='manager',
        actor_id=current_user.id,
        action='deactivated_tenant',
        old_value='active',
        new_value='inactive',
        timestamp=datetime.utcnow()
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
    
    # Delete related tickets first (cascade will handle rest)
    Ticket.query.filter_by(tenant_id=tenant_id).delete()
    
    # Delete tenant
    db.session.delete(tenant)
    db.session.commit()
    
    flash(f'✅ Tenant "{tenant_name}" and all their tickets have been deleted!', 'success')
    return redirect(url_for('manage_tenants'))

# tenants route
@app.route('/tenants/dashboard')
@login_required
def tenant_dashboard():
    if not isinstance(current_user, Tenant):
        abort(403)
    
    tenant_id = current_user.id
    
    # Filters
    status_filter = request.args.get('status', '')
    
    # My tickets only
    query = Ticket.query.filter_by(tenant_id=tenant_id).outerjoin(Unit)
    
    status_enum = to_ticket_status(status_filter)
    if status_enum:
        query = query.filter(Ticket.status == status_enum)
    
    my_tickets = query.order_by(Ticket.created_at.desc()).all()
    
    # Stats
    latest_unit = my_tickets[0].unit.unit_number if (my_tickets and my_tickets[0].unit) else 'Not assigned'
    stats = {
        'open_tickets': Ticket.query.filter_by(tenant_id=tenant_id, status=TicketStatus.OPEN).count(),
        'in_progress': Ticket.query.filter_by(tenant_id=tenant_id, status=TicketStatus.IN_PROGRESS).count(),
        'completed': Ticket.query.filter_by(tenant_id=tenant_id, status=TicketStatus.DONE).count(),
        'unit_number': latest_unit
    }
    notifications = latest_notifications('tenant', tenant_id)
    
    return render_template('./tenants/dashboard.html', 
                         tickets=my_tickets, stats=stats,
                         status_filter=status_filter,
                         notifications=notifications)

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

        # Create new maintenance ticket
        ticket = Ticket(
            title=request.form.get('title', '').strip(),
            description=request.form.get('description', '').strip(),
            priority=requested_priority,
            tenant_id=current_user.id,
            status=TicketStatus.OPEN,
            unit_id=unit_id
        )

        if not ticket.title or not ticket.description:
            flash('Title and description are required.')
            return redirect(url_for('new_ticket'))
            
        db.session.add(ticket)
        db.session.flush()

        # File uploads
        for photo in request.files.getlist('photos'):
            if not photo or not photo.filename:
                continue
            if not allowed_file(photo.filename):
                continue

            ext = photo.filename.rsplit('.', 1)[1].lower()
            unique_name = f"{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{uuid4().hex}.{ext}"
            safe_name = secure_filename(unique_name)
            save_path = os.path.join(app.config['UPLOAD_FOLDER'], safe_name)
            photo.save(save_path)

            db.session.add(Attachment(
                ticket=ticket,
                file_url=f'uploads/{safe_name}',
                uploaded_at=datetime.utcnow(),
            ))

        log_ticket_activity(ticket.id, 'tenant', current_user.id, 'ticket_created', None, TicketStatus.OPEN.value)
        notify_all_managers(f'New ticket submitted: T{ticket.id} - {ticket.title}')
        db.session.commit()
        
        flash('✅ Maintenance request submitted successfully! Ticket #T' + str(ticket.id))
        return redirect(url_for('tenant_dashboard'))
    
    # Existing units for this tenant, otherwise show all units
    tenant_units = Unit.query.join(Ticket).filter(Ticket.tenant_id == current_user.id).distinct().all()
    if not tenant_units:
        tenant_units = Unit.query.order_by(Unit.unit_number.asc()).all()
    
    return render_template('tenants/new_ticket.html', 
                         tenant_units=tenant_units)

# workers route 
@app.route('/worker/dashboard')
@login_required
def worker_dashboard():
    if not isinstance(current_user, Technician):
        abort(403)
    
    tech_id = current_user.id
    
    # Filters
    status_filter = request.args.get('status', '')
    priority_filter = request.args.get('priority', '')
    
    # My assigned tickets only
    query = Ticket.query.join(TicketAssignment).filter(
        TicketAssignment.technician_id == tech_id
    ).outerjoin(Unit).outerjoin(Property)
    
    status_enum = to_ticket_status(status_filter)
    if status_enum:
        query = query.filter(Ticket.status == status_enum)
    if priority_filter:
        query = query.filter(Ticket.priority == priority_filter)
    
    my_tickets = query.order_by(TicketAssignment.assigned_at.desc()).all()
    
    # Stats
    stats = {
        'assigned_count': TicketAssignment.query.filter_by(technician_id=tech_id).count(),
        'in_progress': Ticket.query.join(TicketAssignment).filter(
            TicketAssignment.technician_id == tech_id,
            Ticket.status == TicketStatus.IN_PROGRESS
        ).count(),
        'completed_today': Ticket.query.join(TicketAssignment).filter(
            TicketAssignment.technician_id == tech_id,
            Ticket.status == TicketStatus.DONE,
            Ticket.created_at >= datetime.combine(date.today(), datetime.min.time())
        ).count()
    }
    notifications = latest_notifications('technician', tech_id)
    
    return render_template('./worker/dashboard.html', 
                         tickets=my_tickets, stats=stats,
                         status_filter=status_filter,
                         priority_filter=priority_filter,
                         notifications=notifications)


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


if __name__ == "__main__":
    app.run(debug=True)
