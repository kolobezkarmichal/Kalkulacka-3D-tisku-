# Kalkulačka 3D tisku

Česká desktopová aplikace napsaná v **Pythonu a PySide6**, určená pro výpočet nákladů a prodejních cen 3D tisku. Pracuje zejména se soubory **`.gcode.3mf` exportovanými z Bambu Studia**; podporuje také běžný G-code, pokud obsahuje potřebná data.

Nejnovější dostupný zdrojový kód v tomto repozitáři: **v0.8**.

## Co aplikace umí

- Hromadně načíst tiskové soubory a zobrazit náhledy, čas i spotřebu filamentu podle dostupných dat sliceru.
- Zobrazit jednotlivé filamenty barevně a přiřadit je k položkám lokálního skladu z CSV.
- Rozlišit typ, výrobce, název a skladové ID filamentu, jeho cenu i zůstatek zásoby.
- Převzít přesné HEX barvy z CSV nebo odhadnout orientační odstín podle názvu.
- Spočítat materiál, amortizaci, energii, práci, další náklady a počet kusů.
- Zvolit cenový koeficient nebo pevnou prodejní cenu za jeden tisk.
- Zobrazit náklady, výslednou cenu a rozdíl u každé položky i u celé zakázky.
- Uložit a později obnovit zakázku, vytvořit PDF či CSV.
- Přepínat vzhled aplikace; ovládání číselných polí je chráněno před nechtěnou změnou kolečkem.

## Instalace na Linuxu (například MX Linux KDE)

Stáhni [archiv v0.8](historie/3D_kalkulacka_P2S_v0.8.zip), rozbal jej a otevři terminál ve složce `3D_kalkulacka_P2S`:

```bash
sudo apt install python3-venv kdialog
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
./spustit.sh
```

Příkaz `kdialog` není povinný, ale na KDE se doporučuje kvůli výběru souborů a diakritice. Pro spuštění lze také použít `.venv/bin/python app.py`. Aplikace nepotřebuje připojení k tiskárně ani k webhostingu.

## Použití

1. V Bambu Studiu naslicuj model a exportuj tiskový soubor `.gcode.3mf`.
2. V kalkulačce klikni na **+ Přidat G-code** nebo vyber celou složku.
3. V seznamu tisků vyber položku a zkontroluj automaticky načtený čas a filamenty.
4. Volitelně tlačítkem **Import skladu** načti CSV z vlastní evidence filamentů. V přehledu pak přiřaď konkrétní filament podle jeho ID.
5. V **Nastavení** zadej ceny materiálů, sazbu amortizace, elektřinu a případně cenu ruční práce.
6. Vyber ocenění koeficientem nebo pevnou cenou; zkontroluj **Náklady**, **Cenu** a **Rozdíl**.
7. Zakázku ulož nebo ji exportuj do PDF či CSV.

## Dostupné verze

| Verze | Hlavní novinka | Stažení |
|---|---|---|
| v0.1 | První vydání | [ZIP](historie/3D_kalkulacka_P2S_v0.1.zip) |
| v0.2 | Přehlednější rozhraní a výběr materiálů | [ZIP](historie/3D_kalkulacka_P2S_v0.2.zip) |
| v0.3 | Pevná cena a sklad | [ZIP](historie/3D_kalkulacka_P2S_v0.3.zip) |
| v0.4 | Přehledný výběr filamentu | [ZIP](historie/3D_kalkulacka_P2S_v0.4.zip) |
| v0.5 | Automatické přiřazování barev | [ZIP](historie/3D_kalkulacka_P2S_v0.5.zip) |
| v0.6 | HEX barvy z CSV | [ZIP](historie/3D_kalkulacka_P2S_v0.6.zip) |
| v0.7 | Oprava kolečka myši | [ZIP](historie/3D_kalkulacka_P2S_v0.7.zip) |
| v0.8 | Náklady u jednotlivých položek | [ZIP](historie/3D_kalkulacka_P2S_v0.8.zip) |

Viz také [úplná historie změn](CHANGELOG.md) a [poznámky k jednotlivým vydáním](docs/releases/).

## Soubory projektu

- `app.py` – grafické rozhraní.
- `engine.py` – čtení G-codu, evidence filamentů a výpočty.
- `requirements.txt` – závislost PySide6.
- `spustit.sh` – spuštění v Linuxu.
- `test_*.py` – automatické testy bez nutnosti spouštět grafiku.
- `historie/` – **originální archivní ZIPy v0.1 až v0.8**.

Testy lze spustit příkazem `python3 -m unittest discover -v`.

## Důležité informace

- Čas tisku a spotřeba jsou údaje ze sliceru, **ne skutečné měření**. U chybějících dat je lze doplnit ručně.
- Více modelů naslicovaných na jedné podložce se bere jako jeden tisk. Odpad z proplachování AMS se nemá účtovat duplicitně.
- Kontrola zásob z CSV je informační. **Tisk sám neodečítá materiál ze skladu na webu**.
- Export do PDF představuje kalkulaci, nikoli daňovou fakturu.
- Nastavení je uloženo lokálně v `~/.config/3d-kalkulacka-p2s/settings.json`; zakázky se ukládají jako `*.3dk.json`.

## O projektu

Projekt vzniká podle praktických potřeb autora při práci s 3D tiskárnou, za pomoci umělé inteligence. Dokumentace i program jsou zaměřené na české uživatele.
