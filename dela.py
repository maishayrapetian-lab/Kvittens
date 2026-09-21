"""
dela.py – "Dela eller mejla protokollet" via mobilens egen delningsruta
========================================================================
Safari på iPhone, iPad och Mac kan lämna över en fil från en webbsida till delningsrutan
(samma som när man delar ett foto): välj Mail, Teams eller Filer. Mejlet skickas då från
DITT EGET mejlkonto. Ingenting behöver ställas in.

VIKTIG BEGRÄNSNING: Chrome och Edge (Windows, Android) tillåter bara att vissa filtyper delas
den här vägen – bilder, pdf, text, ljud och video. Excel-filer nekas av webbläsaren
("NotAllowedError"), trots att den först svarar att delning går bra. Där visas därför ingen
knapp utan en förklaring. Den väg som fungerar ÖVERALLT är mejlutskicket i mejl.py.
"""

from __future__ import annotations

import base64

import streamlit as st

XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

_HTML = '<button class="dela-knapp" type="button">Dela eller mejla protokollet</button><p class="dela-info"></p>'

_CSS = """
.dela-knapp{width:100%;min-height:2.5rem;padding:.45rem 1rem;border-radius:6px;border:1px solid #D3DADF;background:#fff;
  color:#1B2B34;font:inherit;cursor:pointer}
.dela-knapp:hover,.dela-knapp:focus-visible{border-color:#0E5A6B;color:#0E5A6B;outline:none}
.dela-info{font-size:.85rem;line-height:1.4;color:#5B6B76;margin:.45rem 0 0}
"""

_JS = """
export default function(component) {
  const { data, parentElement } = component;
  const knapp = parentElement.querySelector('.dela-knapp');
  const info = parentElement.querySelector('.dela-info');
  let fil = null;
  try {
    const bin = atob(data.b64);
    const bytes = new Uint8Array(bin.length);
    for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
    fil = new File([bytes], data.namn, { type: data.mime });
  } catch (e) { fil = null; }

  // Chrome/Edge (Chromium) nekar Excel-filer i delningsrutan. userAgentData finns bara i Chromium-motorn,
  // inte i Safari – och inte i Chrome på iPhone, som använder Safaris motor och därför fungerar.
  const chromium = !!navigator.userAgentData;
  const kan = fil && !chromium && typeof navigator.canShare === 'function' && navigator.canShare({ files: [fil] });
  if (!kan) {
    knapp.style.display = 'none';
    info.textContent = chromium ? data.chromium : data.kan_inte;
    return;
  }
  info.textContent = data.hjalp;
  knapp.onclick = async () => {
    try {
      await navigator.share({ files: [fil], title: data.amne, text: data.text });
      info.textContent = data.klart;
    } catch (e) {
      if (e && e.name === 'AbortError') return;                       // du stängde rutan själv
      info.textContent = (e && e.name === 'NotAllowedError') ? data.nekad : data.fel;
    }
  };
}
"""


def _registrera():
    return st.components.v2.component("dela_protokoll", html=_HTML, css=_CSS, js=_JS)


_komponent = _registrera()


def delaknapp(data: bytes, filnamn: str, amne: str, text: str, key: str = "dela") -> None:
    """Visar dela-knappen. Får ALDRIG fälla exportsteget: går något fel finns nedladdningen alltid kvar."""
    global _komponent
    innehall = {
        "b64": base64.b64encode(data).decode("ascii"), "namn": filnamn, "mime": XLSX, "amne": amne, "text": text,
        "hjalp": "Öppnar mobilens delningsruta med protokollet bifogat. Välj Mail, så skickas det från ditt eget mejlkonto.",
        "klart": "Delningsrutan öppnades. Skickade du mejlet ligger det i din skickat-mapp.",
        "fel": "Det gick inte att dela filen härifrån. Ladda ner protokollet och bifoga det i ett mejl i stället.",
        "kan_inte": "Den här webbläsaren kan inte dela filer direkt. Ladda ner protokollet och bifoga det i ett mejl.",
        "chromium": "Chrome och Edge tillåter inte att Excel-filer delas direkt från en webbsida (bara bilder, pdf och text). "
                    "Ladda ner protokollet och bifoga det i ett mejl – eller slå på mejlutskicket ovan, så skickas det "
                    "automatiskt. I Safari på iPhone finns en dela-knapp här.",
        "nekad": "Webbläsaren nekade att dela Excel-filen. Ladda ner protokollet och bifoga det i ett mejl, "
                 "eller slå på mejlutskicket ovan.",
    }
    try:
        _komponent(key=key, data=innehall)
    except Exception:
        try:                                   # servern kan ha startat om komponentregistret – registrera på nytt
            _komponent = _registrera()
            _komponent(key=key, data=innehall)
        except Exception:
            st.caption("Dela-knappen kunde inte visas här. Ladda ner protokollet och bifoga det i ett mejl.")
