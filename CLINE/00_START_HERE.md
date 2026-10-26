# 00 · START HERE — kaip tęsti darbą

**Savininkas:** Mindaugas (direktorius)
**Projektas:** NovaShop (statinė elektroninė parduotuvė) — repo `mindaugasbusiness-hub/novashop`
**Paskutinis atnaujinimas:** 2026-10-26 (sesija `cline/wfbfjc1p`)
**Darbinis branch:** `cline/wfbfjc1p` — `main` NELIESTAS
**Nuolatinė šaka:** `cline/lenta` — joje tik adresų lenta ir įranga (kad adresas, kurį skaito tavo kompiuteris, niekada nesikeistų)

---

## 1. Viena eilutė rytojui (nukopijuok ir įklijuok)

> Perskaityk `CLINE/00_START_HERE.md`, `01_RYSYS.md` ir `02_DIENORASTIS.md` – tęsiam.

Jei `C:\` nepasiekiamas (sesija debesyse — taip yra dabar), ta pati eilutė su papildymu:

> Perskaityk `CLINE/00_START_HERE.md`, `01_RYSYS.md` ir `02_DIENORASTIS.md` iš repo `mindaugasbusiness-hub/novashop` – tęsiam.

---

## 2. Ryšio paleidimas (Cline pusė — aš, pirmas žingsnis kiekvieną kartą)

```bash
bash tools/relay/start.sh          # relay + tunelis + adreso patikra (~1-3 min, daugiausia DNS)
python3 tools/relay/test-relay.py  # savitikra: 11/11 turi būti OK
```

`start.sh` atspausdina eilutę: `iex (irm https://<naujas-adresas>/agent.ps1)`.
Tą eilutę perduodu direktoriui, jis nukopijuoja ir dukart spaudžia darbalaukyje **CLINE RYSYS**.

## 3. Kaip dirbti su tavo kompiuteriu (kai langas prisijungęs)

```bash
python3 tools/relay/pc.py status                    # kas prisijungę
python3 tools/relay/pc.py cmd "Get-Date"            # viena komanda
python3 tools/relay/pc.py cmd --lines 60 "Get-ChildItem 'C:\Users\M\Desktop' -Force"
```

Visas išvedimas visada rašomas į failą (`/tmp/pc-out/...`), o ekrane rodoma tik pradžia —
taip saugomas kontekstas. Ilgų `-Recurse` per visą diską venk (blokuoja eilę iki 5 min).

---

## 4. Atminties failų tvarka

| Failas | Kam |
|---|---|
| `CLINE/00_START_HERE.md` | šis failas — kaip pradėti |
| `CLINE/01_RYSYS.md` | kaip veikia ryšys (nuorodos, relay, lenta, saugumas) |
| `CLINE/02_DIENORASTIS.md` | ką veikėme, su patikrintais faktais |
| `CLINE/03_TAISYKLES.md` | ko NEGALIMA (1 taisyklė: nieko netrinti be žodžio) |
| `CLINE/04_TODO.md` | kur sustojome |
| `CLINE/05_PRIJUNGIMAS_WINDOWS.md` | ilgalaikis kelias: vietinis `cline` CLI tavo kompiuteryje |
| `CLINE/PRADZIOS_PROMPTAS.txt` | eilutė naujai sesijai |
