import pytest

import kontroller as k


# ---- talparsning ------------------------------------------------------------
@pytest.mark.parametrize("text,vantat", [
    ("1.90", (1.9, 2)), ("24.0", (24.0, 1)), ("2,4", (2.4, 1)), ("72", (72.0, 0)),
    (" 0.021 ", (0.021, 3)), ("", (None, 0)), (None, (None, 0)), ("-.-", (None, 0)), ("DN20", (None, 0)),
])
def test_tolka_tal(text, vantat):
    assert k.tolka_tal(text) == vantat


def test_enheter():
    assert k.flodesfaktor("l/s") == 1
    assert k.flodesfaktor("m³/h") == pytest.approx(1 / 3.6)
    assert k.flodesfaktor("L/H") == pytest.approx(1 / 3600)
    assert k.tryckfaktor("kPa") == 1
    assert k.tryckfaktor("bar") == 100
    assert k.tryckfaktor("mvp") == pytest.approx(9.80665)
    assert k.flodesfaktor("okänd") is None
    assert k.mvp_till_kpa(9.7) == pytest.approx(95.1, abs=0.1)


# ---- Kv-kontrollen -----------------------------------------------------------
def test_imi_exempel():
    """IMI:s eget exempel: STAD DN25, Kv 5, Δp 10 kPa -> 0,44 l/s."""
    assert k.berakna_kv(0.4392, 10) == pytest.approx(5.0, rel=0.001)


def test_alla_facitrader_gar_ihop(facit):
    """De tio verkliga displayerna ska passera utan falsklarm."""
    for rad in facit:
        r = k.kv_kontroll(rad["uppmatt"], rad["mattryck"], rad["kv"])
        assert r.gick_att_rakna and r.ok, rad
        assert abs(r.avvikelse) < 0.005, rad            # verkliga displayer: inom 0,5 %


@pytest.mark.parametrize("falt,fel", [
    ("uppmatt", "0.792"),    # 1 -> 7 i flödet
    ("uppmatt", "1.92"),     # flyttat decimaltecken
    ("mattryck", "8.52"),    # 6 -> 8 i mättrycket
    ("mattryck", "65.2"),    # flyttat decimaltecken
    ("kv", "27"),            # tappat decimaltecken
    ("kv", "2.1"),           # 7 -> 1
])
def test_felavlasningar_fangas(falt, fel):
    rad = {"uppmatt": "0.192", "mattryck": "6.52", "kv": "2.7"}
    rad[falt] = fel
    assert not k.kv_kontroll(rad["uppmatt"], rad["mattryck"], rad["kv"]).ok


def test_forvaxlade_falt_fangas():
    """Projekterat flöde (0.19) inläst som uppmätt flöde går igenom BARA om värdena råkar ligga nära –
    här ligger de 1 % isär och ryms i avrundningen, så det är procentkontrollens jobb. Men förväxlar
    AI:n flöde och Dp smäller det direkt."""
    assert not k.kv_kontroll("6.52", "0.192", "2.7").ok


def test_sista_decimalen_kan_slinka_igenom():
    """Ärlig begränsning: Dp 6.52 -> 6.57 ändrar Kv med 0,4 % och ryms i displayens avrundning."""
    assert k.kv_kontroll("0.192", "6.57", "2.7").ok


def test_kv_kontroll_med_andra_enheter():
    assert k.kv_kontroll("0.6912", "0.0652", "2.7", "m3/h", "bar").ok


def test_ofullstandig_rad_gar_inte_att_rakna():
    assert not k.kv_kontroll("", "6.52", "2.7").gick_att_rakna
    assert not k.kv_kontroll("0.192", "0", "2.7").gick_att_rakna


# ---- procentkontrollen --------------------------------------------------------
def test_procent_gar_ihop_pa_facit(facit):
    procent = {"0.021": "103", "0.192": "101", "0.238": "99", "0.368": "102", "1.90": "101",
               "4.21": "100", "4.24": "101", "3.88": "101", "3.82": "99"}
    for rad in facit:
        if rad["projekterat"]:
            ok, _ = k.procent_kontroll(rad["uppmatt"], rad["projekterat"], procent[rad["uppmatt"]])
            assert ok, rad


def test_procent_fangar_fel_projekterat():
    ok, ber = k.procent_kontroll("0.192", "0.49", "101")     # 0.19 inläst som 0.49
    assert ok is False and ber == pytest.approx(39, abs=1)


def test_procent_utan_underlag():
    assert k.procent_kontroll("0.741", "", "") == (None, None)


# ---- hela raden ---------------------------------------------------------------
def _rad(**a):
    bas = {"typ": "STAD*", "dimension": "25", "installning": "1.7", "kv": "2.7", "mattryck": "6.52",
           "projekterat": "0.19", "uppmatt": "0.192", "procent": "101", "osakra_falt": []}
    bas.update(a)
    return bas


def test_ren_rad_ger_inga_flaggor():
    assert k.kontrollera_rad(_rad()) == []


def test_skymt_kv_bekraftas_av_berakningen():
    """Bild 1 i testbanken: reflex över Kv. AI:n är osäker, men ekvationen går ihop."""
    flaggor = k.kontrollera_rad(_rad(dimension="10", installning="1.6", kv="0.158", mattryck="22.8",
                                     projekterat="0.02", uppmatt="0.021", procent="103", osakra_falt=["kv"]))
    assert [f.niva for f in flaggor] == [k.OSAKER]
    assert "stämmer med beräkningen" in flaggor[0].text and "0,154" in flaggor[0].text


def test_fel_kv_ger_rod_flagga_med_berakat_varde():
    flaggor = k.kontrollera_rad(_rad(kv="2.1"))
    assert flaggor[0].niva == k.FEL and "2,71" in flaggor[0].text


def test_saknat_kv_far_forslag():
    flaggor = k.kontrollera_rad(_rad(kv=""))
    assert flaggor[0].niva == k.OSAKER and "2,71" in flaggor[0].text


def test_lagt_mattryck_och_for_manga_varv():
    nivaer = {f.falt: f.niva for f in k.kontrollera_rad(_rad(mattryck="2.10", uppmatt="0.109", installning="4.5", procent="57"))}
    assert nivaer["mattryck"] == k.INFO and nivaer["installning"] == k.FEL


def test_flodesavvikelse_mot_projekterat_ar_info_inte_fel():
    flaggor = k.kontrollera_rad(_rad(uppmatt="0.230", kv="3.24", procent="121"))
    assert [(f.niva, f.falt) for f in flaggor] == [(k.INFO, "uppmatt")]


def test_text_i_talfalt_flaggas():
    assert any(f.niva == k.FEL and f.falt == "uppmatt" for f in k.kontrollera_rad(_rad(uppmatt="O.192")))


def test_dubbletter(facit):
    rader = [dict(r, klocka=kl) for r, kl in zip(facit[-4:], ("04:34", "04:34", "04:36", "04:36"), strict=True)]
    assert k.hitta_dubbletter(rader) == {1: 0, 3: 2}
    assert k.hitta_dubbletter([dict(r, klocka="") for r in rader]) == {}
