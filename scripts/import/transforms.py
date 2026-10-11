"""Pure value transforms of the Vtiger import (stage 06.2, docs/migration/import.md). No I/O; errors carry codes
and identifiers only, never source values.

- D-30: DATETIME of Vtiger → UTC by epochs (Europe/Moscow before 2022-11-01, Europe/Berlin before 2026-06-13, UTC
  after); TIMESTAMP columns are already UTC (the snapshot restores them in UTC); date-only values are not shifted.
- Phones (owner's answer 2026-10-11): only unambiguous values are normalised to E.164; the rest stay as in the source.
- Value dictionaries: metadata/vtigerValueMap/<Entity>.json (D-38), keyed by "<Module>.<picklist>".
"""
import datetime as dt
import json
import re
from decimal import Decimal, InvalidOperation
from pathlib import Path
from zoneinfo import ZoneInfo

REPO = Path(__file__).resolve().parents[2]
VALUE_MAP_DIR = REPO / "custom/Espo/Modules/Itvolga/Resources/metadata/vtigerValueMap"

UTC = dt.timezone.utc
EPOCHS = (  # (local start inclusive, zone) — D-30
    (dt.datetime(2026, 6, 13), UTC),
    (dt.datetime(2022, 11, 1), ZoneInfo("Europe/Berlin")),
    (dt.datetime.min, ZoneInfo("Europe/Moscow")),
)
DATETIME_RE = re.compile(r"^(\d{4})-(\d{2})-(\d{2}) (\d{2}):(\d{2}):(\d{2})(?:\.\d+)?$")
DATE_RE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})$")
TIME_RE = re.compile(r"^(\d{1,2}):(\d{2})(?::(\d{2}))?$")
TRUE_VALUES = ("1", "on", "yes")


class TransformError(Exception):
    """A value that cannot be converted without guessing. `code` is a closed identifier, never a value."""

    def __init__(self, code):
        super().__init__(code)
        self.code = code


def is_empty(value):
    """Non-empty as the audit counts it (gen_sql.nonempty_expr): SQL TRIM removes spaces only; zero dates are empty."""
    return value is None or value.strip(" ") == "" or value.startswith("0000-00-00")


# --- dates ----------------------------------------------------------------------------------------

def date_only(value):
    if is_empty(value):
        return None
    if not DATE_RE.match(value[:10]) or (len(value) > 10 and not DATETIME_RE.match(value)):
        raise TransformError("bad_date")
    dt.date.fromisoformat(value[:10])
    return value[:10]


def local_datetime(value):
    if is_empty(value):
        return None
    m = DATETIME_RE.match(value)
    if not m:
        raise TransformError("bad_datetime")
    return dt.datetime(*map(int, m.groups()))


def combine(date_value, time_value):
    """Vtiger keeps the activity start/end as a date column plus a varchar time ('HH:MM' or 'HH:MM:SS')."""
    if is_empty(date_value):
        return None
    day = dt.date.fromisoformat(date_only(date_value))
    if is_empty(time_value):
        return None
    m = TIME_RE.match(time_value.strip())
    if not m:
        raise TransformError("bad_time")
    h, mi, s = int(m.group(1)), int(m.group(2)), int(m.group(3) or 0)
    if h > 23 or mi > 59 or s > 59:
        raise TransformError("bad_time")
    return dt.datetime(day.year, day.month, day.day, h, mi, s)


def to_utc(local, flags=None):
    """D-30: a naive local datetime of Vtiger → 'YYYY-MM-DD HH:MM:SS' in UTC. A local time that does not exist
    (DST gap) or exists twice (DST fold) is converted deterministically (zoneinfo, fold=0) and counted in `flags`."""
    if local is None:
        return None
    zone = next(z for start, z in EPOCHS if local >= start)
    if zone is not UTC:
        aware = local.replace(tzinfo=zone)
        back = aware.astimezone(UTC).astimezone(zone).replace(tzinfo=None)
        if flags is not None:
            if back != local:
                flags["dst_gap"] = flags.get("dst_gap", 0) + 1
            elif aware.utcoffset() != local.replace(tzinfo=zone, fold=1).utcoffset():
                flags["dst_fold"] = flags.get("dst_fold", 0) + 1
        local = aware.astimezone(UTC).replace(tzinfo=None)
    return local.strftime("%Y-%m-%d %H:%M:%S")


INSTALLATION_TZ = ZoneInfo("Europe/Moscow")  # D-37: time zone of the EspoCRM installation


def all_day_end(date_value):
    """dateEnd that EspoCRM derives from an all-day end date (Core Event repository): the next local midnight of
    the installation, in UTC. Owned explicitly, so the import and the core agree on it."""
    if date_value is None:
        return None
    day = dt.date.fromisoformat(date_value) + dt.timedelta(days=1)
    return dt.datetime(day.year, day.month, day.day, tzinfo=INSTALLATION_TZ).astimezone(UTC).strftime("%Y-%m-%d %H:%M:%S")


def vt_datetime(value, flags=None):
    return to_utc(local_datetime(value), flags)


def utc_timestamp(value):
    """A TIMESTAMP column restored in UTC: no epoch shift."""
    return None if is_empty(value) else local_datetime(value).strftime("%Y-%m-%d %H:%M:%S")


# --- scalars --------------------------------------------------------------------------------------

def text(value):
    """Text as is; only fully blank values (as the audit counts them) become empty."""
    return None if is_empty(value) else value


def string(value):
    return None if is_empty(value) else value.strip()


def integer(value, zero_is_empty=False):
    if is_empty(value):
        return None
    try:
        number = int(value)
    except ValueError:
        raise TransformError("bad_int") from None
    return None if zero_is_empty and number == 0 else number


def decimal(value, scale, zero_is_empty=False):
    """Decimal string with at most `scale` fractional digits (no float, no rounding: more digits is an error)."""
    if is_empty(value):
        return None
    try:
        number = Decimal(value.strip())
    except InvalidOperation:
        raise TransformError("bad_decimal") from None
    if not number.is_finite():
        raise TransformError("bad_decimal")
    if zero_is_empty and number == 0:
        return None
    if number != number.quantize(Decimal(1).scaleb(-scale)):
        raise TransformError("decimal_scale")
    return format(number.quantize(Decimal(1).scaleb(-scale)), "f")


def checkbox(value):
    """Vtiger checkbox (uitype 56): '1'/'on'/'yes' → True, '0'/'' → False, NULL → None."""
    if value is None:
        return None
    return value.strip(" ").lower() in TRUE_VALUES


# --- phones and e-mails ---------------------------------------------------------------------------

MULTI_RE = re.compile(r"[,;/]|доб|ext|\bд\.", re.IGNORECASE)


def phone(value):
    """→ (number to store, class). Classes: ru11 / ru10 / plus (normalised); local / short / multi / other (kept)."""
    if is_empty(value):
        return None, None
    raw = value.strip()
    digits = re.sub(r"\D", "", raw)
    if MULTI_RE.search(raw):
        return raw, "multi"
    if raw.startswith("+"):
        if digits.startswith("7") and len(digits) == 11:
            return "+" + digits, "ru11"
        return ("+" + digits, "plus") if 7 <= len(digits) <= 15 else (raw, "other")
    if len(digits) == 11 and digits[0] in "78":
        return "+7" + digits[1:], "ru11"
    if len(digits) == 10 and digits[0] in "3489":
        return "+7" + digits, "ru10"
    if 5 <= len(digits) <= 7:
        return raw, "local"
    if 1 <= len(digits) <= 4:
        return raw, "short"
    return raw, "other"


def email(value):
    if is_empty(value):
        return None
    return value.strip().lower()


# --- value dictionaries (D-38) --------------------------------------------------------------------

class ValueMaps:
    def __init__(self, directory=VALUE_MAP_DIR):
        self.maps = {p.stem: json.loads(p.read_text(encoding="utf-8")) for p in Path(directory).glob("*.json")}

    def lookup(self, entity, field, source_key, value):
        """→ target key; '' and NULL stay empty (None). An unknown value is an error, never a guess."""
        if value is None or value == "":
            return None
        spec = self.maps[entity]["fields"][field]["map"]
        for key in (source_key, "(picklist)"):
            if key in spec and value in spec[key]:
                return spec[key][value] or None
        raise TransformError("enum_unmapped")

    def has(self, entity, field, source_key):
        return source_key in self.maps.get(entity, {}).get("fields", {}).get(field, {}).get("map", {})
