# Historie změn – Kalkulačka 3D tisku

Historie vychází ze zachovaných původních ZIP archivů v0.1 až v0.8. Každý archiv obsahuje původní zdrojový kód příslušné verze.

## v0.1 – První vydání

- Samostatná desktopová aplikace pro Linux v Pythonu a PySide6.
- Načítání souborů .gcode.3mf a .gcode z Bambu Studia, včetně více souborů a celé složky.
- Automatické získání doby tisku, spotřeby a barev filamentů, pokud jsou dostupné v souboru.
- Kalkulace materiálu, energie, amortizace, ruční práce, dalších nákladů, počtu kusů a koeficientu.
- Ukládání a otevírání zakázek, export PDF a CSV, demonstrační zakázka.

[Archiv této verze](https://github.com/kolobezkarmichal/Kalkulacka-3D-tisku-/raw/main/historie/3D_kalkulacka_P2S_v0.1.zip)

## v0.2 – Přehlednější rozhraní a výběr materiálů

- Pojmenovaný ceník filamentů: možnost vybrat konkrétní materiál i tehdy, když má stejnou barvu a typ jako jiný.
- Čtyři vzhledy: tmavý, světlý, kombinovaný a barevný.
- Lepší kontrast, ohraničení tabulek, šipky číselných polí a čitelnost dialogu Nastavení.
- Přednostně systémový dialog KDE (kdialog) pro lepší zobrazení české diakritiky.

[Archiv této verze](https://github.com/kolobezkarmichal/Kalkulacka-3D-tisku-/raw/main/historie/3D_kalkulacka_P2S_v0.2.zip)

## v0.3 – Pevná cena a sklad

- Alternativa ke koeficientu: zadání pevné prodejní ceny za jeden tisk.
- Hromadný import databáze filamentů z CSV se zachováním skladových ID.
- Evidence dostupného množství a upozornění na nedostatek materiálu.
- Opakovaný import aktualizuje zásoby a zachovává ručně nastavené ceny.
- Automatické nastavení 200 Kč/kg pro filamenty výrobce 3D FOX označené jako přeběh.

[Archiv této verze](https://github.com/kolobezkarmichal/Kalkulacka-3D-tisku-/raw/main/historie/3D_kalkulacka_P2S_v0.3.zip)

## v0.4 – Přehledný výběr filamentu

- Samostatné okno pro výběr filamentu ze skladu místo nepřehledného dlouhého seznamu.
- Vyhledávání podle ID, názvu, typu či výrobce i bez diakritiky.
- Filtrování podle druhu materiálu a dostupné zásoby, přiřazení konkrétního skladového ID.
- Skrytí nepodstatného údaje veřejný/skrytý z uživatelského rozhraní.

[Archiv této verze](https://github.com/kolobezkarmichal/Kalkulacka-3D-tisku-/raw/main/historie/3D_kalkulacka_P2S_v0.4.zip)

## v0.5 – Automatické přiřazování barev

- Vylepšené odhadování přibližné HEX barvy podle názvu filamentu i u nově importovaných položek.
- Podpora názvů a přívlastků jako armádní zelená, pistáciová, olivová, pastelová, světlá, tmavá a metalická.
- Možnost ručně zadat přesný HEX odstín; ten má přednost před odhadem.

[Archiv této verze](https://github.com/kolobezkarmichal/Kalkulacka-3D-tisku-/raw/main/historie/3D_kalkulacka_P2S_v0.5.zip)

## v0.6 – HEX barvy z CSV

- Načítání sloupce HEX barva z exportu webové evidence filamentů a propojení podle skladového ID.
- Přesná barva z CSV má přednost před odhadem podle názvu.
- Kompatibilita se staršími CSV soubory bez sloupce HEX a zachování individuálních cen.
- Přímé spojení se serverem není součástí této verze; používá se import CSV.

[Archiv této verze](https://github.com/kolobezkarmichal/Kalkulacka-3D-tisku-/raw/main/historie/3D_kalkulacka_P2S_v0.6.zip)

## v0.7 – Oprava kolečka myši

- Kolečko myši již nechtěně nemění hodnoty v číselných polích ani při přejetí nad nimi.
- Zavřené rozbalovací nabídky se kolečkem samy nepřepínají.
- Zůstává možnost měnit hodnoty klávesnicí a ovládacími šipkami; kolečko posouvá stránku.

[Archiv této verze](https://github.com/kolobezkarmichal/Kalkulacka-3D-tisku-/raw/main/historie/3D_kalkulacka_P2S_v0.7.zip)

## v0.8 – Náklady u jednotlivých položek

- V seznamu tisků se nyní zobrazují odděleně Náklady, Cena a Rozdíl (cena minus náklady).
- Výpočet částek respektuje počet kusů v každé položce.
- Záporný rozdíl (prodej pod náklady) je graficky zvýrazněn.
- Vysvětlení nákladů při najetí myší a podrobnější údaje u jednotlivých položek v PDF a CSV.

[Archiv této verze](https://github.com/kolobezkarmichal/Kalkulacka-3D-tisku-/raw/main/historie/3D_kalkulacka_P2S_v0.8.zip)

## v0.8.1 – Oprava českých názvů ukládaných zakázek

- Při prvním uložení zakázky se v návrhu názvu souboru zachovává česká diakritika a mezery (například `Dárek Aleš.3dk.json`).
- Neplatné znaky v názvech souborů jsou bezpečně nahrazeny. Starší zakázky se nemění a zůstávají otevřitelné.
- Doplněny testy pro české názvy souborů. Výpočty a export PDF zůstávají beze změny.
- Kompletní archiv obsahuje Python aplikaci a její zdrojové soubory; k dispozici je i menší opravný balíček.

[Kompletní ZIP aplikace](historie/3D_kalkulacka_P2S_v0.8.1.zip) · [Jen opravné soubory](historie/3D_kalkulacka_P2S_v0.8.1_oprava_nazvu.zip)
