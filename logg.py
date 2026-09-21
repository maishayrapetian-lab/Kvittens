"""
logg.py – felsökningslogg utan känsliga uppgifter
==================================================
Skriver till standardloggen: terminalfönstret lokalt, och "Manage app" -> loggen på Streamlit Community Cloud.
Loggar ALDRIG nycklar, lösenord, mejladresser, objektnamn eller mätvärden – bara VAD som gick fel och VAR,
plus de sex första tecknen i jobbkoden så att ett fel går att följa utan att någon pekas ut.
"""

from __future__ import annotations

import logging

_logg = logging.getLogger("kvittens")
if not _logg.handlers:
    _h = logging.StreamHandler()
    _h.setFormatter(logging.Formatter("%(asctime)s kvittens %(levelname)s %(message)s", "%Y-%m-%d %H:%M:%S"))
    _logg.addHandler(_h)
    _logg.setLevel(logging.INFO)
    _logg.propagate = False


def _id(jobbkod: str | None) -> str:
    return (jobbkod or "------")[:6]


def info(jobbkod: str | None, handelse: str) -> None:
    _logg.info("[%s] %s", _id(jobbkod), handelse)


def fel(jobbkod: str | None, plats: str, e: Exception | str) -> None:
    """plats = var i appen (t.ex. 'avläsning', 'mejl', 'export'). Felets text kommer från appens egna, ofarliga meddelanden."""
    _logg.error("[%s] %s: %s: %s", _id(jobbkod), plats, type(e).__name__ if isinstance(e, Exception) else "fel", str(e)[:300])
