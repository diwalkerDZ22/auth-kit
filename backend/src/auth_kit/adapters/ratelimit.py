"""Implémentations de RateLimiter.

"memory://" ne vaut que pour un seul process ; avec plusieurs workers ou serveurs, utiliser
Redis ("redis://host:6379", pip install auth-kit[redis]) pour partager les compteurs.

Derrière un reverse proxy, lancer uvicorn avec --proxy-headers --forwarded-allow-ips=<ip du proxy> :
sinon tous les clients ont l'IP du proxy et partagent la même limite.
"""
from limits import parse, storage, strategies


class LimitsRateLimiter:
    def __init__(self, storage_uri: str = "memory://", enabled: bool = True):
        self.enabled = enabled
        self._storage = storage.storage_from_string(storage_uri)
        self._window = strategies.FixedWindowRateLimiter(self._storage)

    def hit(self, limit: str, *keys: str) -> bool:
        if not self.enabled:
            return True
        return self._window.hit(parse(limit), *keys)

    def test(self, limit: str, *keys: str) -> bool:
        if not self.enabled:
            return True
        return self._window.test(parse(limit), *keys)

    def reset(self) -> None:
        self._storage.reset()


class NoRateLimiter:
    """Aucune limite (déconseillé hors tests)."""

    enabled = False

    def hit(self, limit: str, *keys: str) -> bool:
        return True

    def test(self, limit: str, *keys: str) -> bool:
        return True

    def reset(self) -> None:
        pass
