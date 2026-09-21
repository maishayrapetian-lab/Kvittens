"""Det som kom till efter kodgranskningen. Varje punkt har minst ett test som visar att skyddet faktiskt slår till."""
import smtplib

import pytest
from conftest import display, svar

import avlasning
import config
import kontroller as k
import mejl
import sakerhet

RAD = {"typ": "STAD*", "dimension": "25", "installning": "1.7", "kv": "2.7", "mattryck": "6.52",
       "projekterat": "0.19", "uppmatt": "0.192", "procent": "101", "osakra_falt": []}


# ---- punkt 10: fler kontroller av mätvärden ----
def test_negativa_och_nollvarden_kan_aldrig_vara_en_matning():
    for falt, varde in (("uppmatt", "-0.192"), ("mattryck", "0"), ("kv", "0.0"), ("installning", "-1")):
        flaggor = k.kontrollera_rad(dict(RAD, **{falt: varde}))
        assert any(f.niva == k.FEL and f.falt == falt and ("negativt" in f.text or "noll" in f.text) for f in flaggor), falt
    assert not any("noll" in f.text for f in k.kontrollera_rad(dict(RAD, installning="0")))      # helt stängd ventil ÄR möjlig


def test_ovanlig_dimension_for_typen_flaggas_men_okanda_typer_lamnas_ifred():
    (f,) = [f for f in k.kontrollera_rad(dict(RAD, dimension="65")) if f.falt == "dimension"]
    assert f.niva == k.OSAKER and "ovanlig för STAD*" in f.text and "10, 15, 20" in f.text
    assert not [f for f in k.kontrollera_rad(dict(RAD, typ="STAF*", dimension="80", kv="72", uppmatt="3.88", mattryck="3.75",
                                                  projekterat="3.84", installning="5.6")) if f.falt == "dimension"]
    assert not [f for f in k.kontrollera_rad(dict(RAD, typ="TBV-CM", dimension="99")) if f.falt == "dimension"]


def test_samma_ventilnummer_pa_flera_rader():
    rader = [{"ventilnummer": "246"}, {"ventilnummer": ""}, {"ventilnummer": " 246 "}, {"ventilnummer": "RV-7"}, {"ventilnummer": "rv-7"}]
    assert k.dubbla_ventilnummer(rader) == {"246": [1, 3], "rv-7": [4, 5]}
    assert k.dubbla_ventilnummer([{"ventilnummer": "1"}, {"ventilnummer": "2"}, {}]) == {}


def test_okand_enhet_raknas_inte_om_i_tysthet():
    """Förut lämnades värdet oförändrat utan ett ord – 691 'gpm' hade hamnat i l/s-kolumnen."""
    (rad,) = avlasning.till_rader(svar([display(flode="691", flode_enhet="gpm")]), "x.jpg")
    assert rad["uppmatt"] == "691" and "uppmatt" in rad["osakra_falt"]
    assert any("Okänd enhet ”gpm”" in t and "INTE omräknat" in t for t in rad["info"])
    (ok,) = avlasning.till_rader(svar(), "x.jpg")
    assert ok["osakra_falt"] == [] and ok["info"] == []


# ---- punkt 9: flera pumpar ----
def test_alla_pumpar_redovisas():
    pump = {"modell": "Grundfos MAGNA3", "reglertyp": "Konst. tryck", "driftsform": "Auto", "uppfordringshojd": "9.7",
            "uppfordringshojd_enhet": "m", "flode": "", "flode_enhet": "", "vatsketemperatur": "", "osaker": False}
    s = svar(pumpar=[pump, dict(pump, modell="Wilo Stratos", reglertyp="Prop. tryck", uppfordringshojd="45", uppfordringshojd_enhet="kPa")])
    forslag = avlasning.alla_pumpforslag(s)
    assert [f["modell"] for f in forslag] == ["Grundfos MAGNA3", "Wilo Stratos"]
    assert forslag[1]["driftform"] == "Proportionellt tryck" and float(forslag[1]["dynamiskt_mvp"]) == pytest.approx(4.59, abs=0.01)
    assert avlasning.pumpforslag(s) == forslag[0] and avlasning.alla_pumpforslag(svar()) == []


# ---- punkt 11: spärr efter upprepade felförsök ----
def test_inloggningen_sparras_och_oppnas_igen():
    s = sakerhet.Sparr(max_forsok=3, sparrtid_s=600)
    for _ in range(2):
        s.fel_forsok(nu=1000)
    assert s.sparrad(1000) == 0
    s.fel_forsok(nu=1000)
    assert s.sparrad(1001) == 599 and s.sparrad(1600) == 0              # spärrad i tio minuter, sedan öppen
    s.fel_forsok(nu=2000)
    s.lyckat()
    s.fel_forsok(nu=2001)
    s.fel_forsok(nu=2002)
    assert s.sparrad(2003) == 0                                         # rätt lösenord nollställer räknaren


# ---- punkt 12: mejlet ----
class _Server:
    brev = None

    def __init__(self, *a, **kw): ...
    def starttls(self, context=None): ...
    def login(self, a, b): ...
    def quit(self): ...

    def send_message(self, brev):
        _Server.brev = brev


INST = {"server": "smtp.gmail.com", "port": 587, "anvandare": "appen@gmail.com", "losenord": "x", "avsandare": "appen@gmail.com"}


def test_dold_arkivkopia_och_storleksgrans(monkeypatch):
    monkeypatch.setattr(smtplib, "SMTP", _Server)
    monkeypatch.setattr(config, "TILLATNA_MEJLDOMANER", [])
    monkeypatch.setattr(config, "MEJL_KOPIA_TILL", "arkiv@foretaget.se")
    mejl.skicka(INST, "kalle@foretaget.se", "p.xlsx", b"x", "O", "2026-09-21", 1, "K")
    assert _Server.brev["Bcc"] == "arkiv@foretaget.se" and _Server.brev["To"] == "kalle@foretaget.se"
    monkeypatch.setattr(config, "MEJL_KOPIA_TILL", "")
    mejl.skicka(INST, "kalle@foretaget.se", "p.xlsx", b"x", "O", "2026-09-21", 1, "K")
    assert _Server.brev["Bcc"] is None
    with pytest.raises(mejl.MejlFel, match="större än"):
        mejl.skicka(INST, "kalle@foretaget.se", "p.xlsx", b"x" * (config.MAX_BILAGA_MB * 1024 * 1024 + 1), "O", "2026-09-21", 1, "K")


# ---- punkt 15: loggen får aldrig innehålla känsligt ----
def test_loggen_kortar_jobbkoden_och_tal_inte_fritext(caplog):
    import logg
    logg._logg.propagate = True
    with caplog.at_level("INFO", logger="kvittens"):
        logg.fel("AbCdEf123456hemligkod", "mejl", mejl.MejlFel("Ingen kontakt med mejlservern."))
        logg.info(None, "felaktigt lösenord vid inloggning")
    logg._logg.propagate = False
    text = caplog.text
    assert "[AbCdEf]" in text and "hemligkod" not in text and "MejlFel" in text and "[------]" in text
