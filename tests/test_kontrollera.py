import anthropic
import pytest

import kontrollera as k

NYCKEL = "sk-ant-api03-" + "A1b2C3d4" * 12


@pytest.fixture(autouse=True)
def _rent(monkeypatch, tmp_path):
    monkeypatch.setattr(k, "_rader", [])
    monkeypatch.setattr(k, "RESULTATFIL", tmp_path / "kontroll_resultat.txt")


def _text():
    return "\n".join(k._rader)


def test_python_paket_och_filer_ar_grona_har():
    assert k.kontroll_python() and k.kontroll_paket() and k.kontroll_filer()
    assert "[FEL]" not in _text()


def test_saknad_nyckel_ger_kod_2(monkeypatch):
    monkeypatch.setattr("hemligheter.reparera", lambda rot: ["Skapade .streamlit/secrets.toml."])
    monkeypatch.setattr("hemligheter.hamta", lambda namn, rot=None: None)
    assert k.main() == 2 and "[FIXAT] Skapade" in _text() and "Ingen API-nyckel" in _text()


def _fel(klass, status, text):
    """Bygg ett SDK-fel utan att vara beroende av vilket HTTP-bibliotek SDK:n råkar använda."""
    e = klass.__new__(klass)
    Exception.__init__(e, text)
    e.message, e.status_code = text, status
    return e


@pytest.mark.parametrize("undantag,vantat", [
    (lambda: _fel(anthropic.AuthenticationError, 401, "invalid x-api-key"), "Nyckeln godkänns inte"),
    (lambda: _fel(anthropic.BadRequestError, 400, "Your credit balance is too low to access the API"), "Kontot saknar saldo"),
    (lambda: _fel(anthropic.NotFoundError, 404, "model not found"), "finns inte för ditt konto"),
    (lambda: _fel(anthropic.APIConnectionError, 0, "Connection error."), "Ingen kontakt"),
])
def test_api_fel_forklaras_pa_vanlig_svenska(monkeypatch, undantag, vantat):
    class Klient:
        def __init__(self, **kw):
            self.messages = self

        def create(self, **kw):
            raise undantag()

    monkeypatch.setattr(anthropic, "Anthropic", Klient)
    assert k.kontroll_api(NYCKEL) is False and vantat in _text() and NYCKEL not in _text()


def test_provavlasning_rapporterar_ratt_och_fel(monkeypatch):
    from conftest import display, svar
    monkeypatch.setattr("avlasning.skapa_klient", lambda n: None)
    monkeypatch.setattr("avlasning.las_av_bild", lambda klient, jpeg: svar())                       # = facit för IMG_2033
    assert k.kontroll_avlasning(NYCKEL) and "alla 8 fält rätt" in _text()
    monkeypatch.setattr("avlasning.las_av_bild", lambda klient, jpeg: svar([display(kv="2.1")]))
    assert k.kontroll_avlasning(NYCKEL) and "AI:n läste '2.1', på displayen står '2.7'" in _text()
