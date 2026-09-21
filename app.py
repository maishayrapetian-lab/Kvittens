"""
Kvittens v3.12 (f.d. Mätarappen) – foto av TA-SCOPE  ->  injusteringsprotokoll i din Excel-mall
===============================================================================
Flöde:  bilder  ->  AI skriver av displayerna  ->  automatiska kontroller
        ->  du granskar och rättar  ->  in i mallen

Starta:   streamlit run app.py
Nyckel:   .streamlit/secrets.toml  med  ANTHROPIC_API_KEY = "sk-ant-..."
          (valfritt)                   APP_LOSENORD = "ditt-lösenord"

Koden är uppdelad så att gränssnittet går att byta ut utan att röra kärnan:
  avlasning.py  AI-avläsningen      kontroller.py  felkontrollerna
  protokoll.py  Excel-exporten      utseende.py    formgivningen
  app.py        (den här filen) knyter ihop dem i Streamlit
"""

from __future__ import annotations

import hashlib
import hmac
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date
from pathlib import Path

import pandas as pd
import streamlit as st

import avlasning
import config
import dela
import demo
import hemligheter
import kontroller
import lagring
import logg
import mejl
import protokoll
import sakerhet
import utseende

MAPP = Path(__file__).resolve().parent
IKON = MAPP / "static" / "ikon.png"           # absolut sökväg: fungerar oavsett varifrån appen startas
st.set_page_config(page_title=f"{config.APPNAMN} – {config.SLOGAN.lower()}", page_icon=str(IKON) if IKON.exists() else "📷", layout="wide")
try:                                         # nyckel i fel fil eller utan citattecken rättas tyst.
    if any((MAPP / ".streamlit").glob("secrets*")):      # Skapar aldrig en ny fil här – det gör kontrollera.bat.
        hemligheter.reparera(MAPP)
except Exception:
    pass
st.markdown(utseende.CSS, unsafe_allow_html=True)


def html(text: str, plats=st) -> None:
    plats.markdown(text, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Hemligheter och lösenord
# ---------------------------------------------------------------------------
def hemlighet(namn: str) -> str | None:
    """Samma källa som kontrollera.bat använder, så att appen och kontrollen aldrig kan vara oense:
    1. projektets egen .streamlit/secrets.toml (läses färskt – nyckelbyte gäller direkt)
    2. Streamlits secrets (så fungerar det i molnet, där ingen fil finns)   3. miljövariabel."""
    varde = hemligheter.hamta(namn, MAPP)
    if varde:
        return varde
    try:
        if namn in st.secrets and str(st.secrets[namn]).strip():
            return str(st.secrets[namn]).strip()
    except Exception:
        pass
    return None


def nas_utifran() -> bool:
    """Körs appen på nätet (inte bara på den egna datorn)? Avgörs av adressen i webbläsaren."""
    try:
        vard = (st.context.headers.get("Host") or "").split(":")[0].lower()
    except Exception:
        vard = ""
    if vard:
        return vard not in ("localhost", "127.0.0.1", "::1", "[::1]")
    # Inget Host-huvud (en mellanliggande proxy kan ha tagit bort det). Gissa inte "egen dator" –
    # fråga i stället vilken adress servern lyssnar på. localhost = bara den här datorn.
    try:
        adress = (st.get_option("server.address") or "").strip().lower()
    except Exception:
        adress = ""
    return adress not in ("", "localhost", "127.0.0.1", "::1")


def krav_losenord() -> None:
    losen = hemlighet("APP_LOSENORD")
    if not losen and config.KRAV_LOSENORD_PA_NATET and nas_utifran():
        html(utseende.sidhuvud(0))
        st.error("Appen är nåbar från nätet men saknar lösenord, så den är spärrad. Lägg till raden "
                 "`APP_LOSENORD = \"...\"` under Secrets i värdtjänstens inställningar och starta om appen.")
        st.stop()
    if not losen or st.session_state.get("inloggad"):
        return
    html(utseende.sidhuvud(0))
    # Två spärrar: en för den här webbläsaren och en gemensam för hela appen (tål fyra gånger fler försök).
    egen = st.session_state.setdefault("sparr", sakerhet.Sparr(config.MAX_FELFORSOK, config.SPARRTID_MINUTER * 60))
    gemensam = lagring.gemensam_sparr(config.MAX_FELFORSOK * 4, config.SPARRTID_MINUTER * 60)
    kvar = max(egen.sparrad(time.time()), gemensam.sparrad(time.time()))
    _, mitten, _ = st.columns([1, 1.2, 1])
    if kvar > 0:
        mitten.error(f"För många felaktiga försök. Inloggningen är spärrad i {int(kvar // 60) + 1} minut(er) till.")
        st.stop()
    with mitten, st.form("login"):
        st.subheader("Logga in")
        angivet = st.text_input("Lösenord", type="password")
        if st.form_submit_button("Logga in", type="primary", width="stretch"):
            if hmac.compare_digest(angivet.encode(), losen.encode()):
                egen.lyckat()
                st.session_state["inloggad"] = True
                st.rerun()
            time.sleep(sakerhet.FORDROJNING_VID_FEL)          # gör upprepade gissningar långsamma
            egen.fel_forsok(time.time())
            gemensam.fel_forsok(time.time())
            logg.info(None, "felaktigt lösenord vid inloggning")
            if egen.sparrad(time.time()) or gemensam.sparrad(time.time()):
                st.rerun()                                     # visa spärren direkt, inte först vid nästa försök
            st.error("Fel lösenord.")
    st.stop()


krav_losenord()
if hemlighet("APP_LOSENORD") and sakerhet.svagt_losenord(hemlighet("APP_LOSENORD")):
    st.warning(f"Lösenordet till appen är svagt (kortare än {sakerhet.MINSTA_LANGD} tecken eller mycket vanligt). "
               "Byt det i `.streamlit/secrets.toml` innan appen blir nåbar för andra – gärna fyra fem slumpade ord.")

# ---------------------------------------------------------------------------
# Tillstånd som ska överleva mellan omritningar
# ---------------------------------------------------------------------------
st.session_state.setdefault("resultat", {})      # bildens hash -> avläsningsresultat
st.session_state.setdefault("seq", 0)

KOLUMNNAMN = {
    "ta_med": "Med", "system": "System", "ventilnummer": "Ventilnr", "placering": "Placering",
    "fabrikat": "Fabrikat", "typ": "Typ", "installning": "Inställning", "dimension": "Dimension",
    "kv": "Kv", "mattryck": "Mättryck kPa", "projekterat": "Projekterat flöde",
    "uppmatt": "Uppmätt flöde", "noteringar": "Noteringar",
}
FALT = [f for f in KOLUMNNAMN if f != "ta_med"]
TILLBAKA = {v: k for k, v in KOLUMNNAMN.items()}


# ---------------------------------------------------------------------------
# Avläsning av en bild (körs i bakgrundstrådar – inga st.-anrop här inne)
# ---------------------------------------------------------------------------
def las_en_bild(klient, namn: str, data: bytes, dubbel: bool) -> dict:
    post = {"namn": namn, "fel": None, "rader": [], "skillnader": {}, "olika_antal": False,
            "pump": None, "bildkvalitet": "", **avlasning.sorteringsinfo(namn, data)}
    try:
        jpeg = avlasning.forbered_bild(data)
        post["jpeg"], post["visning"] = jpeg, avlasning.forhandsvisning(jpeg)
        svar = avlasning.las_av_bild(klient, jpeg)
        post["rader"] = avlasning.till_rader(svar, namn)
        post["pump"] = avlasning.pumpforslag(svar)
        post["pumpar"] = avlasning.alla_pumpforslag(svar)
        post["bildkvalitet"] = svar["bildkvalitet"]
        if dubbel and post["rader"]:
            svar2 = avlasning.las_av_bild(klient, avlasning.forstark_bild(jpeg))
            post["skillnader"], post["olika_antal"] = avlasning.jamfor(
                post["rader"], avlasning.till_rader(svar2, namn))
    except avlasning.AvlasningsFel as e:
        post["fel"] = str(e)
        logg.fel(None, "avläsning", e)
    except Exception as e:                   # oväntat fel ska inte fälla hela omgången
        post["fel"] = f"Oväntat fel: {e}"
        logg.fel(None, "avläsning (oväntat)", e)
    return post


def las_av(filer, dubbel: bool) -> None:
    nyckel = hemlighet("ANTHROPIC_API_KEY")
    if not nyckel:
        st.error("API-nyckel saknas. Dubbelklicka på `kontrollera.bat` i appens mapp – den öppnar rätt fil och visar var nyckeln ska in.")
        return
    jobb = []
    for fil in filer:
        data = fil.getvalue()
        h = hashlib.sha1(data).hexdigest() + ("-2" if dubbel else "-1")
        tidigare = st.session_state["resultat"].get(h)
        if tidigare is None or tidigare["fel"]:              # redan lästa bilder läses inte om
            jobb.append((h, fil.name, data))
    if not jobb:
        st.info("Alla valda bilder är redan avlästa.")
        return
    redan = len(st.session_state["resultat"])
    if redan + len(jobb) > config.MAX_BILDER_PER_JOBB:
        st.error(f"Ett jobb får innehålla högst {config.MAX_BILDER_PER_JOBB} bilder (du har {redan} och försöker lägga till {len(jobb)}). "
                 "Dela upp det i två jobb. Taket ändras i config.py.")
        return
    kvar = lagring.bilder_kvar_idag(config.MAX_BILDER_PER_DYGN)
    if len(jobb) > kvar:
        st.error(f"Dygnstaket är nått: appen läser högst {config.MAX_BILDER_PER_DYGN} bilder per dygn (kostnadsskydd), "
                 f"och {kvar} återstår i dag. Taket ändras i config.py.")
        return
    lagring.rakna_bilder(len(jobb))

    klient = avlasning.skapa_klient(nyckel)
    stapel = st.progress(0.0, text=f"Läser av {len(jobb)} bild(er)…")
    with ThreadPoolExecutor(max_workers=config.SAMTIDIGA_ANROP) as pool:
        framtida = {pool.submit(las_en_bild, klient, namn, data, dubbel): h for h, namn, data in jobb}
        for klara, f in enumerate(as_completed(framtida), start=1):
            post = f.result()
            h = framtida[f]
            gammal = st.session_state["resultat"].get(h)
            if gammal:
                post["seq"] = gammal["seq"]
            else:
                st.session_state["seq"] += 1
                post["seq"] = st.session_state["seq"]
            st.session_state["resultat"][h] = post
            stapel.progress(klara / len(jobb), text=f"Läser av… {klara} av {len(jobb)} klara")
    stapel.empty()


# ---------------------------------------------------------------------------
# Tre tydliga steg, ett i taget:  1 Bilder  ->  2 Granska  ->  3 Exportera
# Varje steg slutar med EN knapp som för vidare. Inget steg kan sluta i en återvändsgränd.
# ---------------------------------------------------------------------------
st.session_state.setdefault("steg", 1)
st.session_state.setdefault("bas", {})             # bildens seq -> tabellen så som du senast lämnade den
st.session_state.setdefault("tabellversion", 0)
st.session_state.setdefault("kvitterat", False)
st.session_state.setdefault("slutdata", None)      # raderna som ska exporteras (sätts när du lämnar granskningen)
st.session_state.setdefault("jobb", {})
st.session_state.setdefault("fil", None)


def ga_till(steg: int) -> None:
    st.session_state["steg"] = steg
    st.rerun()


def borja_om() -> None:
    utfort_av = st.session_state["jobb"].get("utfort_av", "")
    mejl_till = st.session_state["jobb"].get("mejl", "")
    lagring.glom(st.session_state.get("jobbkod", ""))
    st.session_state["jobbkod"] = lagring.ny_kod()
    for nyckel in ("resultat", "bas"):
        st.session_state[nyckel] = {}
    st.session_state.update(seq=0, kvitterat=False, slutdata=None, fil=None,
                            jobb={"utfort_av": utfort_av, "mejl": mejl_till}, steg=1)     # namn och mejladress följer med till nästa jobb
    st.session_state["tabellversion"] += 1
    st.rerun()


# Påbörjat jobb? Koden i adressen (?jobb=...) hämtar tillbaka det om mobilen har laddat om sidan.
if "jobbkod" not in st.session_state:
    kod = st.query_params.get("jobb", "")
    sparat_jobb = lagring.hamta(kod) if kod else None
    if sparat_jobb and sparat_jobb.get("resultat"):
        st.session_state.update({k: v for k, v in sparat_jobb.items() if v is not None})
        st.session_state["tabellversion"] = (sparat_jobb.get("tabellversion") or 0) + 1      # nya tabeller med det sparade innehållet
        st.session_state["jobbkod"] = kod
        st.toast("Ditt påbörjade jobb är tillbaka.")
    else:
        st.session_state["jobbkod"] = lagring.ny_kod()
utkast: dict = {}

if not st.session_state["resultat"]:
    st.session_state["steg"] = 1
steg = st.session_state["steg"]
html(utseende.sidhuvud(steg))
poster = avlasning.sortera(list(st.session_state["resultat"].values()))

# ===========================================================================
# STEG 1 · Bilder
# ===========================================================================
if steg == 1:
    html(utseende.startsida())
    filer = st.file_uploader("Foton av TA-SCOPE-displayen", label_visibility="collapsed",
                             type=["jpg", "jpeg", "png", "webp", "heic", "heif"], accept_multiple_files=True)
    dubbel = st.checkbox("Dubbelkontroll: läs varje bild två gånger och flagga skillnader",
                         value=config.DUBBELKONTROLL_STANDARD)
    if filer:
        anrop = len(filer) * (2 if dubbel else 1)
        st.caption(f"{len(filer)} bild(er) ger {anrop} AI-avläsningar" + (" (dubbelkontrollen läser varje bild två gånger)." if dubbel else "."))
    b1, b2, _ = st.columns([1.2, 1.2, 2])
    if b1.button("Läs av bilderna", type="primary", disabled=not filer, width="stretch"):
        las_av(filer, dubbel)
        if st.session_state["resultat"]:
            st.session_state.update(slutdata=None, fil=None, kvitterat=False)
            ga_till(2)
    if poster:
        st.success(f"{len(poster)} bild(er) är redan avlästa.")
        if b2.button("Fortsätt till granskningen", width="stretch"):
            ga_till(2)
    elif b2.button("Prova med exempelbilder", type="tertiary",
                   help="Sju riktiga foton som redan är avlästa. Inget API-anrop, ingen kostnad."):
        st.session_state["resultat"] = demo.demoposter()
        st.session_state["seq"] = len(st.session_state["resultat"])
        ga_till(2)

# ===========================================================================
# STEG 2 · Granska
# ===========================================================================
elif steg == 2:
    st.subheader("Granska")
    st.caption("Jämför talen med fotot. Behöver något rättas eller kompletteras: öppna rutan under mätningen. "
               "När du har gått igenom alla bilder finns knappen **Fortsätt till export** längst ned.")
    n1, n2, _ = st.columns([1.3, 1.3, 2])
    if n1.button("Lägg till fler bilder", width="stretch"):
        ga_till(1)
    visa_tabeller = n2.toggle("Visa alla tabeller", value=False, help="Öppnar alla tabeller på en gång. Du kan också öppna en i taget.")

    dubbletter = kontroller.hitta_dubbletter([r for p in poster for r in p["rader"]])
    slutrader: list[dict] = []
    redigerade: dict = {}
    antal = {kontroller.FEL: 0, kontroller.OSAKER: 0}
    misslyckade = [p for p in poster if p["fel"]]
    lopnr = 0

    for p in poster:
        with st.container(border=True):
            if p["fel"]:
                st.error(f"**{p['namn']}** – {p['fel']}")
                continue
            vanster, hoger = st.columns([5, 8], gap="medium")
            vanster.image(p.get("visning") or p["jpeg"], caption=p["namn"], width="stretch")
            with hoger:
                if not p["rader"]:
                    st.warning("Ingen instrumentdisplay hittades i bilden.")
                    continue
                if p["bildkvalitet"] == "dålig":
                    st.warning("AI:n bedömer bildkvaliteten som dålig – granska extra noga.")
                if p["olika_antal"]:
                    st.warning("De två avläsningarna hittade olika många displayer i bilden – kontrollera att alla kom med.")

                kortplats = st.container()                        # korten visas ÖVER tabellen men byggs efter den
                nummer = list(range(lopnr + 1, lopnr + 1 + len(p["rader"])))
                bas = st.session_state["bas"].get(p["seq"])
                if bas is None or len(bas) != len(p["rader"]):
                    bas = pd.DataFrame([{"ta_med": True, **{f: str(r.get(f) or "") for f in FALT}} for r in p["rader"]]
                                       ).rename(columns=KOLUMNNAMN)
                bas = bas.copy()
                bas.index = [f"Mätning {n}" for n in nummer]
                # Tabellen ritas ALLTID (även hopfälld) – annars glömmer Streamlit det du har ändrat i den.
                with st.expander("Rätta eller komplettera – system, ventilnummer, placering", expanded=visa_tabeller):
                    redigerad = st.data_editor(
                        bas, key=f"tabell_{p['seq']}_{st.session_state['tabellversion']}", num_rows="fixed", width="stretch",
                        column_config={"Med": st.column_config.CheckboxColumn(help="Bocka ur t.ex. en dubblett.", width="small")})
                redigerade[p["seq"]] = redigerad
                utkast[p["seq"]] = redigerad

                for i, (_, serie) in enumerate(redigerad.iterrows()):
                    rad = {TILLBAKA[k]: ("" if pd.isna(v) else v) for k, v in serie.items()}
                    grund = p["rader"][i]
                    rad.update({k: grund[k] for k in ("procent", "klocka", "bild")})
                    # AI:ns osäkerhet gäller bara så länge du inte har ändrat fältet själv
                    rad["osakra_falt"] = [f for f in grund["osakra_falt"] if str(rad.get(f, "")) == str(grund.get(f) or "")]
                    flaggor = kontroller.kontrollera_rad(rad) if rad["ta_med"] else []
                    for falt, va, vb in p["skillnader"].get(i, []):
                        if str(rad.get(falt, "")) == va:
                            flaggor.append(kontroller.Flagga(
                                kontroller.OSAKER, falt,
                                f"{KOLUMNNAMN[falt]}: de två avläsningarna skiljer sig ('{va}' / '{vb}') – jämför med bilden."))
                    if rad["ta_med"]:
                        for text in grund["info"]:
                            flaggor.append(kontroller.Flagga(kontroller.INFO, "", text))
                        if lopnr + i in dubbletter:
                            flaggor.append(kontroller.Flagga(
                                kontroller.INFO, "",
                                f"Ser ut som samma ventil som Mätning {dubbletter[lopnr + i] + 1} (samma inställning, "
                                f"projekterat flöde och klockslag). Bocka ur en av dem om det är en dubblett."))
                        if grund["kommentar"]:
                            flaggor.append(kontroller.Flagga(kontroller.INFO, "", f"AI:ns kommentar: {grund['kommentar']}"))
                        slutrader.append(rad)
                        for f in flaggor:
                            if f.niva in antal:
                                antal[f.niva] += 1
                    html(utseende.matkort(nummer[i], rad, flaggor), kortplats)
                lopnr += len(p["rader"])

    # ---- Steget slutar alltid här: en ruta som säger vad som återstår och EN knapp vidare ----
    flaggade = antal[kontroller.FEL] + antal[kontroller.OSAKER]
    with st.container(border=True):
        st.markdown("**Klar med granskningen?**")
        html(utseende.sammanfattning(len(slutrader), antal[kontroller.FEL], antal[kontroller.OSAKER]))
        if misslyckade:
            st.warning(f"{len(misslyckade)} bild(er) kunde inte läsas av och kommer inte med. "
                       "Gå till *Lägg till fler bilder* och tryck *Läs av bilderna* igen om du vill försöka på nytt.")
        for nr, platser in kontroller.dubbla_ventilnummer(slutrader).items():
            flaggade += 1
            st.warning(f"Ventilnummer **{nr}** står på flera mätningar (nr {', '.join(str(p) for p in platser)} i exportordning). "
                       "Är det en dubblett, eller är ett nummer felskrivet?")
        kvitterat = True
        if flaggade:
            # Forskning om "automation bias" visar att vi gärna godkänner automatiska förslag ogranskat.
            # Därför: vidare först när de flaggade mätningarna uttryckligen är jämförda med bilderna.
            kvitterat = st.checkbox(f"Jag har jämfört de {flaggade} flaggade värdena (Kontrollera / Osäker) med bilderna.",
                                    value=st.session_state["kvitterat"])
        hinder = ("Inga mätningar är valda – bocka i *Med* för minst en mätning." if not slutrader
                  else "Kryssa i rutan ovan, så tänds knappen." if not kvitterat else "")
        if st.button("Fortsätt till export", type="primary", disabled=bool(hinder), width="stretch"):
            st.session_state["bas"].update(redigerade)             # spara tabellerna så som du lämnade dem
            st.session_state["tabellversion"] += 1
            st.session_state.update(kvitterat=kvitterat, fil=None,
                                    slutdata={"rader": slutrader, "antal": dict(antal)})
            ga_till(3)
        if hinder:
            st.caption(hinder)

# ===========================================================================
# STEG 3 · Exportera
# ===========================================================================
else:
    slutdata = st.session_state["slutdata"] or {"rader": [], "antal": {}}
    slutrader = slutdata["rader"]
    st.subheader("Exportera")
    if st.button("‹ Tillbaka till granskningen", type="tertiary"):
        st.session_state["fil"] = None
        ga_till(2)
    st.caption(f"{len(slutrader)} mätningar skrivs in i injusteringsprotokollet. Fyll i uppgifterna och tryck på **Skapa protokollet**.")

    sparat = st.session_state["jobb"]
    pumpval = [(p, f) for p in poster for f in (p.get("pumpar") or ([p["pump"]] if p.get("pump") else []))]
    pumpbild, forslag, pumpnr = None, {}, 0
    if len(pumpval) > 1:                       # flera pumpdisplayer hittade: välj vilken som hör till protokollet
        etiketter = [f"{f['modell'] or 'Pump'} i {p['namn']} – {f['dynamiskt_mvp'] or '?'} mvp" for p, f in pumpval]
        pumpnr = st.selectbox("Flera pumpar hittades i bilderna. Vilken hör till protokollet?", range(len(pumpval)),
                              format_func=lambda i: etiketter[i])
    if pumpval:
        pumpbild, forslag = pumpval[pumpnr]
    # enter_to_submit=False: på mobilen trycker man gärna "Klar/Enter" för att fälla ihop tangentbordet –
    # det får aldrig råka skapa protokollet och skicka mejlet i förtid.
    with st.form("export", enter_to_submit=False):
        k1, k2, k3 = st.columns(3)
        objekt = k1.text_input("Objekt *", value=sparat.get("objekt", ""), placeholder="t.ex. Söderhallarna")
        byggnad = k2.text_input("Byggnad", value=sparat.get("byggnad", ""))
        utfort_av = k3.text_input("Utfört av *", value=sparat.get("utfort_av", ""), placeholder="ditt namn")
        k4, k5, _ = st.columns(3)
        system = k4.text_input("System", value=sparat.get("system", ""), placeholder="t.ex. VS10",
                               help="Fylls i på alla rader som inte har ett eget system.")
        matdatum = k5.date_input("Mätdatum", value=sparat.get("matdatum") or date.today(), format="YYYY-MM-DD")

        mejlinst = mejl.installningar(hemlighet)
        # Fältet syns ALLTID. Är mejlutskicket inte påslaget är det grått – och appen säger varför och hur man slår på det.
        mejl_till = st.text_input(
            "Mejla protokollet till", value=sparat.get("mejl", "") if mejlinst else "", disabled=not mejlinst,
            placeholder="din.adress@foretaget.se" if mejlinst else "Inte påslaget ännu – se förklaringen nedan",
            help="Protokollet skickas som bilaga när du trycker på Skapa protokollet. Lämna tomt för att bara ladda ner.")
        if not mejlinst:
            glomda = [n for n in hemligheter.bortkommenterade(MAPP) if n.startswith("SMTP_")]
            if glomda:
                st.warning("Raderna " + " och ".join(glomda) + " är ifyllda i nyckelfilen men har fortfarande **#** framför sig. "
                           "Ta bort #-tecknet i början av raderna, spara, och ladda om sidan.")
            with st.expander("Varför är fältet grått? Så slår du på mejlutskick (en gång, ca 10 minuter)"):
                st.markdown(
                    "Appen behöver ett mejlkonto att skicka *från*. Det är den enda vägen som fungerar i alla webbläsare. "
                    "(I Safari på iPhone finns dessutom en dela-knapp när protokollet är skapat; Chrome och Edge tillåter inte det.)\n\n"
                    "1. Skapa ett eget Gmail-konto för appen (inte ditt privata).\n"
                    "2. Slå på tvåstegsverifiering för kontot.\n"
                    "3. Gå till *myaccount.google.com/apppasswords*, skapa ett app-lösenord och kopiera de 16 tecknen.\n"
                    "4. Dubbelklicka på `oppna_nyckelfilen.bat` och lägg till två rader, **utan #** framför:\n\n"
                    "```\nSMTP_ANVANDARE = 'kontots-adress@gmail.com'\nSMTP_LOSENORD = 'abcd efgh ijkl mnop'\n```\n"
                    "5. Spara och ladda om sidan. `kontrollera.bat` (steg 7) visar om inloggningen fungerar.\n\n"
                    "Ligger appen på nätet läggs samma två rader in under *Settings → Secrets*.")

        st.markdown("**Pump och tryck till försättsbladet** (valfritt)")
        if forslag:
            st.caption(f"Förslag avläst från pumpdisplayen i {pumpbild['namn']} ({forslag['modell'] or 'pump'}). Ändra vid behov.")
            if forslag["driftsform_nu"].strip().lower().startswith("max"):
                st.info("Pumpen gick i driftsform *Max.* när bilden togs. Kontrollera att värdet nedan är det inställda "
                        "börvärdet och inte bara den uppfordringshöjd som råkade visas.")
            if forslag["osaker"]:
                st.warning("Pumpdisplayen var svårläst – jämför med bilden.")
        p1, p2, p3, p4 = st.columns(4)
        pump = {
            "beteckning": p1.text_input("Pumpbeteckning", value=sparat.get("pump_bet", ""), placeholder="t.ex. P1"),
            "driftform": p2.text_input("Driftform", value=sparat.get("pump_drift", forslag.get("driftform", "")), key=f"pump_drift_{pumpnr}"),
            "dynamiskt_mvp": p3.text_input("Dynamiskt tryck (mvp)", value=sparat.get("pump_dyn", forslag.get("dynamiskt_mvp", "")),
                                           key=f"pump_dyn_{pumpnr}",
                                           help="Skrivs som t.ex. ”Dynamisk tryck: 9,7 mvp (95 kPa)”. kPa räknas ut åt dig."),
            "statiskt_bar": p4.text_input("Statiskt tryck (bar)", value=sparat.get("pump_stat", "")),
        }
        skapa = st.form_submit_button("Skapa protokollet", type="primary", width="stretch")

    if skapa:
        st.session_state["jobb"] = {"objekt": objekt, "byggnad": byggnad, "utfort_av": utfort_av, "system": system,
                                    "matdatum": matdatum, "mejl": mejl_till.strip(),
                                    "pump_bet": pump["beteckning"], "pump_drift": pump["driftform"],
                                    "pump_dyn": pump["dynamiskt_mvp"], "pump_stat": pump["statiskt_bar"]}
        saknas = [namn for namn, varde in (("Objekt", objekt), ("Utfört av", utfort_av)) if not varde.strip()]
        if not slutrader:
            st.error("Det finns inga mätningar att exportera. Gå tillbaka till granskningen.")
        elif saknas:
            st.session_state["fil"] = None
            st.error(f"Fyll i {' och '.join(saknas)} (fälten märkta med *) och tryck på Skapa protokollet igen.")
        else:
            rader = [dict(r, system=(str(r.get("system") or "").strip() or system)) for r in slutrader]
            try:
                data = protokoll.skapa_protokoll(
                    rader, jobb={"objekt": objekt, "byggnad": byggnad, "datum": matdatum.isoformat(), "utfort_av": utfort_av},
                    pump=pump)
                namn = "_".join(("Injusteringsprotokoll", objekt.strip().replace(" ", "_"), matdatum.isoformat())) + ".xlsx"
                st.session_state["fil"] = {"data": data, "namn": namn, "mejlat": ""}
                if mejl_till.strip():
                    if lagring.kvar_idag("mejl", config.MAX_MEJL_PER_DYGN) <= 0:
                        st.error(f"Dygnstaket för mejl är nått ({config.MAX_MEJL_PER_DYGN} per dygn). Ladda ner protokollet i stället.")
                    else:
                        try:
                            with st.spinner("Skickar mejlet…"):
                                mejl.skicka(mejlinst, mejl_till, namn, data, objekt.strip(), matdatum.isoformat(),
                                            len(rader), utfort_av.strip())
                            lagring.rakna("mejl")
                            st.session_state["fil"]["mejlat"] = mejl_till.strip()
                        except mejl.MejlFel as e:
                            logg.fel(st.session_state.get("jobbkod"), "mejl", e)
                            st.error(f"Protokollet är skapat, men mejlet gick inte iväg: {e}")
            except FileNotFoundError:
                st.error(f"Hittar inte mallen ”{config.MALL}”. Den ska ligga i samma mapp som app.py.")

    if st.session_state["fil"]:
        fil = st.session_state["fil"]
        if fil.get("mejlat"):
            st.success(f"Protokollet är klart och skickat till **{fil['mejlat']}**. Titta i skräpposten om det inte syns i inkorgen.")
        else:
            st.success(f"Protokollet är klart: **{fil['namn']}**")
        st.download_button("Ladda ner protokollet", data=fil["data"], file_name=fil["namn"], type="primary", width="stretch",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        jobbet = st.session_state["jobb"]
        dela.delaknapp(fil["data"], fil["namn"], amne=f"Injusteringsprotokoll {jobbet.get('objekt', '')}".strip(),
                       text=f"Injusteringsprotokoll {jobbet.get('objekt', '')}, utfört av {jobbet.get('utfort_av', '')}.")
        if st.button("Börja på ett nytt jobb", width="stretch"):
            borja_om()

with st.expander("Om dina bilder och uppgifter"):
    st.markdown(
        "- **Bilderna skickas till Anthropics API** för avläsning. Det är enda gången de lämnar appen.\n"
        "- **Inget sparas på disk.** Ett påbörjat jobb – bilder, avlästa värden och det du fyllt i – ligger i serverns minne "
        f"i högst {lagring.MAX_TIMMAR} timmar, så att du kan fortsätta om mobilen laddar om sidan. Startas servern om försvinner det.\n"
        "- **Protokollet** skapas när du trycker *Skapa protokollet* och finns sedan bara hos dig: som nedladdad fil eller i ditt mejl.\n"
        "- **Loggen** innehåller bara tidpunkt och typ av fel – aldrig bilder, mätvärden, objektnamn, mejladresser eller lösenord.\n"
        "- Ligger appen på Streamlit Community Cloud körs den på servrar i USA.")
    if st.session_state["resultat"] and st.button("Radera det här jobbet nu"):
        borja_om()

# Spara jobbet i serverns minne och lägg koden i adressen, så att en omladdad sida hittar tillbaka.
if st.session_state["resultat"]:
    lagring.spara(st.session_state["jobbkod"], st.session_state, utkast)
    if st.query_params.get("jobb") != st.session_state["jobbkod"]:
        st.query_params["jobb"] = st.session_state["jobbkod"]
elif "jobb" in st.query_params:
    del st.query_params["jobb"]

html(utseende.sidfot())
