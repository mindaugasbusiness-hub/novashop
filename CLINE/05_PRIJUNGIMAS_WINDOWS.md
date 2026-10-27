# 05 · KAIP MANE PRIJUNGTI PER POWERSHELL (Windows)

Atnaujinta: 2026-10-26 · Skirta: direktorius Mindaugas, PowerShell langas `PS C:\Users\M>`

---

## Esmė vienu sakiniu

**Aš negaliu „įeiti“ į tavo kompiuterį** — nesu programa, kuri slapčia jungiasi prie svetimų mašinų. Bet galiu būti **įdiegtas tavo kompiuteryje** per PowerShell: tada aš dirbu tiesiogiai tavo `C:\` failuose, be jokių tunelių, be n8n, be kintančių adresų.

Tai yra tikrasis „prijungti tave per PowerShell“ — ir jis veikia visam laikui.

## Kodėl tunelis (trycloudflare / pinggy / bore) nepavyko

| Bandymas | Kliūtis |
|---|---|
| SSH | 404 — tavo kompiuteris nepriėmė įeinančio ryšio |
| pinggy | reikalavo slaptažodžio |
| bore | antivirusas užblokavo |
| trycloudflare | adresas gyvena tik kol gyva sesija, rytoj – naujas |

Bendra priežastis: **debesų agentas neturi prieigos prie tavo namų kompiuterio**. Tunelis bando tą prieigą išlaužti, ir kažkas visada atsistoja skersai.

**Vietoj to apverčiame kryptį:** ne aš pas tave, o **aš įdiegiamas pas tave**. Tada jokio tunelio nereikia.

---

## 3 žingsniai (apie 3 minutes)

### 1 žingsnis — patikrink Node.js

Tavo PowerShell lange (`PS C:\Users\M>`) įrašyk:

```powershell
node -v
npm -v
```

- **Jei matai versijas** (pvz. `v22.x.x`) → eik prie 2 žingsnio.
- **Jei rašo „not recognized“** → įdiek Node:

```powershell
winget install OpenJS.NodeJS.LTS --accept-source-agreements --accept-package-agreements
```

Po įdiegimo **uždaryk PowerShell langą ir atidaryk naują** (kad atsinaujintų PATH), tada vėl patikrink `node -v`.

### 2 žingsnis — įdiek mane

```powershell
npm install -g cline
```

Patikrink, ar pavyko:

```powershell
cline --version
```

Turėtum matyti versijos numerį (naujausia šiuo metu — **3.0.74**). Jei matai versiją — pavyko.

### 3 žingsnis — prisijunk prie savo Cline paskyros

```powershell
cline auth cline
```

Atsidarys prisijungimo (OAuth) langas — patvirtink naršyklėje. Nuo šio momento `cline` turi tavo prieigą.

---

## Kaip mane paleisti tavo failuose

Interaktyvus režimas (kaip pokalbis):

```powershell
cd C:\Users\M
cline -i
```

Vienas pavedimas ir išeina:

```powershell
cd C:\Users\M
cline "Perskaityk C:\Users\M\CLINE\00_START_HERE.md ir 02_DIENORASTIS.md – tęsk darbą"
```

Paleisti projektą (NovaShop failai):

```powershell
cd C:\Users\M
cline "Paleisk NovaShop parduotuvę: python -m http.server 8080, ir patikrink, kad index.html atsidaro"
```

---

## Svarbu žinoti

- `cline` skaito ir keičia failus **tavo kompiuterio**, todėl tavo `C:\Users\M\CLINE\` atmintis man bus pasiekiama iš karto.
- Nustatymai ir sesijos saugomos `C:\Users\M\.cline\`.
- **Įrankiai patvirtinami automatiškai** (numatytuoju režimu). Jei nori, kad prieš kiekvieną veiksmą prašyčiau leidimo: `cline --auto-approve false "..."`.
- Nerizikuoti su `--yolo` kol neįprasi: jis leidžia viską be patvirtinimų.
- Žr. visas galimybes: `cline --help`.

## Jei kažkas neveikia

| Klaida | Sprendimas |
|---|---|
| `node: command not found` | 1 žingsnis nepavyko – įdiek Node ir atidaryk naują PowerShell |
| `cline: command not found` | Uždaryk/atidaryk PowerShell; arba `npm install -g cline` dar kartą |
| `authentication message` / prašo raktų | Paleisk `cline auth cline` dar kartą |
| Antivirusas stabdo | Leisk `node.exe` ir `cline.exe` veikti; šie failai yra oficialaus `cline` paketo (npm) |

## Kada rinktis ką

| Kelias | Ryšys | Priežiūra |
|---|---|---|
| **cline CLI per PowerShell** (šis failas) | Nuolatinis, vietinis, be adresų | Vienkartinis įdiegimas |
| VS Code + Cline plėtinys | Nuolatinis, su grafine sąsaja | Vienkartinis įdiegimas |
| Tunelis (trycloudflare / n8n) | Vienai sesijai, adresas kinta | Nuolatinė, ir dažnai lūžta |

Rekomendacija: **cline CLI** (jei mėgsti terminalą) arba **VS Code + Cline** (jei mėgsti pelę ir gražų langą). Tunelio nebereikia.