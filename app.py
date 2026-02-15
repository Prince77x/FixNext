from flask import Flask, render_template,request,redirect,url_for,flash,abort
from models import db, Manager, Technician, Tenant, Ticket, TicketAssignment, TicketHistory, TicketStatus, Unit, Property, Attachment
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager,current_user,login_user,logout_user,login_required
from flask_migrate import Migrate
from datetime import datetime
app = Flask(__name__, static_folder='statics', static_url_path='/statics')

#app configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SECRET_KEY'] = 'FixNext'

#Flask_login configuration 
loginmanager = LoginManager()
loginmanager.init_app(app)
loginmanager.login_view = "login"

# database initialization
db.init_app(app)
migrate = Migrate(app,db)
with app.app_context():
    db.create_all()

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
    
    # Base query with joins
    query = Ticket.query.join(Unit).outerjoin(TicketAssignment).outerjoin(Technician)
    
    # Apply filters
    if status_filter:
        query = query.filter(Ticket.status == status_filter.replace('_', ' ').upper())
    if priority_filter:
        query = query.filter(Ticket.priority == priority_filter)
    if tech_filter:
        query = query.filter(Technician.id == int(tech_filter))
    
    tickets = query.order_by(Ticket.created_at.desc()).all()
    
    # Stats
    stats = {
        'open_tickets': Ticket.query.filter_by(status=TicketStatus.OPEN).count(),
        'high_priority': Ticket.query.filter(Ticket.priority.in_(['high', 'urgent'])).count(),
        'total_tickets': Ticket.query.count()
    }
    
    technicians = Technician.query.all()
    
    return render_template('./manager/dashboard.html', 
                         tickets=tickets, stats=stats, 
                         technicians=technicians,
                         status_filter=status_filter,
                         priority_filter=priority_filter,
                         tech_filter=tech_filter)


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
    tech_id = request.form['technician_id']
    
    # Remove old assignment
    TicketAssignment.query.filter_by(ticket_id=ticket_id).delete()
    
    # New assignment
    assignment = TicketAssignment(
        ticket_id=ticket_id,
        technician_id=tech_id
    )
    ticket.status = TicketStatus.ASSIGNED
    
    # History log
    history = TicketHistory(
        ticket_id=ticket_id,
        actor_role='manager',
        actor_id=current_user.id,
        action='assigned_to_tech',
        old_value='unassigned',
        new_value=f'Technician ID: {tech_id}'
    )
    
    db.session.add(assignment)
    db.session.add(history)
    db.session.commit()
    
    flash(f'✅ Assigned to Technician #{tech_id}')
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

    return render_template('./tenants/dashboard.html')

# workers route 
@app.route('/worker/dashboard')
@login_required
def worker_dashboard():
    if not isinstance(current_user,Technician):
        abort(403)
    return render_template('./worker/dashboard.html')


if __name__ == "__main__":
    app.run(debug=True)
