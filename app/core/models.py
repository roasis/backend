# Import all models here for Alembic autodiscovery
from app.domains.auth.models import WalletAuth
from app.domains.users.models import User

__all__ = ["User", "WalletAuth"]
