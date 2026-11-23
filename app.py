#!/usr/bin/env python3
"""3D kalkulačka – desktopová aplikace pro Bambu Studio a MX Linux KDE."""
from __future__ import annotations

import base64
import os
import shutil
import subprocess
import csv
import html
import re
import sys
import unicodedata
import uuid
from dataclasses import asdict
from pathlib import Path

try:
    from PySide6.QtCore import Qt, QRectF, QUrl, QLocale, QTranslator, QLibraryInfo
    from PySide6.QtGui import QColor, QFont, QIcon, QPainter, QPainterPath, QPixmap, QPageSize
    from PySide6.QtWidgets import (
        QApplication, QMainWindow, QWidget, QLabel, QPushButton, QFileDialog,
        QVBoxLayout, QHBoxLayout, QGridLayout, QSplitter, QScrollArea, QFrame,
        QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
        QLineEdit, QDoubleSpinBox, QSpinBox, QComboBox, QCheckBox, QDialog, QDialogButtonBox,
        QGroupBox, QMessageBox, QColorDialog, QSizePolicy, QInputDialog
    )
    from PySide6.QtPrintSupport import QPrinter
    from PySide6.QtGui import QTextDocument
except ImportError:
    print('\nChybí PySide6. Nainstaluj závislosti:\n'
          '  python3 -m venv .venv\n'
          '  .venv/bin/python -m pip install -r requirements.txt\n'
          '  .venv/bin/python app.py\n')
    sys.exit(1)

from engine import (
    APP_VERSION, PROJECT_EXT, Filament, PrintJob, Rates, color_name, default_config_path,
    human_duration, load_rates, money, open_project, parse_file, project_totals,
    safe_hex, save_project, save_rates, import_filament_csv, stock_balances, fox_overrun,
    approximate_filament_color, suggested_project_filename
)


THEMES = {
    'dark': dict(label='Tmavý – námořní modrá', base='#101827', surface='#1E2D42',
        text='#F5F8FE', muted='#B9CBE0', edge='#698099', grid='#4B6078',
        input='#111F31', alt='#25364C', accent='#40D5B0', accent_text='#06221B',
        selection='#267C70', select_text='#FFFFFF', scroll='#758BA5', icon='light'),
    'light': dict(label='Světlý – vysoký kontrast', base='#EBF0F5', surface='#FFFFFF',
        text='#172438', muted='#455A74', edge='#97A9BD', grid='#C6D2DF',
        input='#FFFFFF', alt='#F4F7FA', accent='#007E67', accent_text='#FFFFFF',
        selection='#C5EDE3', select_text='#122C27', scroll='#8193A8', icon='dark'),
    'hybrid': dict(label='Kombinovaný – tmavé pozadí / světlé panely', base='#13233A', surface='#FFFFFF',
        text='#12233C', muted='#476079', edge='#829CB5', grid='#C1D0DF',
        input='#F8FBFF', alt='#EAF1F8', accent='#007E69', accent_text='#FFFFFF',
        selection='#C4EDE3', select_text='#14342A', scroll='#849AB0', icon='dark'),
    'color': dict(label='Barevný – fialová a tyrkysová', base='#EAE9FA', surface='#FFFFFF',
        text='#29223E', muted='#62557D', edge='#A79AC6', grid='#CFC5E1',
        input='#F9F6FF', alt='#F0EBFA', accent='#7451BE', accent_text='#FFFFFF',
        selection='#DED1FF', select_text='#302046', scroll='#9380BC', icon='dark'),
}


def build_stylesheet(theme: str) -> str:
    c = THEMES.get(theme, THEMES['dark'])
    edge, text, inp, surface, base, accent = (c[k] for k in ('edge','text','input','surface','base','accent'))
    icon_dir = Path(__file__).resolve().parent / 'assets'
    up = (icon_dir / f"up_{c['icon']}.svg").as_posix()
    down = (icon_dir / f"down_{c['icon']}.svg").as_posix()
    check = (icon_dir / f"check_{c['icon']}.svg").as_posix()
    return f"""
      QApplication, QMainWindow, QWidget#base {{ background-color: {base}; color: {text}; }}
      QDialog {{ background-color: {surface}; color: {text}; }}
      QFrame#headerBox, QFrame#panel, QFrame#statCard, QFrame#costBox,
      QGroupBox {{ background-color: {surface}; color: {text}; border: 1px solid {edge}; border-radius: 9px; }}
      QWidget {{ color: {text}; font-size: 12px; }}
      QLabel {{ color: {text}; background: transparent; }}
      QLabel#muted, QLabel#statCaption {{ color: {c['muted']}; font-size: 11px; }}
      QLabel#appHeading {{ font-size: 20px; font-weight: 800; }}
      QLabel#sectionTitle {{ color: {c['muted']}; font-size: 12px; font-weight: 800; }}
      QLabel#statNumber {{ color: {text}; font-size: 22px; font-weight: 800; }}
      QLabel#strongText {{ font-size: 13px; font-weight: 800; }}
      QLabel#warning {{ color: {'#FFC378' if theme=='dark' else '#985C0D'}; }}
      QLabel#preview {{ background: {inp}; border: 1px solid {edge}; border-radius: 8px; }}
      QLineEdit, QAbstractSpinBox, QComboBox {{
          background-color: {inp}; color: {text}; selection-color: {c['select_text']};
          selection-background-color: {c['selection']}; border: 1px solid {edge}; border-radius: 6px;
          padding: 5px 7px; min-height: 21px;
      }}
      QLineEdit:focus, QAbstractSpinBox:focus, QComboBox:focus {{ border: 2px solid {accent}; }}
      QLineEdit:disabled, QAbstractSpinBox:disabled, QComboBox:disabled {{ color: {c['muted']}; background: {c['alt']}; }}
      QSpinBox, QDoubleSpinBox {{ padding-right: 24px; }}
      QSpinBox::up-button, QDoubleSpinBox::up-button {{
          subcontrol-origin: border; subcontrol-position: top right; width: 23px;
          border-left: 1px solid {edge}; border-top-right-radius: 5px;
          background: {c['alt']};
      }}
      QSpinBox::down-button, QDoubleSpinBox::down-button {{
          subcontrol-origin: border; subcontrol-position: bottom right; width: 23px;
          border-left: 1px solid {edge}; border-bottom-right-radius: 5px;
          background: {c['alt']};
      }}
      QSpinBox::up-arrow, QDoubleSpinBox::up-arrow {{ image: url("{up}"); width: 13px; height: 10px; }}
      QSpinBox::down-arrow, QDoubleSpinBox::down-arrow {{ image: url("{down}"); width: 13px; height: 10px; }}
      QComboBox {{ padding-right: 29px; }}
      QComboBox::drop-down {{ subcontrol-origin: padding; subcontrol-position: top right;
          border-left: 1px solid {edge}; background: {c['alt']}; width: 27px;
          border-top-right-radius: 5px; border-bottom-right-radius: 5px; }}
      QComboBox::down-arrow {{ image: url("{down}"); width: 13px; height: 13px; }}
      QComboBox QAbstractItemView {{ background: {surface}; color: {text};
          border: 1px solid {edge}; selection-color: {c['select_text']};
          selection-background-color: {c['selection']}; outline: none; }}
      QPushButton {{ background: {c['alt']}; color: {text}; border: 1px solid {edge};
          border-radius: 7px; padding: 7px 11px; min-height: 22px; }}
      QPushButton:hover {{ border: 2px solid {accent}; background: {inp}; }}
      QPushButton:pressed {{ background: {c['selection']}; color: {c['select_text']}; }}
      QPushButton#primary {{ background: {accent}; color: {c['accent_text']}; border-color: {accent}; font-weight: 800; }}
      QTableWidget {{ background: {surface}; alternate-background-color: {c['alt']}; color: {text};
          border: 1px solid {edge}; border-radius: 4px; gridline-color: {c['grid']};
          selection-background-color: {c['selection']}; selection-color: {c['select_text']}; }}
      QTableWidget::item {{ padding: 5px; }}
      QHeaderView::section {{ background: {c['alt']}; color: {text};
          border: 0px; border-right: 1px solid {edge}; border-bottom: 2px solid {edge};
          padding: 7px; font-weight: bold; }}
      QTableCornerButton::section {{ background: {c['alt']}; border: 1px solid {edge}; }}
      QScrollArea {{ border: 0px; background: transparent; }}
      QScrollArea > QWidget > QWidget {{ background: transparent; }}
      QGroupBox {{ margin-top: 17px; padding: 13px 9px 9px; font-weight: 750; }}
      QGroupBox::title {{ subcontrol-origin: margin; subcontrol-position: top left;
          left: 14px; padding: 0px 6px; color: {text}; background: {surface}; }}
      QSplitter::handle {{ background: {edge}; width: 6px; }}
      QScrollBar:vertical {{ background: {c['alt']}; width: 15px; margin: 0; border: 1px solid {edge}; }}
      QScrollBar::handle:vertical {{ background: {c['scroll']}; min-height: 29px; border-radius: 5px; margin: 2px; }}
      QScrollBar:horizontal {{ background: {c['alt']}; height: 15px; margin: 0; border: 1px solid {edge}; }}
      QScrollBar::handle:horizontal {{ background: {c['scroll']}; min-width: 29px; border-radius: 5px; margin: 2px; }}
      QScrollBar::add-line, QScrollBar::sub-line {{ height: 0px; width: 0px; }}
      QScrollBar::add-page, QScrollBar::sub-page {{ background: none; }}
      QCheckBox {{ spacing: 6px; color: {text}; background: transparent; }}
      QCheckBox::indicator {{ width: 15px; height: 15px; }}
      QCheckBox::indicator:unchecked {{ background: {inp}; border: 1px solid {edge}; border-radius: 3px; }}
      QCheckBox::indicator:checked {{ background: {accent}; border: 2px solid {accent}; border-radius: 3px; image: url(\"{check}\"); }}
      QDialogButtonBox {{ background: transparent; }}
      QStatusBar {{ background: {surface}; color: {text}; border-top: 1px solid {edge}; }}
    """


def choose_dialog(parent, title: str, *, mode: str, file_filter: str = '', suggested: str = ''):
    """Na KDE přednostně systémový kdialog kvůli diakritice a známému rozhraní.

    Bez kdialog zůstává plně funkční Qt dialog s českými popisky a vlastním panelem složek.
    Vrací seznam cest (i při uložení jednu), prázdný seznam při zrušení.
    """
    base = suggested or str(Path.home())
    # KDE používá pro filtry kdialog syntaxi vzor|popis (nikoli Qt syntax s ;;).
    if '.gcode.3mf' in file_filter:
        kde_filter = '*.gcode.3mf *.gcode *.gco *.3mf|Tiskové soubory Bambu Studio'
    elif '.3dk.json' in file_filter:
        kde_filter = '*.3dk.json *.json|Zakázky 3D kalkulačky'
    elif '*.csv' in file_filter:
        kde_filter = '*.csv|CSV soubory'
    elif '*.pdf' in file_filter:
        kde_filter = '*.pdf|PDF dokumenty'
    else:
        kde_filter = file_filter
    if shutil.which('kdialog'):
        args = ['kdialog', '--title', title]
        if mode == 'files':
            args += ['--getopenfilename', base, kde_filter, '--multiple', '--separate-output']
        elif mode == 'directory':
            args += ['--getexistingdirectory', base]
        elif mode == 'save':
            args += ['--getsavefilename', base, kde_filter]
        else:
            raise ValueError(mode)
        try:
            response = subprocess.run(args, capture_output=True, text=True, errors='replace', check=False)
            if response.returncode == 0:
                return [v for v in response.stdout.splitlines() if v.strip()]
            if response.returncode == 1:  # uživatel zavřel dialog
                return []
            # Program může vrátit chybu při nepodporovaném desktopovém prostředí: použij Qt.
        except (OSError, UnicodeError):
            pass

    dlg = QFileDialog(parent, title, base, file_filter)
    dlg.setOption(QFileDialog.Option.DontUseNativeDialog, True)
    if mode == 'files':
        dlg.setFileMode(QFileDialog.FileMode.ExistingFiles)
        dlg.setAcceptMode(QFileDialog.AcceptMode.AcceptOpen)
    elif mode == 'directory':
        dlg.setFileMode(QFileDialog.FileMode.Directory)
        dlg.setOption(QFileDialog.Option.ShowDirsOnly, True)
    else:
        dlg.setAcceptMode(QFileDialog.AcceptMode.AcceptSave)
    dlg.setLabelText(QFileDialog.DialogLabel.LookIn, 'Složka:')
    dlg.setLabelText(QFileDialog.DialogLabel.FileName, 'Název souboru:')
    dlg.setLabelText(QFileDialog.DialogLabel.FileType, 'Typ souboru:')
    dlg.setLabelText(QFileDialog.DialogLabel.Accept, 'Uložit' if mode == 'save' else 'Vybrat')
    dlg.setLabelText(QFileDialog.DialogLabel.Reject, 'Zrušit')
    # Vlastní seznam odkazů místo chybně přeložených názvů ve standardním postranním panelu.
    sidebar = [Path.home()] + [Path.home() / name for name in ('Plocha','Dokumenty','Stažené','Downloads')]
    dlg.setSidebarUrls([QUrl.fromLocalFile(str(p)) for p in sidebar if p.exists()])
    return dlg.selectedFiles() if dlg.exec() == QDialog.DialogCode.Accepted else []


class ScrollSafeDoubleSpinBox(QDoubleSpinBox):
    """Kolečko mění jen posuvník nadřazeného kontejneru, nikdy hodnotu pole.

    Klávesy nahoru/dolů a klikání na šipky stále normálně upravují hodnotu.
    QWheelEvent.ignore() nechá Qt nabídnout událost rodičovskému QScrollArea.
    """
    def wheelEvent(self, event):
        event.ignore()


class ScrollSafeSpinBox(QSpinBox):
    """Ochrana celočíselných polí před nechtěnou změnou kolečkem."""
    def wheelEvent(self, event):
        event.ignore()


class ScrollSafeComboBox(QComboBox):
    """Kolečko nemění zvolenou možnost; v rozbaleném seznamu lze dál rolovat."""
    def wheelEvent(self, event):
        event.ignore()


def spin(value: float = 0, minimum: float = 0, maximum: float = 1_000_000,
         decimals: int = 2, step: float = 1, suffix: str = '') -> QDoubleSpinBox:
    w = ScrollSafeDoubleSpinBox()
    w.setRange(minimum, maximum)
    w.setDecimals(decimals)
    w.setSingleStep(step)
    w.setValue(value)
    if suffix: w.setSuffix(' ' + suffix)
    w.setMinimumHeight(33)
    return w


def section_title(text: str) -> QLabel:
    label = QLabel(text)
    label.setObjectName('sectionTitle')
    return label


def color_button_style(color: str) -> str:
    c = QColor(safe_hex(color))
    contrast = '#101522' if c.lightnessF() > .60 else '#FFFFFF'
    return (f'QPushButton {{background: {c.name()}; color: {contrast};'
            'border: 1px solid #768192; border-radius: 7px; padding: 5px 10px; font-weight: 700;}')


def _thumb_img(b64: str, size: int = 120) -> QPixmap:
    result = QPixmap()
    if b64:
        try: result.loadFromData(base64.b64decode(b64))
        except ValueError: pass
    return result.scaled(size, size, Qt.AspectRatioMode.KeepAspectRatio,
                         Qt.TransformationMode.SmoothTransformation) if not result.isNull() else result


class MaterialBar(QWidget):
    """Pruh spotřeby, skutečné barvy v poměru k gramáži."""
    def __init__(self):
        super().__init__()
        self.filaments: list[Filament] = []
        self.track_color = '#344155'
        self.edge_color = '#8090A6'
        self.setMinimumHeight(42)
        self.setMaximumHeight(42)

    def set_colors(self, background: str, edge: str):
        self.track_color, self.edge_color = background, edge
        self.update()

    def set_filaments(self, filaments: list[Filament]):
        self.filaments = filaments
        self.setToolTip('\n'.join(f'{f.material} / {color_name(f.color)}: {f.grams:.2f} g' for f in filaments))
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(1, 7, max(0, self.width() - 2), 27)
        clip = QPainterPath()
        clip.addRoundedRect(rect, 9, 9)
        painter.setClipPath(clip)
        painter.fillRect(rect, QColor(self.track_color))
        total = sum(max(0, f.grams) for f in self.filaments)
        if total:
            x = rect.left()
            for i, filament in enumerate(self.filaments):
                width = rect.width() * (max(0, filament.grams) / total)
                painter.fillRect(QRectF(x, rect.top(), width, rect.height()), QColor(safe_hex(filament.color)))
                x += width
        painter.setClipping(False)
        painter.setPen(QColor(self.edge_color))
        painter.drawRoundedRect(rect, 9, 9)
        painter.end()


class StatCard(QFrame):
    def __init__(self, title: str):
        super().__init__()
        self.setObjectName('statCard')
        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 11, 16, 12)
        lay.setSpacing(3)
        k = QLabel(title.upper())
        k.setObjectName('statCaption')
        self.number = QLabel('—')
        self.number.setObjectName('statNumber')
        lay.addWidget(k)
        lay.addWidget(self.number)

    def show_value(self, value: str):
        self.number.setText(value)


class SettingsDialog(QDialog):
    def __init__(self, rates: Rates, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle('Nastavení kalkulačky a ceník filamentů')
        self.resize(1050, 750)
        self.setMinimumWidth(780)
        self.rates = Rates(**asdict(rates))
        outer = QVBoxLayout(self)
        outer.setSpacing(12)
        description = QLabel('Výchozí hodnoty převzaté ze staré kalkulačky. Ceník můžeš upravovat podle skutečných cen.')
        description.setWordWrap(True)
        description.setObjectName('muted')
        outer.addWidget(description)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        outer.addWidget(scroll, 1)
        inner = QWidget()
        scroll.setWidget(inner)
        body = QVBoxLayout(inner)

        costs = QGroupBox('Výchozí sazby')
        form = QGridLayout(costs)
        form.setColumnStretch(1, 1)
        self.printer = QLineEdit(self.rates.printer_name)
        self.amort = spin(self.rates.amortization_per_hour, suffix='Kč/h')
        self.price = spin(self.rates.default_price_kg, suffix='Kč/kg')
        self.factor = spin(self.rates.default_coefficient, 1, 20, 2, .1, '×')
        self.labor = spin(self.rates.manual_hour_rate, suffix='Kč/h')
        form.addWidget(QLabel('Tiskárna'), 0, 0); form.addWidget(self.printer, 0, 1)
        form.addWidget(QLabel('Amortizace'), 1, 0); form.addWidget(self.amort, 1, 1)
        form.addWidget(QLabel('Výchozí cena filamentu'), 2, 0); form.addWidget(self.price, 2, 1)
        form.addWidget(QLabel('Výchozí koeficient'), 3, 0); form.addWidget(self.factor, 3, 1)
        form.addWidget(QLabel('Ruční práce'), 4, 0); form.addWidget(self.labor, 4, 1)
        body.addWidget(costs)

        energy = QGroupBox('Spotřeba energie')
        e = QGridLayout(energy)
        self.energy_mode = ScrollSafeComboBox()
        self.energy_mode.addItem('Pevná sazba v Kč/h (původní kalkulačka)', 'hourly')
        self.energy_mode.addItem('Příkon tiskárny × cena za kWh', 'power')
        self.energy_mode.setCurrentIndex(0 if self.rates.energy_mode == 'hourly' else 1)
        self.hour_energy = spin(self.rates.energy_per_hour, suffix='Kč/h')
        self.power = spin(self.rates.power_watt, suffix='W')
        self.kwh = spin(self.rates.price_kwh, suffix='Kč/kWh')
        e.addWidget(QLabel('Způsob výpočtu'), 0, 0); e.addWidget(self.energy_mode, 0, 1)
        e.addWidget(QLabel('Pevná sazba'), 1, 0); e.addWidget(self.hour_energy, 1, 1)
        e.addWidget(QLabel('Průměrný příkon'), 2, 0); e.addWidget(self.power, 2, 1)
        e.addWidget(QLabel('Cena elektřiny'), 3, 0); e.addWidget(self.kwh, 3, 1)
        self.energy_mode.currentIndexChanged.connect(self._energy_enable)
        self._energy_enable()
        body.addWidget(energy)
        theme_group = QGroupBox('Motiv aplikace')
        theme_layout = QVBoxLayout(theme_group)
        self.theme_choice = ScrollSafeComboBox()
        for key, entry in THEMES.items():
            self.theme_choice.addItem(entry['label'], key)
        index = self.theme_choice.findData(self.rates.theme_name())
        self.theme_choice.setCurrentIndex(max(index, 0))
        theme_layout.addWidget(self.theme_choice)
        theme_layout.addWidget(QLabel('Změna se projeví v hlavním okně, nastavení i tabulkách po potvrzení.'))
        body.addWidget(theme_group)

        catalog = QGroupBox('Ceník a sklad vlastních filamentů')
        cl = QVBoxLayout(catalog)
        note = QLabel('Sklad se páruje podle ID. Barevné vzorky se odhadují z názvů i po dalším importu CSV. Pokud vyplníš přesný HEX, má přednost. Nové položky 3D FOX Přeběh mají cenu 200 Kč/kg; ostatní ceny můžeš doplnit. Při importu se podle ID aktualizují zásoby a ceny zůstávají zachované.')
        note.setWordWrap(True); note.setObjectName('muted')
        cl.addWidget(note)
        self.catalog_table = QTableWidget(0, 8)
        self.catalog_table.setHorizontalHeaderLabels(['ID', 'Název / barva', 'Materiál', 'Výrobce', 'Skladem (g)', 'Datum změny', 'HEX (nepovinné)', 'Cena Kč/kg'])
        self.catalog_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        for col, width in enumerate((55, 245, 90, 115, 100, 115, 115, 115)):
            self.catalog_table.setColumnWidth(col, width)
        self.catalog_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.catalog_table.setMinimumHeight(275)
        self.catalog_table.setShowGrid(True)
        self.catalog_table.setAlternatingRowColors(True)
        cl.addWidget(self.catalog_table)
        controls = QHBoxLayout()
        plus = QPushButton('+ Přidat materiál')
        minus = QPushButton('Odebrat vybrané')
        import_btn = QPushButton('Importovat CSV s filamenty')
        import_btn.setObjectName('primary')
        controls.addWidget(import_btn); controls.addWidget(plus); controls.addWidget(minus); controls.addStretch()
        plus.clicked.connect(lambda: self._add_catalog_row({'name': '', 'material': 'PLA', 'color': '', 'price_kg': self.rates.default_price_kg}))
        import_btn.clicked.connect(self._import_catalog_csv)
        minus.clicked.connect(self._remove_catalog_row)
        cl.addLayout(controls)
        for item in self.rates.catalog:
            self._add_catalog_row(item)
        body.addWidget(catalog)
        body.addStretch()
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        outer.addWidget(buttons)

    def _energy_enable(self):
        by_power = self.energy_mode.currentData() == 'power'
        self.hour_energy.setEnabled(not by_power)
        self.power.setEnabled(by_power)
        self.kwh.setEnabled(by_power)

    def _add_catalog_row(self, entry: dict):
        row = self.catalog_table.rowCount()
        self.catalog_table.insertRow(row)
        price = entry.get('price_kg')
        contents = [str(entry.get('csv_id','')), str(entry.get('name','')),
                    str(entry.get('material','')), str(entry.get('manufacturer','')),
                    '' if entry.get('stock_grams') is None else f"{float(entry['stock_grams']):.1f}",
                    str(entry.get('date_changed','')),
                    str(entry.get('color','')), '' if price is None else f"{float(price):.2f}"]
        for col, value in enumerate(contents):
            cell = QTableWidgetItem(value)
            if col == 0:
                cell.setFlags(cell.flags() & ~Qt.ItemFlag.ItemIsEditable)
            if col in (4, 7):
                cell.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.catalog_table.setItem(row, col, cell)
        # Neznámá pole z dřívějších verzí neničíme; CSV ID držíme při importu.
        self.catalog_table.item(row, 0).setData(Qt.ItemDataRole.UserRole, dict(entry))

    def _catalog_from_table(self) -> list[dict]:
        rows = []
        for row in range(self.catalog_table.rowCount()):
            def val(col):
                widget = self.catalog_table.item(row, col)
                return widget.text().strip() if widget else ''
            original = self.catalog_table.item(row, 0).data(Qt.ItemDataRole.UserRole) or {}
            entry = dict(original)
            name, material, manufacturer = val(1), val(2), val(3)
            if not name and not material: continue
            if not material or not name:
                raise ValueError(f'Řádek {row+1}: vyplň název a materiál.')
            color = val(6).upper()
            if color and not re.fullmatch(r'#[0-9A-F]{6}', color):
                raise ValueError(f'Řádek {row+1}: barva musí být například #FF0000, nebo prázdná.')
            price_text = val(7).replace(' ', '').replace(',', '.')
            try:
                price = float(price_text) if price_text else None
            except ValueError:
                raise ValueError(f'Řádek {row+1}: neplatná cena za kg.') from None
            if price is not None and (not 0 <= price <= 10_000_000):
                raise ValueError(f'Řádek {row+1}: cena musí být nezáporná.')
            stock_text = val(4).replace(' ', '').replace(',', '.')
            try:
                stock = float(stock_text) if stock_text else None
            except ValueError:
                raise ValueError(f'Řádek {row+1}: neplatná zásoba.') from None
            if stock is not None and not 0 <= stock <= 1_000_000_000:
                raise ValueError(f'Řádek {row+1}: zásoba musí být nezáporná.')
            previous_price = original.get('price_kg')
            entry.update(name=name, material=material, manufacturer=manufacturer,
                         stock_grams=stock, date_changed=val(5),
                         color=color, price_kg=price)
            if price is not None and price != previous_price:
                entry['price_is_custom'] = True
            rows.append(entry)
        return rows

    def _import_catalog_csv(self):
        paths = choose_dialog(self, 'Importovat sklad filamentů (CSV)', mode='files',
                              file_filter='CSV soubory (*.csv)')
        if not paths: return
        try:
            previous = self._catalog_from_table()
            incoming, stats = import_filament_csv(paths[0], previous)
        except (OSError, UnicodeError, ValueError, TypeError) as exc:
            QMessageBox.warning(self, 'Import CSV', f'Import se nezdařil: {exc}')
            return
        self.rates.catalog = incoming
        self.catalog_table.setRowCount(0)
        for item in incoming:
            self._add_catalog_row(item)
        QMessageBox.information(self, 'Import hotový',
            f"Načteno {stats['count']} filamentů. Nových: {stats['added']}, aktualizovaných: {stats['updated']}.\n"
            f"Automatická cena 200 Kč/kg: {stats['overruns']} přeběhů 3D FOX.\n\n"
            'Import se uloží po potvrzení tlačítkem OK. Aktuální sklad je pouze informativní.')

    def _remove_catalog_row(self):
        for row in sorted({index.row() for index in self.catalog_table.selectedIndexes()}, reverse=True):
            self.catalog_table.removeRow(row)

    def accept(self):
        try:
            self.rates.catalog = self._catalog_from_table()
        except ValueError as exc:
            QMessageBox.warning(self, 'Ceník a sklad', str(exc))
            return
        self.rates.printer_name = self.printer.text().strip() or 'Bambu Lab P2S'
        self.rates.amortization_per_hour = self.amort.value()
        self.rates.default_price_kg = self.price.value()
        self.rates.default_coefficient = self.factor.value()
        self.rates.manual_hour_rate = self.labor.value()
        self.rates.energy_mode = self.energy_mode.currentData()
        self.rates.energy_per_hour = self.hour_energy.value()
        self.rates.theme = self.theme_choice.currentData()
        self.rates.dark_mode = self.rates.theme == 'dark' 
        self.rates.power_watt = self.power.value()
        self.rates.price_kwh = self.kwh.value()
        super().accept()



def _normalize_search(value: str) -> str:
    """Hledání bez ohledu na diakritiku, velikost písmen a vícenásobné mezery."""
    text = unicodedata.normalize('NFKD', str(value).casefold())
    return ' '.join(''.join(ch for ch in text if not unicodedata.combining(ch)).split())


def _approx_color(name: str, hex_color: str = '') -> str:
    """Zpětně kompatibilní odkaz na společný výpočet barev."""
    return approximate_filament_color(name, hex_color)


class WarehousePicker(QDialog):
    """Přehledný vizuální výběr jediné skladové položky podle ID.

    Používá lokálně naimportovaný katalog. Není to přímé připojení k webu.
    """
    def __init__(self, catalog: list[dict], filament: Filament, price_fallback: float,
                 required_g: float, parent=None):
        super().__init__(parent)
        self.catalog = [dict(item) for item in catalog if item.get('csv_id') and item.get('name')]
        self.current = filament
        self.required_g = max(0., required_g)
        self.price_fallback = price_fallback
        self.chosen: dict | None = None
        self.setWindowTitle('Vybrat filament z mého skladu')
        self.resize(1020, 690)
        self.setMinimumSize(780, 505)
        root = QVBoxLayout(self)
        root.setSpacing(11)
        header = QLabel('VÝBĚR FILAMENTU ZE SKLADU')
        header.setObjectName('appHeading')
        root.addWidget(header)
        info = QLabel(f'Skladem {len(self.catalog)} položek • pro tento tisk je potřeba '
                      f'{self.required_g:,.1f} g • vazba na sklad je podle ID, nikoliv podle názvu.')
        info.setObjectName('muted')
        root.addWidget(info)
        hint = QLabel('Barevné vzorky se automaticky odhadují z názvu filamentu (např. armádní zelená, světle modrá). '
                      'Pokud vyplníš HEX v Nastavení, použije se přesná zadaná barva.')
        hint.setWordWrap(True)
        hint.setObjectName('muted')
        root.addWidget(hint)
        filters = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText('Hledat barvu, výrobce, materiál nebo ID (např. pistáciová, 3D FOX, 22)')
        self.types = ScrollSafeComboBox()
        self.types.addItem('Všechny typy', '')
        self.types.addItems(sorted({str(x.get('material', '')).strip() for x in self.catalog if x.get('material')}))
        self.makers = ScrollSafeComboBox()
        self.makers.addItem('Všichni výrobci', '')
        self.makers.addItems(sorted({str(x.get('manufacturer', '')).strip() for x in self.catalog if x.get('manufacturer')}))
        self.in_stock = QCheckBox('Jen skladem')
        self.in_stock.setChecked(False)
        filters.addWidget(self.search, 1)
        filters.addWidget(self.types)
        filters.addWidget(self.makers)
        filters.addWidget(self.in_stock)
        root.addLayout(filters)
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(['Barva / název', 'ID', 'Materiál', 'Výrobce', 'Skladem (g)', 'Cena Kč/kg'])
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setShowGrid(True)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setIconSize(QPixmap(24, 24).size())
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for col, width in enumerate((320, 65, 100, 125, 115, 110)):
            if col: self.table.setColumnWidth(col, width)
        self.table.itemSelectionChanged.connect(self._selection_changed)
        self.table.itemDoubleClicked.connect(lambda *_: self.accept())
        root.addWidget(self.table, 1)
        self.summary = QLabel('Vyber filament pro zobrazení zásoby a ceny.')
        self.summary.setObjectName('strongText')
        self.summary.setWordWrap(True)
        root.addWidget(self.summary)
        actions = QHBoxLayout()
        self.count = QLabel('')
        self.count.setObjectName('muted')
        actions.addWidget(self.count)
        actions.addStretch(1)
        cancel = QPushButton('Zrušit')
        self.ok = QPushButton('Použít vybraný filament')
        self.ok.setObjectName('primary')
        self.ok.setEnabled(False)
        cancel.clicked.connect(self.reject)
        self.ok.clicked.connect(self.accept)
        actions.addWidget(cancel)
        actions.addWidget(self.ok)
        root.addLayout(actions)
        self.search.textChanged.connect(self._populate)
        self.types.currentIndexChanged.connect(self._populate)
        self.makers.currentIndexChanged.connect(self._populate)
        self.in_stock.toggled.connect(self._populate)
        material_index = self.types.findText(filament.material)
        if material_index >= 0: self.types.setCurrentIndex(material_index)
        self._populate()

    @staticmethod
    def _swatch(item: dict) -> QIcon:
        shade = _approx_color(item.get('name', ''), item.get('color', ''))
        img = QPixmap(22, 22)
        img.fill(Qt.GlobalColor.transparent)
        p = QPainter(img)
        p.setPen(QColor('#707C8B'))
        p.setBrush(QColor(shade))
        p.drawRoundedRect(2, 2, 17, 17, 4, 4)
        p.end()
        return QIcon(img)

    def _populate(self, *_):
        key = _normalize_search(self.search.text())
        typ = self.types.currentData() or self.types.currentText() if self.types.currentIndex() > 0 else ''
        maker = self.makers.currentText() if self.makers.currentIndex() > 0 else ''
        self.table.blockSignals(True)
        self.table.setRowCount(0)
        matching = []
        for entry in self.catalog:
            if typ and entry.get('material', '') != typ: continue
            if maker and entry.get('manufacturer', '') != maker: continue
            qty = float(entry.get('stock_grams') or 0)
            if self.in_stock.isChecked() and qty <= 0: continue
            haystack = _normalize_search(' '.join(str(entry.get(k, '')) for k in
                ('csv_id', 'name', 'material', 'manufacturer')))
            if key and not all(part in haystack for part in key.split()): continue
            matching.append(entry)
        # Default: aktuální ID nahoře, pak zásoby a jména. Snadno najde už použitý filament.
        matching.sort(key=lambda x: (str(x.get('csv_id', '')) != self.current.catalog_id,
                                     float(x.get('stock_grams') or 0) <= 0,
                                     _normalize_search(x.get('name', ''))))
        selected_row = -1
        for entry in matching:
            r = self.table.rowCount()
            self.table.insertRow(r)
            name = QTableWidgetItem(self._swatch(entry), str(entry.get('name', '')))
            name.setData(Qt.ItemDataRole.UserRole, dict(entry))
            shade = _approx_color(str(entry.get('name', '')), str(entry.get('color', '')))
            source = ('HEX z webové evidence (CSV)' if entry.get('color_source')=='web-csv'
                      else 'ručně nastavený HEX' if re.fullmatch(r'#[A-Fa-f0-9]{6}', str(entry.get('color') or ''))
                      else 'orientační odhad podle názvu')
            name.setToolTip(f'Barevný vzorek: {shade} – {source}')
            self.table.setItem(r, 0, name)
            values = [str(entry.get('csv_id', '')), str(entry.get('material', '')),
                      str(entry.get('manufacturer', '')),
                      f"{float(entry.get('stock_grams') or 0):,.0f}".replace(',', ' '),
                      ('—' if entry.get('price_kg') is None else f"{float(entry['price_kg']):.0f}")]
            for col, value in enumerate(values, 1):
                cell = QTableWidgetItem(value)
                if col in (1, 4, 5):
                    cell.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                self.table.setItem(r, col, cell)
            self.table.setRowHeight(r, 43)
            if str(entry.get('csv_id', '')) == self.current.catalog_id: selected_row = r
        self.table.blockSignals(False)
        self.count.setText(f'Zobrazeno {len(matching)} z {len(self.catalog)} filamentů')
        if matching:
            self.table.selectRow(max(0, selected_row))
        else:
            self._selection_changed()

    def _selection_changed(self):
        row = self.table.currentRow()
        item = self.table.item(row, 0) if row >= 0 else None
        selected = item.data(Qt.ItemDataRole.UserRole) if item else None
        self.chosen = selected if isinstance(selected, dict) else None
        self.ok.setEnabled(self.chosen is not None)
        if not self.chosen:
            self.summary.setText('Zadanému filtru neodpovídá žádný filament.')
            return
        entry = self.chosen
        stock = float(entry.get('stock_grams') or 0)
        remainder = stock - self.required_g
        price = entry.get('price_kg')
        price_label = (f'{float(price):.0f} Kč/kg' if price is not None else
                       f'NEOCENĚNO – výchozí sazba {self.price_fallback:.0f} Kč/kg')
        self.summary.setText(
            f"#{entry.get('csv_id')} • {entry.get('material')} • {entry.get('name')} • "
            f"{entry.get('manufacturer')}  |  {price_label}  |  po tomto tisku "
            f"{'CHYBÍ ' + f'{-remainder:.1f} g' if remainder < 0 else f'zbude {remainder:.1f} g'}")

    def accept(self):
        if self.chosen is None: return
        super().accept()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.rates = load_rates()
        self.jobs: list[PrintJob] = []
        self.project_path: Path | None = None
        self.dirty = False
        self._syncing = False
        self.setWindowTitle('3D Kalkulačka – Bambu Studio')
        self.resize(1370, 840)
        self.setMinimumSize(950, 620)
        self.setAcceptDrops(True)
        self._build_ui()
        self._set_theme()
        self._refresh_all()

    def _build_ui(self):
        base = QWidget()
        base.setObjectName('base')
        self.setCentralWidget(base)
        root = QVBoxLayout(base)
        root.setContentsMargins(19, 15, 19, 13)
        root.setSpacing(12)
        headerbox = QFrame()
        headerbox.setObjectName('headerBox')
        headerouter = QVBoxLayout(headerbox)
        headerouter.setContentsMargins(14, 12, 14, 11)
        headerouter.setSpacing(7)
        header = QHBoxLayout()
        header_text = QVBoxLayout()
        heading = QLabel('3D KALKULAČKA')
        heading.setObjectName('appHeading')
        small = QLabel(f'Bambu Studio  •  .gcode.3mf  •  verze {APP_VERSION}')
        small.setObjectName('muted')
        header_text.addWidget(heading)
        header_text.addWidget(small)
        header.addLayout(header_text)
        header.addStretch(1)
        actions = [('+ Přidat G-code', self._pick_files, 'primary'),
                   ('Složka', self._pick_folder, ''),
                   ('Nová', self._new, ''), ('Otevřít', self._open, ''),
                   ('Uložit', self._save, ''), ('PDF', self._export_pdf, ''),
                   ('CSV', self._export_csv, ''), ('Import skladu', self._import_inventory_main, ''),
                   ('Nastavení', self._settings, '')]
        for label, action, obj in actions:
            btn = QPushButton(label)
            btn.setObjectName(obj if obj else 'toolbarButton')
            btn.setMinimumHeight(37)
            btn.clicked.connect(action)
            header.addWidget(btn)
        headerouter.addLayout(header)

        project_line = QHBoxLayout()
        project_line.addWidget(QLabel('Zakázka'))
        self.project_title = QLineEdit('Nová zakázka')
        self.project_title.setMaximumWidth(330)
        self.project_title.textChanged.connect(self._project_changed)
        project_line.addWidget(self.project_title)
        project_line.addSpacing(14)
        project_line.addWidget(QLabel('Koeficient pro nové tisky'))
        self.global_factor = spin(self.rates.default_coefficient, 1, 20, 2, .1, '×')
        self.global_factor.setMaximumWidth(105)
        self.global_factor.valueChanged.connect(self._global_factor_changed)
        project_line.addWidget(self.global_factor)
        factor_apply = QPushButton('Použít na všechny')
        factor_apply.clicked.connect(self._apply_factor)
        project_line.addWidget(factor_apply)
        project_line.addStretch(1)
        self.status_text = QLabel('Přetáhni G-code do okna nebo jej přidej tlačítkem.')
        self.status_text.setObjectName('muted')
        project_line.addWidget(self.status_text)
        headerouter.addLayout(project_line)
        root.addWidget(headerbox)

        cards = QHBoxLayout()
        self.stat_models = StatCard('Tisky / kusy')
        self.stat_time = StatCard('Celkový čas')
        self.stat_grams = StatCard('Spotřeba filamentu')
        self.stat_cost = StatCard('Náklady')
        self.stat_price = StatCard('Cena zakázky')
        for card in (self.stat_models, self.stat_time, self.stat_grams, self.stat_cost, self.stat_price):
            cards.addWidget(card, 1)
        root.addLayout(cards)

        split = QSplitter(Qt.Orientation.Horizontal)
        split.setChildrenCollapsible(False)
        root.addWidget(split, 1)

        left = QFrame()
        left.setObjectName('panel')
        lv = QVBoxLayout(left)
        lv.setContentsMargins(13, 14, 13, 13)
        left_head = QHBoxLayout()
        left_head.addWidget(section_title('TISKY V ZAKÁZCE'))
        left_head.addStretch()
        remove = QPushButton('Odebrat vybraný')
        remove.clicked.connect(self._remove_selected)
        left_head.addWidget(remove)
        lv.addLayout(left_head)
        # Náklady, prodejní cena a skutečný rozdíl pro KAŽDÝ tisk; hodnoty za všechny kusy.
        self.job_table = QTableWidget(0, 8)
        self.job_table.setHorizontalHeaderLabels([
            'Náhled', 'Tisk / podložka', 'Barvy', 'Ks', 'Čas',
            'Náklady', 'Cena', 'Rozdíl'
        ])
        self.job_table.setToolTip('Náklady = materiál + amortizace + energie + práce + další náklady. '
                                  'Cena = prodejní cena. Rozdíl = cena − náklady. '
                                  'Všechny částky jsou za uvedený počet kusů.')
        self.job_table.setAlternatingRowColors(True)
        self.job_table.setShowGrid(True)
        self.job_table.verticalHeader().setVisible(False)
        self.job_table.setIconSize(QPixmap(64, 64).size())
        self.job_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.job_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.job_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.job_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.job_table.setColumnWidth(0, 64)
        self.job_table.setColumnWidth(2, 85)
        self.job_table.setColumnWidth(3, 38)
        self.job_table.setColumnWidth(4, 96)
        self.job_table.setColumnWidth(5, 91)
        self.job_table.setColumnWidth(6, 91)
        self.job_table.setColumnWidth(7, 91)
        for col in (5, 6, 7):
            self.job_table.horizontalHeaderItem(col).setToolTip(
                ('Vlastní náklady na tisk, za všechny kusy.' if col == 5 else
                 'Výsledná prodejní cena za všechny kusy.' if col == 6 else
                 'Cena minus náklady za všechny kusy (záporná = ztráta).'))
        self.job_table.itemSelectionChanged.connect(self._show_selected)
        lv.addWidget(self.job_table, 1)
        hint = QLabel('Více modelů na jedné tiskové podložce tvoří jeden tisk. Čas se mezi modely nerozděluje.')
        hint.setWordWrap(True); hint.setObjectName('muted')
        lv.addWidget(hint)
        split.addWidget(left)

        right = QFrame()
        right.setObjectName('panel')
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(13, 14, 13, 13)
        scroll = QScrollArea()
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidgetResizable(True)
        right_layout.addWidget(scroll)
        container = QWidget()
        scroll.setWidget(container)
        self.details = QVBoxLayout(container)
        self.details.setContentsMargins(3, 0, 3, 10)
        self.details.setSpacing(12)
        self.details.addWidget(section_title('DETAIL VYBRANÉHO TISKU'))
        top = QHBoxLayout()
        self.preview = QLabel('Náhled není k dispozici')
        self.preview.setObjectName('preview')
        self.preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview.setFixedSize(145, 145)
        self.preview.setWordWrap(True)
        top.addWidget(self.preview)
        info = QVBoxLayout()
        self.detail_name = QLineEdit()
        self.detail_name.setPlaceholderText('Název tisku')
        self.detail_name.textEdited.connect(lambda value: self._edit_attr('name', value))
        info.addWidget(QLabel('Název tisku'))
        info.addWidget(self.detail_name)
        self.info_text = QLabel('—')
        self.info_text.setWordWrap(True)
        self.info_text.setObjectName('muted')
        info.addWidget(self.info_text)
        info.addStretch()
        top.addLayout(info, 1)
        self.details.addLayout(top)

        self.details.addWidget(section_title('PARAMETRY A NACENĚNÍ'))
        grid = QGridLayout()
        self.detail_qty = ScrollSafeSpinBox()
        self.detail_qty.setRange(1, 100_000)
        self.detail_qty.valueChanged.connect(lambda value: self._edit_attr('quantity', value))
        self.detail_time = spin(0, 0, 100_000, 3, .1, 'h')
        self.detail_time.valueChanged.connect(lambda value: self._edit_attr('time_seconds', round(value * 3600)))
        self.detail_price_mode = ScrollSafeComboBox()
        self.detail_price_mode.addItem('Koeficient × náklady', 'coefficient')
        self.detail_price_mode.addItem('Pevná výsledná cena', 'fixed')
        self.detail_price_mode.currentIndexChanged.connect(self._price_mode_changed)
        self.detail_factor = spin(1.5, 1, 20, 2, .1, '×')
        self.detail_factor.valueChanged.connect(lambda value: self._edit_attr('coefficient', value))
        self.detail_fixed_price = spin(0, 0, 10_000_000, 2, 10, 'Kč/tisk')
        self.detail_fixed_price.valueChanged.connect(lambda value: self._edit_attr('fixed_unit_price', value))
        self.detail_extra = spin(0, suffix='Kč/tisk')
        self.detail_extra.valueChanged.connect(lambda value: self._edit_attr('extra_cost', value))
        self.detail_labor = spin(0, suffix='min/tisk')
        self.detail_labor.valueChanged.connect(lambda value: self._edit_attr('labor_minutes', value))
        pairs = [('Počet tisků', self.detail_qty), ('Čas jednoho tisku', self.detail_time),
                 ('Způsob nacenění', self.detail_price_mode), ('Koeficient', self.detail_factor),
                 ('Pevná cena za jeden tisk', self.detail_fixed_price),
                 ('Další náklady', self.detail_extra), ('Ruční práce', self.detail_labor)]
        for i, (lbl, widget) in enumerate(pairs):
            row, col = divmod(i, 2)
            grid.addWidget(QLabel(lbl), row * 2, col)
            grid.addWidget(widget, row * 2 + 1, col)
        grid.setColumnStretch(0, 1); grid.setColumnStretch(1, 1)
        self.details.addLayout(grid)

        self.details.addWidget(section_title('FILAMENTY – AUTOMATICKY ZE SOUBORU'))
        self.bar = MaterialBar()
        self.details.addWidget(self.bar)
        self.fil_table = QTableWidget(0, 6)
        self.fil_table.setHorizontalHeaderLabels(['Filament ze skladu', 'Barva', 'Spotřeba g', 'Zbývá po zakázce', 'Kč/kg', 'Cena'])
        self.fil_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.fil_table.setColumnWidth(0, 260)
        self.fil_table.setColumnWidth(1, 88)
        self.fil_table.setColumnWidth(2, 91)
        self.fil_table.setColumnWidth(3, 126)
        self.fil_table.setColumnWidth(4, 100)
        self.fil_table.setColumnWidth(5, 90)
        self.fil_table.verticalHeader().setVisible(False)
        self.fil_table.setShowGrid(True)
        self.fil_table.setMinimumHeight(155)
        self.details.addWidget(self.fil_table)
        note = QLabel('Tlačítkem u filamentu otevřeš přehled skladu se hledáním, výrobcem, typem a ID. Barevné vzorky z názvů jsou jen orientační. Zásoby jsou plánované pro celou zakázku, bez automatického odpisu.')
        note.setWordWrap(True); note.setObjectName('muted')
        self.details.addWidget(note)
        fil_buttons = QHBoxLayout()
        add_fil = QPushButton('+ Filament')
        del_fil = QPushButton('Odebrat filament')
        apply_catalog = QPushButton('Načíst ceny z ceníku')
        save_catalog = QPushButton('Uložit ceny do ceníku')
        add_fil.clicked.connect(self._add_filament)
        del_fil.clicked.connect(self._remove_filament)
        apply_catalog.clicked.connect(self._apply_catalog)
        save_catalog.clicked.connect(self._save_catalog)
        for btn in (add_fil, del_fil, apply_catalog, save_catalog): fil_buttons.addWidget(btn)
        self.details.addLayout(fil_buttons)
        self.details.addWidget(section_title('ROZPIS CENY VYBRANÉHO TISKU'))
        self.cost_box = QFrame()
        self.cost_box.setObjectName('costBox')
        cb = QGridLayout(self.cost_box)
        self.cost_labels: dict[str, QLabel] = {}
        for i, (key, title) in enumerate([
            ('material', 'Materiál'), ('amort', 'Amortizace'), ('energy', 'Energie'),
            ('labor', 'Ruční práce'), ('extra', 'Další náklady'),
            ('base', 'Náklady celkem'), ('profit', 'Rozdíl cena − náklady'),
            ('price', 'Výsledná cena')]):
            lhs = QLabel(title)
            rhs = QLabel('—')
            rhs.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            if key in ('base', 'price'):
                lhs.setObjectName('strongText'); rhs.setObjectName('strongText')
            cb.addWidget(lhs, i, 0); cb.addWidget(rhs, i, 1)
            self.cost_labels[key] = rhs
        cb.setColumnStretch(0, 1)
        self.details.addWidget(self.cost_box)
        self.warning_text = QLabel('')
        self.warning_text.setObjectName('warning')
        self.warning_text.setWordWrap(True)
        self.details.addWidget(self.warning_text)
        self.details.addStretch(1)
        split.addWidget(right)
        split.setSizes([720, 690])
        self.statusBar().showMessage('Připraveno • Výpočet funguje offline')

    def _set_theme(self):
        # Jednotný styl přímo na QApplication, jinak se dialog Nastavení
        # v KDE vykresluje světlý s bílými popisky a tmavými poli.
        theme = self.rates.theme_name()
        QApplication.instance().setStyleSheet(build_stylesheet(theme))
        colors = THEMES[theme]
        if hasattr(self, 'bar'):
            self.bar.set_colors(colors['alt'], colors['edge'])

    def _project_changed(self, _):
        if not self._syncing: self._mark_dirty()

    def _global_factor_changed(self, value: float):
        if not self._syncing:
            self.rates.default_coefficient = value
            self._mark_dirty()

    def _mark_dirty(self):
        self.dirty = True
        self._window_title()

    def _window_title(self):
        self.setWindowTitle(('● ' if self.dirty else '') + '3D Kalkulačka – ' + (self.project_title.text().strip() or 'Nová zakázka'))

    def _selected_job(self) -> PrintJob | None:
        row = self.job_table.currentRow()
        return self.jobs[row] if 0 <= row < len(self.jobs) else None

    def _refresh_all(self):
        current = self.job_table.currentRow()
        self._refresh_table()
        if self.jobs and current < 0:
            self.job_table.selectRow(0)
            self._show_selected()
        elif not self.jobs:
            self._clear_details()
        self._refresh_summary()
        self._refresh_costs()

    def _refresh_table(self):
        current = self.job_table.currentRow()
        self.job_table.blockSignals(True)
        self.job_table.setRowCount(len(self.jobs))
        for row, j in enumerate(self.jobs):
            self.job_table.setRowHeight(row, 72)
            pix = _thumb_img(j.thumbnail_b64, 52)
            image_item = QTableWidgetItem()
            if not pix.isNull(): image_item.setIcon(QIcon(pix))
            image_item.setText('—' if pix.isNull() else '')
            self.job_table.setItem(row, 0, image_item)
            title = QTableWidgetItem(j.name)
            title.setToolTip('\n'.join(j.objects) or j.path)
            self.job_table.setItem(row, 1, title)
            dotbar = QWidget()
            line = QHBoxLayout(dotbar)
            line.setContentsMargins(3, 0, 2, 0)
            line.setSpacing(2)
            for f in j.filaments[:5]:
                dot = QLabel()
                dot.setFixedSize(13, 13)
                dot.setToolTip(f'{f.material}: {color_name(f.color)}, {f.grams:.2f} g')
                dot.setStyleSheet(f'background: {safe_hex(f.color)}; border: 1px solid #667489; border-radius: 6px;')
                line.addWidget(dot)
            line.addStretch()
            self.job_table.setCellWidget(row, 2, dotbar)
            data = j.totals(self.rates)
            # Použij stejný výpočet jako u celkového souhrnu a detailu tisku.
            # Data jsou součtem za počet kusů daného tisku, nikoli pouze za jeden kus.
            values = [
                (3, str(j.quantity)),
                (4, human_duration(data['seconds'])),
                (5, money(data['base'])),
                (6, money(data['price'])),
                (7, money(data['profit'])),
            ]
            breakdown = (
                f"Materiál: {money(data['material'])}\n"
                f"Amortizace: {money(data['amort'])}\n"
                f"Elektřina: {money(data['energy'])}\n"
                f"Ruční práce: {money(data['labor'])}\n"
                f"Další náklady: {money(data['extra'])}\n"
                f"Náklady celkem: {money(data['base'])}\n"
                f"Prodejní cena: {money(data['price'])}\n"
                f"Rozdíl: {money(data['profit'])}\n"
                f"Počet kusů: {j.quantity}"
            )
            for col, value in values:
                item = QTableWidgetItem(value)
                item.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight)
                if col in (5, 6, 7):
                    item.setToolTip(breakdown)
                if col == 7 and data['profit'] < -0.005:
                    item.setForeground(QColor('#FF9487' if self.rates.theme_name() == 'dark' else '#B42318'))
                    item.setToolTip(breakdown + '\nPOZOR: Tisk se prodává pod vlastními náklady.')
                self.job_table.setItem(row, col, item)
        if 0 <= current < len(self.jobs): self.job_table.selectRow(current)
        self.job_table.blockSignals(False)

    def _refresh_summary(self):
        totals = project_totals(self.jobs, self.rates)
        self.stat_models.show_value(f'{len(self.jobs)} / {sum(j.quantity for j in self.jobs)}')
        self.stat_time.show_value(human_duration(totals['seconds']))
        self.stat_grams.show_value(f"{totals['grams']:.2f} g".replace('.', ','))
        self.stat_cost.show_value(money(totals['base']))
        self.stat_price.show_value(money(totals['price']))
        self.status_text.setText(f'{len(self.jobs)} tisků • sazba energie {money(self.rates.hourly_energy_cost())}/h')

    def _show_selected(self):
        j = self._selected_job()
        if not j:
            self._clear_details()
            return
        self._syncing = True
        try:
            self.detail_name.setText(j.name)
            self.detail_qty.setValue(j.quantity)
            self.detail_time.setValue(j.time_seconds / 3600)
            self.detail_factor.setValue(j.coefficient)
            self.detail_price_mode.setCurrentIndex(1 if j.price_mode == 'fixed' else 0)
            self.detail_fixed_price.setValue(j.fixed_unit_price)
            self.detail_factor.setEnabled(j.price_mode != 'fixed')
            self.detail_fixed_price.setEnabled(j.price_mode == 'fixed')
            self.detail_extra.setValue(j.extra_cost)
            self.detail_labor.setValue(j.labor_minutes)
            pix = _thumb_img(j.thumbnail_b64, 139)
            if pix.isNull():
                self.preview.setPixmap(QPixmap())
                self.preview.setText('Náhled není dostupný')
            else:
                self.preview.setText('')
                self.preview.setPixmap(pix)
            desc = [f'Podložka {j.plate} • {len(j.objects)} modelů', f'Vrstev: {j.layers}' if j.layers else '',
                    f'Tryska: {j.nozzle} mm' if j.nozzle else '',
                    f'Výška vrstvy: {j.layer_height} mm' if j.layer_height else '',
                    f'Změn filamentu: {j.switches}' if j.switches else '']
            if j.objects: desc.append('Objekty: ' + ', '.join(j.objects[:5]))
            self.info_text.setText('  •  '.join(x for x in desc if x))
            self._populate_filaments(j)
        finally:
            self._syncing = False
        self._refresh_costs()

    def _clear_details(self):
        self._syncing = True
        self.detail_name.clear()
        self.detail_qty.setValue(1)
        self.detail_time.setValue(0)
        self.detail_factor.setValue(1)
        self.detail_price_mode.setCurrentIndex(0)
        self.detail_fixed_price.setValue(0)
        self.detail_factor.setEnabled(True)
        self.detail_fixed_price.setEnabled(False)
        self.detail_extra.setValue(0)
        self.detail_labor.setValue(0)
        self.preview.clear()
        self.preview.setText('Přidej tiskový soubor')
        self.info_text.setText('Po načtení se zde zobrazí náhled, materiály a rozpis ceny.')
        self.fil_table.setRowCount(0)
        self.bar.set_filaments([])
        self.warning_text.setText('')
        for label in self.cost_labels.values(): label.setText('—')
        self._syncing = False

    def _populate_filaments(self, job: PrintJob):
        self.fil_table.setRowCount(len(job.filaments))
        self.fil_table.setMinimumHeight(min(345, 50 + len(job.filaments) * 47))
        for idx, f in enumerate(job.filaments):
            self.fil_table.setRowHeight(idx, 44)
            # Stručné ID + název. Dlouhé popisy už nejsou v kombinované rozbalovací nabídce.
            holder = QWidget()
            hl = QHBoxLayout(holder)
            hl.setContentsMargins(2, 1, 2, 1)
            hl.setSpacing(4)
            if f.catalog_id:
                shown = f'#{f.catalog_id} • {f.catalog_name or f.material}'
            else:
                shown = f'{f.material} • Vybrat ze skladu…'
            choose = QPushButton(shown)
            choose.setToolTip('Otevřít přehled skladu: hledání podle ID, názvu, materiálu a výrobce.')
            choose.clicked.connect(lambda _, j=job.id, i=idx: self._choose_stock_item(j, i))
            hl.addWidget(choose, 1)
            manual = QPushButton('Typ…')
            manual.setToolTip('Ručně změnit typ materiálu bez výběru konkrétního filamentu ze skladu.')
            manual.clicked.connect(lambda _, j=job.id, i=idx: self._edit_material_type(j, i))
            hl.addWidget(manual)
            self.fil_table.setCellWidget(idx, 0, holder)

            col_btn = QPushButton('●')
            col_btn.setToolTip(f'{color_name(f.color)} • {f.color}\nKlikni pro změnu barvy')
            col_btn.setStyleSheet(color_button_style(f.color))
            col_btn.clicked.connect(lambda _, j=job.id, i=idx: self._choose_filament_color(j, i))
            self.fil_table.setCellWidget(idx, 1, col_btn)
            grams = spin(f.grams, 0, 1_000_000, 2, 0.5)
            grams.valueChanged.connect(lambda val, j=job.id, i=idx: self._edit_filament(j, i, 'grams', val))
            self.fil_table.setCellWidget(idx, 2, grams)
            balances = stock_balances(self.jobs, self.rates.catalog)
            current = balances.get(f.catalog_id) if f.catalog_id else None
            remaining_text = (f"{current['remaining']:.1f} g" if current else '—')
            stock_item = QTableWidgetItem(remaining_text)
            stock_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            if current and current['remaining'] < 0:
                stock_item.setToolTip('Nedostatek materiálu pro celou zakázku!')
                stock_item.setForeground(QColor('#E16B56'))
            self.fil_table.setItem(idx, 3, stock_item)
            price = spin(f.price_kg, 0, 1_000_000, 2, 10)
            price.setToolTip('Cenu můžeš upravit ručně. Výběrem položky z ceníku se doplní automaticky.')
            price.valueChanged.connect(lambda val, j=job.id, i=idx: self._edit_filament(j, i, 'price_kg', val))
            self.fil_table.setCellWidget(idx, 4, price)
            self.fil_table.setItem(idx, 5, QTableWidgetItem(money(f.cost)))
        self.bar.set_filaments(job.filaments)

    def _choose_stock_item(self, job_id: str, idx: int):
        job = self._find_job(job_id)
        if not job or not 0 <= idx < len(job.filaments): return
        if not self.rates.catalog or not any(item.get('csv_id') for item in self.rates.catalog):
            QMessageBox.information(self, 'Sklad není naimportovaný',
                'Nejprve použij tlačítko Import skladu a nahraj CSV ze své webové evidence.')
            return
        f = job.filaments[idx]
        dlg = WarehousePicker(self.rates.catalog, f, self.rates.default_price_kg,
                              f.grams * job.quantity, self)
        if dlg.exec() != QDialog.DialogCode.Accepted or not dlg.chosen: return
        data = dlg.chosen
        f.material = str(data.get('material', '')).strip() or f.material
        f.catalog_name = str(data.get('name', ''))
        f.catalog_id = str(data.get('csv_id', ''))
        f.price_kg = (float(data['price_kg']) if data.get('price_kg') is not None
                      else self.rates.default_price_kg)
        # Při zvolení jiné skladové barvy aktualizujeme barevné rozlišení.
        # Pokud CSV nemá HEX, jde POUZE o orientační odstín odvozený z názvu.
        f.color = _approx_color(f.catalog_name, str(data.get('color', '')))
        self._mark_dirty()
        self._show_selected()
        self._refresh_live()

    def _edit_material_type(self, job_id: str, idx: int):
        job = self._find_job(job_id)
        if not job or not 0 <= idx < len(job.filaments): return
        f = job.filaments[idx]
        new_material, ok = QInputDialog.getText(self, 'Ruční typ filamentu',
            'Materiál (PLA, PETG, ABS…):', QLineEdit.EchoMode.Normal, f.material)
        if not ok or not new_material.strip(): return
        f.material = new_material.strip()
        f.catalog_name = ''
        f.catalog_id = ''
        f.price_kg = self.rates.lookup_price(f.material, f.color)
        self._mark_dirty()
        self._show_selected()
        self._refresh_live()

    def _find_job(self, id_: str) -> PrintJob | None:
        return next((j for j in self.jobs if j.id == id_), None)

    def _edit_filament(self, job_id: str, idx: int, attr: str, value):
        if self._syncing: return
        j = self._find_job(job_id)
        if not j or idx >= len(j.filaments): return
        setattr(j.filaments[idx], attr, value)
        if attr == 'price_kg':
            # Při ruční změně ceny zachováme propojení se skladem.
            pass
        self._mark_dirty()
        self._refresh_live()

    def _choose_filament_color(self, job_id: str, idx: int):
        j = self._find_job(job_id)
        if not j or idx >= len(j.filaments): return
        color = QColorDialog.getColor(QColor(j.filaments[idx].color), self, 'Barva filamentu')
        if color.isValid():
            # Změna zobrazeného odstínu není změna skladové položky.
            self._edit_filament(job_id, idx, 'color', color.name().upper())
            self._show_selected()

    def _price_mode_changed(self, _index: int):
        fixed = self.detail_price_mode.currentData() == 'fixed'
        self.detail_factor.setEnabled(not fixed)
        self.detail_fixed_price.setEnabled(fixed)
        if self._syncing: return
        job = self._selected_job()
        if job is None: return
        if fixed and job.fixed_unit_price == 0:
            # Zachovej nynější nabídkovou cenu jako počáteční pevnou částku.
            job.fixed_unit_price = round(job.totals(self.rates)['unit_price'], 2)
            self._syncing = True
            self.detail_fixed_price.setValue(job.fixed_unit_price)
            self._syncing = False
        self._edit_attr('price_mode', 'fixed' if fixed else 'coefficient')

    def _edit_attr(self, attr: str, value):
        if self._syncing: return
        j = self._selected_job()
        if j is None: return
        setattr(j, attr, value)
        self._mark_dirty()
        self._refresh_live()

    def _refresh_live(self):
        self._refresh_table()
        self._refresh_summary()
        self._refresh_costs()
        job = self._selected_job()
        if job:
            self.bar.set_filaments(job.filaments)
            for row, f in enumerate(job.filaments):
                if row < self.fil_table.rowCount():
                    item = self.fil_table.item(row, 5)
                    if item: item.setText(money(f.cost))
                    stock = stock_balances(self.jobs, self.rates.catalog).get(f.catalog_id) if f.catalog_id else None
                    remaining_cell = self.fil_table.item(row, 3)
                    if remaining_cell:
                        remaining_cell.setText(f"{stock['remaining']:.1f} g" if stock else '—')
                        remaining_cell.setForeground(QColor('#E16B56' if stock and stock['remaining'] < 0
                                                           else THEMES[self.rates.theme_name()]['text']))

    def _refresh_costs(self):
        j = self._selected_job()
        if not j: return
        totals = j.totals(self.rates)
        for key, widget in self.cost_labels.items(): widget.setText(money(totals[key]))
        note = '\n'.join('• ' + w for w in j.warnings)
        balances = stock_balances(self.jobs, self.rates.catalog)
        alerts = []
        for item in self.rates.catalog:
            code = str(item.get('csv_id', ''))
            info = balances.get(code) if code else None
            if info and info['used'] > 0:
                if info['remaining'] < 0:
                    alerts.append(f"NEDOSTATEK: {item.get('name','Filament')} – chybí {-info['remaining']:.1f} g "
                                  f"(na skladě {info['stock']:.1f} g).")
                elif j and any(f.catalog_id == code for f in j.filaments):
                    alerts.append(f"Sklad: {item.get('name','Filament')} – po zakázce zbude {info['remaining']:.1f} g.")
                if item.get('price_kg') is None and j and any(f.catalog_id == code for f in j.filaments):
                    alerts.append(f"CENA NENASTAVENA: {item.get('name','Filament')} – použitá výchozí sazba "
                                  f"{self.rates.default_price_kg:.2f} Kč/kg.")
        if alerts: note += ('\n' if note else '') + '\n'.join('• ' + alert for alert in alerts)
        note += ('\n' if note else '') + 'Stav skladu je informativní; import CSV jej aktualizuje. K fyzickému odpisu nedochází.'
        note += '\nSpotřeba a čas jsou hodnoty sliceru pro celou podložku; odpad se zvlášť nepřičítá.'
        self.warning_text.setText(note)

    def _pick_files(self):
        paths = choose_dialog(self, 'Vyber tiskové soubory z Bambu Studia', mode='files',
            file_filter='Tiskové soubory (*.gcode.3mf *.gcode *.gco *.3mf);;Všechny soubory (*)')
        if paths: self._import_paths(paths)

    def _pick_folder(self):
        chosen = choose_dialog(self, 'Vyber složku s tiskovými soubory', mode='directory')
        folder = chosen[0] if chosen else '' 
        if not folder: return
        paths = sorted(str(p) for p in Path(folder).rglob('*') if p.is_file()
                       and p.name.lower().endswith(('.gcode.3mf', '.gcode', '.gco')))
        if not paths:
            QMessageBox.information(self, 'Načtení složky', 'Ve složce nejsou žádné soubory .gcode.3mf nebo .gcode.')
            return
        if len(paths) > 500:
            QMessageBox.warning(self, 'Načtení složky', 'Složka má více než 500 G-code souborů. Vyber menší složku.')
            return
        self._import_paths(paths)

    def _import_paths(self, paths: list[str]):
        errors, count = [], 0
        for path in paths:
            try:
                found = parse_file(path, self.rates)
                for job in found: job.coefficient = self.global_factor.value()
                self.jobs.extend(found)
                count += len(found)
            except Exception as exc:
                errors.append(f'{Path(path).name}: {exc}')
        if count:
            self._mark_dirty()
            self._refresh_all()
            self.job_table.selectRow(len(self.jobs) - count)
            self._show_selected()
            self.statusBar().showMessage(f'Načteno {count} tisků.')
        if errors:
            QMessageBox.warning(self, 'Některé soubory nešlo načíst', '\n\n'.join(errors[:12]))

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls() and any(u.isLocalFile() for u in event.mimeData().urls()):
            event.acceptProposedAction()
        else: event.ignore()

    def dropEvent(self, event):
        files = [u.toLocalFile() for u in event.mimeData().urls() if u.isLocalFile()]
        if files: self._import_paths(files)
        event.acceptProposedAction()

    def _remove_selected(self):
        row = self.job_table.currentRow()
        if 0 <= row < len(self.jobs):
            self.jobs.pop(row)
            self._mark_dirty()
            self._refresh_all()
            if self.jobs: self.job_table.selectRow(min(row, len(self.jobs) - 1)); self._show_selected()

    def _add_filament(self):
        j = self._selected_job()
        if not j: return
        index = max([f.slot for f in j.filaments] + [0]) + 1
        j.filaments.append(Filament(index, 'PLA', '#A8B2C0', 0, price_kg=self.rates.default_price_kg))
        self._mark_dirty()
        self._show_selected()
        self._refresh_live()

    def _remove_filament(self):
        j = self._selected_job()
        idx = self.fil_table.currentRow()
        if j and 0 <= idx < len(j.filaments):
            j.filaments.pop(idx)
            self._mark_dirty()
            self._show_selected()
            self._refresh_live()

    def _apply_catalog(self):
        j = self._selected_job()
        if not j: return
        for f in j.filaments:
            named = next((item for item in self.rates.catalog if (f.catalog_id and
                           str(item.get('csv_id','')) == f.catalog_id) or
                          (not f.catalog_id and f.catalog_name and
                           item.get('name', '').casefold() == f.catalog_name.casefold() and
                           item.get('material', '').casefold() == f.material.casefold())), None)
            f.price_kg = (self.rates.default_price_kg if named.get('price_kg') is None else float(named['price_kg'])) if named else self.rates.lookup_price(f.material, f.color)
        self._mark_dirty()
        self._show_selected()
        self._refresh_live()

    def _save_catalog(self):
        j = self._selected_job()
        if not j: return
        for f in j.filaments:
            entry = next((x for x in self.rates.catalog if (f.catalog_id and str(x.get('csv_id', '')) == f.catalog_id)
                          or (not f.catalog_id and f.catalog_name and
                              x.get('name', '').casefold() == f.catalog_name.casefold()
                              and x.get('material', '').casefold() == f.material.casefold())), None)
            if entry is None:
                # Jestli existuje právě jedna přesná shoda typu a barvy,
                # uprav ji. Při více kandidátech raději vytvoř samostatný
                # pojmenovaný profil, ať se nepřepíše nesprávná cena.
                matches = [x for x in self.rates.catalog
                           if x.get('material', '').strip().casefold() == f.material.strip().casefold()
                           and x.get('color', '').upper() == f.color.upper()]
                entry = matches[0] if len(matches) == 1 else None
            if entry is None:
                new_name = f'{f.material} – {color_name(f.color)}'
                if any(x.get('name') == new_name for x in self.rates.catalog):
                    new_name += f' – {len(self.rates.catalog)+1}'
                self.rates.catalog.append(dict(name=new_name, material=f.material.strip(),
                                               color=f.color.upper(), price_kg=f.price_kg))
                f.catalog_name = new_name
            else:
                entry['price_kg'] = f.price_kg
                entry['price_is_custom'] = True
                f.catalog_name = entry.get('name','')
        save_rates(self.rates)
        self._mark_dirty()
        self._show_selected()
        self.statusBar().showMessage('Filamenty vybraného tisku jsou uložené v ceníku a dostupné ve výběru.')

    def _apply_factor(self):
        for j in self.jobs: j.coefficient = self.global_factor.value()
        if self.jobs: self._mark_dirty()
        self._show_selected()
        self._refresh_live()

    def _import_inventory_main(self):
        paths = choose_dialog(self, 'Importovat aktualizovaný sklad filamentů (CSV)',
                              mode='files', file_filter='CSV soubory (*.csv)')
        if not paths: return
        previous_by_id = {str(r.get('csv_id')): dict(r) for r in self.rates.catalog if r.get('csv_id')}
        try:
            catalog, stats = import_filament_csv(paths[0], self.rates.catalog)
        except (OSError, UnicodeError, ValueError, TypeError) as exc:
            QMessageBox.warning(self, 'Import skladu selhal', str(exc))
            return
        self.rates.catalog = catalog
        new_by_id = {str(r.get('csv_id')): r for r in catalog if r.get('csv_id')}
        # Aktualizovat již přiřazený odstín, pokud uživatel barvu tisku sám nezměnil.
        for job in self.jobs:
            for filament in job.filaments:
                old = previous_by_id.get(str(filament.catalog_id))
                updated = new_by_id.get(str(filament.catalog_id))
                if old and updated:
                    old_color = _approx_color(str(old.get('name','')), str(old.get('color','')))
                    if filament.color.upper() == old_color.upper():
                        filament.color = _approx_color(str(updated.get('name','')), str(updated.get('color','')))
                    filament.catalog_name = str(updated.get('name',''))
        save_rates(self.rates)
        self._mark_dirty()
        self._show_selected()
        self._refresh_live()
        QMessageBox.information(self, 'Sklad aktualizován',
            f"CSV načteno: {stats['count']} položek. Nových {stats['added']}, "
            f"aktualizovaných {stats['updated']}.\n"
            f"3D FOX Přeběh: {stats['overruns']} položek (200 Kč/kg při prvním importu).\n"
            'Ceny zadané dříve se zachovaly. Stav skladu je pouze orientační, tisk jej automaticky neodepisuje.')

    def _settings(self):
        dlg = SettingsDialog(self.rates, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.rates = dlg.rates
            save_rates(self.rates)
            self._set_theme()
            self._mark_dirty()
            self._refresh_live()
            self._show_selected()  # Obnovit nabídku ceníku materiálů.
            self.statusBar().showMessage('Nastavení uloženo. Ceny u už načtených filamentů zůstaly zachovány.')

    def _confirm_discard(self) -> bool:
        if not self.dirty: return True
        result = QMessageBox.question(self, 'Neuložené změny',
            'V zakázce jsou neuložené změny. Chceš je uložit?',
            QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Save)
        if result == QMessageBox.StandardButton.Cancel: return False
        if result == QMessageBox.StandardButton.Save: return self._save()
        return True

    def _new(self):
        if not self._confirm_discard(): return
        self.jobs.clear()
        self.project_path = None
        self.rates = load_rates()
        self._syncing = True
        self.project_title.setText('Nová zakázka')
        self.global_factor.setValue(self.rates.default_coefficient)
        self._syncing = False
        self.dirty = False
        self._refresh_all()
        self._window_title()

    def _open(self):
        if not self._confirm_discard(): return
        paths = choose_dialog(self, 'Otevřít uloženou zakázku', mode='files',
            file_filter='Zakázka kalkulačky (*.3dk.json);;JSON (*.json)')
        path = paths[0] if paths else '' 
        if not path: return
        try: title, rates, jobs = open_project(path)
        except (ValueError, OSError, TypeError, KeyError) as exc:
            QMessageBox.critical(self, 'Nelze načíst zakázku', str(exc))
            return
        current_inventory = load_rates().catalog
        if current_inventory:
            # Projekt nese historický snímek sazeb, sklad ale vždy patří aktuálnímu importu.
            rates.catalog = current_inventory
        self.rates, self.jobs, self.project_path = rates, jobs, Path(path)
        self._syncing = True
        self.project_title.setText(title)
        self.global_factor.setValue(rates.default_coefficient)
        self._syncing = False
        self.dirty = False
        self._set_theme()
        self._refresh_all()
        self._window_title()

    def _save(self) -> bool:
        path = self.project_path
        if path is None:
            suggested = suggested_project_filename(self.project_title.text())
            paths = choose_dialog(self, 'Uložit zakázku', mode='save',
                suggested=str(Path.home() / suggested),
                file_filter='Zakázka kalkulačky (*.3dk.json)')
            pathname = paths[0] if paths else '' 
            if not pathname: return False
            path = Path(pathname)
            if not path.name.endswith(PROJECT_EXT): path = path.with_name(path.name + PROJECT_EXT)
        try: save_project(path, self.project_title.text(), self.rates, self.jobs)
        except OSError as exc:
            QMessageBox.critical(self, 'Ukládání selhalo', str(exc))
            return False
        self.project_path = path
        self.dirty = False
        self._window_title()
        self.statusBar().showMessage(f'Zakázka uložena: {path}')
        return True

    def _export_csv(self):
        if not self.jobs:
            QMessageBox.information(self, 'Export CSV', 'Nejdříve přidej nějaký tisk.')
            return
        suggested = (self.project_title.text().strip() or 'zakazka').replace('/', '-') + '.csv'
        paths = choose_dialog(self, 'Export položek do CSV', mode='save',
            suggested=str(Path.home() / suggested), file_filter='CSV (*.csv)')
        path = paths[0] if paths else '' 
        if not path: return
        try:
            with open(path, 'w', newline='', encoding='utf-8-sig') as handle:
                writer = csv.writer(handle, delimiter=';')
                writer.writerow(['TISKY', 'Ks', 'Čas/h na tisk', 'Spotřeba/g na tisk', 'Náklady/Kč celkem', 'Způsob ceny', 'Koeficient / pevná cena na ks', 'Cena/Kč celkem', 'Rozdíl cena−náklady/Kč celkem'])
                for j in self.jobs:
                    total = j.totals(self.rates)
                    writer.writerow([j.name, j.quantity, f'{j.time_seconds/3600:.3f}'.replace('.', ','),
                                     f'{sum(f.grams for f in j.filaments):.2f}'.replace('.', ','),
                                     f'{total["base"]:.2f}'.replace('.', ','),
                                     'Pevná' if j.price_mode == 'fixed' else 'Koeficient',
                                     (f'{j.fixed_unit_price:.2f}' if j.price_mode == 'fixed' else f'{j.coefficient:.2f}').replace('.', ','),
                                     f'{total["price"]:.2f}'.replace('.', ','),
                                     f'{total["profit"]:.2f}'.replace('.', ',')])
                total = project_totals(self.jobs, self.rates)
                writer.writerow(['CELKEM', '', f'{total["seconds"]/3600:.3f}'.replace('.', ','),
                                 f'{total["grams"]:.2f}'.replace('.', ','),
                                 f'{total["base"]:.2f}'.replace('.', ','), '', '',
                                 f'{total["price"]:.2f}'.replace('.', ','),
                                     f'{total["profit"]:.2f}'.replace('.', ',')])
                writer.writerow([])
                writer.writerow(['FILAMENTY', 'Položka skladu', 'Materiál', 'Barva HEX', 'Spotřeba/g na tisk', 'Cena Kč/kg', 'Cena filamentu/Kč na tisk', 'Skladové ID', 'Zbývá po zakázce/g'])
                for j in self.jobs:
                    for f in j.filaments:
                        balance = stock_balances(self.jobs, self.rates.catalog).get(f.catalog_id) if f.catalog_id else None
                        writer.writerow([j.name, f.catalog_name or '', f.material, f.color,
                                         f'{f.grams:.2f}'.replace('.', ','),
                                         f'{f.price_kg:.2f}'.replace('.', ','),
                                         f'{f.cost:.2f}'.replace('.', ','), f.catalog_id,
                                         f"{balance['remaining']:.2f}".replace('.', ',') if balance else ''])
            self.statusBar().showMessage(f'CSV exportováno: {path}')
        except OSError as exc: QMessageBox.critical(self, 'Export CSV', str(exc))

    def _export_pdf(self):
        if not self.jobs:
            QMessageBox.information(self, 'Export PDF', 'Nejdříve přidej nějaký tisk.')
            return
        suggested = (self.project_title.text().strip() or 'zakazka').replace('/', '-') + '.pdf'
        paths = choose_dialog(self, 'Export tiskového protokolu', mode='save',
            suggested=str(Path.home() / suggested), file_filter='PDF (*.pdf)')
        path = paths[0] if paths else '' 
        if not path: return
        esc = html.escape
        totals = project_totals(self.jobs, self.rates)
        rows = []
        for j in self.jobs:
            amount = j.totals(self.rates)
            rows.append(f'<tr><td><b>{esc(j.name)}</b><br/><small>{esc(", ".join(j.objects))}</small></td>'
                        f'<td align="center">{j.quantity}</td><td align="right">{esc(human_duration(j.time_seconds))}</td>'
                        f'<td align="right">{sum(f.grams for f in j.filaments):.2f} g</td>'
                        f'<td align="right">{esc(money(amount["base"]))}</td>'
                        f'<td align="right"><b>{esc(money(amount["price"]))}</b>'
                        f'<br/><small>{"Pevná cena" if j.price_mode == "fixed" else "Koeficient "+str(j.coefficient)}'
                        f' / ks {esc(money(amount["unit_price"]))}</small></td>'
                        f'<td align="right">{esc(money(amount["profit"]))}</td></tr>')
            if j.filaments:
                detail = ' • '.join(f'<span style="color:{safe_hex(f.color)}">&#9679;</span> '
                                    f'{esc(f.catalog_name or f.material)} {esc(color_name(f.color))} {f.grams:.2f} g '
                                    f'({esc(money(f.cost))})' for f in j.filaments)
                rows.append(f'<tr><td colspan="7" style="background:#F4F7FA; color:#64748B; font-size:9pt">{detail}</td></tr>')
        doc_html = f'''<!doctype html><html><head><meta charset="UTF-8"/><style>
          body {{font-family: "DejaVu Sans", sans-serif; color:#172033; font-size:10pt;}}
          h1 {{color:#0E9470; font-size:19pt; margin-bottom:5px;}}
          h2 {{font-size:11pt; color:#64748B; margin-top:21px;}}
          table {{border-collapse:collapse; width:100%;}}
          th {{background:#E9F3F0; padding:7px; text-align:left; border-bottom:1px solid #B6C7C3;}}
          td {{padding:8px; border-bottom:1px solid #E2E8F0;}}
          .total {{background:#E8F6F1; padding:13px; margin-top:12px;}}
          .muted {{color:#64748B; font-size:9pt;}}
        </style></head><body>
          <h1>{esc(self.project_title.text() or "Kalkulace 3D tisku")}</h1>
          <p class="muted">Kalkulace 3D tisku • {esc(self.rates.printer_name)} •
             Vytvořeno v aplikaci 3D Kalkulačka</p>
          <h2>POLOŽKY ZAKÁZKY</h2>
          <table><tr><th>Tisk / objekty</th><th>Ks</th><th>Čas/ks</th><th>g/ks</th><th>Náklady</th><th>Cena</th><th>Rozdíl</th></tr>
          {''.join(rows)}</table>
          <h2>CELKOVÉ NÁKLADY</h2>
          <table><tr><td>Materiál</td><td align="right">{esc(money(totals['material']))}</td></tr>
          <tr><td>Amortizace</td><td align="right">{esc(money(totals['amort']))}</td></tr>
          <tr><td>Energie</td><td align="right">{esc(money(totals['energy']))}</td></tr>
          <tr><td>Ruční práce</td><td align="right">{esc(money(totals['labor']))}</td></tr>
          <tr><td>Další náklady</td><td align="right">{esc(money(totals['extra']))}</td></tr>
          <tr><td><b>Náklady dohromady</b></td><td align="right"><b>{esc(money(totals['base']))}</b></td></tr>
          <tr><td><b>Rozdíl cena − náklady</b></td><td align="right"><b>{esc(money(totals['profit']))}</b></td></tr></table>
          <p class="total"><b>VÝSLEDNÁ CENA ZAKÁZKY: {esc(money(totals['price']))}</b></p>
          <p class="muted">Čas a spotřeba vycházejí z exportu sliceru, pokud jsou v souboru dostupné.
          Celkový čas je součet tisků včetně zadaných kusů. Údaje o proplachování se znovu nepřičítají.
          Ruční práce a ostatní náklady jsou účtovány na jeden tisk. Ceny jsou orientační.</p>
          </body></html>'''
        try:
            printer = QPrinter(QPrinter.PrinterMode.HighResolution)
            printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
            printer.setOutputFileName(path)
            printer.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
            doc = QTextDocument()
            doc.setDefaultFont(QFont('DejaVu Sans', 10))
            doc.setHtml(doc_html)
            doc.print_(printer)
            self.statusBar().showMessage(f'PDF uloženo: {path}')
        except Exception as exc:
            QMessageBox.critical(self, 'Export PDF selhal', str(exc))

    def closeEvent(self, event):
        if self._confirm_discard(): event.accept()
        else: event.ignore()


def main():
    app = QApplication(sys.argv)
    app.setApplicationName('3D kalkulačka P2S')
    QLocale.setDefault(QLocale('cs_CZ'))
    app.setStyle('Fusion')
    window = MainWindow()
    window.show()
    for arg in sys.argv[1:]:
        if Path(arg).is_file():
            if arg.endswith(PROJECT_EXT):
                try:
                    title, rates, jobs = open_project(arg)
                    window.jobs, window.rates, window.project_path = jobs, rates, Path(arg)
                    window._syncing = True
                    window.project_title.setText(title)
                    window._syncing = False
                    window._set_theme()
                    window._refresh_all()
                    window._window_title()
                except Exception as exc: QMessageBox.warning(window, 'Načtení zakázky', str(exc))
            else: window._import_paths([arg])
    return app.exec()


if __name__ == '__main__':
    sys.exit(main())
