# Windows pusė — kas yra šiame aplanke

| Failas | Kam skirtas |
|---|---|
| `irasyk.ps1` | **Vienintelis, kurį reikia paleisti.** Atsisiunčia viską, sutvarko nuorodas, nieko netrina |
| `CLINE-RYSYS.ps1` | Širdis: suranda šiandienos adresą ir prisijungia (atmintis → mainai → lenta → klausimas) |
| `CLINE-RYSYS.cmd` | Kad galėtum spausti dvigubai (naršyklės/Explorer dvigubas paspaudimas) |
| `CLINE-PRADZIA.cmd` | Atidaro atmintį `C:\Users\M\CLINE\00_START_HERE.md` |
| `sukurk-nuorodas.ps1` | Sukuria/atkuria darbalaukio nuorodas „CLINE RYSYS“ ir „CLINE - PRADZIA“ |

## Įrašymas arba taisymas (viena eilutė)

PowerShell lange (tavo `PS C:\Users\M>`):

```powershell
iex (irm https://raw.githubusercontent.com/mindaugasbusiness-hub/novashop/cline/lenta/windows/irasyk.ps1)
```

Ką jis padarys:
1. atsisiųs failus į `C:\Users\M\CLINE\iranga\` ir atmintį į `C:\Users\M\CLINE\`;
2. jei failas jau yra ir skiriasi — seną išsaugos su datos galūne (`.senas`), **nieko netrins**;
3. sukurs/atnaujins abi darbalaukio nuorodas;
4. parodys, ką daryti toliau.

## Taisymas, kai nuorodos dingo

```powershell
powershell -ExecutionPolicy Bypass -File "C:\Users\M\CLINE\iranga\sukurk-nuorodas.ps1"
```

## Kaip patikrinti, kas nutiko

```powershell
notepad "C:\Users\M\CLINE\logai\rysys-$(Get-Date -Format yyyyMMdd).log"
```

Žurnale kiekvienas bandymas su laiku: iš kur paimtas adresas, ar jis gyvas, ar pavyko prisijungti.

## Be jokio kopijavimo (pasirinktinai)

Jei repo bus padarytas privatus, galima paskelbti adresą adresų lentoje, ir tada pakanka vieno
paspaudimo — nereikės nieko kopijuoti. Tam nuoroda paleidžiama su `-Auto`:

```powershell
powershell -ExecutionPolicy Bypass -File "C:\Users\M\CLINE\iranga\CLINE-RYSYS.ps1" -Auto
```

Kol repo viešas, taip daryti **nereikėtų**: kas perskaito lentą, tas gali vykdyti komandas tavo
kompiuteryje, kol gyva sesija. Plačiau — `CLINE/01_RYSYS.md`, 5 skyrius.
