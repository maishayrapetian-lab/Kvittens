"""Filen med API-nyckeln är det som oftast går fel för den som inte kodar. Därför testas den hårt."""
import tomllib

import hemligheter as h

NYCKEL = "sk-ant-api03-" + "A1b2C3d4" * 12          # påhittad, men med en riktig nyckels form och längd


def _mapp(tmp_path):
    (tmp_path / ".streamlit").mkdir()
    return tmp_path / ".streamlit"


def test_exakt_det_som_hande_nyckel_i_exempelfilen_utan_citattecken(tmp_path, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    m = _mapp(tmp_path)
    (m / "secrets.toml").write_text('APP_LOSENORD = "admin"\n', encoding="utf8")                  # den fil appen läser: ingen nyckel
    (m / "secrets.toml.example").write_text(                                                      # den fil som redigerades
        f"# Kopiera den här filen ...\n\nANTHROPIC_API_KEY = {NYCKEL}\n\nAPP_LOSENORD = Trumpet-och-Flöjt85!\n", encoding="utf8")

    medd = h.reparera(tmp_path)

    assert h.hamta("ANTHROPIC_API_KEY", tmp_path) == NYCKEL
    assert h.hamta("APP_LOSENORD", tmp_path) == "Trumpet-och-Flöjt85!"                           # det starka lösenordet ersätter "admin"
    assert tomllib.loads((m / "secrets.toml").read_text(encoding="utf8"))["ANTHROPIC_API_KEY"] == NYCKEL   # giltig TOML nu
    assert NYCKEL not in (m / "secrets.toml.example").read_text(encoding="utf8")                  # nyckeln ligger inte kvar i fel fil
    assert any("fel fil" in x for x in medd) and not any(NYCKEL in x for x in medd)               # besked, men aldrig nyckeln


def test_ratt_fil_men_utan_citattecken_rattas(tmp_path):
    m = _mapp(tmp_path)
    (m / "secrets.toml").write_text(f"ANTHROPIC_API_KEY = {NYCKEL}\r\nAPP_LOSENORD = hej!på dig\r\n", encoding="utf8")
    medd = h.reparera(tmp_path)
    d = tomllib.loads((m / "secrets.toml").read_text(encoding="utf8"))
    assert d == {"ANTHROPIC_API_KEY": NYCKEL, "APP_LOSENORD": "hej!på dig"} and any("inte giltig" in x for x in medd)


def test_korrekt_fil_lamnas_helt_orord(tmp_path):
    m = _mapp(tmp_path)
    text = f'# min kommentar\nANTHROPIC_API_KEY = "{NYCKEL}"\nAPP_LOSENORD = "ventil-gurka-tåg-fjorton"\n'
    (m / "secrets.toml").write_text(text, encoding="utf8")
    assert h.reparera(tmp_path) == [] and (m / "secrets.toml").read_text(encoding="utf8") == text


def test_anteckningar_sparade_som_txt_med_bom_och_smarta_citattecken(tmp_path):
    m = _mapp(tmp_path)
    (m / "secrets.toml.txt").write_text(f"ANTHROPIC_API_KEY = “{NYCKEL}”\n", encoding="utf-8-sig")
    h.reparera(tmp_path)
    assert h.hamta("ANTHROPIC_API_KEY", tmp_path) == NYCKEL


def test_inget_alls_ger_en_fardig_fil_att_klistra_i(tmp_path, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    medd = h.reparera(tmp_path)
    assert (tmp_path / ".streamlit" / "secrets.toml").exists() and "Skapade" in medd[0]
    assert h.hamta("ANTHROPIC_API_KEY", tmp_path) is None                                         # platshållaren räknas inte som nyckel
    assert h.reparera(tmp_path) == []                                                             # andra körningen ändrar inget


def test_platshallare_och_nyckel_id_ar_inte_riktiga_nycklar():
    assert not h.riktig_nyckel("sk-ant-...") and not h.riktig_nyckel("apikey_01WxMjrZonuYcVLTTfgsUhC1") and not h.riktig_nyckel(None)
    assert h.riktig_nyckel(NYCKEL)


def test_losenord_med_krangliga_tecken_overlever(tmp_path):
    m = _mapp(tmp_path)
    (m / "secrets.toml").write_text(f"ANTHROPIC_API_KEY = {NYCKEL}\nAPP_LOSENORD = it's \\ \"knepigt\" #1\n", encoding="utf8")
    h.reparera(tmp_path)
    assert tomllib.loads((m / "secrets.toml").read_text(encoding="utf8"))["APP_LOSENORD"] == 'it\'s \\ "knepigt" #1'


def test_projektets_fil_vinner_over_en_gammal_nyckel_i_miljon(tmp_path, monkeypatch):
    """Det som hände på riktigt: kontrollen var grön men appen skickade en gammal, borttagen nyckel."""
    m = _mapp(tmp_path)
    (m / "secrets.toml").write_text(f'ANTHROPIC_API_KEY = "{NYCKEL}"\n', encoding="utf8")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-api03-GAMMAL" + "x" * 60)
    assert h.hamta("ANTHROPIC_API_KEY", tmp_path) == NYCKEL
    assert any("miljövariabeln" in x and "…xxxx" in x for x in h.skuggnycklar(tmp_path))


def test_miljovariabeln_anvands_bara_nar_filen_saknar_nyckel(tmp_path, monkeypatch):
    _mapp(tmp_path)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-fran-miljon")
    assert h.hamta("ANTHROPIC_API_KEY", tmp_path) == "sk-ant-fran-miljon"


def test_nyckelbyte_galler_direkt_utan_omstart(tmp_path, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    m = _mapp(tmp_path)
    (m / "secrets.toml").write_text(f'ANTHROPIC_API_KEY = "{NYCKEL}"\n', encoding="utf8")
    assert h.hamta("ANTHROPIC_API_KEY", tmp_path) == NYCKEL
    ny = NYCKEL[:-4] + "NY99"
    (m / "secrets.toml").write_text(f'ANTHROPIC_API_KEY = "{ny}"\n', encoding="utf8")
    assert h.hamta("ANTHROPIC_API_KEY", tmp_path) == ny and h.fingeravtryck(ny) == "…NY99"
