"""
utseende.py – appens formgivning
=================================
Färger och typsnitt ligger i .streamlit/config.toml (Streamlits officiella tema).
Här finns bara det som temat inte kan: sidhuvudet, mätkorten och kontrollremsan.

Formgivningsprinciper:
  1. Varje siffra ska gå att jämföra med fotot på en sekund  -> stora, tydliga tal.
  2. EN sak får sticka ut: kontrollremsan, som visar om Kv går ihop med flöde och Δp.
  3. Allt annat är tyst: hårlinjer, inga skuggor, inga övertoningar.
  4. Status visas alltid med ORD + färg – aldrig bara färg.

Allt som kommer från AI:n eller användaren körs genom html.escape() innan det
blir HTML, så att ett konstigt tecken på en ventilbricka aldrig kan förstöra sidan.
"""

from __future__ import annotations

from html import escape

import config
import kontroller

CSS = """
<style>
:root{
  --papper:#F6F8F9; --yta:#FFFFFF; --linje:#D3DADF; --blyerts:#1B2B34; --gra:#5B6B76;
  --petrol:#0E5A6B; --massing:#A07C22;
  --rod:#B42318; --rod-bg:#FCE9E7; --gul:#7A5600; --gul-bg:#FFF1CC;
  --gron:#17663F; --gron-bg:#E1F2E8; --info:#44545F; --info-bg:#ECF0F2;
}
[data-testid="stHeader"]{display:none}
[data-testid="stMainBlockContainer"]{max-width:1180px;padding-top:1.25rem;padding-bottom:3rem}

/* ---- uppladdningsrutan på svenska ----
   Streamlit har ingen språkinställning för den inbyggda texten. Ändrar Streamlit rutans uppbyggnad
   slutar reglerna matcha och den engelska originaltexten visas igen – inget går sönder. */
[data-testid="stFileUploaderDropzone"] button [data-testid="stMarkdownContainer"] p{font-size:0}
[data-testid="stFileUploaderDropzone"] button [data-testid="stMarkdownContainer"] p::after{content:"Välj bilder";font-size:1rem}
[data-testid="stFileUploaderDropzoneInstructions"] span{font-size:0}
[data-testid="stFileUploaderDropzoneInstructions"] span::after{content:"JPG, PNG, WEBP eller HEIC, högst 25 MB per bild";font-size:.875rem}

/* ---- sidhuvud ---- */
.ma-huvud{display:flex;flex-wrap:wrap;align-items:center;justify-content:space-between;gap:.75rem 2rem;
  padding-bottom:.9rem;border-bottom:1px solid var(--linje);margin-bottom:.5rem}
.ma-marke{display:flex;align-items:center;gap:.7rem;color:var(--blyerts)}
.ma-marke b{font-size:1.25rem;font-weight:700;letter-spacing:-.01em;line-height:1.1;display:block}
.ma-marke span{font-size:.85rem;color:var(--gra);display:block}
.ma-marke b .ma-kv{font-style:normal;color:var(--massing)}
.ma-symbol{width:34px;height:34px;border-radius:6px;background:var(--petrol);position:relative;flex:none}
.ma-symbol::before{content:"";position:absolute;left:7px;right:7px;top:16px;height:2px;background:#fff;opacity:.55}
.ma-symbol::after{content:"";position:absolute;left:19px;top:8px;width:3px;height:18px;border-radius:2px;background:var(--massing);
  box-shadow:0 0 0 2px var(--petrol)}
.ma-steg{display:flex;gap:.35rem;list-style:none;margin:0;padding:0;font-size:.9rem}
.ma-steg li{display:flex;align-items:center;gap:.45rem;padding:.3rem .7rem .3rem .35rem;border-radius:999px;color:var(--gra);margin:0}
.ma-steg i{font-style:normal;font-weight:600;width:1.5rem;height:1.5rem;border-radius:50%;display:grid;place-items:center;
  border:1px solid var(--linje);background:var(--yta);font-size:.8rem}
.ma-steg li.nu{background:var(--yta);color:var(--blyerts);font-weight:600;border:1px solid var(--linje)}
.ma-steg li.nu i{background:var(--petrol);border-color:var(--petrol);color:#fff}
.ma-steg li.klar i{background:var(--gron-bg);border-color:var(--gron-bg);color:var(--gron)}

/* ---- startsida ---- */
.ma-start{padding:1.2rem 0 .9rem;max-width:40rem}
.ma-start h1{font-size:clamp(1.7rem,4.5vw,2.6rem);font-weight:700;letter-spacing:-.02em;line-height:1.1;margin:0 0 .8rem;padding:0;color:var(--blyerts);text-wrap:balance}
.ma-start p{font-size:1.05rem;line-height:1.55;color:var(--gra);margin:0}
.ma-formel{display:inline-block;margin-top:1.1rem;padding:.45rem .8rem;border:1px solid var(--linje);border-left:3px solid var(--massing);
  border-radius:6px;background:var(--yta);color:var(--blyerts);font-size:.95rem}
.ma-formel b{font-weight:600}

/* ---- mätkort ---- */
.ma-kort{padding:.2rem 0 1rem;border-bottom:1px solid var(--linje);margin-bottom:.9rem}
.ma-kort.av{opacity:.45}
.ma-rubrik{display:flex;flex-wrap:wrap;align-items:baseline;justify-content:space-between;gap:.3rem 1rem;margin-bottom:.55rem}
.ma-namn{font-size:1.05rem;font-weight:700;color:var(--blyerts)}
.ma-namn span{font-weight:400;color:var(--gra);margin-left:.6rem}
.ma-etikett{display:inline-block;font-size:.8rem;font-weight:600;padding:.12rem .6rem;border-radius:999px;white-space:nowrap}
.ma-etikett.stammer{background:var(--gron-bg);color:var(--gron)} .ma-etikett.fel{background:var(--rod-bg);color:var(--rod)}
.ma-etikett.osaker{background:var(--gul-bg);color:var(--gul)}    .ma-etikett.info{background:var(--info-bg);color:var(--info)}
.ma-varden{display:grid;grid-template-columns:repeat(auto-fit,minmax(5.2rem,1fr));gap:.6rem .8rem;margin:0 0 .7rem}
.ma-varden div{min-width:0}
.ma-varden dt{font-size:.78rem;color:var(--gra);margin:0 0 .05rem}
.ma-varden dd{display:inline-block;padding:0 .15em;margin:0 0 0 -.15em;font-size:1.45rem;font-weight:600;line-height:1.15;color:var(--blyerts);white-space:nowrap}
.ma-varden dd small{font-size:.8rem;font-weight:400;color:var(--gra);margin-left:.2rem}
.ma-varden dd.tom{color:#A9B4BB;font-weight:400}
.ma-varden dd.markt{box-shadow:inset 0 -.5em 0 var(--gul-bg)}
.ma-varden dd.markt.fel{box-shadow:inset 0 -.5em 0 var(--rod-bg)}

/* ---- kontrollremsan ---- */
.ma-remsa{margin:.1rem 0 .6rem}
.ma-remsa-text{display:flex;flex-wrap:wrap;gap:.1rem 1.1rem;font-size:.85rem;color:var(--gra);margin-bottom:.3rem}
.ma-remsa-text b{color:var(--blyerts);font-weight:600}
.ma-spar{position:relative;height:14px;border-radius:3px;background:var(--info-bg);overflow:hidden}
.ma-band{position:absolute;top:0;bottom:0;background:#BFE3CE}
.ma-noll{position:absolute;top:0;bottom:0;left:50%;width:1px;background:#B9C3C9}
.ma-visare{position:absolute;top:-1px;bottom:-1px;width:4px;margin-left:-2px;border-radius:2px;background:var(--massing)}
.ma-spar.fel .ma-visare{background:var(--rod)}

.ma-not{font-size:.9rem;color:var(--gra);margin:0 0 .5rem}.ma-not b{color:var(--blyerts);font-weight:600}
.ma-flaggor{list-style:none;margin:0;padding:0;font-size:.9rem;line-height:1.45}
.ma-flaggor li{display:flex;gap:.55rem;align-items:baseline;margin:.25rem 0;padding:0;color:var(--blyerts)}
.ma-flaggor .ma-etikett{flex:none;min-width:4.9rem;text-align:center}

.ma-summa{display:flex;gap:1.6rem;flex-wrap:wrap;margin:.2rem 0 .6rem}
.ma-summa div{display:flex;align-items:baseline;gap:.4rem;color:var(--gra);font-size:.9rem}
.ma-summa b{font-size:1.5rem;font-weight:600;color:var(--blyerts)}
.ma-summa .fel b{color:var(--rod)} .ma-summa .osaker b{color:var(--gul)}
.ma-fot b{color:var(--blyerts);font-weight:600}
.ma-fot{margin-top:2.5rem;padding-top:.9rem;border-top:1px solid var(--linje);font-size:.82rem;color:var(--gra);line-height:1.5}
@media (max-width:640px){ .ma-steg li:not(.nu) span{display:none} .ma-varden dd{font-size:1.3rem} }
</style>
"""

_STEG = ("Bilder", "Granska", "Exportera")
_NIVA = {kontroller.FEL: ("fel", "Kontrollera"), kontroller.OSAKER: ("osaker", "Osäker"), kontroller.INFO: ("info", "Info")}


def sv(text) -> str:
    """Svenskt decimalkomma för visning. '0.158' -> '0,158'."""
    return escape(str(text or "").strip().replace(".", ","))


def ordmarke() -> str:
    """Appens namn, med de första bokstäverna (Kv) i mässing."""
    namn, accent = config.APPNAMN, config.NAMN_ACCENT
    if accent and namn.startswith(accent):
        return f'<i class="ma-kv">{escape(accent)}</i>{escape(namn[len(accent):])}'
    return escape(namn)


def sidhuvud(aktivt_steg: int) -> str:
    """aktivt_steg: 1 = Bilder, 2 = Granska, 3 = Exportera."""
    steg = "".join(
        f'<li class="{"nu" if n == aktivt_steg else "klar" if n < aktivt_steg else ""}">'
        f'<i>{"✓" if n < aktivt_steg else n}</i><span>{namn}</span></li>'
        for n, namn in enumerate(_STEG, start=1))
    return (f'<div class="ma-huvud"><div class="ma-marke"><div class="ma-symbol"></div>'
            f'<div><b>{ordmarke()}</b><span>av {escape(config.UPPHOV)}</span></div></div>'
            f'<ol class="ma-steg">{steg}</ol></div>')


def startsida() -> str:
    """Användarna är injusterare som kan sitt jobb – startsidan säger bara vad man gör här."""
    return ('<div class="ma-start"><h1>Ladda upp dina mätningar</h1>'
            '<p>Foton av TA-SCOPE-displayen, en eller flera displayer per bild. På mobilen kan du fotografera direkt. '
            'Värdena kontrollräknas och skrivs in i injusteringsprotokollet.</p></div>')


def _etikett(klass: str, text: str) -> str:
    return f'<span class="ma-etikett {klass}">{escape(text)}</span>'


def status_for(flaggor: list) -> tuple[str, str]:
    nivaer = {f.niva for f in flaggor}
    if kontroller.FEL in nivaer:
        return "fel", "Kontrollera"
    if kontroller.OSAKER in nivaer:
        return "osaker", "Osäker"
    return "stammer", "Stämmer"


def kontrollremsa(kv: kontroller.KvResultat, kv_avlast: str) -> str:
    """Remsan visar avvikelsen mellan avläst Kv och Kv uträknat ur flöde och Δp.
    Det gröna bandet är vad displayens avrundning tillåter; visaren är den faktiska avvikelsen."""
    if not kv.gick_att_rakna:
        return ""
    spann = max(kv.tolerans * 2.5, 0.02)                      # remsans bredd: ±2,5 × toleransen
    def pos(v: float) -> float:
        return min(max(50 + 50 * v / spann, 1.5), 98.5)
    dec = 3 if kv.kv_beraknat < 1 else 2 if kv.kv_beraknat < 100 else 1
    avv = f"{kv.avvikelse * 100:+.1f}".replace(".", ",").replace("-", "−")
    return (f'<div class="ma-remsa"><div class="ma-remsa-text"><span>Kv avläst <b>{sv(kv_avlast)}</b></span>'
            f'<span>beräknat ur flöde och Δp <b>{kontroller.sv(kv.kv_beraknat, dec)}</b></span>'
            f'<span>avvikelse <b>{avv} %</b></span>'
            f'<span title="Så mycket kan displayens avrundning förklara">tillåtet <b>±{kontroller.sv(kv.tolerans * 100, 1)} %</b></span></div>'
            f'<div class="ma-spar{"" if kv.ok else " fel"}" role="img" aria-label="Avvikelse {avv} procent, '
            f'tillåtet plus minus {kv.tolerans * 100:.1f} procent">'
            f'<div class="ma-band" style="left:{pos(-kv.tolerans):.1f}%;right:{100 - pos(kv.tolerans):.1f}%"></div>'
            f'<div class="ma-noll"></div><div class="ma-visare" style="left:{pos(kv.avvikelse):.1f}%"></div></div></div>')


def matkort(nr: int, rad: dict, flaggor: list) -> str:
    """Ett kort per mätning: stora tal att jämföra med fotot, kontrollremsa och flaggor."""
    markta = {f.falt: ("fel" if f.niva == kontroller.FEL else "") for f in flaggor
              if f.niva in (kontroller.FEL, kontroller.OSAKER) and f.falt}

    def varde(etikett: str, falt: str, enhet: str = "") -> str:
        text = str(rad.get(falt) or "").strip()
        klass = "tom" if not text else f"markt {markta[falt]}".strip() if falt in markta else ""
        inne = f'{sv(text)}<small>{escape(enhet)}</small>' if text else "–"
        return f'<div><dt>{etikett}</dt><dd class="{klass}">{inne}</dd></div>'

    ventil = " ".join(x for x in (str(rad.get("typ") or "").strip(), str(rad.get("dimension") or "").strip()) if x)
    bricka = str(rad.get("ventilnummer") or "").strip()
    rubrik = escape(ventil or "Okänd ventil") + (f'<span>ventil {escape(bricka)}</span>' if bricka else "")
    if not rad.get("ta_med", True):
        return (f'<div class="ma-kort av"><div class="ma-rubrik"><div class="ma-namn">Mätning {nr}<span>{rubrik}</span></div>'
                f'{_etikett("info", "Tas inte med")}</div></div>')

    klass, ord_ = status_for(flaggor)
    not_text = str(rad.get("noteringar") or "").strip()
    notering = f'<p class="ma-not">Noteringar: <b>{escape(not_text)}</b></p>' if not_text else ""
    kv = kontroller.kv_kontroll(rad.get("uppmatt"), rad.get("mattryck"), rad.get("kv"))
    lista = "".join(f'<li>{_etikett(*_NIVA[f.niva])}<span>{escape(f.text)}</span></li>' for f in flaggor)
    return (f'<div class="ma-kort"><div class="ma-rubrik"><div class="ma-namn">Mätning {nr}<span>{rubrik}</span></div>{_etikett(klass, ord_)}</div>'
            f'<dl class="ma-varden">{varde("Uppmätt flöde", "uppmatt", config.FLODESENHET)}'
            f'{varde("Mättryck", "mattryck", config.TRYCKENHET)}{varde("Kv", "kv")}'
            f'{varde("Inställning", "installning", "varv")}{varde("Projekterat", "projekterat", config.FLODESENHET)}</dl>'
            f'{kontrollremsa(kv, rad.get("kv"))}'
            f'{notering}'
            f'{f"<ul class=ma-flaggor>{lista}</ul>" if lista else ""}</div>')


def sammanfattning(matningar: int, gar_inte_ihop: int, osakra: int) -> str:
    """Tre tal på EN rad – även på mobilen, där Streamlits egna mätare staplas på höjden."""
    def del_(tal: int, text: str, klass: str) -> str:
        return f'<div class="{klass if tal else ""}"><b>{tal}</b><span>{text}</span></div>'
    return (f'<div class="ma-summa"><div><b>{matningar}</b><span>mätningar</span></div>'
            f'{del_(gar_inte_ihop, "går inte ihop", "fel")}{del_(osakra, "osäkra", "osaker")}</div>')


def sidfot() -> str:
    return (f'<div class="ma-fot"><b>{escape(config.APPNAMN)}</b> {escape(config.VERSION)} – {escape(config.SLOGAN.lower())}. '
            f'Skapad av {escape(config.UPPHOV)}. © {escape(config.UPPHOV_AR)} {escape(config.UPPHOV)}.<br>'
            f'Avläsningarna är förslag – den som undertecknar protokollet ansvarar för värdena. '
            f'Bilderna skickas till Anthropics API för avläsning. '
            f'Ett påbörjat jobb ligger i serverns minne i högst 12 timmar och sparas aldrig på disk.</div>')
