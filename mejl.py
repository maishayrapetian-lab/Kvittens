"""
mejl.py – skickar det färdiga protokollet som bilaga
=====================================================
Appen mejlar via en vanlig mejlserver (SMTP). Enklast är ett Gmail-konto med ett "app-lösenord".

Lägg de här raderna i .streamlit/secrets.toml (lokalt) eller under Secrets (på nätet):

    SMTP_ANVANDARE = 'adressen-som-appen-mejlar-fran@gmail.com'
    SMTP_LOSENORD  = 'abcd efgh ijkl mnop'          # app-lösenordet, INTE det vanliga lösenordet

Annan mejlserver än Gmail? Lägg också till  SMTP_SERVER  och  SMTP_PORT  (587 = STARTTLS, 465 = SSL).

Använd helst ett EGET Gmail-konto för appen. Ett app-lösenord ger åtkomst till hela brevlådan,
så det ska inte vara din privata.

Skydd mot missbruk: mejlets text är fast (ingen fri text går att skicka), adressen kontrolleras,
antalet mejl per dygn är begränsat, och mottagardomäner kan låsas i config.py.
"""

from __future__ import annotations

import re
import smtplib
import ssl
from collections.abc import Callable
from email.message import EmailMessage

import config

XLSX = ("application", "vnd.openxmlformats-officedocument.spreadsheetml.sheet")


class MejlFel(Exception):
    """Fel med en förklaring som kan visas direkt för användaren."""


def installningar(hamta: Callable[[str], str | None]) -> dict | None:
    """Läs SMTP-inställningarna. None om mejlutskick inte är inställt."""
    anvandare, losen = hamta("SMTP_ANVANDARE"), hamta("SMTP_LOSENORD")
    if not anvandare or not losen:
        return None
    port = hamta("SMTP_PORT") or "587"
    return {"server": hamta("SMTP_SERVER") or "smtp.gmail.com", "port": int(port) if str(port).isdigit() else 587,
            "anvandare": anvandare.strip(), "losenord": losen.replace(" ", ""),          # Google visar app-lösenordet med mellanslag
            "avsandare": (hamta("MEJL_AVSANDARE") or anvandare).strip()}


def giltig_adress(text: str) -> bool:
    t = (text or "").strip()
    if len(t) > 254 or any(tecken in t for tecken in "\r\n"):
        return False
    return bool(re.fullmatch(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}", t))


def tillaten_adress(text: str) -> bool:
    domaner = [d.lower().lstrip("@") for d in config.TILLATNA_MEJLDOMANER]
    return not domaner or text.strip().lower().rsplit("@", 1)[-1] in domaner


def _anslut(inst: dict):
    sammanhang = ssl.create_default_context()
    if inst["port"] == 465:
        server = smtplib.SMTP_SSL(inst["server"], inst["port"], timeout=30, context=sammanhang)
    else:
        server = smtplib.SMTP(inst["server"], inst["port"], timeout=30)
        server.starttls(context=sammanhang)
    server.login(inst["anvandare"], inst["losenord"])
    return server


def _oversatt(e: Exception) -> MejlFel:
    if isinstance(e, smtplib.SMTPAuthenticationError):
        return MejlFel("Mejlservern godkände inte inloggningen. För Gmail krävs ett app-lösenord (16 tecken), "
                       "inte kontots vanliga lösenord – se DRIFTSÄTTNING.md.")
    if isinstance(e, smtplib.SMTPServerDisconnected):
        return MejlFel("Mejlservern stängde anslutningen vid inloggningen. Kontrollera SMTP_ANVANDARE och app-lösenordet.")
    if isinstance(e, smtplib.SMTPRecipientsRefused):
        return MejlFel("Mejlservern godkände inte mottagarens adress. Kontrollera stavningen.")
    if isinstance(e, smtplib.SMTPException):
        return MejlFel(f"Mejlservern svarade med ett fel: {e}")
    return MejlFel("Ingen kontakt med mejlservern. Kontrollera nätet – vissa nätverk blockerar mejlportarna 587/465.")


def testa_inloggning(inst: dict) -> None:
    """Används av kontrollera.bat: loggar in på mejlservern utan att skicka något."""
    try:
        _anslut(inst).quit()
    except (smtplib.SMTPException, OSError) as e:
        raise _oversatt(e) from e


def skicka(inst: dict, till: str, filnamn: str, data: bytes, objekt: str, datum: str, antal: int, utfort_av: str) -> None:
    till = (till or "").strip()
    if not giltig_adress(till):
        raise MejlFel("Mejladressen ser inte riktig ut. Kontrollera stavningen.")
    if not tillaten_adress(till):
        raise MejlFel("Protokoll får bara mejlas till: " + ", ".join("@" + d.lstrip("@") for d in config.TILLATNA_MEJLDOMANER))

    if len(data) > config.MAX_BILAGA_MB * 1024 * 1024:
        raise MejlFel(f"Bilagan är större än {config.MAX_BILAGA_MB} MB och skickas inte. Ladda ner protokollet i stället.")

    brev = EmailMessage()
    brev["From"] = f"{config.APPNAMN} <{inst['avsandare']}>"
    brev["To"] = till
    kopia = (config.MEJL_KOPIA_TILL or "").strip()
    if kopia and giltig_adress(kopia) and kopia.lower() != till.lower():
        brev["Bcc"] = kopia                      # dold arkivkopia; send_message tar bort Bcc-raden ur brevet som skickas
    brev["Subject"] = f"Injusteringsprotokoll {objekt} {datum}".replace("\r", " ").replace("\n", " ")
    brev.set_content(
        f"Hej,\n\nHär kommer injusteringsprotokollet för {objekt}.\n\n"
        f"Mätdatum: {datum}\nAntal mätningar: {antal}\nUtfört av: {utfort_av}\n\n"
        f"Skickat från {config.APPNAMN}. Avläsningarna är gjorda med AI och granskade av den som utfört mätningen; "
        f"den som undertecknar protokollet ansvarar för värdena.\n\n{config.APPNAMN} är utvecklad av {config.UPPHOV}.\n")
    brev.add_attachment(data, maintype=XLSX[0], subtype=XLSX[1], filename=filnamn)
    try:
        server = _anslut(inst)
        try:
            server.send_message(brev)
        finally:
            server.quit()
    except (smtplib.SMTPException, OSError) as e:
        raise _oversatt(e) from e
