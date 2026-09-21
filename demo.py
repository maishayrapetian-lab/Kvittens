"""
demo.py – exempelbilder utan API-anrop
=======================================
Laddar testbankens foton tillsammans med deras facit, precis som om de just hade
lästs av. Gratis, fungerar utan API-nyckel, och visar en ny användare hela flödet
på tio sekunder – användbart både för att prova appen och för att visa upp den.
"""

from __future__ import annotations

import json
from pathlib import Path

import avlasning

MAPP = Path(__file__).with_name("testbilder")

# Det som utöver facit hör till respektive bild (så som det faktiskt såg ut vid avläsningen)
_KLOCKA = {"IMG_1538.jpeg": ["00:13"], "IMG_1640.jpeg": ["10:28"], "IMG_2031.jpeg": ["06:29"], "IMG_2032.jpeg": ["06:32"],
           "IMG_2033.jpeg": ["06:33"], "IMG_2034.jpeg": ["06:36"], "FullSizeRender.jpeg": ["04:34", "04:34", "04:36", "04:36"]}
_PROCENT = {"IMG_1538.jpeg": ["101"], "IMG_1640.jpeg": ["-.-"], "IMG_2031.jpeg": ["102"], "IMG_2032.jpeg": ["99"],
            "IMG_2033.jpeg": ["101"], "IMG_2034.jpeg": ["103"], "FullSizeRender.jpeg": ["100", "101", "101", "99"]}
_PUMP = {"modell": "Grundfos MAGNA3", "reglertyp": "Konst. tryck", "driftsform": "Max.", "uppfordringshojd": "9.7",
         "uppfordringshojd_enhet": "m", "flode": "", "flode_enhet": "", "vatsketemperatur": "49", "osaker": False}
_TERMOMETER = {"typ": "termometer", "varde": "59", "enhet": "°C", "analog": True, "kommentar": "oskarp, visaren strax under 60"}


def _svar(bild: str, facit: list[dict]) -> dict:
    displayer = []
    for i, f in enumerate(facit):
        skymd = bild == "IMG_2034.jpeg"
        displayer.append({
            "instrument": "TA SCOPE", "position": "", "klocka": _KLOCKA[bild][i],
            "flode": f["uppmatt"], "flode_enhet": "l/s", "dp": f["mattryck"], "dp_enhet": "kPa",
            "temperatur": "", "temperatur_enhet": "°C",
            "projekterat_flode": f["projekterat"] or "0", "projekterat_enhet": "l/s", "procent": _PROCENT[bild][i],
            "ventil": f"{f['typ']} {f['dimension']}", "installning": f["installning"], "installning_enhet": "varv",
            "kv": f["kv"], "medium": "Vatten", "ventilnummer": f["ventilnummer"],
            "osakra_falt": ["kv"] if skymd else [],
            "kommentar": "En reflex skymmer de två sista siffrorna i Kv." if skymd else "",
        })
    pump = bild == "IMG_1640.jpeg"
    return {"displayer": displayer, "pumpar": [_PUMP] if pump else [], "ovriga_matare": [_TERMOMETER] if pump else [],
            "bildkvalitet": "bra"}


def demoposter() -> dict[str, dict]:
    facit = {k: v for k, v in json.loads((MAPP / "facit.json").read_text(encoding="utf8")).items() if not k.startswith("_")}
    ut = {}
    for seq, (bild, rader) in enumerate(facit.items(), start=1):
        data = (MAPP / bild).read_bytes()
        svar = _svar(bild, rader)
        jpeg = avlasning.forbered_bild(data)
        ut[f"demo-{bild}"] = {
            "namn": bild, "seq": seq, "fel": None, "jpeg": jpeg, "visning": avlasning.forhandsvisning(jpeg),
            "rader": avlasning.till_rader(svar, bild), "skillnader": {}, "olika_antal": False,
            "pump": avlasning.pumpforslag(svar), "pumpar": avlasning.alla_pumpforslag(svar), "bildkvalitet": "bra",
            **avlasning.sorteringsinfo(bild, data)}
    return ut
