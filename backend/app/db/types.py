from datetime import timezone

from sqlalchemy import DateTime
from sqlalchemy.types import TypeDecorator


class UTCDateTime(TypeDecorator):
    """DateTime toujours renvoyé avec un fuseau (UTC).

    PostgreSQL renvoie déjà des dates avec fuseau ; SQLite renvoie des dates
    « naïves », ce qui fait planter les comparaisons avec datetime.now(timezone.utc).
    """

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is not None and value.tzinfo is not None:
            value = value.astimezone(timezone.utc)
        return value

    def process_result_value(self, value, dialect):
        if value is not None and value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value
