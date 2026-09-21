"""
sakerhet.py – små skydd kring inloggningen
===========================================
Det verkliga skyddet är ett långt lösenord. De här funktionerna är skyddsnätet:
de varnar när lösenordet är svagt och gör upprepade gissningar långsamma.
"""

from __future__ import annotations

MINSTA_LANGD = 12
FORDROJNING_VID_FEL = 2.0          # sekunder att vänta efter ett felaktigt lösenord

_VANLIGA = {"admin", "administrator", "password", "losenord", "lösenord", "hemligt", "byt-mig", "qwerty",
            "123456", "12345678", "123456789", "1234567890", "matarappen", "mätarappen", "welcome", "test"}


def svagt_losenord(losen: str | None) -> bool:
    """True om lösenordet är kort, står på listan över de vanligaste eller bara består av ett tecken."""
    text = (losen or "").strip()
    return len(text) < MINSTA_LANGD or text.lower() in _VANLIGA or len(set(text)) <= 2


class Sparr:
    """Räknar felaktiga lösenord och spärrar inloggningen en stund efter för många i rad.

    En räknare per webbläsarsession PLUS en gemensam för hela appen (den gemensamma tål fler försök, så att
    en enda person som skriver fel inte låser ute alla andra, men ett automatiserat angrepp ändå stoppas)."""

    def __init__(self, max_forsok: int, sparrtid_s: float):
        self.max_forsok, self.sparrtid_s = max_forsok, sparrtid_s
        self.fel, self.sparrad_till = 0, 0.0

    def sparrad(self, nu: float) -> float:
        """Sekunder kvar av spärren (0 = inte spärrad)."""
        return max(0.0, self.sparrad_till - nu)

    def fel_forsok(self, nu: float) -> None:
        self.fel += 1
        if self.fel >= self.max_forsok:
            self.sparrad_till, self.fel = nu + self.sparrtid_s, 0

    def lyckat(self) -> None:
        self.fel = 0
