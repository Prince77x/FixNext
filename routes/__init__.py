from .auth_routes import register_auth_routes
from .manager_routes import register_manager_routes
from .tenant_routes import register_tenant_routes
from .worker_routes import register_worker_routes
from .shared_routes import register_shared_routes


def register_routes(app):
    register_auth_routes(app)
    register_manager_routes(app)
    register_tenant_routes(app)
    register_worker_routes(app)
    register_shared_routes(app)


__all__ = ['register_routes']
