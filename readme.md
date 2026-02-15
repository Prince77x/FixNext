📖 PropertyFix Documentation
============================

*Property maintenance management system for apartment complexes and society*

* * * * *

🏠 Quick Start
--------------

Prerequisites
-------------

bash

`Python 3.10+ pip install Flask Flask-Login Flask-SQLAlchemy Flask-Migrate Werkzeug `

Installation (2 minutes)
------------------------

bash

`# 1. Clone & Setup  git clone <your-repo>  cd propertyfix pip install -r requirements.txt   # 2. Run  python3 app.py `

Open: `http://localhost:5000`

Test Users (Auto-created on first run)
--------------------------------------

text

`👑 MANAGER:     manager1@gmail.com / manager123 → /manager/dashboard 🏠 TENANT:       / 123456 → /tenants/dashboard 🔧 TECHNICIAN:  tech@test.com / 123456   → /worker/dashboard `

* * * * *

🏗️ Architecture Overview
-------------------------

text

`Frontend: Jinja2 + TailwindCSS (Mobile-first, Glassmorphism) Backend: Flask 2.x + Flask-Login + Flask-SQLAlchemy Database: SQLite (Development) → PostgreSQL (Production) Authentication: Role-based (3 user types) Deployment: Render/Vercel/Heroku/Docker `

text

`┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐ │   🏠 Tenant     │───▶│   Ticket System  │◀───│   👑 Manager    │ │                 │    │                  │    │                 │ └─────────────────┘    │   Unit → Property│    └─────────────────┘
 │     Assignment   │           │ │   History/Notes  │           ▼ └──────────────────┘    ┌─────────────────┐ │   🔧 Technician │ │                 │ └─────────────────┘ `

* * * * *

👥 User Roles & Features
------------------------

| Role | Dashboard | Key Features |
| --- | --- | --- |
| 👑 Manager | `/manager/dashboard` | ✅ Assign tickets\
✅ Add/manage tenants\
✅ Add technicians\
✅ Export CSV reports\
✅ Filter/search tickets |
| 🏠 Tenant | `/tenants/dashboard` | ✅ Submit maintenance requests\
✅ Track ticket status\
✅ Photo upload ready\
✅ Unit assignment |
| 🔧 Technician | `/worker/dashboard` | ✅ View MY assignments only\
✅ Update status (In Progress/Done)\
✅ Mobile-first design\
✅ Skill-based filtering |

* * * * *

🗄️ Database Schema
-------------------

Core Models
-----------

python

`# User Models (all inherit Flask-Login UserMixin)  class  Tenant:  # Tenants submit tickets    id, name, email, password_hash, phone, is_active  tickets = relationship("Ticket")    class  Manager:  # Property managers    id, name, email, password_hash, is_active   class  Technician:  # Maintenance workers    id, name, email, password_hash, skill, is_active  assignments = relationship("TicketAssignment")    class  Ticket:  # Maintenance requests    id, title, description, status, priority  tenant_id, unit_id, created_at  assignments, history, attachments   class  Unit:  # Apartment units    id, property_id, unit_number  tickets = relationship("Ticket")    class  Property:  # Apartment buildings    id, name, address  units = relationship("Unit")  `

Entity Relationships
--------------------

text

`Tenant 1:N Ticket N:1 Unit 1:N Property  |         | N:1    N:M TicketAssignment N:1 Technician | N:1 TicketHistory `

* * * * *

🌐 API Routes
-------------

Authentication
--------------

text

`POST /login              # Email/password login GET  /logout             # Logout all roles `

Manager Routes
--------------

text

`GET  /manager/dashboard          # Dashboard + filters POST /manager/add_technician     # Create technician POST /manager/assign/<ticket_id> # Assign to technician GET  /manager/tenants            # Manage tenants POST /manager/add_tenant         # Create tenant POST /manager/delete_tenant/<id> # Delete tenant GET  /manager/export             # CSV export `

Tenant Routes
-------------

text

`GET  /tenants/dashboard  # My tickets + stats POST /tenants/new_ticket # Submit maintenance request `

Technician Routes
-----------------

text

`GET  /worker/dashboard   # My assignments only `

* * * * *

📁 Project Structure
--------------------

text

`propertyfix/ ├── app.py                    # Main Flask app + all routes ├── models.py                 # SQLAlchemy ORM models ├── templates/ │   ├── base.html            # Layout wrapper │   ├── index.html           # Landing page │   ├── login.html │   ├── manager/ │   │   ├── dashboard.html │   │   ├── add_technician.html │   │   └── tenants.html │   ├── tenants/ │   │   ├── dashboard.html │   │   └── new_ticket.html │   └── worker/ │       └── dashboard.html ├── statics/ │   ├── css/ │   └── js/ ├── database.db              # SQLite dev database ├── requirements.txt └── README.md `

* * * * *

🚀 Installation & Deployment
----------------------------

Local Development
-----------------

bash

`# Clone & Install  git clone <repo>  cd propertyfix pip install -r requirements.txt   # Database (auto-creates)  rm -f database.db # Fresh start  python app.py   # Access: http://localhost:5000  `

Production Deployment (Render.com - 2 minutes)
----------------------------------------------

bash

`# 1. Push to GitHub  git push origin main   # 2. Render.com → New Web Service → Connect GitHub repo  # 3. Build: python app.py  # 4. Environment: SECRET_KEY=your-secret-here  `

Docker (Production)
-------------------

text

`FROM python:3.11-slim WORKDIR /app COPY . . RUN pip install -r requirements.txt EXPOSE 5000 CMD ["python", "app.py"] `

* * * * *

🔧 Configuration
----------------

Environment Variables
---------------------

text

`SECRET_KEY=your-super-secret-key-here SQLALCHEMY_DATABASE_URI=sqlite:///database.db FLASK_ENV=development  # or production `

Test Data Creation
------------------

python

`# In flask shell: flask shell  from app import app, db from models import Manager, Tenant, Technician from werkzeug.security import generate_password_hash   with app.app_context():   db.session.add(Manager(name="Admin", email="manager@test.com",   password_hash=generate_password_hash("123456")))   db.session.add(Tenant(name="John Tenant", email="tenant@test.com",   password_hash=generate_password_hash("123456")))   db.session.commit()  `

* * * * *

📱 Key Features
---------------

✨ Mobile-First Design
---------------------

text

`✅ Responsive (320px → Desktop) ✅ Touch-friendly (48px buttons) ✅ Glassmorphism UI ✅ Fast loading (no JS frameworks) ✅ PWA-ready `

🔒 Security
-----------

text

`✅ Password hashing (PBKDF2) ✅ Role-based access control ✅ SQLAlchemy ORM (SQL injection safe) ✅ Session protection (Flask-Login) ✅ CSRF ready (Flask-WTF) `

📊 Smart Features
-----------------

text

`✅ Real-time ticket filtering ✅ Auto-unit assignment ✅ CSV export (Manager) ✅ Ticket history audit trail ✅ Priority badges (Low🟢/High🔴/Urgent🚨) `

* * * * *

🧪 Testing
----------

Test Users
----------

text

`👑 manager@test.com / 123456 → Manager Dashboard 🏠 tenant@test.com / 123456 → Tenant Portal 🔧 tech@test.com / 123456   → Technician Dashboard `

Manual Testing Flow
-------------------

text

`1\. Manager: Add Technician → Assign ticket → Export CSV 2\. Tenant: Submit ticket → Track status 3\. Technician: Update status → Mark Done `

* * * * *

🎨 UI Components
----------------

text

`📊 Stats Cards          → Open/In Progress/Done counts 🎫 Filterable Tables    → Status/Priority/Technician ➕ New Ticket Form      → Priority picker + photo upload 🔧 Status Badges        → Open/Assigned/In Progress/Done 📱 Mobile Navigation    → Sticky header + touch targets `

* * * * *

🔄 Common Issues & Solutions
----------------------------

| Issue | Solution |
| --- | --- |
| 403 Forbidden | Fix `load_user()` callback in `app.py` |
| Login fails | Delete `database.db` + recreate test users |
| No dashboard | Create missing template files |
| Unit not found | Add Property → Unit → link to tenant |

* * * * *

🚀 Next Features (Roadmap)
--------------------------

text

`v1.1 → File Uploads (Attachments) v1.2 → Push Notifications v1.3 → Mobile App (PWA) v1.4 → Multi-property support v1.5 → Reports/PDF export `

* * * * *

🤝 Contributing
---------------

1.  Fork repository

2.  Create feature branch (`git checkout -b feature/xyz`)

3.  Add tests (if applicable)

4.  Commit (`git commit -m "Add XYZ"`)

5.  Push & PR

* * * * *

📞 Support
----------

text

`💬 Discord: propertyfix.dev/discord 📧 Email: hello@propertyfix.com 🐛 Issues: github.com/yourusername/propertyfix/issues 📚 Docs: propertyfix.readthedocs.io `

* * * * *

📄 License
----------

MIT License - Free for commercial use

text

`PropertyFix © 2026 Built with ❤️ for property managers worldwide `
