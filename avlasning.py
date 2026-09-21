"""
avlasning.py – från foto till protokollrader
=============================================
1. forbered_bild()   rätt rotation, lagom storlek
2. las_av_bild()     AI:n skriver AV displayen (tolkar inte) och svarar i ett låst JSON-format
3. till_rader()      vanlig kod gör om svaret till rader i protokollets kolumner
4. jamfor()          dubbelkontroll: skiljer sig två avläsningar av samma bild?

Principen: AI:n gör bara det den är bra på – att läsa av. All tolkning
(dela upp "STAD* 10", räkna om enheter, välja fabrikat) görs av vanlig kod,
som alltid gör likadant och går att testa.
"""

from __future__ import annotations

import base64
import io
import json
import re

from PIL import Image, ImageFilter, ImageOps

import config
import kontroller

try:                                   # iPhone-bilder i HEIC-format (valfritt paket)
    from pillow_heif import register_heif_opener

    register_heif_opener()
except Exception:                      # pragma: no cover
    pass


class AvlasningsFel(Exception):
    """Ett fel med en förklaring som går att visa direkt för användaren."""


# ---------------------------------------------------------------------------
# 1. Bilder
# ---------------------------------------------------------------------------
def forbered_bild(data: bytes) -> bytes:
    """Vrid bilden rätt (mobilfoton ligger ofta 'på sidan' i filen), skala ned, spara som JPEG."""
    try:
        bild = Image.open(io.BytesIO(data))
        bild = ImageOps.exif_transpose(bild).convert("RGB")
    except Exception as e:
        raise AvlasningsFel(f"Filen gick inte att öppna som bild ({e}).") from e
    bild.thumbnail((config.MAX_BILDKANT, config.MAX_BILDKANT), Image.LANCZOS)
    ut = io.BytesIO()
    bild.save(ut, "JPEG", quality=config.JPEG_KVALITET)
    return ut.getvalue()


def forstark_bild(jpeg: bytes) -> bytes:
    """Kontrast- och skärpeförstärkt kopia till dubbelkontrollen (ger AI:n en 'andra blick')."""
    bild = Image.open(io.BytesIO(jpeg)).convert("RGB")
    bild = ImageOps.autocontrast(bild, cutoff=1)
    bild = bild.filter(ImageFilter.UnsharpMask(radius=2, percent=120, threshold=3))
    ut = io.BytesIO()
    bild.save(ut, "JPEG", quality=config.JPEG_KVALITET)
    return ut.getvalue()


def forhandsvisning(jpeg: bytes) -> bytes:
    """Lättare kopia för visning i webbläsaren (fullstor bild gör sidan trög på mobilen)."""
    bild = Image.open(io.BytesIO(jpeg)).convert("RGB")
    bild.thumbnail((config.VISNINGSKANT, config.VISNINGSKANT), Image.LANCZOS)
    ut = io.BytesIO()
    bild.save(ut, "JPEG", quality=82)
    return ut.getvalue()


def _fototid(data: bytes) -> str | None:
    try:
        exif = Image.open(io.BytesIO(data)).getexif()
        return exif.get_ifd(0x8769).get(36867) or exif.get(306)      # DateTimeOriginal / DateTime
    except Exception:
        return None


def _filnummer(namn: str) -> int | None:
    tal = re.findall(r"\d+", namn or "")
    return int(tal[-1]) if tal else None


def sorteringsinfo(namn: str, data: bytes) -> dict:
    """Det som behövs för att lägga bilderna i den ordning de TOGS."""
    return {"fototid": _fototid(data), "filnummer": _filnummer(namn)}


def sortera(poster: list[dict]) -> list[dict]:
    """Sortera bildposter i mätordning, så att raderna hamnar rätt i protokollet.

    1. Fototid (EXIF) – om ALLA bilder har den.
    2. Annars löpnumret i filnamnet (IMG_2031 < IMG_2032). Bilder utan nummer
       (t.ex. skärmbilder) läggs sist, i den ordning de laddades upp ('seq').
    """
    if poster and all(p.get("fototid") for p in poster):
        return sorted(poster, key=lambda p: (p["fototid"], p.get("seq", 0)))
    return sorted(poster, key=lambda p: (p.get("filnummer") is None, p.get("filnummer") or 0, p.get("seq", 0)))


# ---------------------------------------------------------------------------
# 2. AI-avläsningen
# ---------------------------------------------------------------------------
def _obj(egenskaper: dict) -> dict:
    """Alla fält obligatoriska och inga extra fält – då garanterar API:t formatet."""
    return {"type": "object", "properties": egenskaper,
            "required": list(egenskaper), "additionalProperties": False}


def _txt(beskrivning: str) -> dict:
    return {"type": "string", "description": beskrivning}


SCHEMA = _obj({
    "displayer": {
        "type": "array",
        "description": "En post per display på ett injusteringsinstrument (t.ex. TA-SCOPE), "
                       "i läsordning: uppifrån och ned, vänster till höger. Tom lista om ingen finns.",
        "items": _obj({
            "instrument": _txt("Instrumentets namn som det står på höljet, t.ex. 'TA SCOPE'. Tom sträng om okänt."),
            "position": _txt("Var i bilden displayen sitter, t.ex. 'mitten', 'uppe till höger'."),
            "klocka": _txt("Klockslaget i displayens överkant, t.ex. '06:36'."),
            "flode": _txt("Talet efter 'Flöde:', tecken för tecken, t.ex. '0.021'."),
            "flode_enhet": _txt("Enheten efter flödet, t.ex. 'l/s'."),
            "dp": _txt("Talet efter 'Dp:', t.ex. '22.8'."),
            "dp_enhet": _txt("Enheten efter Dp, t.ex. 'kPa'."),
            "temperatur": _txt("Talet efter 'Temp:'. Tom sträng om fältet är tomt (vanligt)."),
            "temperatur_enhet": _txt("Enheten efter Temp, t.ex. '°C'."),
            "projekterat_flode": _txt("Talet i rutan vid skrivplatta-ikonen (projekterat flöde), t.ex. '0.19'."),
            "projekterat_enhet": _txt("Enheten i samma ruta, t.ex. 'l/s'."),
            "procent": _txt("Procenttalet till höger om projekterat flöde, t.ex. '101'. Tom sträng om det står '-.-'."),
            "ventil": _txt("HELA ventilraden exakt som den står, inklusive asterisk och mellanslag, t.ex. 'STAD* 10'."),
            "installning": _txt("Talet i rutan vid ratt-ikonen, t.ex. '1.6'."),
            "installning_enhet": _txt("Ordet efter inställningen, t.ex. 'varv'."),
            "kv": _txt("Talet efter 'Kv =', t.ex. '0.158'."),
            "medium": _txt("Texten vid droppe-ikonen, t.ex. 'Vatten'."),
            "ventilnummer": _txt("Nummer/text på en bricka eller skylt som hänger vid ventilen i bilden, t.ex. '246'. Tom sträng om ingen syns."),
            "osakra_falt": {
                "type": "array",
                "description": "Namnen på de fält ovan där något tecken var skymt, suddigt eller tvetydigt.",
                "items": {"type": "string"},
            },
            "kommentar": _txt("Kort förklaring till osäkra fält, annars tom sträng."),
        }),
    },
    "pumpar": {
        "type": "array",
        "description": "En post per pumpdisplay i bilden (t.ex. Grundfos MAGNA3). Tom lista om ingen finns.",
        "items": _obj({
            "modell": _txt("Fabrikat och modell som det står på pumpen, t.ex. 'Grundfos MAGNA3'."),
            "reglertyp": _txt("Texten under 'Reglertyp', t.ex. 'Konst. tryck'."),
            "driftsform": _txt("Texten under 'Driftsform', t.ex. 'Max.'."),
            "uppfordringshojd": _txt("Talet vid 'Uppfordringshöjd' eller 'Börvärde', t.ex. '9.7'."),
            "uppfordringshojd_enhet": _txt("Enheten, t.ex. 'm'."),
            "flode": _txt("Pumpens flöde om det visas, annars tom sträng."),
            "flode_enhet": _txt("Enheten för pumpens flöde."),
            "vatsketemperatur": _txt("Talet vid 'Vätsketemperatur', t.ex. '49'."),
            "osaker": {"type": "boolean", "description": "true om något på pumpdisplayen var svårläst."},
        }),
    },
    "ovriga_matare": {
        "type": "array",
        "description": "Andra mätare i bilden: termometrar, manometrar. Tom lista om inga finns.",
        "items": _obj({
            "typ": {"type": "string", "enum": ["termometer", "manometer", "annan"]},
            "varde": _txt("Avläst värde, t.ex. '59'."),
            "enhet": _txt("Enhet, t.ex. '°C' eller 'bar'."),
            "analog": {"type": "boolean", "description": "true för visarinstrument."},
            "kommentar": _txt("T.ex. 'oskarp, visaren strax under 60'."),
        }),
    },
    "bildkvalitet": {"type": "string", "enum": ["bra", "ok", "dålig"]},
})


SYSTEMPROMPT = """Du läser av mätinstrument på foton från injustering av värme- och kylsystem. \
Resultatet skrivs in i ett injusteringsprotokoll, så varje tecken måste bli rätt.

DIN UPPGIFT ÄR ATT SKRIVA AV – INTE ATT TOLKA.
- Skriv varje värde tecken för tecken som det står på displayen. Behåll decimalpunkt, \
avslutande nollor ('1.90', '24.0') och alla specialtecken.
- Ventilraden skrivs av i sin helhet. En asterisk hör till namnet: 'STAD* 10' och 'STAD 10' \
är OLIKA ventiler. Lägg aldrig till och ta aldrig bort en asterisk.
- Räkna aldrig ut ett värde och gissa aldrig. Är ett tecken skymt, suddigt eller träffat av en \
reflex: ge din bästa läsning, lägg fältets namn i osakra_falt och förklara kort i kommentar. \
Är fältet helt oläsligt: tom sträng, och fältnamnet i osakra_falt.
- Ett tomt fält på displayen (t.ex. 'Temp:' utan tal) blir tom sträng.

SÅ SER TA-SCOPE-SKÄRMEN 'Mätning flöde' UT, uppifrån och ned:
- röd list: klockslag
- 'Flöde:'  stort tal + enhet (t.ex. l/s)
- 'Dp:'     stort tal + enhet (t.ex. kPa)
- 'Temp:'   oftast tomt + °C
- skrivplatta-ikon: ruta med projekterat flöde (t.ex. '0.19 l/s'), till höger ett procenttal \
(eller '-.-' om inget projekterat flöde är inlagt)
- ventil-ikon: ruta med ventilen (t.ex. 'STAD* 25')
- ratt-ikon: ruta med inställningen (t.ex. '1.7 varv'), till höger 'Kv = 2.7'
- droppe-ikon: medium (t.ex. 'Vatten')
Blanda inte ihop det stora flödet överst med det projekterade flödet i rutan.

FLERA DISPLAYER: En bild kan visa flera instrument, eller vara en skärmbild av ett fotobibliotek \
med flera miniatyrer. Varje display är en egen mätning och får en egen post, även om två displayer \
ser ut att visa samma ventil. Hoppa över miniatyrer som inte visar något instrument.

ANNAT I BILDEN: En pumpdisplay (t.ex. Grundfos MAGNA3) redovisas under pumpar. Termometrar och \
manometrar redovisas under ovriga_matare. Visarinstrument (analoga) är svåra att läsa av exakt – \
sätt analog=true och beskriv i kommentar var visaren står. En bricka med nummer som hänger vid \
ventilen är ventilnumret för displayen i samma bild."""

ANVANDARTEXT = "Läs av alla instrument i bilden enligt instruktionerna."


def skapa_klient(api_nyckel: str):
    import anthropic

    return anthropic.Anthropic(api_key=api_nyckel, max_retries=3, timeout=120.0)


def las_av_bild(klient, jpeg: bytes, modell: str | None = None) -> dict:
    """Skicka en (förberedd) bild till Claude och få tillbaka avläsningen enligt SCHEMA."""
    import anthropic

    try:
        svar = klient.messages.create(
            model=modell or config.MODELL,
            max_tokens=config.MAX_TOKENS,
            system=SYSTEMPROMPT,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg",
                                                 "data": base64.standard_b64encode(jpeg).decode()}},
                    {"type": "text", "text": ANVANDARTEXT},
                ],
            }],
            # Strukturerat svar: API:t garanterar giltig JSON enligt schemat.
            output_config={"format": {"type": "json_schema", "schema": SCHEMA}},
        )
    except anthropic.AuthenticationError as e:
        raise AvlasningsFel("API-nyckeln godkändes inte. Dubbelklicka på kontrollera.bat – den visar vilken nyckel som används och om den fungerar.") from e
    except anthropic.RateLimitError as e:
        raise AvlasningsFel("För många anrop just nu – vänta en minut och försök igen.") from e
    except (anthropic.APIConnectionError, anthropic.APITimeoutError) as e:
        raise AvlasningsFel("Fick ingen kontakt med AI-tjänsten. Kontrollera nätet och försök igen.") from e
    except anthropic.APIStatusError as e:
        raise AvlasningsFel(f"AI-tjänsten svarade med fel {e.status_code}: {getattr(e, 'message', e)}") from e

    if svar.stop_reason == "max_tokens":
        raise AvlasningsFel("Svaret blev avklippt – bilden innehåller för många displayer. Dela upp den.")
    if svar.stop_reason == "refusal":
        raise AvlasningsFel("AI:n avböjde att läsa bilden.")
    text = next((b.text for b in svar.content if getattr(b, "type", "") == "text"), "")
    try:
        return stada_svar(json.loads(text))
    except (json.JSONDecodeError, TypeError, AttributeError) as e:
        raise AvlasningsFel("AI:ns svar gick inte att tolka. Försök igen.") from e


def stada_svar(svar: dict) -> dict:
    """Bälte och hängslen: se till att alla listor och textfält finns och har rätt typ."""
    def s(v) -> str:
        return "" if v is None else str(v).strip()

    ut = {"displayer": [], "pumpar": [], "ovriga_matare": [], "bildkvalitet": s(svar.get("bildkvalitet")) or "ok"}
    for d in svar.get("displayer") or []:
        post = {k: s(d.get(k)) for k in SCHEMA["properties"]["displayer"]["items"]["properties"]
                if k != "osakra_falt"}
        post["osakra_falt"] = [s(x) for x in (d.get("osakra_falt") or [])]
        ut["displayer"].append(post)
    for p in svar.get("pumpar") or []:
        post = {k: s(p.get(k)) for k in SCHEMA["properties"]["pumpar"]["items"]["properties"] if k != "osaker"}
        post["osaker"] = bool(p.get("osaker"))
        ut["pumpar"].append(post)
    for m in svar.get("ovriga_matare") or []:
        ut["ovriga_matare"].append({"typ": s(m.get("typ")) or "annan", "varde": s(m.get("varde")),
                                    "enhet": s(m.get("enhet")), "analog": bool(m.get("analog")),
                                    "kommentar": s(m.get("kommentar"))})
    return ut


# ---------------------------------------------------------------------------
# 3. Från avläsning till protokollrader
# ---------------------------------------------------------------------------
_FALTNAMN = {"flode": "uppmatt", "dp": "mattryck", "projekterat_flode": "projekterat",
             "ventil": "typ", "installning": "installning", "kv": "kv",
             "ventilnummer": "ventilnummer", "temperatur": "noteringar"}


def dela_ventil(ventil: str) -> tuple[str, str]:
    """'STAD* 10' -> ('STAD*', '10').   'TA-COMPACT-P 15' -> ('TA-COMPACT-P', '15').

    Typen lämnas orörd – asterisken skiljer olika ventilgenerationer åt.
    """
    v = " ".join(str(ventil or "").split())
    m = re.fullmatch(r"(.*?\S)\s+(?:DN\s*)?(\d{1,4})", v, flags=re.IGNORECASE)
    return (m.group(1), m.group(2)) if m else (v, "")


def _omrakna(text: str, faktor: float | None) -> tuple[str, bool]:
    """Räkna om till protokollets enhet. Returnerar (text, omräknad?)."""
    tal, _ = kontroller.tolka_tal(text)
    if tal is None or faktor is None or faktor == 1.0:
        return text, False
    return f"{tal * faktor:.4g}", True


def _temperaturnotering(display: dict, svar: dict, forsta: bool) -> tuple[str, bool]:
    """Temperaturer hör hemma i Noteringar. Returnerar (text, osäker?)."""
    delar, osaker = [], False
    if display.get("temperatur"):
        delar.append(f"Temp {display['temperatur'].replace('.', ',')} °C")
    if forsta:                                   # bildens övriga temperaturer läggs på första raden
        for p in svar["pumpar"]:
            if p.get("vatsketemperatur"):
                delar.append(f"{'Temp ' if not delar else ''}{p['vatsketemperatur'].replace('.', ',')} °C (pump)")
        for m in svar["ovriga_matare"]:
            if m["typ"] == "termometer" and m["varde"]:
                ca = "ca " if m["analog"] else ""
                delar.append(f"{'Temp ' if not delar else ''}{ca}{m['varde'].replace('.', ',')} °C (termometer)")
                osaker = osaker or m["analog"]
    return ", ".join(delar), osaker


def till_rader(svar: dict, bild: str) -> list[dict]:
    rader = []
    for i, d in enumerate(svar["displayer"]):
        typ, dim = dela_ventil(d["ventil"])
        uppmatt, q_om = _omrakna(d["flode"], kontroller.flodesfaktor(d["flode_enhet"] or config.FLODESENHET))
        mattryck, p_om = _omrakna(d["dp"], kontroller.tryckfaktor(d["dp_enhet"] or config.TRYCKENHET))
        proj, _ = _omrakna(d["projekterat_flode"],
                           kontroller.flodesfaktor(d["projekterat_enhet"] or d["flode_enhet"] or config.FLODESENHET))
        procent = "".join(re.findall(r"\d+", d["procent"]))[:4]

        info = []
        # "0 l/s" + "-.- %" betyder att inget projekterat flöde är inlagt – då ska cellen vara tom
        if not procent and (kontroller.tolka_tal(proj)[0] or 0) == 0:
            if proj:
                info.append("Inget projekterat flöde inlagt i instrumentet – cellen lämnas tom.")
            proj = ""
        okanda = []
        for falt, enhet, faktor, mal in (("uppmatt", d["flode_enhet"], kontroller.flodesfaktor(d["flode_enhet"]), config.FLODESENHET),
                                         ("mattryck", d["dp_enhet"], kontroller.tryckfaktor(d["dp_enhet"]), config.TRYCKENHET)):
            if enhet.strip() and faktor is None:                 # AI:n läste en enhet som appen inte kan räkna om
                okanda.append(falt)
                info.append(f"Okänd enhet ”{enhet}” – värdet är INTE omräknat till {mal}. Kontrollera och räkna om för hand.")
        if q_om:
            info.append(f"Flödet omräknat från {d['flode']} {d['flode_enhet']} till {config.FLODESENHET}.")
        if p_om:
            info.append(f"Mättrycket omräknat från {d['dp']} {d['dp_enhet']} till {config.TRYCKENHET}.")

        notering, temp_osaker = _temperaturnotering(d, svar, forsta=(i == 0))
        osakra = sorted({_FALTNAMN[f] for f in d["osakra_falt"] if f in _FALTNAMN} | ({"noteringar"} if temp_osaker else set())
                        | set(okanda))
        ta_scope = "SCOPE" in d["instrument"].upper()

        rader.append({
            "bild": bild, "display_nr": i + 1, "position": d["position"], "klocka": d["klocka"],
            "system": "", "ventilnummer": d["ventilnummer"], "placering": "",
            "fabrikat": config.FABRIKAT_TA_SCOPE if (ta_scope and typ) else "",
            "typ": typ, "installning": d["installning"], "dimension": dim, "kv": d["kv"],
            "mattryck": mattryck, "projekterat": proj, "uppmatt": uppmatt, "noteringar": notering,
            "procent": procent, "osakra_falt": osakra, "kommentar": d["kommentar"], "info": info,
        })
    return rader


def _pump(p: dict) -> dict:
    driftform = p["reglertyp"].replace("Konst.", "Konstant").replace("Prop.", "Proportionellt").strip()
    hojd, _ = kontroller.tolka_tal(p["uppfordringshojd"])
    faktor = kontroller.tryckfaktor(p["uppfordringshojd_enhet"] or "m")
    mvp = ""
    if hojd is not None and faktor:
        mvp = f"{hojd * faktor / 9.80665:.3g}" if faktor != 9.80665 else p["uppfordringshojd"]
    return {"modell": p["modell"], "driftform": driftform, "dynamiskt_mvp": mvp,
            "driftsform_nu": p["driftsform"], "osaker": p["osaker"]}


def alla_pumpforslag(svar: dict) -> list[dict]:
    """Ett förslag per pumpdisplay i bilden."""
    return [_pump(p) for p in svar["pumpar"]]


def pumpforslag(svar: dict) -> dict | None:
    """Förslag till försättsbladets pumprader ur bildens första pumpdisplay."""
    forslag = alla_pumpforslag(svar)
    return forslag[0] if forslag else None


# ---------------------------------------------------------------------------
# 4. Dubbelkontroll
# ---------------------------------------------------------------------------
_JAMFOR = ("uppmatt", "mattryck", "kv", "projekterat", "typ", "dimension", "installning", "ventilnummer")


def _norm(v) -> str:
    return str(v or "").replace(",", ".").replace(" ", "").casefold()


def jamfor(rader_a: list[dict], rader_b: list[dict]) -> tuple[dict[int, list[tuple[str, str, str]]], bool]:
    """Jämför två avläsningar av samma bild.

    Returnerar ({radindex: [(fält, värde A, värde B), ...]}, olika_antal).
    """
    if len(rader_a) != len(rader_b):
        return {}, True
    skillnader = {}
    for i, (a, b) in enumerate(zip(rader_a, rader_b, strict=True)):      # lika långa – kontrollerat ovan
        diff = [(f, str(a.get(f) or ""), str(b.get(f) or "")) for f in _JAMFOR if _norm(a.get(f)) != _norm(b.get(f))]
        if diff:
            skillnader[i] = diff
    return skillnader, False
