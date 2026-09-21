import time

import lagring


def _rent():
    lager = lagring._lager()
    lager["jobb"].clear()
    lager["raknare"].clear()
    return lager


def test_spara_och_hamta_med_utkast_av_tabellerna():
    _rent()
    kod = lagring.ny_kod()
    lagring.spara(kod, {"resultat": {"a": 1}, "steg": 2, "bas": {1: "bekräftad"}, "fil": "ska inte sparas"}, utkast={1: "rättad", 2: "ny"})
    data = lagring.hamta(kod)
    assert data["resultat"] == {"a": 1} and data["steg"] == 2 and "fil" not in data
    assert data["bas"] == {1: "rättad", 2: "ny"}                       # det man hann rätta följer med
    assert lagring.hamta("fel-kod") is None and len(kod) >= 16


def test_gamla_jobb_forsvinner_och_antalet_ar_begransat(monkeypatch):
    lager = _rent()
    lagring.spara("gammalt", {"resultat": {"a": 1}})
    lager["jobb"]["gammalt"]["tid"] = time.time() - (lagring.MAX_TIMMAR * 3600 + 5)
    assert lagring.hamta("gammalt") is None
    monkeypatch.setattr(lagring, "MAX_JOBB", 3)
    for i in range(5):                                                # fem jobb, det äldsta först
        lager["jobb"][f"jobb{i}"] = {"tid": time.time() - 100 + i, "data": {"resultat": {"a": i}}, "utkast": {}}
    lagring.spara("sist", {"resultat": {"a": 9}})
    assert sorted(lager["jobb"]) == ["jobb3", "jobb4", "sist"]        # de tre nyaste är kvar
    assert lagring.hamta("jobb0") is None and lagring.hamta("sist")["resultat"] == {"a": 9}


def test_glom_och_dygnsraknare():
    _rent()
    lagring.spara("x", {"resultat": {"a": 1}})
    lagring.glom("x")
    assert lagring.hamta("x") is None
    assert lagring.bilder_kvar_idag(10) == 10
    lagring.rakna_bilder(7)
    assert lagring.bilder_kvar_idag(10) == 3
    lagring.rakna_bilder(7)
    assert lagring.bilder_kvar_idag(10) == 0
