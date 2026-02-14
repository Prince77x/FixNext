from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
import enum
from flask_login import UserMixin

db = SQLAlchemy()

# ================= ENUMS =================

class TicketStatus(enum.Enum):
    OPEN = "open"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    DONE = "done"


# ================= TENANT =================

class Tenant(db.Model, UserMixin):
    __tablename__ = "tenants"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120))
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255))

    tickets = db.relationship("Ticket", back_populates="tenant")

# ================= MANAGER =================

class Manager(db.Model,UserMixin):
    __tablename__ = "managers"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120))
    email = db.Column(db.String(120), unique=True)
    password_hash = db.Column(db.String(255))


# ================= TECHNICIAN =================

class Technician(db.Model,UserMixin):
    __tablename__ = "technicians"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120))
    email = db.Column(db.String(120), unique=True)
    password_hash = db.Column(db.String(255))
    skill = db.Column(db.String(100))

    assignments = db.relationship("TicketAssignment", back_populates="technician")


# ================= PROPERTY =================

class Property(db.Model):
    __tablename__ = "properties"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120))
    address = db.Column(db.Text)

    units = db.relationship("Unit", back_populates="property")


# ================= UNIT =================

class Unit(db.Model):
    __tablename__ = "units"

    id = db.Column(db.Integer, primary_key=True)
    property_id = db.Column(db.Integer, db.ForeignKey("properties.id"))
    unit_number = db.Column(db.String(50))

    property = db.relationship("Property", back_populates="units")
    tickets = db.relationship("Ticket", back_populates="unit")


# ================= TICKET =================

class Ticket(db.Model,UserMixin):
    __tablename__ = "tickets"

    id = db.Column(db.Integer, primary_key=True)

    title = db.Column(db.String(200))
    description = db.Column(db.Text)

    status = db.Column(db.Enum(TicketStatus), default=TicketStatus.OPEN)
    priority = db.Column(db.String(20), default="medium")

    tenant_id = db.Column(db.Integer, db.ForeignKey("tenants.id"))
    unit_id = db.Column(db.Integer, db.ForeignKey("units.id"))

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    tenant = db.relationship("Tenant", back_populates="tickets")
    unit = db.relationship("Unit", back_populates="tickets")

    assignments = db.relationship("TicketAssignment", back_populates="ticket", cascade="all, delete")
    history = db.relationship("TicketHistory", back_populates="ticket", cascade="all, delete")
    attachments = db.relationship("Attachment", back_populates="ticket", cascade="all, delete")


# ================= ASSIGNMENTS =================

class TicketAssignment(db.Model):
    __tablename__ = "ticket_assignments"

    id = db.Column(db.Integer, primary_key=True)
    ticket_id = db.Column(db.Integer, db.ForeignKey("tickets.id"))
    technician_id = db.Column(db.Integer, db.ForeignKey("technicians.id"))

    assigned_at = db.Column(db.DateTime, default=datetime.utcnow)

    ticket = db.relationship("Ticket", back_populates="assignments")
    technician = db.relationship("Technician", back_populates="assignments")


# ================= HISTORY (ACTIVITY LOG) =================

class TicketHistory(db.Model):
    __tablename__ = "ticket_history"

    id = db.Column(db.Integer, primary_key=True)
    ticket_id = db.Column(db.Integer, db.ForeignKey("tickets.id"))

    actor_role = db.Column(db.String(20))   # tenant / manager / technician
    actor_id = db.Column(db.Integer)

    action = db.Column(db.String(100))
    old_value = db.Column(db.String(100))
    new_value = db.Column(db.String(100))

    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    ticket = db.relationship("Ticket", back_populates="history")


# ================= ATTACHMENTS =================

class Attachment(db.Model):
    __tablename__ = "attachments"

    id = db.Column(db.Integer, primary_key=True)
    ticket_id = db.Column(db.Integer, db.ForeignKey("tickets.id"))

    file_url = db.Column(db.String(255))
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)

    ticket = db.relationship("Ticket", back_populates="attachments")


# ================= NOTIFICATIONS =================

class Notification(db.Model):
    __tablename__ = "notifications"

    id = db.Column(db.Integer, primary_key=True)

    user_role = db.Column(db.String(20))
    user_id = db.Column(db.Integer)

    message = db.Column(db.Text)
    is_read = db.Column(db.Boolean, default=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
