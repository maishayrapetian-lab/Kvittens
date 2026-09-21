"""
config.py – alla inställningar på ett ställe
=============================================
Här ändrar du saker utan att röra resten av koden.
"""

# --- Namn och profil ---------------------------------------------------------
# Byter du namn på tjänsten räcker det att ändra här. Färger och typsnitt: .streamlit/config.toml
APPNAMN = "Kvittens"              # Kv-värdet + att kvittera: appen kontrollräknar Kv, och du kvitterar avläsningen
NAMN_ACCENT = "Kv"                # de här första bokstäverna färgas i mässing i sidhuvudet (tom sträng = ingen accent)
SLOGAN = "Från display till injusteringsprotokoll"
UPPHOV = "Mais Hayrapetian"       # visas under namnet, i sidfoten och i mejlen
UPPHOV_AR = "2026"
VERSION = "3.12"

# --- AI-modell ---------------------------------------------------------------
# "claude-sonnet-5" är standardvalet. Billigare/snabbare: "claude-haiku-4-5-20251001".
# Högsta precision: "claude-opus-5".
MODELL = "claude-sonnet-5"
MAX_TOKENS = 4000              # räcker till ca 12 displayer i en och samma bild

# Bilder skalas ned till så här många pixlar på långsidan innan de skickas.
# 2200 px utnyttjar de nya modellernas högupplösta läge utan att API:t behöver
# skala om bilden en gång till. Kör du Haiku 4.5: sätt 1568.
MAX_BILDKANT = 2200
JPEG_KVALITET = 90
VISNINGSKANT = 1400            # storlek på bilden som visas bredvid mätningarna

# Dubbelkontroll = varje bild läses två gånger (andra gången kontrastförstärkt).
# Fält där de två avläsningarna skiljer sig flaggas. Kostar dubbelt, fångar fler fel.
DUBBELKONTROLL_STANDARD = True
SAMTIDIGA_ANROP = 4            # hur många bilder som läses parallellt

# --- Excel-mallen ------------------------------------------------------------
MALL = "mall.xlsx"             # din mall, konverterad från .xls till .xlsx
BLAD_PROTOKOLL = "Injust.protokoll"
BLAD_FORSATTSBLAD = "Försättsblad"
FORSTA_DATARAD = 9             # första raden under rubrikerna

# Kolumn i protokollet för varje fält (A=1, B=2 ...)
KOLUMNER = {
    "system": 1,          # A
    "ventilnummer": 2,    # B
    "placering": 3,       # C
    "fabrikat": 4,        # D
    "typ": 5,             # E
    "installning": 6,     # F
    "dimension": 7,       # G
    "kv": 8,              # H
    "mattryck": 9,        # I  (kPa)
    "projekterat": 10,    # J
    "uppmatt": 11,        # K
    "noteringar": 12,     # L
}

# Rubrikceller
CELL_OBJEKT = {"protokoll": "G2", "forsattsblad": "J2"}
CELL_BYGGNAD = {"protokoll": "G3", "forsattsblad": "J3"}
CELL_DATUM = {"protokoll": "L2", "forsattsblad": "O2"}
CELL_UTFORT_AV = {"protokoll": "A5", "forsattsblad": "A4"}

# Pumpraderna på försättsbladet (texten är förskriven i mallen, värdena fylls i)
CELL_PUMP_RUBRIK = "A10"       # "Pump  inställd på:"
CELL_PUMP_DRIFTFORM = "A13"    # "Driftform: Konstant tryck"
CELL_PUMP_DYNAMISKT = "A14"    # "Dynamisk tryck:  mvp ( kPa)"
CELL_PUMP_STATISKT = "A15"     # "Statisk tryck:  Bar"

# Protokollets enheter – avläsningar i andra enheter räknas om hit
FLODESENHET = "l/s"
TRYCKENHET = "kPa"

# --- Fabrikat ----------------------------------------------------------------
# TA-SCOPE:s ventildatabas innehåller bara IMI:s egna ventiler. Visar displayen
# ett ventilnamn (STAD*, STAF* ...) är fabrikatet därför givet.
# Bolaget heter IMI sedan 2024 och ventilerna säljs under varumärket "IMI TA".
# Vill du hellre skriva bara "IMI": ändra raden nedan.
FABRIKAT_TA_SCOPE = "IMI TA"

# --- Kontroller --------------------------------------------------------------
# Kv-kontrollen: q = Kv · √Δp  ->  Kv = 36 · q[l/s] / √Δp[kPa]
# Toleransen = displayens avrundning + denna marginal.
KV_MARGINAL = 0.01             # 1 %
PROCENT_MARGINAL = 1.0         # procentenheter utöver avrundningen
MIN_MATTRYCK_KPA = 3.0         # under detta anger tillverkaren sämre mätnoggrannhet
FLODESTOLERANS = 0.10          # ±10 % mot projekterat flöde (AMA VVS & Kyla)

# Dimensioner (DN) som finns för respektive ventiltyp enligt IMI:s datablad. Avviker avläsningen flaggas den
# som "ovanlig" – inte som fel, eftersom listan kan vara ofullständig. Typer som saknas här kontrolleras inte.
DIMENSIONER = {
    "STAD": [10, 15, 20, 25, 32, 40, 50], "STAD*": [10, 15, 20, 25, 32, 40, 50], "STADA": [10, 15, 20, 25, 32, 40, 50],
    "STAF": [20, 25, 32, 40, 50, 65, 80, 100, 125, 150, 200, 250, 300, 350, 400],
    "STAF*": [65, 80, 100, 125, 150], "STAF-SG": [65, 80, 100, 125, 150, 200, 250, 300, 350, 400], "STAF-SG*": [65, 80, 100, 125, 150],
}

# Max antal varv för ventilfamiljer där det är verifierat (fullt öppen).
# STAD-familjen: 4 varv. Fler läggs till när Kv-tabellerna är inlagda.
MAX_VARV = {"STAD": 4.0, "STAD*": 4.0, "STADA": 4.0, "STAD-C": 4.0, "STAD ZERO": 4.0}

# --- Drift på nätet ------------------------------------------------------------
KRAV_LOSENORD_PA_NATET = True    # utan lösenord spärras appen när den nås från annat håll än din egen dator
MAX_BILDER_PER_DYGN = 400        # kostnadsskydd: fler bilder än så läses inte av per dygn (alla användare tillsammans)

# --- Mejlutskick av protokollet (se mejl.py och DRIFTSÄTTNING.md) ---------------
MAX_MEJL_PER_DYGN = 60           # skydd mot missbruk: fler mejl än så skickas inte per dygn
TILLATNA_MEJLDOMANER = []        # t.ex. ["foretaget.se"] – tom lista = vilken adress som helst

MAX_BILDER_PER_JOBB = 80         # ett enskilt jobb får inte bli hur stort som helst (kostnad och minne)
MEJL_KOPIA_TILL = ""             # t.ex. "arkiv@foretaget.se" – får en dold kopia av varje mejlat protokoll
MAX_BILAGA_MB = 10               # skydd mot att något annat än ett protokoll skickas av misstag

# --- Inloggning -----------------------------------------------------------------
MAX_FELFORSOK = 5                # så många felaktiga lösenord i rad, sedan spärras inloggningen en stund
SPARRTID_MINUTER = 10

# --- Åtkomst -----------------------------------------------------------------
# Lösenord sätts i .streamlit/secrets.toml (APP_LOSENORD). Saknas det körs appen öppet,
# vilket är praktiskt lokalt på din egen dator.
