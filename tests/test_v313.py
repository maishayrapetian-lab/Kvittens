"""Det som kom till efter felsökningen av v3.12. Ett test per rättad punkt."""
import io
import sys
from pathlib import Path

import pytest
from openpyxl import load_workbook

import config
import protokoll

ROT = Path(__file__).resolve().parents[1]


def _oppna(data):
    return load_workbook(io.BytesIO(data))


# ---- punkt A: konfigurationsfilen måste finnas i förrådet ----
def test_streamlit_konfigurationen_finns_och_skyddar_feltexter():
    fil = ROT / ".streamlit" / "config.toml"
    assert fil.is_file(), "utan .streamlit/config.toml får appen fel tema och visar hela feltexter"
    import tomllib
    konf = tomllib.loads(fil.read_text(encoding="utf8"))
    assert konf["client"]["showErrorDetails"] != "full"        # besökare ska inte se traceback
    assert konf["server"]["enableStaticServing"] is True       # typsnitten i static/ måste kunna hämtas
    assert konf["theme"]["primaryColor"].upper() == "#0E5A6B"


# ---- punkt B: ingen text får bli en Excel-formel ----
@pytest.mark.parametrize("text", ['=HYPERLINK("http://elak","klicka")', "=1+1", "+1+1", "-1+1", "@SUM(A1)",
                                  "=cmd|' /C calc'!A0"])
def test_text_som_ser_ut_som_en_formel_skrivs_som_text(text):
    data = protokoll.skapa_protokoll(
        [{"system": text, "placering": text, "typ": text, "noteringar": text, "dimension": text}],
        jobb={"objekt": text, "byggnad": text, "datum": "2026-09-21", "utfort_av": text})
    wb = _oppna(data)
    ws, fs = wb[config.BLAD_PROTOKOLL], wb[config.BLAD_FORSATTSBLAD]
    celler = ["A9", "C9", "E9", "G9", "L9", config.CELL_OBJEKT["protokoll"], config.CELL_UTFORT_AV["protokoll"]]
    for c in celler:
        assert ws[c].data_type == "s", f"{c} blev en formel ({ws[c].data_type})"
        assert ws[c].value == text
    assert fs[config.CELL_OBJEKT["forsattsblad"]].data_type == "s"


def test_vanlig_text_och_tal_paverkas_inte(facit):
    rader = [dict(r, fabrikat="IMI TA", system="VS10", placering="", noteringar="") for r in facit]
    ws = _oppna(protokoll.skapa_protokoll(rader, jobb={"objekt": "Testhuset", "byggnad": "", "datum": "2026-09-20",
                                                       "utfort_av": "Anna Andersson"}))[config.BLAD_PROTOKOLL]
    assert [ws.cell(9, k).value for k in range(1, 13)] == ["VS10", 246, None, "IMI TA", "STAF*", 3.7, 65, 13.9, 24, 1.88, 1.9, None]
    assert ws["K9"].data_type == "n" and ws["G3"].value == "-"


# ---- punkt C: spärren utan lösenord får inte gissa "egen dator" ----
@pytest.mark.parametrize("host,adress,vantat", [
    ("localhost", None, False), ("127.0.0.1", None, False), ("kvittens.streamlit.app", None, True),
    ("192.168.1.55", None, True), ("", "localhost", False), ("", "0.0.0.0", True), ("", None, False),
])
def test_nas_utifran(host, adress, vantat, monkeypatch):
    import streamlit as st
    sys.path.insert(0, str(ROT))
    import importlib.util
    spec = importlib.util.spec_from_file_location("app_nas", ROT / "app.py")
    # app.py ritar hela appen vid import – testa funktionen som fristående kod i stället
    kall = (ROT / "app.py").read_text(encoding="utf8")
    start = kall.index("def nas_utifran()")
    slut = kall.index("def krav_losenord()")
    rum = {"st": st}
    exec(compile(kall[start:slut], "app.py", "exec"), rum)
    monkeypatch.setattr(type(st.context), "headers", property(lambda self: {"Host": host} if host is not None else {}))
    monkeypatch.setattr(st, "get_option", lambda namn: adress if namn == "server.address" else None)
    assert rum["nas_utifran"]() is vantat
    assert spec is not None
