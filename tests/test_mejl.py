import smtplib
from email import message_from_bytes

import pytest

import config
import mejl

INST = {"server": "smtp.gmail.com", "port": 587, "anvandare": "appen@gmail.com", "losenord": "abcdefghijklmnop", "avsandare": "appen@gmail.com"}


class LatsasServer:
    """Står in för mejlservern: spelar in vad som skickas i stället för att skicka det."""
    loggar = []

    def __init__(self, server, port, **kw):
        self.info = {"server": server, "port": port, "tls": False, "inloggad": None, "brev": None, "stangd": False}
        LatsasServer.loggar.append(self.info)

    def starttls(self, context=None):
        self.info["tls"] = True

    def login(self, anvandare, losenord):
        if losenord == "fel":
            raise smtplib.SMTPAuthenticationError(535, b"Username and Password not accepted")
        self.info["inloggad"] = (anvandare, losenord)

    def send_message(self, brev):
        self.info["brev"] = brev

    def quit(self):
        self.info["stangd"] = True


@pytest.fixture(autouse=True)
def _latsas(monkeypatch):
    LatsasServer.loggar = []
    monkeypatch.setattr(smtplib, "SMTP", LatsasServer)
    monkeypatch.setattr(smtplib, "SMTP_SSL", LatsasServer)
    monkeypatch.setattr(config, "TILLATNA_MEJLDOMANER", [])


def test_installningar_gmail_som_standard_och_app_losenord_utan_mellanslag():
    varden = {"SMTP_ANVANDARE": "appen@gmail.com", "SMTP_LOSENORD": "abcd efgh ijkl mnop"}
    assert mejl.installningar(varden.get) == INST
    assert mejl.installningar({}.get) is None and mejl.installningar({"SMTP_ANVANDARE": "x@y.se"}.get) is None


def test_protokollet_skickas_krypterat_som_bilaga():
    mejl.skicka(INST, " kalle@foretaget.se ", "Injusteringsprotokoll_Kv._Eken_2026-09-21.xlsx", b"PK-excelinnehall", "Kv. Eken", "2026-09-21", 10, "Kalle K")
    (s,) = LatsasServer.loggar
    assert s["tls"] and s["inloggad"] == ("appen@gmail.com", "abcdefghijklmnop") and s["stangd"]
    brev = s["brev"]
    assert brev["To"] == "kalle@foretaget.se" and brev["Subject"] == "Injusteringsprotokoll Kv. Eken 2026-09-21"
    assert "appen@gmail.com" in brev["From"]
    bilaga = [d for d in message_from_bytes(bytes(brev)).walk() if d.get_filename()][0]
    assert bilaga.get_filename() == "Injusteringsprotokoll_Kv._Eken_2026-09-21.xlsx"
    assert bilaga.get_content_type().endswith("spreadsheetml.sheet") and bilaga.get_payload(decode=True) == b"PK-excelinnehall"
    assert "Antal mätningar: 10" in brev.get_body().get_content() and "Utfört av: Kalle K" in brev.get_body().get_content()


@pytest.mark.parametrize("adress", ["", "kalle", "kalle@", "kalle@foretaget", "a b@foretaget.se", "kalle@foretaget.se\nBcc: alla@spam.se",
                                    "kalle@foretaget.se, annan@spam.se", "<kalle@foretaget.se>"])
def test_felaktiga_adresser_och_forsok_att_smyga_in_mottagare_stoppas(adress):
    with pytest.raises(mejl.MejlFel):
        mejl.skicka(INST, adress, "p.xlsx", b"x", "Objekt", "2026-09-21", 1, "K")
    assert LatsasServer.loggar == []                                   # servern kontaktas aldrig


def test_mottagardomaner_kan_lasas(monkeypatch):
    monkeypatch.setattr(config, "TILLATNA_MEJLDOMANER", ["foretaget.se"])
    mejl.skicka(INST, "kalle@FORETAGET.se", "p.xlsx", b"x", "O", "2026-09-21", 1, "K")
    with pytest.raises(mejl.MejlFel, match="@foretaget.se"):
        mejl.skicka(INST, "kalle@gmail.com", "p.xlsx", b"x", "O", "2026-09-21", 1, "K")


def test_fel_losenord_forklaras_begripligt():
    with pytest.raises(mejl.MejlFel, match="app-lösenord"):
        mejl.skicka(dict(INST, losenord="fel"), "kalle@foretaget.se", "p.xlsx", b"x", "O", "2026-09-21", 1, "K")
    with pytest.raises(mejl.MejlFel, match="app-lösenord"):
        mejl.testa_inloggning(dict(INST, losenord="fel"))


def test_ingen_kontakt_och_ssl_port(monkeypatch):
    mejl.testa_inloggning(dict(INST, port=465))
    assert LatsasServer.loggar[-1]["port"] == 465 and not LatsasServer.loggar[-1]["tls"]      # 465 = SSL direkt, ingen STARTTLS

    def ingen_kontakt(*a, **kw):
        raise OSError("timed out")
    monkeypatch.setattr(smtplib, "SMTP", ingen_kontakt)
    with pytest.raises(mejl.MejlFel, match="Ingen kontakt"):
        mejl.testa_inloggning(INST)
