# 01 · RYŠYS — kaip veikia dvi darbalaukio nuorodos

Atnaujinta: 2026-10-26 · Šaltinis: patikrinta gyvai šioje sesijoje (ne spėjimai)

---

## 1. Dvi nuorodos ir ką jos daro

| Nuoroda darbalaukyje | Ką paleidžia | Ką daro |
|---|---|---|
| **CLINE RYSYS** | `C:\Users\M\CLINE\iranga\CLINE-RYSYS.cmd` → `CLINE-RYSYS.ps1` | Suranda šiandienos adresą, patikrina, ar jis gyvas, ir prisijungia |
| **CLINE - PRADZIA** | `C:\Users\M\CLINE\iranga\CLINE-PRADZIA.cmd` | Atidaro atmintį `00_START_HERE.md` ir jos aplanką |

## 2. Adreso paieškos tvarka (paleidėjas eina iš eilės)

1. **Atmintis** — `C:\Users\M\CLINE\prisijungimas.txt` (jei ten įrašyta eilutė).
2. **Mainai** — tai, ką ką tik nukopijavai (Ctrl+C). **Šis kelias patikimiausias ir saugiausias.**
3. **Adresų lenta** — GitHub (veikia TIK su `-Auto`, žr. 5 skyrių dėl saugumo).
4. **Klausimas tau** — jei nieko nerado, langas prašo įklijuoti eilutę ir Enter.

Kiekvienas bandymas įrašomas į `C:\Users\M\CLINE\logai\rysys-YYYYMMDD.log`
(data, laikas, šaltinis, adresas, rezultatas). Todėl visada galima pažiūrėti, kas nutiko.

## 3. Kelias nuo tavo pelės iki mano ekrano

```
Tu: dukart spaudi CLINE RYSYS
        |
        v
Windows: CLINE-RYSYS.ps1  ->  randa adresą (atmintis / mainai / lenta)
        |                    ->  patikrina https://<adresas>/health = 200
        v
Windows: iex (irm https://<adresas>/agent.ps1)   <- agent.ps1 turi raktą viduje
        |
        v
trycloudflare tunelis (HTTPS)
        |
        v
Cline pusė: tools/relay/relay.py  (127.0.0.1:8798)
        |  aš: python3 tools/relay/pc.py cmd "Get-Date"
        v
Windows: PowerShell vykdo, rezultatas siunčiamas atgal -> aš jį matau
```

Agentas (`agent.ps1`) **long-pollina** `/next` kas 15 s, todėl komandą gauna per 1–3 sekundes.

## 4. Patikrinta gyvai (2026-10-26)

| Teiginys | Kaip patikrinta | Rezultatas |
|---|---|---|
| `relay.py` + `agent.ps1` + `pc.py` grandis veikia | `python3 tools/relay/test-relay.py` | **11/11 OK** |
| Komanda eina ir grįžta per viešą HTTPS tunelį | Simuliuotas agentas per `trycloudflare` + `pc.py cmd 'Get-Date'` | **atsakymas gautas** |
| `cloudflared` atsisiunčiamas šioje aplinkoje | `curl` į GitHub releases | **HTTP 200, 40 MB** |
| Viešas adresas atsako per HTTPS | `curl https://<adresas>/health` | **200** |
| `raw.githubusercontent.com` pasiekiamas (lentai) | `curl` | **200** |
| Gist kūrimas botui | `gh gist create` | **403 (neleidžiama)** — todėl lenta perkelta į nuolatinę šaką |
| Adresas rytoj veiks be naujo paleidimo | loginė išvada iš architektūros | **NE** — adresas gyvas tik kol gyva sesija |

## 5. Saugumas (perskaityk prieš naudodamas `-Auto`)

- Repo `novashop` yra **VIEŠAS**.
- `agent.ps1` turi raktą viduje, todėl **kas perskaito adresą, tas gali vykdyti komandas tavo kompiuteryje**, kol gyva sesija.
- Todėl:
  - Adresų lenta **nepaskelbiama** automatiškai. `lenta.py skelbti` atsisako, kol repo viešas; apeiti galima tik aiškiai su `--force` (ir tai tik sąmoningai prisiėmus riziką).
  - Rankinis kelias (Ctrl+C + CLINE RYSYS) **nieko neskelbia** — jis saugiausias ir jo pakanka.
  - Lenta skirta tik tam atvejui, kai repo padarytas privatus (GitHub → Settings → Danger Zone → Change visibility).
- Raktas (`/tmp/relay.token`) yra sesijos laikinas: kai sesija baigiasi, jis nebeveikia.

## 6. Ką daryti, kai kas nors nepavyksta

| Požymis | Priežastis | Sprendimas |
|---|---|---|
| Langas rašo „adresas neatsako“ | Pasenęs adresas atmintyje | Paprašyk manęs naujos eilutės, nukopijuok, paleisk iš naujo |
| Langas prašo įklijuoti | Nieko nerado atmintyje nei mainuose | Įklijuok eilutę ir Enter |
| Nuorodos darbalaukyje dingo | Kažkas nuvalė darbalaukį | `iex (irm .../windows/irasyk.ps1)` — viską sutvarkys iš naujo |
| Reikia pilno žurnalo | Norisi pamatyti, kas nutiko | `C:\Users\M\CLINE\logai\rysys-YYYYMMDD.log` |
| Adresas kinta kiekvieną kartą | Architektūros savybė, ne klaida | Tam, kad būtų pastovu, naudok `05_PRIJUNGIMAS_WINDOWS.md` kelią |
