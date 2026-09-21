import io

import pytest
from conftest import display, svar
from PIL import Image

import avlasning as a
import config


# ---- asterisken får aldrig försvinna ------------------------------------------
@pytest.mark.parametrize("ventil,typ,dim", [
    ("STAD* 10", "STAD*", "10"), ("STAD 10", "STAD", "10"), ("STAF* 65", "STAF*", "65"),
    ("STAF-SG* 100", "STAF-SG*", "100"), ("TA-COMPACT-P 15", "TA-COMPACT-P", "15"),
    ("STAD ZERO 20", "STAD ZERO", "20"), ("STAD*  32", "STAD*", "32"), ("STAD* DN 25", "STAD*", "25"),
    ("STAP", "STAP", ""), ("", "", ""),
])
def test_dela_ventil(ventil, typ, dim):
    assert a.dela_ventil(ventil) == (typ, dim)


def test_rad_fran_vanlig_display():
    (rad,) = a.till_rader(svar(), "IMG_2033.jpeg")
    assert (rad["typ"], rad["dimension"], rad["fabrikat"]) == ("STAD*", "25", config.FABRIKAT_TA_SCOPE)
    assert (rad["uppmatt"], rad["mattryck"], rad["kv"], rad["projekterat"], rad["installning"]) == \
           ("0.192", "6.52", "2.7", "0.19", "1.7")
    assert rad["noteringar"] == "" and rad["osakra_falt"] == [] and rad["procent"] == "101"


def test_bilden_med_pump_och_termometer():
    """IMG_1640: inget projekterat flöde, pumpdisplay och analog termometer i samma bild."""
    s = svar(
        displayer=[display(flode="0.741", dp="3.51", projekterat_flode="0", procent="-.-", ventil="STAD* 32",
                           installning="4", kv="14.2")],
        pumpar=[{"modell": "Grundfos MAGNA3", "reglertyp": "Konst. tryck", "driftsform": "Max.",
                 "uppfordringshojd": "9.7", "uppfordringshojd_enhet": "m", "flode": "", "flode_enhet": "",
                 "vatsketemperatur": "49", "osaker": False}],
        ovriga=[{"typ": "termometer", "varde": "59", "enhet": "°C", "analog": True, "kommentar": "oskarp"}])
    (rad,) = a.till_rader(s, "IMG_1640.jpeg")
    assert rad["projekterat"] == "" and rad["procent"] == ""
    assert any("Inget projekterat" in t for t in rad["info"])
    assert rad["noteringar"] == "Temp 49 °C (pump), ca 59 °C (termometer)"
    assert "noteringar" in rad["osakra_falt"]                     # analog avläsning = alltid osäker
    assert a.pumpforslag(s) == {"modell": "Grundfos MAGNA3", "driftform": "Konstant tryck",
                                "dynamiskt_mvp": "9.7", "driftsform_nu": "Max.", "osaker": False}


def test_temperatur_pa_displayen_hamnar_i_noteringar():
    (rad,) = a.till_rader(svar([display(temperatur="45.2")]), "x.jpg")
    assert rad["noteringar"] == "Temp 45,2 °C"


def test_flera_displayer_ger_flera_rader_och_bricka_blir_ventilnummer():
    rader = a.till_rader(svar([display(ventilnummer="246"), display(flode="4.24")]), "x.jpg")
    assert [r["display_nr"] for r in rader] == [1, 2]
    assert rader[0]["ventilnummer"] == "246" and rader[1]["uppmatt"] == "4.24"


def test_osakra_falt_oversatts_till_protokollets_faltnamn():
    (rad,) = a.till_rader(svar([display(osakra_falt=["kv", "flode", "okänt"])]), "x.jpg")
    assert rad["osakra_falt"] == ["kv", "uppmatt"]


def test_andra_enheter_raknas_om():
    (rad,) = a.till_rader(svar([display(flode="691", flode_enhet="l/h", dp="0.0652", dp_enhet="bar",
                                        projekterat_flode="684", projekterat_enhet="l/h")]), "x.jpg")
    assert float(rad["uppmatt"]) == pytest.approx(0.1919, abs=0.0001)
    assert float(rad["mattryck"]) == pytest.approx(6.52)
    assert float(rad["projekterat"]) == pytest.approx(0.19)
    assert len(rad["info"]) == 2


def test_okant_instrument_far_inget_fabrikat():
    (rad,) = a.till_rader(svar([display(instrument="")]), "x.jpg")
    assert rad["fabrikat"] == ""


def test_stada_svar_tal_ogiltiga_varden():
    s = a.stada_svar({"displayer": [{"flode": 0.192, "kv": None, "osakra_falt": None}], "pumpar": None})
    assert s["displayer"][0]["flode"] == "0.192" and s["displayer"][0]["kv"] == ""
    assert s["displayer"][0]["osakra_falt"] == [] and s["pumpar"] == [] and s["bildkvalitet"] == "ok"


# ---- dubbelkontrollen -----------------------------------------------------------
def test_jamfor_hittar_skillnad_men_bryr_sig_inte_om_komma_eller_mellanslag():
    ra = a.till_rader(svar([display()]), "x")
    rb = a.till_rader(svar([display(installning="1.8", kv="2,7", ventil="STAD*  25")]), "x")
    skillnader, olika = a.jamfor(ra, rb)
    assert olika is False and skillnader == {0: [("installning", "1.7", "1.8")]}


def test_jamfor_olika_antal_displayer():
    assert a.jamfor(a.till_rader(svar([display(), display()]), "x"), a.till_rader(svar(), "x")) == ({}, True)


# ---- bilder ----------------------------------------------------------------------
def _jpeg(storlek, orientering=None):
    bild = Image.new("RGB", storlek, "white")
    exif = Image.Exif()
    if orientering:
        exif[0x0112] = orientering
    ut = io.BytesIO()
    bild.save(ut, "JPEG", exif=exif)
    return ut.getvalue()


def test_bild_vrids_ratt_och_skalas_ned():
    ut = Image.open(io.BytesIO(a.forbered_bild(_jpeg((4032, 3024), orientering=6))))   # liggande fil, stående foto
    assert ut.size == (int(config.MAX_BILDKANT * 3024 / 4032), config.MAX_BILDKANT)
    assert a.forstark_bild(a.forbered_bild(_jpeg((800, 600))))[:2] == b"\xff\xd8"          # fortfarande JPEG


def test_trasig_fil_ger_begripligt_fel():
    with pytest.raises(a.AvlasningsFel):
        a.forbered_bild(b"inte en bild")


def test_sortering_efter_filnummer_annars_uppladdningsordning():
    poster = [{"namn": n, "seq": i, **a.sorteringsinfo(n, b"")} for i, n in
              enumerate(["IMG_2034.jpeg", "IMG_2033.jpeg", "IMG_2031.jpeg", "IMG_1640.jpeg"])]
    assert [p["namn"] for p in a.sortera(poster)] == ["IMG_1640.jpeg", "IMG_2031.jpeg", "IMG_2033.jpeg", "IMG_2034.jpeg"]
    poster.insert(0, {"namn": "FullSizeRender.jpeg", "seq": -1, **a.sorteringsinfo("FullSizeRender.jpeg", b"")})
    assert [p["namn"] for p in a.sortera(poster)][-1] == "FullSizeRender.jpeg"     # bilder utan nummer läggs sist
    assert [p["namn"] for p in a.sortera(poster)][0] == "IMG_1640.jpeg"


def test_sortering_efter_fototid_nar_alla_har_den():
    poster = [{"namn": "b.jpg", "seq": 0, "fototid": "2026:09:18 06:36:10", "filnummer": 1},
              {"namn": "a.jpg", "seq": 1, "fototid": "2026:09:18 06:29:55", "filnummer": 2}]
    assert [p["namn"] for p in a.sortera(poster)] == ["a.jpg", "b.jpg"]


# ---- schemat måste följa API:ts regler för strukturerade svar -----------------------
def test_schemat_foljer_api_reglerna():
    def ga(nod):
        if nod.get("type") == "object":
            assert nod["additionalProperties"] is False
            assert sorted(nod["required"]) == sorted(nod["properties"])      # inga valfria fält
            for under in nod["properties"].values():
                ga(under)
        elif nod.get("type") == "array":
            ga(nod["items"])
        assert isinstance(nod.get("type"), str) and "anyOf" not in nod       # inga unionstyper

    ga(a.SCHEMA)


# ---- API-anropet (med låtsas-klient) ---------------------------------------------------
class _Block:
    def __init__(self, text):
        self.type, self.text = "text", text


class _Klient:
    def __init__(self, text, stop="end_turn"):
        self._svar = type("S", (), {"content": [_Block(text)], "stop_reason": stop})()
        self.messages = self
        self.anrop = None

    def create(self, **kw):
        self.anrop = kw
        return self._svar


def test_las_av_bild_skickar_bild_och_schema():
    import json
    klient = _Klient(json.dumps(svar()))
    ut = a.las_av_bild(klient, _jpeg((100, 100)))
    assert ut["displayer"][0]["ventil"] == "STAD* 25"
    kw = klient.anrop
    assert kw["model"] == config.MODELL and kw["output_config"]["format"]["schema"] is a.SCHEMA
    assert kw["messages"][0]["content"][0]["type"] == "image"              # bilden före texten
    assert "temperature" not in kw                                         # stöds inte längre av API:t


@pytest.mark.parametrize("text,stop", [("{}", "max_tokens"), ("nej", "refusal"), ("inte json", "end_turn")])
def test_las_av_bild_felfall(text, stop):
    with pytest.raises(a.AvlasningsFel):
        a.las_av_bild(_Klient(text, stop), _jpeg((100, 100)))
