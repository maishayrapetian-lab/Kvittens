"""
utvardera.py – mät appens träffsäkerhet mot ett facit
======================================================
Enklast:  dubbelklicka på  utvardera.bat  (Windows)  eller  utvardera.command  (Mac).
Annars:   python utvardera.py            (använder mappen testbilder/)
          python utvardera.py min_mapp   (egen mapp med bilder + facit.json)

API-nyckeln hämtas från .streamlit/secrets.toml – samma fil som appen använder –
eller från miljövariabeln ANTHROPIC_API_KEY. Varje körning kostar ett API-anrop per bild.

Resultatet skrivs både på skärmen och till filen  utvardering_resultat.txt,
så att det finns kvar även om fönstret stängs.

Varför? Utan mätning vet man inte om en ändring (ny prompt, ny modell, annan
bildstorlek) gör appen bättre eller sämre. Kör före och efter varje ändring.
"""

from __future__ import annotations

import json
import sys
import traceback
from datetime import datetime
from pathlib import Path

ROT = Path(__file__).resolve().parent
RESULTATFIL = ROT / "utvardering_resultat.txt"
FALT = ("typ", "dimension", "installning", "kv", "mattryck", "projekterat", "uppmatt", "ventilnummer")

_rader: list[str] = []


def skriv(text: str = "") -> None:
    """Skriv både till skärmen och till resultatfilen."""
    _rader.append(text)
    try:
        print(text, flush=True)
    except UnicodeEncodeError:                       # äldre Windows-konsoler klarar inte alla tecken
        print(text.encode("ascii", "replace").decode(), flush=True)


def spara() -> None:
    RESULTATFIL.write_text("\n".join(_rader) + "\n", encoding="utf8")


def hitta_nyckel(rot: Path = ROT) -> str | None:
    """Reparerar secrets-filen vid behov (fel filnamn, saknade citattecken) och hämtar nyckeln."""
    import hemligheter

    for m in hemligheter.reparera(rot):
        skriv(f"[FIXAT] {m}")
    return hemligheter.hamta("ANTHROPIC_API_KEY", rot)


def norm(v) -> str:
    return str(v or "").replace(",", ".").strip()


def main(mapp: Path) -> int:
    skriv(f"Utvärdering av Kvittens – {datetime.now():%Y-%m-%d %H:%M}")
    skriv(f"Python {sys.version.split()[0]} · mapp: {mapp}")

    nyckel = hitta_nyckel()
    if not nyckel:
        skriv("\nSTOPP: hittar ingen API-nyckel.")
        skriv("Dubbelklicka på kontrollera.bat – den öppnar rätt fil åt dig och berättar var nyckeln ska in.")
        return 2
    if not nyckel.startswith("sk-ant-"):
        skriv("\nSTOPP: det som står som ANTHROPIC_API_KEY ser inte ut som en nyckel (ska börja med sk-ant-).")
        skriv("Står det kvar exempeltext, eller ett nyckel-ID som börjar med apikey_?")
        return 2

    try:
        import avlasning
        import config
    except ModuleNotFoundError as e:
        skriv(f"\nSTOPP: paketet '{e.name}' saknas i den Python som körs nu.")
        skriv("Kör skriptet via utvardera.bat / utvardera.command, som använder projektets virtuella miljö,")
        skriv("eller installera paketen med:  pip install -r requirements.txt")
        return 3

    facitfil = mapp / "facit.json"
    if not facitfil.exists():
        skriv(f"\nSTOPP: hittar inte {facitfil}.")
        return 2
    facit = {k: v for k, v in json.loads(facitfil.read_text(encoding="utf8")).items() if not k.startswith("_")}
    skriv(f"Modell: {config.MODELL} · {len(facit)} bilder · {sum(len(v) for v in facit.values())} displayer\n")

    klient = avlasning.skapa_klient(nyckel)
    ratt = totalt = 0
    fel_per_falt = {f: 0 for f in FALT}
    for bild, vantat in facit.items():
        try:
            svar = avlasning.las_av_bild(klient, avlasning.forbered_bild((mapp / bild).read_bytes()))
            rader = avlasning.till_rader(svar, bild)
        except (avlasning.AvlasningsFel, FileNotFoundError) as e:
            skriv(f"✗ {bild}: {e}")
            if "API-nyckeln" in str(e):                  # samma fel väntar på alla bilder – avbryt direkt
                skriv("\nSTOPP: nyckeln i .streamlit/secrets.toml godkänns inte. Skapa en ny i Console och klistra in den.")
                return 2
            totalt += len(vantat) * len(FALT)
            for f in FALT:
                fel_per_falt[f] += len(vantat)
            continue
        missar = 0
        if len(rader) != len(vantat):
            skriv(f"✗ {bild}: hittade {len(rader)} displayer, facit säger {len(vantat)}")
        for i, v in enumerate(vantat):
            fick = rader[i] if i < len(rader) else {}
            for f in FALT:
                totalt += 1
                if norm(fick.get(f)) == norm(v[f]):
                    ratt += 1
                else:
                    missar += 1
                    fel_per_falt[f] += 1
                    skriv(f"✗ {bild} display {i + 1} · {f}: fick '{fick.get(f, '')}', facit '{v[f]}'")
        if not missar and len(rader) == len(vantat):
            skriv(f"✓ {bild}: alla {len(vantat) * len(FALT)} fält rätt")

    skriv(f"\nRätt: {ratt} av {totalt} fält ({100 * ratt / max(totalt, 1):.1f} %)")
    skriv("Fel per fält: " + (", ".join(f"{f} {n}" for f, n in fel_per_falt.items() if n) or "inga"))
    return 0 if ratt == totalt else 1


if __name__ == "__main__":
    kod = 9
    try:
        kod = main(Path(sys.argv[1]) if len(sys.argv) > 1 else ROT / "testbilder")
    except Exception:                                # inget ska kunna få fönstret att bara försvinna utan besked
        skriv("\nOVÄNTAT FEL – klistra in allt nedan till Claude:\n" + traceback.format_exc())
    finally:
        skriv(f"\nResultatet är sparat i {RESULTATFIL.name}")
        spara()
    sys.exit(kod)
