# Kalkulačka 3D tisku – instalátor pro Windows

**Verze aplikace: 0.8.1, Windows 10/11 (64bit).** Program je napsaný v Pythonu a používá PySide6, ale instalátor obsahuje potřebné součásti, takže **na cílovém počítači není nutné instalovat Python, PySide6 ani Inno Setup**.

## Instalace

1. Stáhni soubor `Kalkulacka-3D-tisku-v0.8.1-Windows-Setup.exe` z této stránky vydání.
2. Spusť ho dvojklikem a projdi český instalační průvodce.
3. Program se nainstaluje do uživatelské složky, vytvoří zástupce v nabídce Start a volitelně na ploše.
4. Spusť **3D Kalkulačka P2S**. Pro běžnou práci není nutné připojení k internetu.

Instalace probíhá pro aktuálního uživatele a běžně nevyžaduje oprávnění správce. Instalátor **není digitálně podepsaný**, proto může Windows SmartScreen zobrazit bezpečnostní upozornění. Na počítačích s omezenými oprávněními může být instalace zablokována.

## Používání

V Bambu Studiu vyexportuj tiskový soubor `.gcode.3mf`. V kalkulačce klikni na **Přidat G-code**, zkontroluj čas tisku a spotřebu barevných filamentů. V **Nastavení** zadej cenu materiálu, energie a amortizace. Lze zvolit cenový koeficient nebo pevnou cenu. Zakázku můžeš uložit jako `.3dk.json`, případně exportovat do PDF a CSV. CSV sklad filamentů z PHP evidence lze importovat podle skladového ID; automatické odečítání ze serverového skladu neprobíhá.

## Uložená data a odinstalování

- Nastavení a ceník: `%APPDATA%\3d-kalkulacka-p2s\settings.json`.
- Zakázky, PDF a CSV: složka zvolená při ukládání.
- Odinstalování v **Nastavení Windows → Aplikace → Nainstalované aplikace**. Uživatelské nastavení a dokumenty se úmyslně nemažou.

## Sestavení pro vývojáře

Zdrojový Python kód a skripty jsou ve složce `windows/` v repozitáři. Pro vlastní sestavení je potřeba Windows s Pythonem 3.12 (64bit), internet při sestavování, PyInstaller a Inno Setup 6. V kořeni repozitáře spusť:

```powershell
powershell -ExecutionPolicy Bypass -File windows\SESTAVIT_WINDOWS.ps1
```

Výsledný instalátor najdeš ve složce `output/`. Sestavování na GitHub Actions je popsáno v `.github/workflows/windows-installer.yml`.

## Upozornění

Kalkulace vycházejí z odhadů Bambu Studia. Instalátor byl automaticky sestaven a základní spuštění programu ověřeno v GitHub Actions na Windows. Instalaci a ovládání na dalších konfiguracích systému Windows zatím není možné zaručit. Aplikace je český komunitní projekt vznikající s pomocí umělé inteligence.
