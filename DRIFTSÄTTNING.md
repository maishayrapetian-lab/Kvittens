# Ut i fält – så lägger du upp Kvittens på nätet

Målet: en adress som du och kollegorna öppnar i mobilen. Räkna med en knapp timme vid datorn första gången.

## Tre saker att veta innan du börjar

1. **Servern ligger i USA.** Streamlit Community Cloud kör alla appar där, och det går inte att välja. Bilderna passerar den servern och Anthropics API. Stäm av med arbetsgivaren att det är okej för jobbfoton, och använd inte appen på objekt med särskilda säkerhetskrav.
2. **Appen somnar efter 12 timmar utan besök.** Första besökaren på morgonen får en sida med knappen *Yes, get this app back up!* – tryck och vänta någon minut. Vem som helst med åtkomst kan väcka den.
3. **Gratis, men utan garantier.** Det räcker gott för fälttest och kollegor. Blir det en betald tjänst flyttar man till en betald värd i EU – koden är densamma.

## Steg 1 – Lägg koden på GitHub (privat)

1. Skapa ett gratiskonto på **github.com**.
2. Installera **GitHub Desktop** från desktop.github.com och logga in.
3. *File → Add local repository* → välj `Dokument/matarapp`. Säger programmet att mappen inte är ett repository: välj *create a repository* och sedan *Create repository*.
4. Tryck **Publish repository**. Låt **Keep this code private** vara ikryssad. Tryck *Publish*.

**Kontrollera på github.com:** förrådet ska vara märkt *Private*, och i mappen `.streamlit` ska det bara ligga `config.toml`. Syns en fil som börjar med `secrets` där: stanna och hör av dig. (Filen `.gitignore` i paketet hindrar det, liksom att `.venv` laddas upp.)

## Steg 2 – Starta appen på Streamlit Community Cloud

1. Gå till **share.streamlit.io** och logga in med GitHub. Godkänn åtkomsten. Eftersom förrådet är privat ber Streamlit om behörighet även till privata förråd – det behövs.
2. Välj **Create app** och att appen ska hämtas från GitHub. Fyll i:
   - Repository: `ditt-konto/matarapp`
   - Branch: `main`
   - Main file path: `app.py`
   - App URL: välj något kort, t.ex. `kvittens`
3. Öppna **Advanced settings**:
   - Python version: **3.12**
   - **Secrets:** dubbelklicka på `oppna_nyckelfilen.bat` på datorn, kopiera de två raderna och klistra in dem här. Citattecknen måste vara med – här finns ingen automatisk rättning:
     ```
     ANTHROPIC_API_KEY = 'sk-ant-...'
     APP_LOSENORD = 'ditt långa lösenord'
     ```
4. Tryck **Deploy**. Första starten tar några minuter.

Utan `APP_LOSENORD` spärrar appen sig själv när den ligger på nätet. Det är avsiktligt.

## Steg 3 – Släpp in kollegorna

En app från ett privat förråd är privat från början: bara du ser den. Öppna appen, tryck **Share** uppe till höger och bjud in kollegornas e-postadresser. De loggar in med Google eller en länk som skickas till mejlen, och anger sedan appens lösenord. Två lås: vem som får komma in, och lösenordet.

Gratisnivån tillåter **en** privat app – det är precis vad du behöver.

## Steg 4 – Mobilen

Öppna adressen i mobilens webbläsare och logga in.

- **iPhone:** Dela-knappen → *Lägg till på hemskärmen*.
- **Android:** menyn → *Lägg till på startskärmen*.

Då ligger appen som en ikon bland de andra.

## Steg 5 – Sätt ett kostnadstak

Logga in på **platform.claude.com** och sätt en månadsgräns för API-kostnaden under *Billing / Limits*. Appen har dessutom ett eget tak på 400 avlästa bilder per dygn (`MAX_BILDER_PER_DYGN` i `config.py`). En avläsning kostar några ören per bild – taken finns för att ett läckt lösenord aldrig ska kunna bli dyrt.

## Steg 6 – Mejlutskick av protokollet (valfritt)

Med det här påslaget får exportsteget fältet **Mejla protokollet till**. Skriver man sin adress där skickas protokollet som bilaga i samma stund som det skapas. Nedladdningen finns alltid kvar, och adressen följer med till nästa jobb.

I **Safari på iPhone** finns knappen *Dela eller mejla protokollet*, som öppnar delningsrutan med filen bifogad och skickar från ditt eget mejlkonto – utan någon inställning. **Chrome och Edge tillåter inte att Excel-filer delas så**, så på Android och Windows är stegen nedan den väg som fungerar: då skriver man in en adress och får protokollet skickat automatiskt.

Appen behöver då ett mejlkonto att skicka *från*. Enklast är Gmail:

1. **Skapa ett eget Gmail-konto för appen**, t.ex. `kvittens.dittforetag@gmail.com`. Använd inte ditt privata: ett app-lösenord ger åtkomst till hela brevlådan.
2. Slå på **tvåstegsverifiering** för kontot (Google-kontot → Säkerhet).
3. Gå till **myaccount.google.com/apppasswords**, skapa ett app-lösenord med namnet "Kvittens" och kopiera de 16 tecknen.
4. Lägg till två rader, **utan # framför** – lokalt via `oppna_nyckelfilen.bat`, och på nätet under appens *Settings → Secrets*:
   ```
   SMTP_ANVANDARE = 'kvittens.dittforetag@gmail.com'
   SMTP_LOSENORD = 'abcd efgh ijkl mnop'
   ```
5. Kör `kontrollera.bat`. Steg 7 loggar in på mejlservern utan att skicka något och säger om det fungerar.

Skydd mot missbruk: mejlets text är fast (ingen fri text går att skicka), adressen kontrolleras, högst 60 mejl skickas per dygn (`MAX_MEJL_PER_DYGN`), och du kan låsa mottagarna till företagets domän med `TILLATNA_MEJLDOMANER = ["foretaget.se"]` i `config.py`. Annan mejlserver än Gmail: lägg även till `SMTP_SERVER` och `SMTP_PORT`.

Hamnar mejlet i skräpposten första gången: markera det som *inte skräp*, så lär sig mejlprogrammet.

## Så arbetar du i fält

- **Fota som vanligt** i undercentralen. Täckningen är ofta dålig där, och appen behöver inte vara öppen när du fotar.
- **Ladda upp när du har täckning.** En bild får visa flera displayer. Häng gärna ventilbrickan i bild – då fylls ventilnumret i.
- **Somnar mobilen eller laddas sidan om** finns jobbet kvar: adressen får en kod (`?jobb=…`) och jobbet ligger i serverns minne i upp till 12 timmar. Stäng inte fliken förrän protokollet är nedladdat. Inget sparas på disk.
- **Flaggade värden** jämför du med fotot innan du går vidare. Varje miss du hittar är värdefull: lägg bilden i `testbilder/` och rätt värden i `facit.json`, så växer testbanken med verkligheten.

## När en ny version kommer

1. Packa upp zip-filen **var som helst**, till exempel i Hämtade filer. Packa inte upp den inuti `Dokument/matarapp` – då hamnar allt dubbelt.
2. Dubbelklicka på **`uppdatera.bat`** i den uppackade mappen. Den hittar din installation, lägger filerna rätt och rör aldrig nyckelfilen eller `.venv`.
3. Dubbelklicka på `kontrollera.bat` i `Dokument/matarapp` – allt ska vara [OK].
4. Öppna GitHub Desktop. Ändringarna syns till vänster. Skriv en rad längst ned, t.ex. "v3.12", tryck **Commit to main** och sedan **Push origin**.
5. På github.com dyker en gul prick upp bredvid senaste ändringen medan kontrollen kör. Grön bock = allt gick igenom. Rött kryss = klicka på det och skicka texten till Claude.
6. Appen på nätet uppdateras av sig själv inom någon minut.

## Om något strular

| Du ser | Gör så här |
|---|---|
| Sidan "app is sleeping" | Tryck på väck-knappen och vänta en minut. |
| "saknar lösenord, så den är spärrad" | Lägg till `APP_LOSENORD` under *Settings → Secrets* för appen. |
| "API-nyckeln godkändes inte" | Nyckeln under *Secrets* är fel eller borttagen i Console. Klistra in en ny. |
| Rött fel vid start | Logga in på share.streamlit.io, öppna appen och *Manage app* nere till höger. Kopiera loggen till Claude. |
| "mejlet gick inte iväg" | Protokollet är ändå skapat – ladda ner det. Kör `kontrollera.bat` och läs steg 7. Oftast är app-lösenordet fel. |
| Dygnstaket är nått | Höj `MAX_BILDER_PER_DYGN` i `config.py`, eller vänta till i morgon. |
