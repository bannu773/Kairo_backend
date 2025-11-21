# Routes package
from app.routes.auth import api as auth_api
from app.routes.tasks import api as tasks_api
from app.routes.users import api as users_api
from app.routes.health import api as health_api

__all__ = ['auth_api', 'tasks_api', 'users_api', 'health_api']
