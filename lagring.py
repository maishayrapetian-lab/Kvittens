"""
lagring.py – så att ett påbörjat jobb överlever att mobilen somnar
===================================================================
I fält händer det hela tiden: du laddar upp bilder, låser skärmen eller byter till kameran,
och när du kommer tillbaka har webbläsaren laddat om sidan. Utan det här vore allt borta.

Lösningen: varje jobb får en slumpad kod som läggs i adressen (…/?jobb=Ab3xK9…). Jobbets data
ligger i serverns minne under den koden. Laddas sidan om med samma adress hämtas jobbet tillbaka.

  * Inget skrivs till disk. Startas servern om, eller somnar appen, är jobben borta.
  * Ett jobb ligger kvar i högst MAX_TIMMAR och som mest MAX_JOBB jobb sparas samtidigt.
  * Koden är lång och slumpad – den går inte att gissa. Den skyddas dessutom av inloggningen.

Här finns också dygnsräknaren som sätter ett tak för antalet avlästa bilder (kostnadsskydd).
"""

from __future__ import annotations

import secrets
import threading
import time
from datetime import date

import streamlit as st

MAX_TIMMAR = 12
MAX_JOBB = 40
SPARADE_NYCKLAR = ("resultat", "seq", "steg", "bas", "tabellversion", "kvitterat", "slutdata", "jobb")


@st.cache_resource
def _lager() -> dict:
    return {"jobb": {}, "raknare": {}, "las": threading.Lock()}


def gemensam_sparr(max_forsok: int, sparrtid_s: float):
    """En inloggningsspärr som delas av alla besökare (skydd mot automatiserade gissningar)."""
    import sakerhet

    lager = _lager()
    with lager["las"]:
        if "sparr" not in lager:
            lager["sparr"] = sakerhet.Sparr(max_forsok, sparrtid_s)
        return lager["sparr"]


def ny_kod() -> str:
    return secrets.token_urlsafe(12)


def _stada(lager: dict) -> None:
    nu = time.time()
    jobb = lager["jobb"]
    for kod in [k for k, v in jobb.items() if nu - v["tid"] > MAX_TIMMAR * 3600]:
        del jobb[kod]
    for kod in sorted(jobb, key=lambda k: jobb[k]["tid"])[:max(0, len(jobb) - MAX_JOBB)]:
        del jobb[kod]


def spara(kod: str, tillstand: dict, utkast: dict | None = None) -> None:
    """Spara jobbets tillstånd. 'utkast' = tabellerna så som de ser ut just nu (ännu inte bekräftade)."""
    lager = _lager()
    with lager["las"]:
        lager["jobb"][kod] = {"tid": time.time(), "data": {k: tillstand.get(k) for k in SPARADE_NYCKLAR}, "utkast": utkast or {}}
        _stada(lager)


def hamta(kod: str) -> dict | None:
    lager = _lager()
    with lager["las"]:
        _stada(lager)
        post = lager["jobb"].get(kod)
        if not post:
            return None
        data = dict(post["data"])
        if post["utkast"]:                                   # det du hann rätta innan sidan laddades om följer med
            data["bas"] = {**(data.get("bas") or {}), **post["utkast"]}
        return data


def glom(kod: str) -> None:
    lager = _lager()
    with lager["las"]:
        lager["jobb"].pop(kod, None)


def kvar_idag(namn: str, tak: int) -> int:
    """Hur många av 'namn' (t.ex. bilder, mejl) återstår i dag innan taket är nått?"""
    lager = _lager()
    with lager["las"]:
        return max(0, tak - lager["raknare"].get((date.today().isoformat(), namn), 0))


def rakna(namn: str, antal: int = 1) -> None:
    lager = _lager()
    with lager["las"]:
        idag = date.today().isoformat()
        lager["raknare"] = {k: v for k, v in lager["raknare"].items() if k[0] == idag}     # gamla dagar kastas
        lager["raknare"][(idag, namn)] = lager["raknare"].get((idag, namn), 0) + antal


def bilder_kvar_idag(tak: int) -> int:
    return kvar_idag("bilder", tak)


def rakna_bilder(antal: int) -> None:
    rakna("bilder", antal)
