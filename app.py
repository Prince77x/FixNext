from flask import Flask, render_template
from models import db, Manager, Technician,Tenant,Ticket,TicketAssignment,TicketHistory,TicketStatus
app = Flask(__name__, static_folder='statics', static_url_path='/statics')

#app configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'

db.init_app(app)
with app.app_context():
    db.create_all()
    
# home route 
@app.route('/')
def home():
    return render_template('index.html')

if __name__ == "__main__":
    app.run(debug=True)