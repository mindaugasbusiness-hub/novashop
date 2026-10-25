# 2026-10-25 · CLOUD SESIJOS SANTRAUKA

## Ką M paprašė
- Viename kompiuterio aplanke turėti visus prisijungimus, raktus, seifą ir visus atliktus darbus.
- Naujas DI, gavęs vieną nuorodą, turi žinoti visą eigą be papildomo aiškinimo.
- Įjungus kompiuterį informacija turi būti automatiškai atnaujinama; n8n turi prižiūrėti problemas ir atnaujinti puslapį.
- Niekas netrinama, neperkeliama ir nepervardinama be M leidimo.

## A) SERVISAI
- Patikrinta: n8n, broker, Qdrant, Kumštis tools, Žvėris UI, naršyklės daemonas, F6, pultas, naršyklės CDP.
- F6 buvo neveikiantis, nes kitas procesas užėmė F1 ir senas scriptas blokavo visus F6–F11.
- F6 pataisytas: F1 paliktas esamam procesui, F6–F11 veikia, `:8766` = 200. Originalo kopija padaryta.
- Žvėris UI `:8091` grąžino 500, nes trūko `C:\workspace\zveris\ui\static\index.html`.
- Puslapis atkurtas pagal esamą API. Patikra: pagrindinis puslapis 200, `/api/status` 200, `/api/memory/chat` 200.
- Žvėris AI modelių skaičius: 0. Puslapis veikia, bet modelio atsakymams reikia atskirai paleisto modelio.

## B) AUKCIONAS
- Svetainė `https://penktadienioaukcionas.lt` patikrinta: 200.
- n8n aktyvus workflow „Aukciono stebėjimas“ kas 5 min tikrina svetainę.
- Penktadienį 19:55 siunčiamas aukciono priminimas.
- Šiandien aukciono stebėjimas turėjo 145 sėkmingus vykdymus.

## C) VPS
- VPS `5.175.171.113` servisai: aukcionas, Vilko mokykla, cloudflared ir vilkas-tts — active.
- Admin slaptažodis išimtas iš `aukcionas.service` ir paliktas `.env`.
- Originalo kopijos VPS padarytos.
- VPS svetainė 200; disko užimtumas apie 44 %.

## Kiti svarbūs n8n workflow
- „Kumštis – vadovų ir specialistų valdyba“: aktyvus, laukia `POST /webhook/kumstis`.
- „Kumštis – DeFi skeneris“: aktyvus, kasdien 08:00 ir `POST /webhook/defi-scan`, ataskaitą rašo į Desktop.
- Testinis nukritimo workflow sąmoningai neaktyvus, kad nesiųstų netikrų pranešimų.

## Automatika, kurią reikia palaikyti
- VISKAS būsena įrašoma kas 5 min ir prieš išjungimą.
- n8n turi kas 5 min tikrinti Žvėris UI, prireikus jį atkurti ir padaryti F5 tik agento naršyklėje.
- n8n turi atnaujinti vieną naujausią istorijos failą iš VISKAS dokumentų ir vietinių Cline sesijų.
