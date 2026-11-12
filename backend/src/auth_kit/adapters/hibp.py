"""BreachChecker Have I Been Pwned (k-anonymity : seuls les 5 premiers caractères du SHA-1 sortent)."""
import hashlib
import logging
import urllib.request

logger = logging.getLogger(__name__)


class HibpBreachChecker:
    def __init__(self, timeout: float = 3, url: str = "https://api.pwnedpasswords.com/range/"):
        self.timeout = timeout
        self.url = url

    def is_breached(self, password: str) -> bool:
        """En cas de panne de l'API, le mot de passe est accepté (les autres règles s'appliquent toujours)."""
        digest = hashlib.sha1(password.encode("utf-8")).hexdigest().upper()
        prefix, suffix = digest[:5], digest[5:]
        request = urllib.request.Request(
            self.url + prefix,
            headers={"User-Agent": "auth-kit-password-check", "Add-Padding": "true"},
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                body = response.read().decode("utf-8")
        except Exception:
            logger.warning("API Have I Been Pwned injoignable : vérification des fuites ignorée")
            return False
        for line in body.splitlines():
            candidate, _, count = line.partition(":")
            if candidate == suffix and count.strip() != "0":   # "0" = ligne de remplissage (Add-Padding)
                return True
        return False
