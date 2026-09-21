import json
import sys
from pathlib import Path

import pytest

ROT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROT))


@pytest.fixture(scope="session")
def facit():
    data = json.loads((ROT / "testbilder" / "facit.json").read_text(encoding="utf8"))
    return [dict(rad, bild=bild) for bild, rader in data.items() if not bild.startswith("_") for rad in rader]


def display(**andringar):
    """En TA-SCOPE-display så som AI:n rapporterar den (alla fält text)."""
    bas = {"instrument": "TA SCOPE", "position": "mitten", "klocka": "06:33", "flode": "0.192", "flode_enhet": "l/s",
           "dp": "6.52", "dp_enhet": "kPa", "temperatur": "", "temperatur_enhet": "°C",
           "projekterat_flode": "0.19", "projekterat_enhet": "l/s", "procent": "101", "ventil": "STAD* 25",
           "installning": "1.7", "installning_enhet": "varv", "kv": "2.7", "medium": "Vatten",
           "ventilnummer": "", "osakra_falt": [], "kommentar": ""}
    bas.update(andringar)
    return bas


def svar(displayer=None, pumpar=None, ovriga=None, kvalitet="bra"):
    return {"displayer": displayer if displayer is not None else [display()],
            "pumpar": pumpar or [], "ovriga_matare": ovriga or [], "bildkvalitet": kvalitet}
