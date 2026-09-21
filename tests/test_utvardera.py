import sakerhet
import utvardera as u


def test_nyckeln_hittas_i_samma_fil_som_appen_anvander(tmp_path, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    (tmp_path / ".streamlit").mkdir()
    (tmp_path / ".streamlit" / "secrets.toml").write_text('# kommentar\nANTHROPIC_API_KEY = "sk-ant-abc123"\nAPP_LOSENORD = "x"\n', encoding="utf8")
    assert u.hitta_nyckel(tmp_path) == "sk-ant-abc123"


def test_filen_gar_fore_miljovariabeln_och_utan_bada_finns_ingen_nyckel(tmp_path, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-env")
    assert u.hitta_nyckel(tmp_path) == "sk-ant-env"                    # ingen nyckel i filen -> miljövariabeln duger
    monkeypatch.delenv("ANTHROPIC_API_KEY")
    assert u.hitta_nyckel(tmp_path) is None


def test_trasig_toml_tolkas_anda(tmp_path, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    (tmp_path / ".streamlit").mkdir()
    (tmp_path / ".streamlit" / "secrets.toml").write_text('ANTHROPIC_API_KEY = "sk-ant-xyz"\nAPP_LOSENORD = glömt citattecken\n', encoding="utf8")
    assert u.hitta_nyckel(tmp_path) == "sk-ant-xyz"


def _kor(monkeypatch, tmp_path, nyckel):
    monkeypatch.setattr(u, "hitta_nyckel", lambda *a: nyckel)
    monkeypatch.setattr(u, "_rader", [])
    kod = u.main(tmp_path)
    return kod, "\n".join(u._rader)


def test_utan_nyckel_far_man_besked_i_stallet_for_ett_fonster_som_forsvinner(monkeypatch, tmp_path):
    kod, text = _kor(monkeypatch, tmp_path, None)
    assert kod == 2 and "hittar ingen API-nyckel" in text and "kontrollera.bat" in text


def test_nyckel_id_kanns_igen(monkeypatch, tmp_path):
    kod, text = _kor(monkeypatch, tmp_path, "apikey_01ABC")
    assert kod == 2 and "apikey_" in text and "sk-ant-" in text


def test_svaga_losenord():
    assert all(sakerhet.svagt_losenord(x) for x in ("admin", "Admin", "", None, "kort", "aaaaaaaaaaaaaaaa", "1234567890"))
    assert not sakerhet.svagt_losenord("ventil-gurka-tåg-fjorton")
