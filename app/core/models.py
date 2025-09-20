# Import all models here for Alembic autodiscovery
from app.domains.artist.models import Artist
from app.domains.auth.models import WalletAuth
from app.domains.gallery.models import Gallery

__all__ = ["Artist", "WalletAuth", "Gallery"]
