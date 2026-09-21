"""
uppdatera.py – lägger en ny version på rätt plats, utan att något hamnar dubbelt
=================================================================================
Bakgrund: zip-paketet innehåller en mapp som heter  matarapp . Packar man upp det INUTI den
gamla mappen får man  matarapp/matarapp/...  – två kopior av alla filer, och ingen vet vilken
app.py som är den riktiga. Det här skriptet gör uppdateringen åt dig, på samma sätt varje gång.

Så använder du det:
  1. Packa upp den nya zip-filen VAR SOM HELST (t.ex. i Hämtade filer).
  2. Dubbelklicka på  uppdatera.bat  i den uppackade mappen.

Skriptet:
  * hittar din riktiga installation (mappen som har .venv eller nyckelfilen)
  * kopierar de nya filerna dit
  * rör ALDRIG  .streamlit/secrets*  eller  .venv
  * flyttar en felaktig inre kopia (matarapp/matarapp) till en säkerhetsmapp – raderar inget
  * tar bort __pycache__ (skapas om av sig själv)
  * talar om vad du ska göra i GitHub Desktop efteråt

Bara Pythons standardbibliotek används, så det fungerar även innan paketen är installerade.
"""

from __future__ import annotations

import shutil
import sys
from datetime import datetime
from pathlib import Path

HAR = Path(__file__).resolve().parent
ROR_ALDRIG = {".venv", "venv", "env", ".git", "__pycache__", ".pytest_cache", ".ruff_cache"}
KANNETECKEN = ("app.py", "avlasning.py", "kontroller.py")          # så känns en kopia av appen igen


def skyddad(rel: Path) -> bool:
    """Filer som aldrig får skrivas över eller kopieras: nyckelfilen, miljön, resultatfiler."""
    delar = rel.parts
    if any(d in ROR_ALDRIG for d in delar):
        return True
    if len(delar) >= 2 and delar[-2] == ".streamlit" and delar[-1].lower().startswith("secrets"):
        return True
    return rel.name.endswith("resultat.txt") or rel.suffix == ".pyc"


def ar_installation(mapp: Path) -> bool:
    """En riktig installation har en Python-miljö eller en nyckelfil – det har aldrig en nyuppackad kopia."""
    return mapp.is_dir() and ((mapp / ".venv").is_dir() or (mapp / "venv").is_dir()
                              or any((mapp / ".streamlit").glob("secrets*")) or (mapp / ".git").is_dir())


def hitta_installation(hem: Path | None = None) -> Path | None:
    hem = hem or Path.home()
    kandidater = [hem / d / "matarapp" for d in ("Documents", "Dokument", "OneDrive/Documents", "OneDrive/Dokument", "Desktop", "Skrivbord")]
    kandidater += [hem / "matarapp"]
    return next((k for k in kandidater if ar_installation(k)), None)


def kopiera(kalla: Path, mal: Path) -> int:
    antal = 0
    for fil in sorted(kalla.rglob("*")):
        rel = fil.relative_to(kalla)
        if not fil.is_file() or skyddad(rel):
            continue
        (mal / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(fil, mal / rel)
        antal += 1
    return antal


def stada(mal: Path, skriv=print) -> None:
    """Flytta undan felaktiga inre kopior och ta bort __pycache__."""
    for inre in (mal / "matarapp", mal / "matarapp" / "matarapp"):
        if inre.is_dir() and all((inre / k).exists() for k in KANNETECKEN):
            # Ligger nyckelfilen bara i den inre kopian? Rädda den först.
            for hemlig in (inre / ".streamlit").glob("secrets*") if (inre / ".streamlit").is_dir() else []:
                ratt = mal / ".streamlit" / hemlig.name
                if not ratt.exists():
                    ratt.parent.mkdir(exist_ok=True)
                    shutil.move(str(hemlig), str(ratt))
                    skriv(f"  Nyckelfilen låg i den inre kopian och är flyttad till rätt plats: .streamlit/{hemlig.name}")
            undan = mal.parent / f"matarapp_gammal_kopia_{datetime.now():%Y%m%d_%H%M%S}"
            shutil.move(str(inre), str(undan))
            skriv(f"  En dubblettkopia av appen låg i {inre.relative_to(mal.parent)}. Den är FLYTTAD (inte raderad) till: {undan}")
            skriv("  Titta gärna i den, och släng den sedan själv när du ser att allt fungerar.")
            break
    borttagna = 0
    for cache in list(mal.rglob("__pycache__")):
        if not any(d in (".venv", "venv", "env", ".git") for d in cache.relative_to(mal).parts):
            shutil.rmtree(cache, ignore_errors=True)
            borttagna += 1
    if borttagna:
        skriv(f"  Tog bort {borttagna} __pycache__-mapp(ar). De skapas om av sig själva och ska inte ligga på GitHub.")


def main(kalla: Path = HAR, mal: Path | None = None, skriv=print) -> int:
    skriv("Uppdatering av Kvittens")
    skriv(f"Ny version: {kalla}")
    if not all((kalla / k).exists() for k in KANNETECKEN):
        skriv("\nSTOPP: den här mappen ser inte ut att innehålla appen. Packa upp zip-filen på nytt.")
        return 1
    mal = mal or hitta_installation()
    if mal is None:
        skriv("\nSTOPP: hittar ingen tidigare installation (letade efter Dokument/matarapp med .venv eller nyckelfil).")
        skriv("Är detta första installationen? Flytta då hela den här mappen till Dokument och dubbelklicka på installera.bat.")
        return 2
    if mal.resolve() == kalla.resolve():
        skriv("\nDen här mappen ÄR din installation, så det finns inget att kopiera. Jag städar bara.")
        stada(mal, skriv)
        return 0

    skriv(f"Din installation: {mal}\n")
    antal = kopiera(kalla, mal)
    skriv(f"  {antal} filer uppdaterade. Nyckelfilen och .venv är orörda.")
    stada(mal, skriv)
    skriv("\nKLART. Gör nu så här:")
    skriv("  1. Dubbelklicka på kontrollera.bat i din installation – allt ska vara [OK].")
    skriv("  2. Öppna GitHub Desktop. Ändringarna syns till vänster. Skriv t.ex. 'ny version' längst ned,")
    skriv("     tryck Commit to main och sedan Push origin. Appen på nätet uppdateras av sig själv.")
    return 0


if __name__ == "__main__":
    try:
        kod = main()
    except Exception as e:                       # inget ska kunna få fönstret att bara försvinna utan besked
        print(f"\nOVÄNTAT FEL: {e}\nSkicka en bild på det här fönstret till Claude.")
        kod = 9
    sys.exit(kod)
