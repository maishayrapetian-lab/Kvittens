"""
protokoll.py – skriver in mätningarna i din Excel-mall
=======================================================
Mallen laddas med openpyxl, som behåller logga, typsnitt, utskriftsinställningar
och rutnät. Bara värdena fylls i:

  * en rad per mätning från rad 9 och nedåt, varje värde i sin kolumn
  * objekt, byggnad, datum och utfört av i rubrikfälten (båda bladen)
  * pumpdata på försättsbladets förskrivna rader
"""

from __future__ import annotations

import io
from copy import copy
from pathlib import Path

from openpyxl import load_workbook

import config
from kontroller import mvp_till_kpa, tolka_tal

_TALFALT = ("installning", "dimension", "kv", "mattryck", "projekterat", "uppmatt")
_TEXTFALT = ("system", "ventilnummer", "placering", "fabrikat", "typ", "noteringar")


def _kolumnformat(ws) -> dict[int, object]:
    """Mallens rutnät och typsnitt ligger som standardformat på kolumnerna.
    openpyxl ärver dem inte automatiskt till nya celler, så vi hämtar dem här."""
    ut = {}
    for bokstav, dim in ws.column_dimensions.items():
        start = dim.min or ws[f"{bokstav}1"].column
        for kol in range(start, (dim.max or start) + 1):
            ut[kol] = dim._style
    return ut


def _sv(text: str) -> str:
    return str(text).strip().replace(".", ",")


def skapa_protokoll(rader: list[dict], jobb: dict | None = None, pump: dict | None = None,
                    mall: str | Path | None = None) -> bytes:
    """Returnerar den ifyllda Excel-filen som bytes (redo för nedladdning).

    rader: mätningarna i protokollordning. Värdena är TEXT precis som de lästes av
           ('1.90') – då kan vi behålla displayens antal decimaler i Excel.
    jobb:  {"objekt", "byggnad", "datum", "utfort_av"} – skrivs alltid över i mallen (tomt blir tomt).
    pump:  {"beteckning", "driftform", "dynamiskt_mvp", "statiskt_bar"}
    """
    pump = pump or {}
    wb = load_workbook(mall or Path(__file__).with_name(config.MALL))
    ws = wb[config.BLAD_PROTOKOLL]
    fs = wb[config.BLAD_FORSATTSBLAD]
    format_per_kolumn = _kolumnformat(ws)
    sista_kolumn = max(config.KOLUMNER.values())

    # ---- mätningarna ------------------------------------------------------
    for i, rad in enumerate(rader):
        r = config.FORSTA_DATARAD + i
        for kol in range(1, sista_kolumn + 1):                 # ge hela raden mallens utseende
            cell = ws.cell(r, kol)
            cell.value = None                                  # rensa ev. exempeltext i mallen
            if kol in format_per_kolumn:
                cell._style = copy(format_per_kolumn[kol])
        ws.row_dimensions[r].height = 15

        for falt in _TEXTFALT:
            text = str(rad.get(falt) or "").strip()
            if not text:
                continue
            cell = ws.cell(r, config.KOLUMNER[falt])
            if falt == "ventilnummer" and text.isdigit() and not text.startswith("0"):
                cell.value, cell.number_format = int(text), "0"
            else:
                cell.value = text

        for falt in _TALFALT:
            text = str(rad.get(falt) or "").strip()
            if not text:
                continue
            cell = ws.cell(r, config.KOLUMNER[falt])
            tal, decimaler = tolka_tal(text)
            if tal is None:                                    # t.ex. "DN20" – skrivs som text
                cell.value = text
                continue
            cell.value = int(tal) if decimaler == 0 else tal   # riktiga tal: svensk Excel visar decimalkomma
            cell.number_format = "0" if decimaler == 0 else "0." + "0" * decimaler

        if str(rad.get("noteringar") or "").strip():           # noteringar får radbrytas
            not_cell = ws.cell(r, config.KOLUMNER["noteringar"])
            just = copy(not_cell.alignment)
            just.wrap_text, just.vertical = True, "center"
            not_cell.alignment = just
            if len(str(rad["noteringar"])) > 28:
                ws.row_dimensions[r].height = 24
                for kol in range(1, sista_kolumn):
                    c = ws.cell(r, kol)
                    j = copy(c.alignment)
                    j.vertical = "center"
                    c.alignment = j

    # Mallens exempelrader som blev över (om färre mätningar än exempelrader) rensas
    r = config.FORSTA_DATARAD + len(rader)
    while r <= ws.max_row and any(ws.cell(r, k).value not in (None, "") for k in range(1, sista_kolumn + 1)):
        for kol in range(1, sista_kolumn + 1):
            ws.cell(r, kol).value = None
        r += 1

    # ---- rubrikfält på båda bladen -----------------------------------------
    # Mallen delas av flera användare. Därför skrivs fälten ALLTID över när jobbuppgifter skickas med –
    # annars följer förra jobbets objekt eller en kollegas namn med in i nästa protokoll.
    if jobb:
        for nyckel, celler in (("objekt", config.CELL_OBJEKT), ("byggnad", config.CELL_BYGGNAD),
                               ("datum", config.CELL_DATUM), ("utfort_av", config.CELL_UTFORT_AV)):
            varde = str(jobb.get(nyckel) or "").strip()
            if nyckel == "byggnad" and not varde:
                varde = "-"                                        # mallens sätt att visa "ingen byggnad"
            ws[celler["protokoll"]] = varde or None
            fs[celler["forsattsblad"]] = varde or None

    # ---- pumpdata på försättsbladet -----------------------------------------
    if str(pump.get("beteckning") or "").strip():
        fs[config.CELL_PUMP_RUBRIK] = f"Pump {pump['beteckning'].strip()} inställd på:"
    if str(pump.get("driftform") or "").strip():
        fs[config.CELL_PUMP_DRIFTFORM] = f"Driftform: {pump['driftform'].strip()}"
    mvp, _ = tolka_tal(pump.get("dynamiskt_mvp"))
    if mvp is not None:
        fs[config.CELL_PUMP_DYNAMISKT] = (f"Dynamisk tryck: {_sv(pump['dynamiskt_mvp'])} mvp "
                                          f"({mvp_till_kpa(mvp):.0f} kPa)")
    if tolka_tal(pump.get("statiskt_bar"))[0] is not None:
        fs[config.CELL_PUMP_STATISKT] = f"Statisk tryck: {_sv(pump['statiskt_bar'])} Bar"

    ut = io.BytesIO()
    wb.save(ut)
    return ut.getvalue()
