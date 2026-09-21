# Kvittens v3.12

Foto av TA-SCOPE → AI skriver av displayen → appen letar fel → du bekräftar → in i din injusteringsmall.

## Nytt sedan förra versionen

| Förut | Nu |
|---|---|
| En bild → fasta celler (`FIELD_CELLS`) | Många bilder, **en rad per display**, varje värde i protokollets kolumn |
| AI:n svarade med fritext-JSON som kunde gå sönder | **Strukturerat svar** – API:t garanterar formatet |
| Du var enda felkontrollen | **Appen letar fel åt dig först**: Kv-kontroll, procentkontroll, dubbelkontroll, rimlighet |
| Typ "städades" (STAD* → STAD) | Ventilraden skrivs av **tecken för tecken** – asterisken är kvar |
| Fabrikat "TA" | **IMI TA** (en rad i `config.py` om du hellre vill ha "IMI") |
| – | Pumpdisplay → **försättsbladets** rader (driftform, dynamiskt tryck mvp/kPa) |
| – | Temperaturer → **Noteringar**, bricka i bild → **Ventilnummer** |
| – | Bilderna sorteras i **den ordning de togs**, vrids rätt och skalas ned |
| – | **Lösenord**, och export spärras tills flaggade rader är kvitterade |
| – | **150 automatiska tester** + mätning av träffsäkerhet mot facit |

## Nytt i 3.12 – efter kodgranskningen

Alla femton punkter är genomgångna – se **`GRANSKNING.md`** för vad som gjordes med var och en, och varför några medvetet väntar.

- **`uppdatera.bat`** – nytt sätt att uppdatera: packa upp zip-filen var som helst och dubbelklicka på `uppdatera.bat` i den uppackade mappen. Filerna hamnar rätt, nyckelfilen och `.venv` rörs inte, och en felaktig dubblettkopia flyttas undan. Det löser grundorsaken till att samma filer låg både i roten och i `matarapp/`.
- **Automatisk kontroll på GitHub** vid varje uppladdning: tester, kodgranskning och en spärr mot incheckade nyckelfiler.
- Nya kontroller: negativa värden och nollvärden, ovanlig dimension för ventiltypen, samma ventilnummer på flera rader, okända enheter.
- Flera pumpar kan väljas, inloggningen spärras efter fem felförsök, mejlet kan få en dold arkivkopia.
- Rutan *Om dina bilder och uppgifter* och knappen *Radera det här jobbet nu*.
- Exakt låsta paketversioner och en felsökningslogg utan känsliga uppgifter.

## Nytt i 3.11 – ärligt besked om dela-knappen

I 3.10 visades dela-knappen även i Chrome och Edge, där den aldrig kan fungera: de webbläsarna tillåter bara att bilder, pdf, text, ljud och video delas från en webbsida, inte Excel-filer. Nu visas knappen bara där den fungerar (Safari), och annars ett klart besked om vad man gör i stället.

## Nytt i 3.10 – mejl som går att välja

Förut var mejlfältet helt dolt tills en mejlserver var inställd, så det såg ut som att funktionen saknades.

- **Dela eller mejla protokollet**: ny knapp som dyker upp när protokollet är skapat. Den öppnar mobilens egen delningsruta med filen bifogad – välj Mail, Teams eller Filer. Mejlet skickas från ditt eget konto. **Kräver ingen inställning alls** – men fungerar bara i **Safari** (iPhone, iPad, Mac). Chrome och Edge tillåter inte att Excel-filer delas den vägen; där visas en förklaring i stället för knappen. Den väg som fungerar överallt är mejlutskicket.
- **Mejla protokollet till** syns nu alltid. Är mejlutskicket inte påslaget är fältet grått, och en ruta direkt under förklarar varför och hur man slår på det.
- Appen upptäcker om mejlraderna är ifyllda i nyckelfilen men fortfarande har **#** framför sig – ett lätt misstag.

## Nytt i 3.9 – appen heter Kvittens

**Kv**ittens = *Kv*-värdet + att *kvittera*. Appen kontrollräknar Kv för varje mätning, och du kvitterar avläsningen innan den går in i protokollet – samma ord som när man kvitterar ett larm i en DUC.

- Namnet står i sidhuvudet med **Kv** i mässing, och under det: *av Mais Hayrapetian*. Sidfoten och mejlen anger också upphovet.
- Protokollet självt är orört: det är företagets dokument och undertecknas av den som utfört mätningen.
- Byta namn igen? Tre rader i `config.py`: `APPNAMN`, `NAMN_ACCENT` och `UPPHOV`. Mappen heter fortfarande `matarapp` – det är bara ett tekniskt namn, och att byta det skulle bryta din installation.

## Nytt i 3.8 – protokollet på mejlen

- I exportsteget finns fältet **Mejla protokollet till**. Protokollet skickas som bilaga när du trycker *Skapa protokollet*; nedladdningen finns alltid kvar, och adressen följer med till nästa jobb.
- Fungerar mejlet inte skapas protokollet ändå, med ett begripligt besked om vad som gick fel.
- Aktiveras med två rader i nyckelfilen (`SMTP_ANVANDARE`, `SMTP_LOSENORD`) – se `DRIFTSÄTTNING.md`, steg 6. `kontrollera.bat` har fått ett sjunde steg som testar mejlinloggningen.
- Skydd: fast mejltext, adresskontroll (inga insmugna mottagare), dygnstak och möjlighet att låsa mottagardomäner.

## Nytt i 3.7 – redo för fält

Läs **`DRIFTSÄTTNING.md`** – där står steg för steg hur appen läggs upp på nätet och används från mobilen.

- **Jobbet överlever att mobilen somnar.** Laddas sidan om hämtas det påbörjade jobbet tillbaka via en kod i adressen. Det ligger i serverns minne i högst 12 timmar och sparas aldrig på disk.
- **Spärr utan lösenord.** Nås appen från annat håll än din egen dator och `APP_LOSENORD` saknas, spärrar den sig själv.
- **Dygnstak** på 400 avlästa bilder (`MAX_BILDER_PER_DYGN`) som kostnadsskydd.
- Streamlit-versionen är låst till den som är testad, så att en automatisk uppgradering inte kan ändra appen bakom ryggen på dig.

## Nytt i 3.6 – tre steg, ett i taget

Förut låg allt på en lång sida, och efter granskningen fanns ingen knapp som förde vidare. Nu är appen tre skärmar:

1. **Bilder** – ladda upp och tryck *Läs av bilderna*. Du hamnar direkt i granskningen.
2. **Granska** – jämför talen med fotona. Längst ned finns rutan *Klar med granskningen?* med knappen **Fortsätt till export**. Finns flaggade värden är knappen släckt tills du kryssat i att du jämfört dem – och appen säger det i klartext.
3. **Exportera** – fyll i objekt, utfört av m.m. och tryck **Skapa protokollet**. Saknas något obligatoriskt får du besked om vad. Sedan **Ladda ner protokollet**, och **Börja på ett nytt jobb** (ditt namn följer med).

Du kan gå tillbaka från export till granskning utan att förlora det du rättat i tabellerna.

## Nytt i 3.5 – appen och kontrollen kan inte längre vara oense

- Appen läser nyckeln från **samma ställe som `kontrollera.bat`**: projektets egen `.streamlit/secrets.toml`. Förut frågade appen Streamlit först, som även läser en global fil i din användarmapp och kan hålla kvar ett gammalt värde – då kunde kontrollen vara grön medan appen skickade en gammal, borttagen nyckel.
- Filen läses om vid varje avläsning. **Byter du nyckel gäller den nya direkt**, utan omstart.
- Kontrollen visar nyckelns **fyra sista tecken**, så att du kan jämföra med listan i Console, och varnar om en annan nyckel ligger kvar någon annanstans på datorn.

## Nytt i 3.4 – tål misstag, och kontrollerar sig själv

- **`kontrollera.bat`**: en genomgång i sex steg som slutar med en riktig avläsning av en testbild. Resultatet sparas i `kontroll_resultat.txt`.
- **`installera.bat`**: installerar allt utan terminal.
- **Förlåtande nyckelhantering** (`hemligheter.py`): fel filnamn, saknade citattecken, "smarta" citattecken och olika textkodningar från Anteckningar klaras av och rättas.
- Exempelfilen `secrets.toml.example` är borttagen – den var för lätt att förväxla med den riktiga filen.
- Appens ikon och mall hittas oavsett från vilken mapp appen startas.
- Provkört i en helt ren installation från grunden, och med riktig uppladdning i webbläsare hela vägen fram till API:t.

## Nytt i 3.3 – dubbelklicka i stället för terminal

- **`starta_appen.bat`** (Windows) / **`starta_appen.command`** (Mac): startar appen med projektets egen Python och bara på din egen dator (`localhost`), inte på hela nätverket.
- **`utvardera.bat`** / **`utvardera.command`**: kör träffsäkerhetsmätningen och håller fönstret öppet. Resultatet sparas alltid i `utvardering_resultat.txt`.
- `utvardera.py` hämtar nu API-nyckeln från **samma `secrets.toml` som appen**. Förut krävde skriptet en miljövariabel, så det avslutades direkt – fönstret bara flimrade till.
- Appen **varnar för svaga lösenord** (kortare än 12 tecken eller vanliga som "admin") och väntar två sekunder efter varje felgissning.

## Nytt i 3.2 – rakt på sak, och säkert för flera användare

- **Startsidan** säger bara det som behövs: *Ladda upp dina mätningar*. Användarna är injusterare som kan sitt jobb.
- **En gemensam mall.** Alla mätningar går in i samma injusteringsprotokoll (`mall.xlsx`).
- Eftersom mallen delas är den **rensad** från det som var förifyllt (objekt, namn, exempelsystem), och protokollets huvud skrivs alltid över vid export. **Objekt** och **Utfört av** måste fyllas i innan protokollet går att ladda ner – annars kunde en kollegas protokoll få fel namn eller förra jobbets objekt.
- Uppgifterna till protokollet (objekt, byggnad, system, datum, utfört av) och pumpdata ligger nu i **exportsteget**, där de hör hemma.

## Utseendet (nytt i 3.1)

- **Mätkort** bredvid varje foto: stora tal att jämföra med displayen, status i ord (Stämmer / Osäker / Kontrollera) och osäkra värden markerade direkt i talet.
- **Kontrollremsan** visar Kv-kontrollen grafiskt: grönt fält = vad displayens avrundning tillåter, visaren = den faktiska avvikelsen.
- **Sidhuvud med tre steg** (Bilder, Granska, Exportera), startsida, inloggningssida och sidfot med ansvarstext.
- **Prova med exempelbilder**: sju riktiga foton som redan är avlästa. Inget API-anrop, ingen kostnad – bra både för att prova och för att visa upp tjänsten.
- Tabellerna för rättning ligger hopfällda under varje bild, så att sidan är lugn på mobilen.
- Typsnittet **Barlow** (DIN-inspirerat, som textningen på tekniska ritningar; vanlig nolla) ligger i `static/` – inga anrop till Google Fonts.
- Streamlits utvecklarmeny är dold, och fel visas aldrig som kod för besökare (de står i terminalen i stället).

### Byt namn och profil

| Vad | Var |
|---|---|
| Namn, slogan, version | `config.py` → `APPNAMN`, `SLOGAN`, `VERSION` |
| Färger, typsnitt, hörnradier | `.streamlit/config.toml` |
| Ikon i webbläsarfliken | `static/ikon.png` |
| Sidhuvud, mätkort, kontrollremsa | `utseende.py` |

### Var går gränsen för Streamlit?

Det här utseendet räcker gott till pilotkunder och en liten prenumerationstjänst. Det Streamlit **inte** klarar är egen registrering och betalning, full kontroll över mobilupplevelsen (tabellen är Streamlits egen) och mycket trafik. Blir det aktuellt byts bara `app.py` och `utseende.py` mot ett eget webbgränssnitt – kärnan (`avlasning.py`, `kontroller.py`, `protokoll.py`) vet ingenting om Streamlit och följer med oförändrad.

## Kom igång – tre dubbelklick

| Steg | Windows | Mac | Vad den gör |
|---|---|---|---|
| 1 | `installera.bat` | `installera.command` | Skapar projektets egen Python-miljö och installerar paketen. Körs en gång. |
| 2 | `kontrollera.bat` | `kontrollera.command` | Går igenom allt: Python, paket, filer, API-nyckel, kontakt med AI-tjänsten, saldo, modell och **en riktig provavläsning**. Säger på vanlig svenska vad som är fel. Saknas nyckeln öppnas rätt fil åt dig. |
| 3 | `starta_appen.bat` | `starta_appen.command` | Startar appen i webbläsaren, bara på din egen dator. |

`utvardera.bat` kör hela träffsäkerhetsmätningen på alla testbilder.
`oppna_nyckelfilen.bat` öppnar filen med API-nyckel och lösenord i Anteckningar – t.ex. när du ska byta nyckel.

Första gången kan Windows varna för en nedladdad fil: välj *Mer information* och *Kör ändå*. På Mac: högerklicka och välj *Öppna*.

### API-nyckeln

Nyckeln ska ligga i `.streamlit/secrets.toml`. `kontrollera.bat` skapar filen och öppnar den åt dig. Koden är förlåtande: hamnar nyckeln i fel fil (t.ex. en `.txt` eller en exempelfil) eller tappar citattecknen, så **flyttas och rättas den automatiskt**, och nyckeln tas bort ur den felaktiga filen. Nyckeln skrivs aldrig ut – varken på skärmen eller i resultatfilerna, som därför är ofarliga att skicka vidare. Ladda däremot aldrig upp själva `secrets.toml` någonstans.

### Om något är rött

Skicka innehållet i `kontroll_resultat.txt` till Claude. Varje rött besked säger också vad du ska göra.

## Så hittar appen fel

| Kontroll | Skyddar | Hur |
|---|---|---|
| **Kv-kontroll** 🔴 | Uppmätt flöde, Mättryck, Kv | `Kv = 36 · q[l/s] / √Δp[kPa]` måste stämma med avläst Kv, inom displayens avrundning + 1 % |
| **Procentkontroll** 🔴 | Projekterat flöde | Displayens procent måste stämma med uppmätt ÷ projekterat |
| **Dubbelkontroll** 🟡 | Typ, Dimension, Inställning, Ventilnummer m.fl. | Bilden läses två gånger (andra gången kontrastförstärkt); skillnader flaggas |
| **AI:ns egen osäkerhet** 🟡 | Alla fält | Skymda/suddiga tecken rapporteras per fält. Analoga visare är *alltid* osäkra |
| **Rimlighet** 🔴/🔵 | Inställning, Mättryck, Flöde | > 4 varv på STAD-familjen · Δp < 3 kPa · avvikelse > ±10 % mot projekterat |
| **Dubbletter** 🔵 | Hela raden | Samma ventil, inställning, projekterat flöde och klockslag |

Kv-kontrollen kan dessutom *rädda* ett värde: är Kv skymt av en reflex visar appen intervallet som flöde och Δp tillåter.

## Mät träffsäkerheten

Dubbelklicka på `utvardera.bat` (Mac: `utvardera.command`).

Skriptet läser av `testbilder/` och jämför fält för fält med `testbilder/facit.json`. Kör det **före och efter** varje ändring av prompt, modell eller bildstorlek – annars vet du inte om ändringen gjorde appen bättre eller sämre. Fyll på testbanken med svåra bilder från fältet; varje fel du hittar i verkligheten hör hemma där.

## Testerna

`python -m pytest tests` – kräver ingen API-nyckel. De bevisar bland annat att alla tio verkliga displayer i testbanken passerar utan falsklarm, att sex typiska felavläsningar fångas, att asterisken överlever hela vägen till Excel och att logga, rutnät och decimaler behålls i mallen.

## Anpassa

Allt ligger i `config.py`: modell, bildstorlek, mallens celler och kolumner, fabrikat, toleranser. `mall.xlsx` är din `.xls`-mall konverterad till `.xlsx` (Python kan inte skriva i det gamla formatet). Byter du mall: spara den som `.xlsx` i Excel och lägg den här.

## Känt och ärligt

- **Själva AI-anropet är inte provkört** här – det kräver din API-nyckel. Allt runt omkring är testat. Första körningen av `utvardera.py` är därför det viktigaste nästa steget.
- Kv-kontrollen fångar grova fel (fel siffra, flyttat decimaltecken, förväxlade fält), **inte alltid sista decimalen** – displayen avrundar. Ett test visar det uttryckligen.
- Inställning, Typ och Dimension skyddas bara av dubbelkontrollen. Nästa nivå är IMI:s Kv-tabeller (typ + DN + varv → Kv). `STAD` och `STAD*` behöver **var sin** tabell, och tabellen för `STAD*` är ännu inte verifierad från primärkälla.
- TA-SCOPE:s databas innehåller bara IMI:s ventiler. Mäter du andra fabrikat i Kv-läge visar displayen inget ventilnamn – då lämnas Fabrikat och Typ tomma åt dig.
- Bilderna skickas till Anthropics API för avläsning. Undvik personuppgifter i bild.
