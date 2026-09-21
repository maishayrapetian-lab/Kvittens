# Kodgranskningen – vad som gjordes med varje punkt

Granskningen bedömer projektet som ett vanligt programvaruprojekt. Tre förutsättningar gör att allt inte passar här: ägaren kodar inte själv (allt måste gå att sköta med dubbelklick), appen ska ligga på en gratis värd där **disken nollställs vid varje omstart**, och appen har lovat användarna att **ingenting sparas**. Principen har varit: laga det som är trasigt, bygg det som är billigt och skyddar på riktigt, och skjut upp det som kräver ett beslut av dig.

| # | Punkt | Beslut | Kommentar |
|---|---|---|---|
| 2 | Dubbla filer, `__pycache__` i Git | **Åtgärdat** | Orsaken var att zip-filen packats upp inuti den gamla mappen. `uppdatera.bat` lägger nu varje ny version rätt, flyttar undan dubblettkopian (raderar inget) och tar bort `__pycache__`. Förslaget om `src/`-struktur och `pyproject.toml` är **inte** genomfört: Streamlit Community Cloud vill ha `app.py` och `requirements.txt` i roten, och dubbelklicksfilerna bygger på det. |
| 3 | Automatisk kontroll (CI) | **Åtgärdat** | `.github/workflows/kontroll.yml`: syntax, Ruff och alla tester på Python 3.12 och 3.13 vid varje uppladdning – plus en spärr som stoppar om en nyckelfil, `__pycache__` eller dubblettmappen råkar checkas in. |
| 14 | Lås beroenden | **Åtgärdat** | Exakta versioner i `requirements.txt`, testade i en ren installation. Testverktygen ligger i `requirements-dev.txt`. |
| 10 | Fler kontroller av mätvärden | **Åtgärdat** | Negativa värden och nollvärden, dimension som är ovanlig för ventiltypen, samma ventilnummer på flera rader, och enheter som appen inte känner igen (förut lämnades värdet oomräknat utan ett ord – en riktig lucka). |
| 9 | Flera pumpar | **Åtgärdat** | Alla pumpdisplayer redovisas, och man väljer vilken som hör till protokollet. |
| 11 | Inloggning | **Delvis** | Spärr efter fem felaktiga lösenord (per webbläsare, plus en gemensam mot automatiska gissningar). Individuella konton finns redan på ett annat ställe: en privat app på Streamlit släpper bara in inbjudna e-postadresser. Roller och ändringslogg kräver en databas – se punkt 1. |
| 12 | Mejlskydd | **Fanns redan + två tillägg** | Adresskontroll, låsbara domäner, dygnstak och fast mejltext fanns sedan 3.8. Nytt: dold arkivkopia (`MEJL_KOPIA_TILL`) och storleksgräns på bilagan. |
| 13 | Tydlighet om bilder och uppgifter | **Åtgärdat** | Rutan *Om dina bilder och uppgifter* på varje sida, och knappen *Radera det här jobbet nu*. |
| 15 | Loggning och typer | **Delvis** | `logg.py` loggar vad som gick fel och var – aldrig nycklar, mejladresser, objektnamn eller mätvärden. En omskrivning till dataklasser är inte gjord: mycket ändrad kod, ingen nytta för användaren, och 150 tester skyddar redan strukturerna. |
| 4 | Billigare AI-avläsning | **Delvis, med invändning** | Nytt: tak per jobb och besked om antal AI-avläsningar före start. **Inte** genomfört: att bara dubbelläsa när första avläsningen är osäker. Det låter klokt men är bakvänt här: när Kv- eller procentkontrollen slår till har appen redan flaggat värdet. Dubbelläsningen behövs för de fält som *ingen* formel skyddar – typ, dimension, inställning och ventilnummer – och de kan vara fel utan att första avläsningen verkar osäker. Kostnaden är några ören per bild. |
| 1 | Databas i stället för minne | **Uppskjutet – kräver ditt beslut** | På gratisvärden nollställs disken vid omstart, så SQLite ger ingen beständighet där. En molndatabas betyder att kundernas foton och protokoll lagras permanent hos ännu en leverantör, och appens löfte "inget sparas" måste då tas bort. Risken som finns i dag är liten: ett jobb tar minuter, och förloras bara om servern startas om just då. |
| 6, 7 | Ifyllnad från tidigare jobb, historik, sökning | **Uppskjutet** | Bygger helt på punkt 1. |
| 8 | PDF-export | **Uppskjutet – bra nästa steg** | Kräver antingen LibreOffice på servern (tungt på gratisvärden) eller en egen PDF-mall som måste hållas lika som Excel-mallen. Värt att göra när appen används i fält. |
| 5 | Bildkvalitet, beskärning, zoom | **Uppskjutet – bra nästa steg** | En inzoomad display bredvid varje mätning vore den största förbättringen av granskningen. Den kräver att AI:n också anger *var* i bilden displayen sitter, vilket ändrar avläsningen och måste mätas om med `utvardera.bat`. |

## Rekommenderad ordning härifrån

1. Kör `uppdatera.bat`, ladda upp med GitHub Desktop och se att bocken på GitHub blir grön.
2. Använd appen i fält och samla riktiga missar i `testbilder/`.
3. Inzoomad display per mätning (punkt 5).
4. PDF-export (punkt 8).
5. Beslut om beständig lagring (punkt 1) – först när historik verkligen efterfrågas.
