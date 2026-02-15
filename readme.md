# 🏠 PropertyFix  
### Property Maintenance Management System (Flask + SQLAlchemy)

PropertyFix is a mobile-first property maintenance management system designed for apartment complexes.  
It streamlines communication between **Tenants**, **Managers**, and **Technicians** through a simple ticket-based workflow.

---

## ✨ Features

### 👑 Manager
- View all maintenance tickets
- Assign tickets to technicians
- Add / manage tenants & technicians
- Filter and search tickets
- Export CSV reports

### 🏠 Tenant
- Submit maintenance requests
- Track ticket status
- Unit-based ticket creation
- Mobile-friendly dashboard

### 🔧 Technician
- View only assigned tickets
- Update ticket status (Open → In Progress → Done)
- Touch-friendly mobile UI

---

## 🏗 Tech Stack

### Backend
- Python 3.10+
- Flask
- Flask-Login
- Flask-SQLAlchemy

### Frontend
- Jinja2 Templates
- TailwindCSS (mobile-first)

### Database
- SQLite (development)
- PostgreSQL (production ready)

### Authentication
- Role-based login (Manager / Tenant / Technician)

---

## Installation
`git clone https://github.com/Prince77x/FixNext.git
cd Fixnest
pip install -r requirements.txt
python3 app.py
`

## Project structure
`
propertyfix/
├── app.py
├── models.py
├── templates/
│   ├── base.html
│   ├── login.html
│   ├── manager/
│   ├── tenants/
│   └── worker/
├── statics/
│   ├── css/
│   └── js/
├── database.db
├── requirements.txt
└── README.md
`

### 🏠 Property Maintenance Management System — Demo Submission

- I built a mobile-first property maintenance system using Flask + SQLAlchemy with role-based authentication for Tenant, Manager, and Technician.

- The demo includes:

- Secure login with 3 roles
- Tenants can create maintenance tickets with title, description & status
- Managers can view all tickets, assign technicians, and update priority/status
- Technicians see only assigned tasks and update progress
- Full workflow: Open → Assigned → In Progress → Done
- Activity tracking per ticket
- Responsive UI for mobile and desktop
- Deployed live + GitHub source included

#### 🔗 Live Demo: https://propertyfix.up.railway.app
           $ Demo login credentials
                ->Manager => email: manager1@gmail.com  
                                          password : manager123
                -> tenants => email: tenant@gmail.com
                                          password: 12345
                ->technician => email: raja@gmail.com
                                               password : 12345
#### 🔗 GitHub Repo: https://github.com/Prince77x/FixNext.git
#### 🔗 Project roadmap: https://drive.google.com/file/d/1EkKqKgw24NNHIag33XPheGH18kmZ4cxl/view?usp=sharing