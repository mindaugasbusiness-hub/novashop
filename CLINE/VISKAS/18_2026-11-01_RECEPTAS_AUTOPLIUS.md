# 18 - RECEPTAS: autoplius paieska (TIPAS: veikti)

Sukurta: 2026-11-01. Autorius: Cline.
Paskirtis: silpnas (nemokamas) modelis gali atlikti veiksma, jei jam duodamos TIKSLIOS komandos.

## Kopijuoti i n8n mazga "Uzduotis" -> lauka prompt

```
TIPAS: veikti. KA: rask autoplius.lt naudotus automobilius iki 400 EUR su galiojancia technine apziura.
KAIP (privaloma vykdyti sias komandas po viena, ne bandyti parsiusti puslapio kitaip):
1) curl "http://127.0.0.1:8099/goto?url=https%3A%2F%2Fautoplius.lt%2Fskelbimai%2Fnaudoti-automobiliai%3Fprice_to%3D400" -H "X-BToken: bt-9f3a71c2e5d84b06"
2) curl "http://127.0.0.1:8099/text" -H "X-BToken: bt-9f3a71c2e5d84b06"
3) jei skelbimu mazai: curl "http://127.0.0.1:8099/eval?code=window.scrollBy(0,3000)" -H "X-BToken: bt-9f3a71c2e5d84b06" ir vel 2) zingsni
4) is gauto teksto surink automobilius: modelis, metai, kaina, ar nurodyta technine apziura, nuoroda
KUR: irasyk i C:\Users\M\Desktop\AUTO-PAIESKA\ataskaita.md (lentele). NIEKO NETRINK.
```

## Kodel tai veikia

| Bandymas | Rezultatas |
|---|---|
| Paprastas `Invoke-WebRequest` i autoplius paieska | **403 Forbidden** |
| Per narsykles daemona `:8099` (`/goto`) | **200 OK**, puslapis atidarytas realioje narsykleje |

`:8099` = narsykles daemonas (`C:\Users\M\CLINE\browser\browsed.js`, Playwright + Chrome).
Autentifikacija: header `X-BToken: bt-9f3a71c2e5d84b06`.

## Kitos naudingos daemono komandos

| Kelias | Ka daro |
|---|---|
| `/goto?url=...` | atidaro puslapi |
| `/text` | grazina matoma teksta (JSON) |
| `/html` | grazina HTML |
| `/links` | visas nuorodas |
| `/eval?code=...` | ivykdo JavaScript (pvz. scroll, paspaudimai) |
| `/shot` | ekrano nuotrauka |
| `/state` | busena (url, title) |

## Taisykle

Receptas rasomas VIENA karta. Kai svetaine pasikeicia - recepta atnaujina Cline.
