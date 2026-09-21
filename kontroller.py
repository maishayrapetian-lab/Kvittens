"""
kontroller.py – appens "felfångare"
====================================
Ren logik utan AI och utan gränssnitt, så att allt här går att testa automatiskt.

Grundidén: TA-SCOPE-displayen kontrollerar sig själv. Flöde, Δp och Kv hänger ihop:

        q = Kv · √Δp          (q i m³/h, Δp i bar)
  ->    Kv = 36 · q / √Δp     (q i l/s,  Δp i kPa)

Läser AI:n en siffra fel i något av de tre värdena går ekvationen inte ihop,
och raden flaggas. Kontrollen fångar grova fel (fel siffra, flyttat decimaltecken,
förväxlade fält) – inte alltid sista decimalen, eftersom displayen avrundar.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass

import config

# Nivåer på flaggor
FEL = "fel"          # en kontroll gick inte ihop – titta på bilden
OSAKER = "osäker"    # AI:n eller dubbelkontrollen är osäker
INFO = "info"        # bra att veta, inget avläsningsfel


@dataclass
class Flagga:
    niva: str
    falt: str
    text: str

    @property
    def ikon(self) -> str:
        return {FEL: "🔴", OSAKER: "🟡", INFO: "🔵"}.get(self.niva, "•")


# ---------------------------------------------------------------------------
# Tal och enheter
# ---------------------------------------------------------------------------
def tolka_tal(text) -> tuple[float | None, int]:
    """'1.90' -> (1.9, 2)   '2,4' -> (2.4, 1)   '' -> (None, 0)

    Returnerar talet OCH antalet decimaler som displayen visade.
    Decimalerna behövs både för Excel-formatet (1,90 ska inte bli 1,9)
    och för att räkna ut hur mycket displayen kan ha avrundat.
    """
    if text is None:
        return None, 0
    t = str(text).strip().replace(" ", "").replace(",", ".").replace("−", "-")
    if not re.fullmatch(r"-?\d+(\.\d+)?", t):
        return None, 0
    decimaler = len(t.split(".")[1]) if "." in t else 0
    return float(t), decimaler


def halv_enhet(decimaler: int) -> float:
    """Största möjliga avrundningsfel: halva sista siffran. 2 decimaler -> 0,005."""
    return 0.5 * 10 ** (-decimaler)


_FLODE_TILL_LS = {
    "l/s": 1.0,
    "l/h": 1 / 3600,
    "l/min": 1 / 60,
    "m3/h": 1 / 3.6,
    "m³/h": 1 / 3.6,
}
_TRYCK_TILL_KPA = {
    "kpa": 1.0,
    "pa": 0.001,
    "bar": 100.0,
    "mbar": 0.1,
    "mvp": 9.80665,
    "mh2o": 9.80665,
    "m": 9.80665,
    "mmh2o": 0.00980665,
    "psi": 6.894757,
}


def _enhet(text) -> str:
    return str(text or "").strip().lower().replace(" ", "")


def flodesfaktor(enhet) -> float | None:
    return _FLODE_TILL_LS.get(_enhet(enhet))


def tryckfaktor(enhet) -> float | None:
    return _TRYCK_TILL_KPA.get(_enhet(enhet))


def mvp_till_kpa(mvp: float) -> float:
    return mvp * 9.80665


# ---------------------------------------------------------------------------
# Kv-kontrollen
# ---------------------------------------------------------------------------
@dataclass
class KvResultat:
    gick_att_rakna: bool
    ok: bool = True
    kv_beraknat: float | None = None
    kv_min: float | None = None
    kv_max: float | None = None
    avvikelse: float | None = None     # relativ, t.ex. 0.004 = 0,4 %
    tolerans: float | None = None


def berakna_kv(q_ls: float, dp_kpa: float) -> float:
    return 36.0 * q_ls / math.sqrt(dp_kpa)


def kv_kontroll(flode, dp, kv, flodesenhet="l/s", tryckenhet="kPa") -> KvResultat:
    """Jämför avläst Kv med Kv uträknat ur avläst flöde och Δp.

    Toleransen byggs av hur mycket displayen kan ha avrundat de tre värdena
    plus en liten marginal (config.KV_MARGINAL).
    """
    q, q_dec = tolka_tal(flode)
    p, p_dec = tolka_tal(dp)
    k, k_dec = tolka_tal(kv)
    fq, fp = flodesfaktor(flodesenhet), tryckfaktor(tryckenhet)
    if None in (q, p, k, fq, fp) or q <= 0 or p <= 0 or k <= 0:
        return KvResultat(gick_att_rakna=False)

    hq, hp = halv_enhet(q_dec), halv_enhet(p_dec)
    kv_ber = berakna_kv(q * fq, p * fp)
    kv_min = berakna_kv(max(q - hq, 1e-12) * fq, (p + hp) * fp)
    kv_max = berakna_kv((q + hq) * fq, max(p - hp, 1e-12) * fp)

    avrundning = (hq / q) + 0.5 * (hp / p) + (halv_enhet(k_dec) / k)
    tolerans = avrundning + config.KV_MARGINAL
    avvikelse = kv_ber / k - 1.0
    return KvResultat(
        gick_att_rakna=True,
        ok=abs(avvikelse) <= tolerans,
        kv_beraknat=kv_ber,
        kv_min=kv_min,
        kv_max=kv_max,
        avvikelse=avvikelse,
        tolerans=tolerans,
    )


def procent_kontroll(flode, projekterat, procent) -> tuple[bool | None, float | None]:
    """Stämmer displayens procent med uppmätt / projekterat?

    Projekterat flöde visas avrundat (ofta 2 decimaler), så kontrollen räknar med
    hela intervallet. Returnerar (ok, beräknad procent) eller (None, None).
    """
    q, _ = tolka_tal(flode)
    pr, pr_dec = tolka_tal(projekterat)
    pc, pc_dec = tolka_tal(procent)
    if None in (q, pr, pc) or pr <= 0 or q <= 0:
        return None, None
    h = halv_enhet(pr_dec)
    hog = 100 * q / max(pr - h, 1e-12)
    lag = 100 * q / (pr + h)
    m = halv_enhet(pc_dec) + config.PROCENT_MARGINAL
    return (lag - m) <= pc <= (hog + m), 100 * q / pr


# ---------------------------------------------------------------------------
# Format för visning
# ---------------------------------------------------------------------------
def sv(tal: float, decimaler: int = 2) -> str:
    """Svenskt talformat: 0.158 -> '0,158'."""
    return f"{tal:.{decimaler}f}".replace(".", ",")


def _kv_decimaler(kv: float) -> int:
    return 3 if kv < 1 else 2 if kv < 100 else 1


# ---------------------------------------------------------------------------
# Alla kontroller för en rad
# ---------------------------------------------------------------------------
def kontrollera_rad(rad: dict) -> list[Flagga]:
    """rad = en mätning med textfälten: typ, installning, dimension, kv, mattryck,
    projekterat, uppmatt (redan i protokollets enheter) samt ev. procent och
    osakra_falt (lista från AI:n)."""
    flaggor: list[Flagga] = []

    # 1. Fält som måste finnas
    for falt, namn in (("uppmatt", "Uppmätt flöde"), ("mattryck", "Mättryck")):
        if tolka_tal(rad.get(falt))[0] is None:
            if str(rad.get(falt) or "").strip():
                flaggor.append(Flagga(FEL, falt, f"{namn}: '{rad.get(falt)}' är inte ett tal"))
            else:
                flaggor.append(Flagga(FEL, falt, f"{namn} saknas"))

    # 1b. Noll eller negativa värden kan aldrig vara en riktig mätning
    for falt, namn in (("uppmatt", "Uppmätt flöde"), ("mattryck", "Mättryck"), ("kv", "Kv"), ("installning", "Inställning")):
        tal, _ = tolka_tal(rad.get(falt))
        if tal is not None and (tal < 0 or (tal == 0 and falt != "installning")):
            flaggor.append(Flagga(FEL, falt, f"{namn} är {'negativt' if tal < 0 else 'noll'} ({rad.get(falt)}) – det kan inte stämma."))

    # 2. Kv-kontrollen
    kv = kv_kontroll(rad.get("uppmatt"), rad.get("mattryck"), rad.get("kv"))
    kv_osaker = "kv" in (rad.get("osakra_falt") or [])
    if kv.gick_att_rakna:
        d = _kv_decimaler(kv.kv_beraknat)
        if not kv.ok:
            flaggor.append(Flagga(
                FEL, "kv",
                f"Kv går inte ihop: avläst {str(rad.get('kv')).replace('.', ',')}, "
                f"beräknat ur flöde och Δp {sv(kv.kv_beraknat, d)} "
                f"({sv(kv.avvikelse * 100, 1) if kv.avvikelse < 0 else '+' + sv(kv.avvikelse * 100, 1)} %). "
                f"Något av flöde, mättryck eller Kv är fel avläst."))
        elif kv_osaker:
            flaggor.append(Flagga(
                OSAKER, "kv",
                f"Kv var svårläst men stämmer med beräkningen "
                f"({sv(kv.kv_min, d)}–{sv(kv.kv_max, d)})."))
    elif tolka_tal(rad.get("kv"))[0] is None and tolka_tal(rad.get("uppmatt"))[0] and tolka_tal(rad.get("mattryck"))[0]:
        q, p = tolka_tal(rad["uppmatt"])[0], tolka_tal(rad["mattryck"])[0]
        if q > 0 and p > 0:
            k = berakna_kv(q, p)
            flaggor.append(Flagga(OSAKER, "kv", f"Kv saknas – beräknat ur flöde och Δp blir det {sv(k, _kv_decimaler(k))}."))

    # 3. Procentkontrollen (skyddar projekterat flöde)
    ok, ber = procent_kontroll(rad.get("uppmatt"), rad.get("projekterat"), rad.get("procent"))
    if ok is False:
        flaggor.append(Flagga(
            FEL, "projekterat",
            f"Projekterat flöde går inte ihop: displayen visar {rad.get('procent')} %, "
            f"men uppmätt/projekterat ger {ber:.0f} %."))

    # 4. Rimlighet
    p, _ = tolka_tal(rad.get("mattryck"))
    if p is not None and 0 < p < config.MIN_MATTRYCK_KPA:
        flaggor.append(Flagga(INFO, "mattryck",
                              f"Lågt mättryck ({sv(p, 2)} kPa < {sv(config.MIN_MATTRYCK_KPA, 0)} kPa) – sämre mätnoggrannhet."))

    varv, _ = tolka_tal(rad.get("installning"))
    max_varv = config.MAX_VARV.get(str(rad.get("typ") or "").strip().upper())
    if varv is not None and max_varv is not None and varv > max_varv:
        flaggor.append(Flagga(FEL, "installning",
                              f"Inställning {sv(varv, 1)} varv är mer än {rad.get('typ')} kan ha ({sv(max_varv, 0)} varv)."))

    typ = str(rad.get("typ") or "").strip().upper()
    dim, _ = tolka_tal(rad.get("dimension"))
    kanda = config.DIMENSIONER.get(typ)
    if kanda and dim is not None and int(dim) not in kanda:
        flaggor.append(Flagga(OSAKER, "dimension",
                              f"Dimension {rad.get('dimension')} är ovanlig för {rad.get('typ')} (brukar vara "
                              f"{', '.join(str(d) for d in kanda)}). Är typ eller dimension fel avläst?"))

    q, _ = tolka_tal(rad.get("uppmatt"))
    pr, _ = tolka_tal(rad.get("projekterat"))
    if q and pr and pr > 0:
        avv = q / pr - 1
        if abs(avv) > config.FLODESTOLERANS:
            flaggor.append(Flagga(INFO, "uppmatt",
                                  f"Flödet avviker {avv * 100:+.0f} % från projekterat (gräns ±{config.FLODESTOLERANS * 100:.0f} %)."))

    # 5. Fält som AI:n själv markerat som svårlästa (utom Kv, som hanterats ovan)
    namn = {"uppmatt": "uppmätt flöde", "mattryck": "mättryck", "projekterat": "projekterat flöde",
            "installning": "inställning", "typ": "ventiltyp", "dimension": "dimension",
            "ventilnummer": "ventilnummer", "noteringar": "temperatur"}
    for falt in rad.get("osakra_falt") or []:
        if falt != "kv" and falt in namn:
            flaggor.append(Flagga(OSAKER, falt, f"AI:n är osäker på {namn[falt]} – jämför med bilden."))

    return flaggor


def hitta_dubbletter(rader: list[dict]) -> dict[int, int]:
    """Samma ventil fotad två gånger? Returnerar {radindex: index på tidigare rad}.

    Två rader räknas som trolig dubblett om typ, dimension, inställning och
    projekterat flöde är lika OCH displayens klocka visar samma minut.
    """
    sedda: dict[tuple, int] = {}
    ut: dict[int, int] = {}
    for i, r in enumerate(rader):
        klocka = str(r.get("klocka") or "").strip()
        if not klocka:
            continue
        nyckel = tuple(str(r.get(k) or "").strip() for k in ("typ", "dimension", "installning", "projekterat")) + (klocka,)
        if nyckel in sedda:
            ut[i] = sedda[nyckel]
        else:
            sedda[nyckel] = i
    return ut


def dubbla_ventilnummer(rader: list[dict]) -> dict[str, list[int]]:
    """Samma ventilnummer på flera rader? Returnerar {ventilnummer: [radnummer, ...]} (radnummer från 1).
    Två rader med samma nummer är antingen en dubblett eller ett felskrivet nummer – båda ska upptäckas."""
    sedda: dict[str, list[int]] = {}
    for i, r in enumerate(rader, start=1):
        nr = str(r.get("ventilnummer") or "").strip().casefold()
        if nr:
            sedda.setdefault(nr, []).append(i)
    return {nr: platser for nr, platser in sedda.items() if len(platser) > 1}
