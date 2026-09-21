"""
kontrollera.py – går igenom hela installationen och säger vad som är fel
=========================================================================
Enklast:  dubbelklicka på  kontrollera.bat  (Windows)  eller  kontrollera.command  (Mac).

Skriptet ändrar bara en sak: det reparerar filen med API-nyckeln om nyckeln hamnat i fel
fil eller saknar citattecken. Nyckeln skrivs aldrig ut. Allt annat är rena kontroller.

Resultatet sparas i  kontroll_resultat.txt  – klistra in det till Claude om något är rött.

Avslutskoder:  0 = allt fungerar   2 = API-nyckeln saknas   3 = paket saknas   1 = annat fel
"""

from __future__ import annotations

import importlib
import json
import sys
import traceback
from datetime import datetime
from pathlib import Path

ROT = Path(__file__).resolve().parent
RESULTATFIL = ROT / "kontroll_resultat.txt"
PAKET = {"streamlit": "streamlit", "anthropic": "anthropic", "pandas": "pandas", "openpyxl": "openpyxl", "PIL": "pillow"}
_rader: list[str] = []


def skriv(text: str = "") -> None:
    _rader.append(text)
    try:
        print(text, flush=True)
    except UnicodeEncodeError:
        print(text.encode("ascii", "replace").decode(), flush=True)


def ok(text: str) -> None:
    skriv(f"  [OK]  {text}")


def fel(text: str, gor: str = "") -> None:
    skriv(f"  [FEL] {text}")
    if gor:
        skriv(f"        -> {gor}")


def kontroll_python() -> bool:
    skriv("1. Python")
    v = sys.version_info
    i_venv = sys.prefix != getattr(sys, "base_prefix", sys.prefix)
    if v < (3, 10):
        fel(f"Python {v.major}.{v.minor} är för gammal.", "Installera Python 3.12 från python.org och kör installera.bat.")
        return False
    ok(f"Python {v.major}.{v.minor}.{v.micro} ({'projektets egen miljö' if i_venv else 'datorns vanliga Python'})")
    return True


def kontroll_paket() -> bool:
    skriv("2. Paket")
    saknas = []
    for modul, pipnamn in PAKET.items():
        try:
            m = importlib.import_module(modul)
            ok(f"{pipnamn} {getattr(m, '__version__', '')}".strip())
        except Exception:
            saknas.append(pipnamn)
            fel(f"{pipnamn} saknas.")
    if saknas:
        skriv("        -> Dubbelklicka på installera.bat (Mac: installera.command) och kör sedan den här kontrollen igen.")
        return False
    import inspect

    from anthropic.resources.messages import Messages

    if "output_config" not in inspect.signature(Messages.create).parameters:
        fel("Paketet anthropic är för gammalt för strukturerade svar.", "Kör installera.bat igen – den uppdaterar paketen.")
        return False
    return True


def kontroll_filer() -> bool:
    skriv("3. Appens filer")
    import config

    behovs = [config.MALL, "app.py", "avlasning.py", "kontroller.py", "protokoll.py", "utseende.py", "hemligheter.py",
              ".streamlit/config.toml", "static/barlow-400.woff2", "static/ikon.png", "testbilder/facit.json"]
    saknas = [f for f in behovs if not (ROT / f).exists()]
    if saknas:
        fel("Saknas: " + ", ".join(saknas), "Packa upp zip-filen igen över mappen och välj att ersätta filerna.")
        return False
    ok(f"Alla {len(behovs)} filer finns, inklusive mallen {config.MALL}.")
    return True


def kontroll_nyckel() -> str | None:
    skriv("4. API-nyckel och lösenord")
    import hemligheter
    import sakerhet

    for m in hemligheter.reparera(ROT):
        skriv(f"  [FIXAT] {m}")
    nyckel = hemligheter.hamta("ANTHROPIC_API_KEY", ROT)
    if not nyckel:
        fel("Ingen API-nyckel i .streamlit/secrets.toml.",
            "Filen öppnas nu. Klistra in nyckeln mellan citattecknen på raden ANTHROPIC_API_KEY, spara och kör kontrollen igen.")
        return None
    if nyckel.startswith("apikey_"):
        fel("Det som står i filen är nyckelns ID, inte nyckeln.", "Skapa en ny nyckel i Console och kopiera strängen som börjar med sk-ant-.")
        return None
    if not hemligheter.riktig_nyckel(nyckel):
        fel("Det som står som API-nyckel ser inte ut som en nyckel (ska börja med sk-ant- och vara lång).",
            "Kopiera nyckeln på nytt från Console – hela strängen, utan mellanslag.")
        return None
    ok(f"Nyckel hittad i .streamlit/secrets.toml. Den slutar på {hemligheter.fingeravtryck(nyckel)} – jämför med listan under API keys i Console.")
    for plats in hemligheter.skuggnycklar(ROT):
        skriv(f"  [OBS] Det finns en ANNAN nyckel i {plats}. Appen använder ändå projektets fil, men ta gärna bort den gamla.")
    losen = hemligheter.hamta("APP_LOSENORD", ROT)
    if not losen:
        ok("Inget lösenord satt – okej så länge appen bara körs på din egen dator.")
    elif sakerhet.svagt_losenord(losen):
        skriv("  [OBS] Lösenordet är svagt. Byt till minst 12 tecken innan appen blir nåbar för andra.")
    else:
        ok("Lösenordet är tillräckligt långt.")
    return nyckel


def kontroll_api(nyckel: str) -> bool:
    skriv("5. Kontakt med AI-tjänsten")
    import anthropic

    import config

    try:
        klient = anthropic.Anthropic(api_key=nyckel, max_retries=1, timeout=60.0)
        klient.messages.create(model=config.MODELL, max_tokens=5, messages=[{"role": "user", "content": "Svara bara: OK"}])
    except anthropic.AuthenticationError:
        fel("Nyckeln godkänns inte. Den är felkopierad eller borttagen i Console.",
            "Skapa en ny nyckel på platform.claude.com -> API keys och klistra in den i .streamlit/secrets.toml.")
        return False
    except anthropic.PermissionDeniedError as e:
        fel(f"Nyckeln saknar behörighet: {getattr(e, 'message', e)}")
        return False
    except anthropic.NotFoundError:
        fel(f"Modellen {config.MODELL} finns inte för ditt konto.", "Klistra in det här till Claude, så byter vi modell i config.py.")
        return False
    except anthropic.BadRequestError as e:
        text = str(getattr(e, "message", e))
        if "credit" in text.lower() or "balance" in text.lower() or "billing" in text.lower():
            fel("Kontot saknar saldo.", "Lägg in ett litet belopp under Billing på platform.claude.com. Några tior räcker länge.")
        else:
            fel(f"API:t avvisade anropet: {text}")
        return False
    except anthropic.RateLimitError:
        fel("För många anrop just nu (eller så saknas saldo).", "Vänta en minut och försök igen. Kontrollera Billing i Console.")
        return False
    except (anthropic.APIConnectionError, anthropic.APITimeoutError):
        fel("Ingen kontakt med api.anthropic.com.", "Kontrollera internet. På jobbnät kan en brandvägg blockera – prova mobilens delade nät.")
        return False
    except anthropic.APIStatusError as e:
        fel(f"AI-tjänsten svarade med fel {e.status_code}: {getattr(e, 'message', e)}")
        return False
    ok(f"Nyckeln fungerar och modellen {config.MODELL} svarar.")
    return True


def kontroll_avlasning(nyckel: str) -> bool:
    skriv("6. Riktig provavläsning av en testbild (kostar några ören)")
    import avlasning

    bild = "IMG_2033.jpeg"
    facit = json.loads((ROT / "testbilder" / "facit.json").read_text(encoding="utf8"))[bild][0]
    try:
        svar = avlasning.las_av_bild(avlasning.skapa_klient(nyckel), avlasning.forbered_bild((ROT / "testbilder" / bild).read_bytes()))
        rader = avlasning.till_rader(svar, bild)
    except avlasning.AvlasningsFel as e:
        fel(f"Avläsningen misslyckades: {e}")
        return False
    if not rader:
        fel("AI:n hittade ingen display i testbilden.", "Klistra in hela den här texten till Claude.")
        return False
    missar = [(f, rader[0].get(f, ""), v) for f, v in facit.items() if str(rader[0].get(f, "")).replace(",", ".") != v]
    if missar:
        for f, fick, vantat in missar:
            skriv(f"  [OBS] {f}: AI:n läste '{fick}', på displayen står '{vantat}'")
        skriv("        -> Avläsningen fungerar tekniskt. Kör utvardera.bat för hela mätningen och skicka resultatet till Claude.")
        return True
    ok(f"{bild}: alla {len(facit)} fält rätt avlästa ({rader[0]['typ']} {rader[0]['dimension']}, {rader[0]['uppmatt']} l/s, Kv {rader[0]['kv']}).")
    return True


def kontroll_mejl() -> bool:
    skriv("7. Mejlutskick (valfritt)")
    import hemligheter
    import mejl

    inst = mejl.installningar(lambda namn: hemligheter.hamta(namn, ROT))
    if not inst:
        skriv("  [--]  Inte inställt. Protokollet går att ladda ner ändå. Vill du kunna mejla det: se DRIFTSÄTTNING.md, steg 6.")
        return True
    try:
        mejl.testa_inloggning(inst)
    except mejl.MejlFel as e:
        fel(str(e))
        return False
    ok(f"Inloggningen på {inst['server']} fungerar. Mejlen skickas från {inst['avsandare']}.")
    return True


def main() -> int:
    skriv(f"Kontroll av Kvittens – {datetime.now():%Y-%m-%d %H:%M}")
    skriv(f"Mapp: {ROT}\n")
    if not kontroll_python():
        return 1
    if not kontroll_paket():
        return 3
    if not kontroll_filer():
        return 1
    nyckel = kontroll_nyckel()
    if not nyckel:
        return 2
    if not kontroll_api(nyckel) or not kontroll_avlasning(nyckel):
        return 1
    if not kontroll_mejl():
        return 1
    skriv("\nALLT FUNGERAR. Starta appen med starta_appen.bat, eller kör hela mätningen med utvardera.bat.")
    return 0


if __name__ == "__main__":
    kod = 1
    try:
        kod = main()
    except Exception:
        skriv("\nOVÄNTAT FEL – klistra in allt nedan till Claude:\n" + traceback.format_exc())
    finally:
        skriv(f"\nResultatet är sparat i {RESULTATFIL.name}")
        RESULTATFIL.write_text("\n".join(_rader) + "\n", encoding="utf8")
    sys.exit(kod)
