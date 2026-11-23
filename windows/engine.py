"""Datový model a čtečka Bambu Studio G-code / .gcode.3mf (bez dalších knihoven)."""
from __future__ import annotations

import base64
import colorsys
import csv
import io
import math
import os
import sys
import unicodedata
import json
import re
import uuid
import zipfile
from dataclasses import asdict, dataclass, field, fields
from datetime import datetime
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

APP_VERSION = '0.8.1'
PROJECT_EXT = '.3dk.json'


def suggested_project_filename(title: str) -> str:
    """Název souboru zakázky: ponechá českou diakritiku a mezery.

    Odstraní pouze znaky nepovolené v názvech souborů napříč systémy.
    Nemění název zakázky uvnitř JSON ani soubory již uložených zakázek.
    """
    title = unicodedata.normalize('NFC', str(title or ''))
    # Řídicí znaky a oddělovače cest nesmějí tvořit název souboru.
    title = re.sub(r'[\x00-\x1f\x7f<>:"/\\|?*]', '_', title)
    title = re.sub(r'\s+', ' ', title).strip(' .')
    # Ochrana před příliš dlouhými názvy.
    title = title[:120].rstrip(' .') or 'zakázka'
    if title.split('.')[0].casefold() in {
        'con', 'prn', 'aux', 'nul',
        *(f'com{i}' for i in range(1, 10)),
        *(f'lpt{i}' for i in range(1, 10)),
    }:
        title = '_' + title
    return title + PROJECT_EXT


def float_or(value: Any, default: float = 0.0) -> float:
    try:
        return float(str(value).strip().replace(',', '.'))
    except (TypeError, ValueError):
        return default


def safe_hex(value: str) -> str:
    value = (value or '').strip().upper()
    return value if re.fullmatch(r'#[A-F0-9]{6}', value) else '#737D91'


def color_name(value: str) -> str:
    """Zjednodušené české názvy barev; odstín zůstává uložen v HEX."""
    import colorsys
    value = safe_hex(value)
    r, g, b = (int(value[i:i+2], 16) / 255 for i in (1, 3, 5))
    h, s, v = colorsys.rgb_to_hsv(r, g, b)
    if v < .18: return 'Černá'
    if s < .13:
        if v > .90: return 'Bílá'
        return 'Šedá'
    hue = h * 360
    if hue < 15 or hue >= 345: return 'Červená'
    if hue < 43: return 'Oranžová'
    if hue < 71: return 'Žlutá'
    if hue < 168: return 'Zelená'
    if hue < 200: return 'Tyrkysová'
    if hue < 254: return 'Modrá'
    if hue < 291: return 'Fialová'
    if hue < 345: return 'Růžová'
    return 'Jiná'


def human_duration(seconds: float) -> str:
    s = max(0, int(round(seconds)))
    h, r = divmod(s, 3600)
    m, sec = divmod(r, 60)
    if h: return f'{h} h {m:02d} min'
    if m: return f'{m} min {sec:02d} s'
    return f'{sec} s'


def money(n: float) -> str:
    return f'{n:,.2f}'.replace(',', ' ').replace('.', ',') + ' Kč'


@dataclass
class Rates:
    printer_name: str = 'Bambu Lab P2S'
    amortization_per_hour: float = 10.0
    energy_mode: str = 'hourly'  # 'hourly' nebo 'power'
    energy_per_hour: float = 2.0
    power_watt: float = 100.0
    price_kwh: float = 6.0
    default_price_kg: float = 200.0
    default_coefficient: float = 1.5
    manual_hour_rate: float = 0.0
    catalog: list[dict[str, Any]] = field(default_factory=list)
    dark_mode: bool = True  # kompatibilita s v0.1
    theme: str = ''  # prázdné = převzít starou volbu dark_mode

    def __post_init__(self):
        # Převod staršího ceníku bez pojmenování na jednoznačné položky.
        # Díky tomu se v nabídce rozlišují i dva filamenty stejného typu.
        used: set[tuple[str, str]] = set()
        for entry in self.catalog:
            typ = str(entry.get('material', '')).strip() or 'Materiál'
            color = str(entry.get('color', '')).strip()
            base = str(entry.get('name', '')).strip()
            if not base:
                base = typ + (' – ' + color_name(color) if color else ' – obecný')
            name = base
            n = 2
            while (typ.casefold(), name.casefold()) in used:
                name = f'{base} ({n})'
                n += 1
            entry['name'] = name
            used.add((typ.casefold(), name.casefold()))

    def theme_name(self) -> str:
        return self.theme if self.theme in ('dark', 'light', 'hybrid', 'color') else ('dark' if self.dark_mode else 'light')

    def hourly_energy_cost(self) -> float:
        if self.energy_mode == 'power':
            return self.power_watt / 1000 * self.price_kwh
        return self.energy_per_hour

    def lookup_price(self, material: str, color: str) -> float:
        material = material.strip().casefold()
        color = safe_hex(color)
        for item in self.catalog:
            if str(item.get('material', '')).strip().casefold() == material and safe_hex(item.get('color', '')) == color and item.get('color', ''):
                return float_or(item.get('price_kg'), self.default_price_kg)
        for item in self.catalog:
            if str(item.get('material', '')).strip().casefold() == material and not item.get('color', ''):
                return float_or(item.get('price_kg'), self.default_price_kg)
        return self.default_price_kg



def _plain_search(text: str) -> str:
    # Kvůli různým variantám "Přeběh" a "Prebeh" bez ohledu na diakritiku.
    normalized = unicodedata.normalize('NFKD', text.casefold())
    return ''.join(c for c in normalized if not unicodedata.combining(c))



# Záměrně jednoduché offline pravidlo: barevný vzorek je orientační,
# nikoliv přesné určení pigmentu konkrétního výrobce. Hodnoty lze přepsat HEX.
# Specifické názvy mají přednost před obecnými, aby např. "armádní zelená"
# nezískala stejnou barvu jako obyčejná "zelená".
_SPECIFIC_SHADES: tuple[tuple[tuple[str, ...], str], ...] = (
    (("armadni", "khaki"), "#667453"),
    (("olivov", "olive"), "#778453"),
    (("lesni zelen", "forest green"), "#2D6547"),
    (("pistaci", "pistachio"), "#B4D18D"),
    (("limetk", "lime green"), "#BDE34D"),
    (("smaragd", "emerald"), "#168460"),
    (("matova zelen", "mint green", "mentol"), "#9ADCC0"),
    (("petrolej", "petrol blue"), "#337785"),
    (("tyrkys", "turquoise"), "#39B0B7"),
    (("nebesk", "sky blue"), "#82BDEA"),
    (("kralovska modr", "royal blue"), "#3358C4"),
    (("namornicka modr", "navy blue"), "#293C75"),
    (("levandul", "lavender"), "#B6A2D6"),
    (("fuchsi", "fuchsia"), "#D9439C"),
    (("lizatkov",), "#EE79B1"),
    (("bordo", "bordo", "vinov", "burgundy"), "#812B4C"),
    (("pudrov", "dusty pink"), "#D8B2B9"),
    (("staroruz",), "#BC829B"),
    (("mandarink", "tangerine"), "#F09C3D"),
    (("medena", "medeny", "copper"), "#B46C45"),
    (("bronz", "bronze"), "#A47A47"),
    (("stribr", "silver"), "#A8B2BB"),
    (("zlat", "gold"), "#D9AD43"),
    (("pastelove hned",), "#B6967B"),
    (("cokolad", "chocolate"), "#634632"),
    (("bezov", "beige", "kremov", "cream"), "#DBCAAD"),
    (("slonov", "ivory"), "#ECE3CA"),
    (("prirodn", "natural"), "#E8DEBF"),
    (("duhov", "rainbow"), "#9A9ECD"),
    (("glow zelen", "glow green"), "#A5E76B"),
    (("fosforescenc",), "#B4EA6A"),
    (("pruhledn", "transparent", "translucent"), "#DFE6E7"),
)
_BASE_SHADES: tuple[tuple[tuple[str, ...], str], ...] = (
    (("cern", "black"), "#24262B"),
    (("bil", "white"), "#F2F3F2"),
    (("sed", "siva", "gray", "grey"), "#999FA7"),
    (("cerven", "cerv", "red"), "#D64643"),
    (("oranz", "orange"), "#EE923A"),
    (("zlut", "yellow"), "#EECF37"),
    (("zelen", "green"), "#68AD72"),
    (("modr", "blue"), "#558DCD"),
    (("fial", "purple", "violet"), "#9065BB"),
    (("ruz", "pink"), "#EB8FB6"),
    (("hned", "brown"), "#927256"),
)


def approximate_filament_color(name: str, custom_hex: str = '') -> str:
    """Přibližná barva z českého/anglického názvu. Přesné ruční HEX má přednost.

    Výsledek je pouze vizualizace; sklad, cena ani typ materiálu se tím nemění.
    Neznámý název se označí neutrální šedou, nesnažíme se číst fotografie.
    """
    manual = str(custom_hex or '').strip().upper()
    if re.fullmatch(r'#[A-F0-9]{6}', manual):
        return manual
    words = _plain_search(str(name or ''))
    matched_specific = False
    result = '#87919D'  # Neznámý název – netvrdit, že známe barvu.
    for keys, color in _SPECIFIC_SHADES:
        if any(key in words for key in keys):
            result = color
            matched_specific = True
            break
    if not matched_specific:
        for keys, color in _BASE_SHADES:
            if any(key in words for key in keys):
                result = color
                break
    if matched_specific or result == '#87919D':
        return result

    # Obecný název barvy se modifikuje slovy tmavá/světlá/pastelová.
    # U ustálených specifických názvů (armádní, pistáciová…) jsou správné
    # odstíny zvoleny přímo výše a další modifikace se nepoužije.
    if any(mod in words for mod in ('tmav', 'dark', 'deep', 'temn')):
        light_delta = -0.19
    elif any(mod in words for mod in ('svetl', 'light', 'bled', 'pastel')):
        light_delta = 0.19
    else:
        light_delta = 0.0
    vivid = any(mod in words for mod in ('neon', 'zariv', 'fluorescen', 'vivid'))
    if not light_delta and not vivid:
        return result
    r, g, b = (int(result[i:i+2], 16) / 255.0 for i in (1, 3, 5))
    h, l, sat = colorsys.rgb_to_hls(r, g, b)
    l = max(.09, min(.93, l + light_delta))
    if 'pastel' in words:
        sat = min(sat, .48)
    if vivid:
        sat = max(sat, .86)
        l = max(l, .50)
    nr, ng, nb = colorsys.hls_to_rgb(h, l, sat)
    return '#' + ''.join(f'{round(v * 255):02X}' for v in (nr, ng, nb))


def fox_overrun(manufacturer: str, name: str, description: str = '') -> bool:
    maker = ''.join(c for c in _plain_search(manufacturer) if c.isalnum())
    return '3dfox' in maker and 'prebeh' in _plain_search(name + ' ' + description)


def import_filament_csv(path: str | Path, catalog: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, int]]:
    """Načte export uživatelovy evidence a přepíše stav podle stálého ID.

    Zachová dříve doplněné ceny. U nových položek 3D FOX Přeběh
    nastaví 200 Kč/kg; ostatní ceny zůstanou nepřiřazené.
    CSV není fyzický odpis ze skladu, pouze import aktuálního stavu.
    """
    p = Path(path)
    if p.stat().st_size > 15_000_000:
        raise ValueError('Soubor CSV je neobvykle velký (limit 15 MB).')
    raw = p.read_bytes()
    try:
        contents = raw.decode('utf-8-sig')
    except UnicodeDecodeError:
        contents = raw.decode('cp1250')
    if not contents.strip():
        raise ValueError('CSV je prázdné.')
    delimiter = ';' if contents.splitlines()[0].count(';') >= contents.splitlines()[0].count(',') else ','
    reader = csv.DictReader(io.StringIO(contents, newline=''), delimiter=delimiter)
    if not reader.fieldnames:
        raise ValueError('Chybí hlavička CSV.')
    required = {'ID', 'Název / barva', 'Materiál', 'Výrobce', 'Množství (g)'}
    actual = {str(k).strip() for k in reader.fieldnames}
    if not required.issubset(actual):
        raise ValueError('Nepodporovaný export CSV. Chybí sloupce: ' + ', '.join(sorted(required - actual)))
    result = [dict(item) for item in catalog]
    by_id = {str(item.get('csv_id')): item for item in result if item.get('csv_id')}
    new, updated, overrun, seen = 0, 0, 0, set()
    for row_number, raw_row in enumerate(reader, start=2):
        row = {str(k).strip(): (str(v).strip() if v is not None else '')
               for k, v in raw_row.items() if k is not None}
        if not any(row.values()):
            continue
        record_id = row.get('ID', '')
        if not record_id:
            raise ValueError(f'Řádek {row_number}: chybí ID filamentu.')
        if record_id in seen:
            raise ValueError(f'Řádek {row_number}: duplicitní ID {record_id}.')
        seen.add(record_id)
        name = row.get('Název / barva', '')
        material = row.get('Materiál', '')
        maker = row.get('Výrobce', '')
        if not name or not material:
            raise ValueError(f'Řádek {row_number}: chybí název nebo druh materiálu.')
        value = row.get('Množství (g)', '').replace(' ', '').replace('\u00a0','').replace(',', '.')
        try:
            grams = float(value)
        except ValueError:
            raise ValueError(f'Řádek {row_number}: neplatná zásoba {value!r}.') from None
        if not math.isfinite(grams) or grams < 0:
            raise ValueError(f'Řádek {row_number}: zásoba musí být nezáporné číslo.')
        is_overrun = fox_overrun(maker, name, row.get('Popis', ''))
        if is_overrun:
            overrun += 1
        item = by_id.get(record_id)
        if item is None:
            # Zachování případné ruční ceny stejného existujícího materiálu.
            matches = [x for x in result if not x.get('csv_id') and
                       x.get('name', '').strip().casefold() == name.casefold() and
                       x.get('material', '').strip().casefold() == material.casefold()]
            if len(matches) == 1:
                item = matches[0]
            else:
                item = {}
                result.append(item)
            new += 1
        else:
            updated += 1
        old_price = item.get('price_kg')
        # Webová evidence je primárním zdrojem barvy, pokud CSV obsahuje sloupec HEX barva.
        # Starší CSV bez tohoto sloupce zůstanou plně podporovaná.
        hex_columns = ('HEX barva', 'HEX', 'HEX kód')
        hex_column = next((col for col in hex_columns if col in row), None)
        csv_hex = row.get(hex_column, '').upper() if hex_column else None
        if csv_hex is not None and csv_hex and not re.fullmatch(r'#[0-9A-F]{6}', csv_hex):
            raise ValueError(f'Řádek {row_number}: chybný HEX kód {csv_hex!r}.')
        current_hex = item.get('color', '') if csv_hex is None else csv_hex
        item.update(csv_id=record_id, name=name, material=material, manufacturer=maker,
                    stock_grams=grams, date_changed=row.get('Datum změny', ''),
                    visibility=row.get('Viditelnost', ''), source='csv',
                    color=current_hex, color_source=('web-csv' if csv_hex else 'name'))
        if is_overrun and not item.get('price_is_custom'):
            # Automatická sazba platí i při opakovaném importu, pokud ji uživatel neupravil.
            item['price_kg'] = 200.0
        elif old_price is not None and str(old_price).strip() != '':
            item['price_kg'] = float_or(old_price)
        else:
            item['price_kg'] = None
        by_id[record_id] = item
    if not seen:
        raise ValueError('V CSV nejsou žádné filamenty.')
    return result, {'added': new, 'updated': updated, 'overruns': overrun, 'count': len(seen)}


def stock_balances(jobs: list['PrintJob'], catalog: list[dict[str, Any]]) -> dict[str, dict[str, float]]:
    """Výhled zásob po celé zakázce. Zdrojové CSV a sklad se NEMĚNÍ."""
    result = {str(item['csv_id']): {'stock': float_or(item.get('stock_grams')),
                                   'used': 0.0, 'remaining': float_or(item.get('stock_grams'))}
              for item in catalog if item.get('csv_id')}
    for j in jobs:
        for f in j.filaments:
            if f.catalog_id and f.catalog_id in result:
                result[f.catalog_id]['used'] += max(0.0, f.grams) * max(1, j.quantity)
    for entry in result.values():
        entry['remaining'] = entry['stock'] - entry['used']
    return result


@dataclass
class Filament:
    slot: int
    material: str
    color: str
    grams: float
    meters: float = 0.0
    price_kg: float = 200.0
    profile: str = ''
    catalog_name: str = ''  # volitelná výslovně zvolená položka ceníku
    catalog_id: str = ''  # stabilní ID skladové položky CSV; propojení se zásobami

    @property
    def cost(self) -> float:
        return max(0.0, self.grams) * max(0.0, self.price_kg) / 1000


@dataclass
class PrintJob:
    id: str
    name: str
    path: str
    plate: int
    objects: list[str]
    time_seconds: float
    filaments: list[Filament]
    printer: str = ''
    nozzle: str = ''
    layer_height: str = ''
    layers: int = 0
    switches: int = 0
    thumbnail_b64: str = ''
    warnings: list[str] = field(default_factory=list)
    quantity: int = 1
    coefficient: float = 1.5
    extra_cost: float = 0.0
    labor_minutes: float = 0.0
    model_time_seconds: float = 0.0
    price_mode: str = 'coefficient'  # 'coefficient' nebo 'fixed'
    fixed_unit_price: float = 0.0  # výsledná pevná cena jednoho tisku (Kč)

    def totals(self, rates: Rates) -> dict[str, float]:
        qty = max(1, self.quantity)
        hours = max(0.0, self.time_seconds) / 3600
        material = sum(f.cost for f in self.filaments)
        amort = hours * rates.amortization_per_hour
        energy = hours * rates.hourly_energy_cost()
        labor = max(0.0, self.labor_minutes) / 60 * rates.manual_hour_rate
        extra = max(0.0, self.extra_cost)
        base = material + amort + energy + labor + extra
        unit_price = (max(0.0, self.fixed_unit_price) if self.price_mode == 'fixed'
                      else base * max(1.0, self.coefficient))
        return dict(grams=sum(max(0.0, f.grams) for f in self.filaments) * qty,
                    seconds=max(0.0, self.time_seconds) * qty,
                    material=material * qty, amort=amort * qty,
                    energy=energy * qty, labor=labor * qty, extra=extra * qty,
                    base=base * qty, price=unit_price * qty,
                    profit=(unit_price - base) * qty,
                    unit_base=base, unit_price=unit_price)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, obj: dict[str, Any]) -> 'PrintJob':
        allowed = {f.name for f in fields(cls)}
        values = {k: v for k, v in obj.items() if k in allowed}
        values['filaments'] = [Filament(**{k: v for k, v in f.items() if k in {x.name for x in fields(Filament)}})
                               for f in obj.get('filaments', [])]
        return cls(**values)


def default_config_path() -> Path:
    # Na Windows respektuje standardní uživatelské nastavení (Roaming AppData).
    # Na Linuxu ponecháváme původní umístění kvůli kompatibilitě nastavení.
    if sys.platform == 'win32':
        appdata = os.environ.get('APPDATA')
        root = Path(appdata) if appdata else Path.home() / 'AppData' / 'Roaming'
        return root / '3d-kalkulacka-p2s' / 'settings.json'
    return Path.home() / '.config' / '3d-kalkulacka-p2s' / 'settings.json'


def load_rates() -> Rates:
    path = default_config_path()
    if not path.exists(): return Rates()
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
        return Rates(**{key: value for key, value in data.items() if key in {f.name for f in fields(Rates)}})
    except (ValueError, OSError, TypeError):
        return Rates()


def save_rates(rates: Rates) -> None:
    path = default_config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix('.tmp')
    tmp.write_text(json.dumps(asdict(rates), ensure_ascii=False, indent=2), encoding='utf-8')
    tmp.replace(path)


def save_project(path: str | Path, title: str, rates: Rates, jobs: list[PrintJob]) -> None:
    data = {'format': '3dk-p2s', 'version': 1, 'saved_at': datetime.now().isoformat(timespec='seconds'),
            'title': title, 'rates': asdict(rates), 'jobs': [j.to_dict() for j in jobs]}
    p = Path(path)
    tmp = p.with_name(p.name + '.tmp')
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    tmp.replace(p)


def open_project(path: str | Path) -> tuple[str, Rates, list[PrintJob]]:
    obj = json.loads(Path(path).read_text(encoding='utf-8'))
    if obj.get('format') != '3dk-p2s' or obj.get('version') != 1:
        raise ValueError('Neznámý formát souboru zakázky.')
    rates = Rates(**{k: v for k, v in obj['rates'].items() if k in {f.name for f in fields(Rates)}})
    return obj.get('title', 'Nová zakázka'), rates, [PrintJob.from_dict(j) for j in obj.get('jobs', [])]


def _gcode_header(text: str) -> dict[str, Any]:
    def get_list(pattern: str) -> list[str]:
        m = re.search(pattern, text, flags=re.I | re.M)
        if not m: return []
        return [x.strip().strip('"') for x in re.split(r'[;,]', m.group(1)) if x.strip()]

    data: dict[str, Any] = {}
    line = re.search(r';\s*model printing time:\s*([^;\r\n]+);\s*total estimated time:\s*([^;\r\n]+)', text, re.I)
    if line:
        data['model_time'] = _parse_duration(line.group(1))
        data['time'] = _parse_duration(line.group(2))
    # Starší Bambu/Prusa profily mohou zapisovat přímo sekundy.
    if not data.get('time'):
        m = re.search(r';\s*estimated printing time[^:\n]*:\s*(\d+h[^\r\n]*|\d+m[^\r\n]*|\d+s)', text, re.I)
        if m: data['time'] = _parse_duration(m.group(1))
    data['weights'] = [float_or(v) for v in get_list(r';\s*total filament weight \[g\]\s*:\s*([^\r\n]+)')]
    data['meters'] = [float_or(v) / 1000 for v in get_list(r';\s*total filament length \[mm\]\s*:\s*([^\r\n]+)')]
    # Bambu komentáře: barevné profily mohou být v hlavičce i na konci.
    data['types'] = get_list(r';\s*filament_type\s*=\s*([^\r\n]+)')
    data['colors'] = get_list(r';\s*filament_colour\s*=\s*([^\r\n]+)')
    m = re.search(r';\s*total layer number:\s*(\d+)', text, re.I)
    data['layers'] = int(m.group(1)) if m else 0
    m = re.search(r';\s*layer_height\s*=\s*([0-9.,]+)', text, re.I)
    data['layer_height'] = m.group(1) if m else ''
    return data


def _parse_duration(text: str) -> float:
    secs = 0
    for num, unit in re.findall(r'(\d+(?:[.,]\d+)?)\s*([hms])\b', text, flags=re.I):
        secs += float_or(num) * {'h': 3600, 'm': 60, 's': 1}[unit.lower()]
    return secs


def _get_zip_head(z: zipfile.ZipFile, name: str, limit: int = 1_500_000) -> str:
    with z.open(name) as f:
        return f.read(limit).decode('utf-8-sig', 'replace')


def _xml_meta(node: ET.Element) -> dict[str, str]:
    return {child.attrib.get('key', ''): child.attrib.get('value', '')
            for child in node.findall('./metadata')}


def _project_settings(z: zipfile.ZipFile) -> dict[str, Any]:
    name = 'Metadata/project_settings.config'
    if name not in z.namelist(): return {}
    try:
        raw = z.read(name)
        if len(raw) > 4_000_000: return {}
        return json.loads(raw.decode('utf-8-sig'))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return {}


def _filament_profiles(settings: dict[str, Any]) -> list[str]:
    candidates = settings.get('filament_settings_id') or []
    return candidates if isinstance(candidates, list) else []


def _make_filaments(plate: ET.Element | None, meta: dict[str, Any], settings: dict[str, Any], rates: Rates) -> list[Filament]:
    out = []
    profiles = _filament_profiles(settings)
    if plate is not None:
        for el in plate.findall('filament'):
            grams = float_or(el.attrib.get('used_g'))
            if grams <= 0: continue  # Profil připravený, ale nepoužitý.
            slot = int(el.attrib.get('id', len(out) + 1))
            material = el.attrib.get('type', 'Neurčeno') or 'Neurčeno'
            color = safe_hex(el.attrib.get('color', ''))
            profile = profiles[slot - 1] if 0 < slot <= len(profiles) else ''
            out.append(Filament(slot, material, color, grams, float_or(el.attrib.get('used_m')),
                                rates.lookup_price(material, color), profile))
    if out: return out
    types = meta.get('types') or settings.get('filament_type') or []
    colors = meta.get('colors') or settings.get('filament_colour') or []
    weights = meta.get('weights') or []
    if not isinstance(types, list): types = []
    if not isinstance(colors, list): colors = []
    for i, grams in enumerate(weights):
        if grams <= 0: continue
        material = types[i] if i < len(types) else 'Neurčeno'
        color = safe_hex(colors[i] if i < len(colors) else '')
        out.append(Filament(i + 1, material, color, grams,
                            (meta.get('meters') or [])[i] if i < len(meta.get('meters') or []) else 0,
                            rates.lookup_price(material, color), profiles[i] if i < len(profiles) else ''))
    return out


def _sequence_switches(z: zipfile.ZipFile, plate: int) -> int:
    try:
        data = json.loads(z.read('Metadata/filament_sequence.json'))
        seq = data.get(f'plate_{plate}', {}).get('sequence', [])
        return sum(seq[i] != seq[i-1] for i in range(1, len(seq)))
    except (KeyError, ValueError, TypeError): return 0


def parse_3mf(path: str | Path, rates: Rates) -> list[PrintJob]:
    path = Path(path)
    with zipfile.ZipFile(path) as z:
        if 'Metadata/slice_info.config' not in z.namelist() and not any(re.fullmatch(r'Metadata/plate_\d+\.gcode', n) for n in z.namelist()):
            raise ValueError('Soubor neobsahuje naslicované G-code. V Bambu Studiu použij Export plate sliced file (.gcode.3mf).')
        plates: list[ET.Element] = []
        if 'Metadata/slice_info.config' in z.namelist():
            xml = z.read('Metadata/slice_info.config')
            plates = ET.fromstring(xml).findall('plate')
        lookup: dict[int, ET.Element] = {}
        for i, plate in enumerate(plates, start=1):
            info = _xml_meta(plate)
            idx = int(info.get('index', i))
            lookup[idx] = plate
        if not lookup:
            indices = [int(re.search(r'plate_(\d+)\.gcode', name).group(1)) for name in z.namelist() if re.fullmatch(r'Metadata/plate_\d+\.gcode', name)]
            lookup = {idx: None for idx in indices}
        project_settings = _project_settings(z)
        result = []
        for plate_num, plate in sorted(lookup.items()):
            info = _xml_meta(plate) if plate is not None else {}
            gname = f'Metadata/plate_{plate_num}.gcode'
            if gname not in z.namelist(): continue
            header = _gcode_header(_get_zip_head(z, gname))
            seconds = float_or(info.get('prediction')) or header.get('time', 0)
            filaments = _make_filaments(plate, header, project_settings, rates)
            weight = float_or(info.get('weight'))
            notes = []
            if not filaments and weight > 0:
                filaments = [Filament(1, 'Neurčeno', '#737D91', weight, price_kg=rates.default_price_kg)]
                notes.append('Typ a barvu filamentu se nepodařilo určit. Zkontroluj je ručně.')
            if not filaments: notes.append('Ve zdrojovém souboru nebyla nalezena spotřeba filamentu. Doplň ji ručně.')
            if not seconds: notes.append('V souboru není odhad času tisku. Doplň jej ručně.')
            if weight and filaments and abs(sum(f.grams for f in filaments) - weight) > max(.5, weight * .05):
                notes.append('Součet hmotností filamentů se liší od celkového údaje sliceru. Ověř spotřebu.')
            names = [el.attrib.get('name', '') for el in plate.findall('object')] if plate is not None else []
            names = [n for n in names if n]
            thumb_name = f'Metadata/plate_{plate_num}_small.png'
            if thumb_name not in z.namelist(): thumb_name = f'Metadata/plate_{plate_num}.png'
            thumb = ''
            if thumb_name in z.namelist() and z.getinfo(thumb_name).file_size < 2_000_000:
                thumb = base64.b64encode(z.read(thumb_name)).decode('ascii')
            nm = re.sub(r'\.gcode\.3mf$|\.3mf$', '', path.name, flags=re.I)
            if len(lookup) > 1: nm += f' – podložka {plate_num}'
            result.append(PrintJob(
                id=uuid.uuid4().hex, name=nm, path=str(path), plate=plate_num, objects=names,
                time_seconds=seconds, filaments=filaments, printer=rates.printer_name,
                nozzle=info.get('nozzle_diameters') or header.get('nozzle', ''),
                layer_height=str(project_settings.get('layer_height') or header.get('layer_height') or ''),
                layers=header.get('layers', 0), switches=_sequence_switches(z, plate_num),
                thumbnail_b64=thumb, warnings=notes, coefficient=rates.default_coefficient,
                model_time_seconds=header.get('model_time', 0)))
        if not result: raise ValueError('V archivu není žádná podložka s tiskovým G-codem.')
        return result


def parse_plain_gcode(path: str | Path, rates: Rates) -> list[PrintJob]:
    path = Path(path)
    with path.open('rb') as f:
        head = f.read(1_500_000)
        if path.stat().st_size > 1_500_000:
            f.seek(max(0, path.stat().st_size - 500_000))
            tail = f.read(500_000)
        else:
            tail = b''
    meta = _gcode_header(head.decode('utf-8-sig', 'replace') + '\n' + tail.decode('utf-8', 'replace'))
    filaments = _make_filaments(None, meta, {}, rates)
    seconds = meta.get('time', 0)
    warnings = []
    if not seconds: warnings.append('G-code neobsahuje odhad tiskového času. Doplň jej ručně.')
    if not filaments: warnings.append('G-code neobsahuje spotřebu filamentu. Doplň ji ručně.')
    return [PrintJob(id=uuid.uuid4().hex, name=path.stem, path=str(path), plate=1, objects=[],
                     time_seconds=seconds, filaments=filaments, printer=rates.printer_name,
                     layer_height=meta.get('layer_height', ''), layers=meta.get('layers', 0),
                     model_time_seconds=meta.get('model_time', 0),
                     warnings=warnings, coefficient=rates.default_coefficient)]


def parse_file(path: str | Path, rates: Rates) -> list[PrintJob]:
    path = Path(path)
    if not path.is_file(): raise FileNotFoundError(path)
    if path.name.lower().endswith(('.gcode.3mf', '.3mf')):
        return parse_3mf(path, rates)
    if path.name.lower().endswith(('.gcode', '.gco')):
        return parse_plain_gcode(path, rates)
    raise ValueError('Podporované soubory: .gcode.3mf, .gcode, .gco')


def project_totals(jobs: list[PrintJob], rates: Rates) -> dict[str, float]:
    keys = ('grams', 'seconds', 'material', 'amort', 'energy', 'labor', 'extra', 'base', 'price', 'profit')
    return {key: sum(job.totals(rates)[key] for job in jobs) for key in keys}
