from flask import render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required
from werkzeug.security import check_password_hash

from repositories import find_manager_by_email, find_tenant_by_email, find_technician_by_email


def register_auth_routes(app):
    @app.route('/')
    def home():
        return render_template('index.html')

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if request.method == 'POST':
            email = request.form.get('email')
            password = request.form.get('password')

            tenant = find_tenant_by_email(email)
            if tenant and check_password_hash(tenant.password_hash, password):
                login_user(tenant)
                return redirect(url_for('tenant_dashboard'))

            manager = find_manager_by_email(email)
            if manager and check_password_hash(manager.password_hash, password):
                login_user(manager)
                return redirect(url_for('manager_dashboard'))

            technician = find_technician_by_email(email)
            if technician and check_password_hash(technician.password_hash, password):
                login_user(technician)
                return redirect(url_for('worker_dashboard'))

            flash('Invalid credentials')

        return render_template('login.html')

    @app.route('/logout')
    @login_required
    def logout():
        logout_user()
        flash('You have been logged out successfully!')
        return redirect(url_for('login'))
