"""
hemligheter.py – hittar och reparerar filen med API-nyckel och lösenord
========================================================================
Rätt fil heter  .streamlit/secrets.toml  och ska se ut så här:

    ANTHROPIC_API_KEY = "sk-ant-..."
    APP_LOSENORD = "ett långt lösenord"

Två misstag är lätta att göra, och båda ska koden klara av i stället för att bara sluta fungera:
  1. Nyckeln klistras in i fel fil (secrets.toml.example, secrets.toml.txt ...).
  2. Citattecknen försvinner, så att filen inte längre är giltig TOML.

reparera() letar upp nyckeln var den än hamnat, skriver en korrekt secrets.toml och
tar bort nyckeln ur den felaktiga filen (så att den aldrig kan följa med upp på GitHub).
Nyckeln skrivs ALDRIG ut – varken på skärmen eller i någon logg.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

import sakerhet

ROT = Path(__file__).resolve().parent
RATT_NAMN = "secrets.toml"
FELNAMN = ("secrets.toml.example", "secrets_toml.example", "secrets.toml.txt", "secrets.toml.example.txt",
           "secrets.txt", "secrets", "secrets.toml.toml")
PLATSHALLARE_NYCKEL = "KLISTRA-IN-NYCKELN-HÄR"
MALL = ('# Appens hemligheter. Den här filen ska ALDRIG läggas upp på GitHub (den står i .gitignore).\n'
        '# Klistra in din API-nyckel mellan citattecknen. Den börjar med sk-ant-\n'
        f'ANTHROPIC_API_KEY = "{PLATSHALLARE_NYCKEL}"\n\n'
        '# Lösenord för att öppna appen. Minst 12 tecken, och inte ett du använder någon annanstans.\n'
        '# Ta bort raden för att köra utan lösenord (bara lokalt på din egen dator).\n'
        'APP_LOSENORD = ""\n\n'
        '# Valfritt: mejlutskick av protokollet. Ta bort # framför raderna och fyll i (se DRIFTSÄTTNING.md, steg 6).\n'
        '# SMTP_ANVANDARE = "adressen-appen-mejlar-fran@gmail.com"\n'
        '# SMTP_LOSENORD = "app-lösenordet med 16 tecken"\n')


def tolka(text: str) -> dict[str, str]:
    """Förlåtande tolkning av rader som  NAMN = värde  – med eller utan citattecken."""
    ut: dict[str, str] = {}
    for rad in text.replace("\ufeff", "").splitlines():
        m = re.match(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*[=:]\s*(.*?)\s*$", rad)
        if not m or rad.lstrip().startswith("#"):
            continue
        namn, varde = m.group(1), m.group(2)
        if len(varde) >= 2 and varde[0] in "\"'“”" and varde[-1] in "\"'“”":     # även "smarta" citattecken
            varde = varde[1:-1]
        elif varde[:1] in "\"'“”":                                                # glömt avslutande citattecken
            varde = varde[1:]
        ut[namn] = varde.strip()
    return ut


def riktig_nyckel(varde: str | None) -> bool:
    v = (varde or "").strip()
    return v.startswith("sk-ant-") and len(v) >= 40 and "..." not in v


def _toml(varde: str) -> str:
    """Skriv värdet som giltig TOML. Enkla citattecken kräver inga specialregler för \\ och \"."""
    if "'" not in varde and "\n" not in varde:
        return f"'{varde}'"
    return '"' + varde.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _giltig_toml(text: str) -> bool:
    try:
        import tomllib

        tomllib.loads(text.replace("\ufeff", ""))
        return True
    except ModuleNotFoundError:                          # Python < 3.11: lita på vår egen tolkning
        return True
    except Exception:
        return False


def _las_text(fil: Path) -> str:
    for kodning in ("utf-8-sig", "utf-16", "cp1252"):   # Anteckningar kan spara i olika kodningar
        try:
            return fil.read_text(encoding=kodning)
        except (UnicodeError, ValueError):
            continue
    return fil.read_text(encoding="utf-8", errors="replace")


def _skriv_sakert(fil: Path, text: str) -> None:
    tmp = fil.with_name(fil.name + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, fil)                                 # antingen hela nya filen eller hela gamla – aldrig en halv


def reparera(rot: Path = ROT) -> list[str]:
    """Se till att .streamlit/secrets.toml finns, är giltig och innehåller nyckeln om den finns någonstans.
    Returnerar begripliga meddelanden om vad som gjordes (aldrig själva nyckeln)."""
    medd: list[str] = []
    mapp = rot / ".streamlit"
    mapp.mkdir(exist_ok=True)
    ratt = mapp / RATT_NAMN
    text = _las_text(ratt) if ratt.exists() else ""
    varden = tolka(text)
    andrad = False

    # 1. Har nyckeln hamnat i en fil med fel namn?
    for plats in (mapp, rot):
        for namn in FELNAMN:
            fel = plats / namn
            if not fel.is_file():
                continue
            feltext = _las_text(fel)
            hittat = tolka(feltext)
            if not riktig_nyckel(hittat.get("ANTHROPIC_API_KEY")):
                continue
            if not riktig_nyckel(varden.get("ANTHROPIC_API_KEY")):
                varden["ANTHROPIC_API_KEY"] = hittat["ANTHROPIC_API_KEY"]
                # lösenordet i filen du själv redigerade gäller, om det som redan står i rätt fil saknas eller är svagt
                losen = hittat.get("APP_LOSENORD", "")
                if losen and losen != "byt-mig" and sakerhet.svagt_losenord(varden.get("APP_LOSENORD")):
                    varden["APP_LOSENORD"] = losen
                andrad = True
                medd.append(f"Nyckeln låg i fel fil ({fel.name}). Den är flyttad till {RATT_NAMN}, som är filen appen läser.")
            # nyckeln får inte ligga kvar i en fil som inte skyddas av .gitignore
            _skriv_sakert(fel, MALL)
            medd.append(f"{fel.name} är återställd till en tom mall, så att nyckeln bara finns på ett ställe.")

    # 2. Saknas filen helt?
    if not ratt.exists() and not andrad:
        _skriv_sakert(ratt, MALL)
        medd.append(f"Skapade {mapp.name}/{RATT_NAMN}. Klistra in API-nyckeln där, mellan citattecknen.")
        return medd

    # 3. Ogiltig TOML (t.ex. citattecken som försvunnit) eller flyttade värden -> skriv om filen korrekt
    if andrad or not _giltig_toml(text):
        if not andrad:
            medd.append(f"{RATT_NAMN} var inte giltig (saknade troligen citattecken). Filen är rättad.")
        rader = ["# Appens hemligheter. Den här filen ska ALDRIG läggas upp på GitHub (den står i .gitignore)."]
        for namn, varde in varden.items():
            rader.append(f"{namn} = {_toml(varde)}")
        _skriv_sakert(ratt, "\n".join(rader) + "\n")
    return medd


def las(rot: Path = ROT) -> dict[str, str]:
    """Värdena ur .streamlit/secrets.toml (förlåtande tolkning). Tom dict om filen saknas."""
    fil = rot / ".streamlit" / RATT_NAMN
    return tolka(_las_text(fil)) if fil.is_file() else {}


def _duger(varde: str | None) -> str | None:
    v = (varde or "").strip()
    return None if (not v or v == PLATSHALLARE_NYCKEL or v in ("sk-ant-...", "byt-mig")) else v


def hamta(namn: str, rot: Path = ROT) -> str | None:
    """Projektets egen fil går först, sedan miljövariabeln. Platshållare räknas som 'saknas'.

    Filen läses om vid varje anrop. Byter du nyckel gäller den nya direkt – ingen omstart behövs –
    och en gammal nyckel som ligger kvar någon annanstans på datorn kan aldrig ta över."""
    return _duger(las(rot).get(namn)) or _duger(os.environ.get(namn))


def fingeravtryck(nyckel: str | None) -> str:
    """De fyra sista tecknen – lagom för att känna igen nyckeln i Consoles lista, ofarligt att visa."""
    return f"…{nyckel.strip()[-4:]}" if nyckel and len(nyckel.strip()) > 20 else "(ingen)"


def skuggnycklar(rot: Path = ROT) -> list[str]:
    """Finns det ANDRA nycklar på datorn som skiljer sig från projektets? Returnerar var de ligger."""
    egen = _duger(las(rot).get("ANTHROPIC_API_KEY"))
    ut = []
    miljo = _duger(os.environ.get("ANTHROPIC_API_KEY"))
    if miljo and miljo != egen:
        ut.append(f"miljövariabeln ANTHROPIC_API_KEY (slutar på {fingeravtryck(miljo)})")
    globalt = Path.home() / ".streamlit" / RATT_NAMN
    if globalt.is_file() and globalt.resolve() != (rot / ".streamlit" / RATT_NAMN).resolve():
        annan = _duger(tolka(_las_text(globalt)).get("ANTHROPIC_API_KEY"))
        if annan and annan != egen:
            ut.append(f"{globalt} (slutar på {fingeravtryck(annan)})")
    return ut


def bortkommenterade(rot: Path = ROT) -> list[str]:
    """Rader som är ifyllda men fortfarande har # framför sig, t.ex.  # SMTP_ANVANDARE = "jag@gmail.com".
    Ett lätt misstag: man fyller i värdet men glömmer ta bort #."""
    fil = rot / ".streamlit" / RATT_NAMN
    if not fil.is_file():
        return []
    aktiva, ut = las(rot), []
    for rad in _las_text(fil).splitlines():
        m = re.match(r"^\s*#+\s*([A-Z][A-Z0-9_]*)\s*=\s*(.+?)\s*$", rad)
        if not m or m.group(1) in aktiva:
            continue
        varde = m.group(2).strip("\"'“” ")
        if varde and "adressen-appen" not in varde and "app-lösenordet" not in varde and "..." not in varde:
            ut.append(m.group(1))
    return ut
