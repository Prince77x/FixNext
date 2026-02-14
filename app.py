from flask import Flask, render_template,request,redirect,url_for,flash,abort
from models import db, Manager, Technician,Tenant,Ticket,TicketAssignment,TicketHistory,TicketStatus
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager,current_user,login_user,logout_user,login_required

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
with app.app_context():
    db.create_all()

# user loader
@loginmanager.user_loader
def load_user(user_id):
     return (
         Manager.query.get(int(user_id)) or
         Tenant.query.get(int(user_id)) or 
         Technician.query.get(int(user_id))
         )

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


# manager route
@app.route('/manager/dashboard')
@login_required
def manager_dashboard():
    if not isinstance(current_user,Manager):
        abort(403)
    return render_template('./manager/dashboard.html')

# tenants route
@app.route('/tenants/dashboard')
@login_required
def tenant_dashboard():
    if not isinstance(current_user,Tenant):
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