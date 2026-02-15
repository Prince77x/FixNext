from models import Manager, Technician, Tenant


def find_tenant_by_email(email):
    return Tenant.query.filter_by(email=email).first()


def find_manager_by_email(email):
    return Manager.query.filter_by(email=email).first()


def find_technician_by_email(email):
    return Technician.query.filter_by(email=email).first()


def get_active_managers():
    return Manager.query.filter_by(is_active=True).all()
