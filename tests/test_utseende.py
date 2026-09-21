import re

import demo
import kontroller as k
import utseende as u

RAD = {"ta_med": True, "typ": "STAD*", "dimension": "25", "installning": "1.7", "kv": "2.7", "mattryck": "6.52",
       "projekterat": "0.19", "uppmatt": "0.192", "ventilnummer": "", "noteringar": ""}


def test_kort_for_ren_matning():
    html = u.matkort(5, RAD, [])
    assert "Mätning 5" in html and "STAD* 25" in html and ">Stämmer<" in html
    assert "0,192" in html and "6,52" in html                      # svenskt decimalkomma i visningen
    assert "ma-flaggor" not in html


def test_fientlig_text_blir_aldrig_html():
    html = u.matkort(1, dict(RAD, typ="<script>alert(1)</script>", ventilnummer='"><img src=x>', noteringar="<b>x</b>"),
                     [k.Flagga(k.INFO, "", "<i>hej</i>")])
    assert "<script>" not in html and "<img" not in html and "<i>hej" not in html and "<b>x" not in html
    assert "&lt;script&gt;" in html


def test_remsan_visaren_inom_bandet_nar_det_stammer():
    html = u.kontrollremsa(k.kv_kontroll("0.192", "6.52", "2.7"), "2.7")
    band_v, band_h = (float(x) for x in re.search(r'ma-band" style="left:([\d.]+)%;right:([\d.]+)%', html).groups())
    visare = float(re.search(r'ma-visare" style="left:([\d.]+)%', html).group(1))
    assert band_v < visare < 100 - band_h and 'class="ma-spar"' in html
    assert "2,71" in html and "+0,3 %" in html


def test_remsan_blir_rod_och_visaren_stannar_i_kanten_vid_fel():
    html = u.kontrollremsa(k.kv_kontroll("0.192", "6.52", "27"), "27")
    assert 'class="ma-spar fel"' in html and 'ma-visare" style="left:1.5%' in html


def test_ingen_remsa_utan_underlag():
    assert u.kontrollremsa(k.kv_kontroll("", "6.52", "2.7"), "2.7") == ""


def test_status_och_markering_av_falt():
    flaggor = [k.Flagga(k.OSAKER, "kv", "svårläst"), k.Flagga(k.INFO, "", "upplysning")]
    assert u.status_for(flaggor) == ("osaker", "Osäker")
    assert u.status_for(flaggor + [k.Flagga(k.FEL, "kv", "fel")]) == ("fel", "Kontrollera")
    html = u.matkort(1, RAD, flaggor)
    assert 'class="markt"' in html and ">Osäker<" in html and ">Info<" in html


def test_urbockad_matning_och_notering():
    assert "Tas inte med" in u.matkort(2, dict(RAD, ta_med=False), [])
    assert "Noteringar: <b>Temp 49 °C (pump)</b>" in u.matkort(2, dict(RAD, noteringar="Temp 49 °C (pump)"), [])


def test_sidhuvud_visar_ratt_steg():
    html = u.sidhuvud(2)
    assert html.count('class="klar"') == 1 and html.count('class="nu"') == 1 and "Granska" in html


def test_demot_ger_tio_matningar_som_alla_gar_ihop():
    poster = demo.demoposter()
    rader = [r for p in poster.values() for r in p["rader"]]
    assert len(poster) == 7 and len(rader) == 10
    assert all(r["typ"].endswith("*") and r["fabrikat"] == "IMI TA" for r in rader)
    assert not [f for r in rader for f in k.kontrollera_rad(r) if f.niva == k.FEL]
    assert all(p["visning"][:2] == b"\xff\xd8" for p in poster.values())


def test_ordmarke_och_upphov_syns(monkeypatch):
    import config
    assert u.ordmarke() == '<i class="ma-kv">Kv</i>ittens'
    huvud = u.sidhuvud(1)
    assert "av Mais Hayrapetian" in huvud and 'ma-kv">Kv</i>ittens' in huvud
    assert "Skapad av Mais Hayrapetian" in u.sidfot() and "© 2026 Mais Hayrapetian" in u.sidfot()
    monkeypatch.setattr(config, "APPNAMN", "Annat <namn>")               # byter man namn ska accenten inte ställa till det
    assert u.ordmarke() == "Annat &lt;namn&gt;"
