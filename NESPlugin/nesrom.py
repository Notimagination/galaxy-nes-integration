"""Reading NES / Famicom files: which GamesDB IDs (CRC32) identify them, and readable titles from file names."""
import hashlib
import logging
import os
import re
import unicodedata
import zipfile
import zlib
from dataclasses import dataclass
from typing import Tuple

NAME_ID_PREFIX = "NES-NAME-"

# Everything Mesen 2 can open. .zip is read here; .7z cannot be read, so it is identified by name only.
DEFAULT_EXTENSIONS = (".nes", ".fds", ".qd", ".unf", ".unif", ".studybox", ".nsf", ".nsfe", ".zip", ".7z")
ROM_EXTENSIONS = frozenset(DEFAULT_EXTENSIONS) - {".zip", ".7z"}
MAX_ROM_BYTES = 32 * 1024 * 1024   # real NES files are far below this; bigger files are identified by name

_ARTICLES = r"The|A|An|Le|La|Les|El|Los|Las|Der|Die|Das|Il"
_ARTICLE_RE = re.compile(r"^(?P<main>.+?), (?P<article>%s)(?P<rest> - .*)?$" % _ARTICLES, re.I)
_TAG_RE = re.compile(r"\(([^()]*)\)|\[([^\[\]]*)\]")


@dataclass
class RomInfo:
    ids: Tuple[str, ...] = ()   # candidate GamesDB IDs, best first (8 upper-case hex digits); empty = unreadable
    kind: str = "name"          # ines | unif | fds | raw | zip | name


def parse_extensions(value):
    """The extension list from config.ini; an empty or missing value means 'all supported'."""
    result = []
    for part in (value or "").replace(";", ",").split(","):
        ext = part.strip().lower()
        if ext:
            result.append(ext if ext.startswith(".") else "." + ext)
    return tuple(result) or DEFAULT_EXTENSIONS


def _crc(*chunks):
    value = 0
    for chunk in chunks:
        value = zlib.crc32(chunk, value)
    return "%08X" % (value & 0xFFFFFFFF)


def _size_field(low, high_nibble, unit):
    """NES 2.0 ROM size: plain count of units, or the exponent form when the high nibble is 0xF."""
    if high_nibble == 0xF:
        return (1 << (low >> 2)) * ((low & 3) * 2 + 1)
    return (low | (high_nibble << 8)) * unit


def _ines_ids(data):
    """iNES / NES 2.0: PRG+CHR without header and trainer is the ID databases use; others are fallbacks."""
    flags6, flags7 = data[6], data[7]
    start = 16 + (512 if flags6 & 0x04 else 0)
    if (flags7 & 0x0C) == 0x08:     # NES 2.0
        prg = _size_field(data[4], data[9] & 0x0F, 16384)
        chr_ = _size_field(data[5], data[9] >> 4, 8192)
    else:
        prg, chr_ = data[4] * 16384, data[5] * 8192
    body = data[start:start + prg + chr_]
    return [_crc(body), _crc(data), _crc(data[16:]), _crc(data[start:start + prg])]


def _unif_ids(data):
    prg, chr_, pos = [], [], 32
    while pos + 8 <= len(data):
        tag = data[pos:pos + 4]
        size = int.from_bytes(data[pos + 4:pos + 8], "little")
        chunk = data[pos + 8:pos + 8 + size]
        if tag.startswith(b"PRG"):
            prg.append((tag, chunk))
        elif tag.startswith(b"CHR"):
            chr_.append((tag, chunk))
        pos += 8 + size
    rom = [c for _t, c in sorted(prg)] + [c for _t, c in sorted(chr_)]
    return ([_crc(*rom)] if rom else []) + [_crc(data)]


def identify_bytes(data):
    """Candidate IDs for the contents of one ROM file."""
    ids, kind = [], "raw"
    try:
        if data[:4] == b"NES\x1a" and len(data) >= 16:
            ids, kind = _ines_ids(data), "ines"
        elif data[:4] == b"UNIF" and len(data) >= 32:
            ids, kind = _unif_ids(data), "unif"
        elif data[:4] == b"FDS\x1a" and len(data) >= 16:
            ids, kind = [_crc(data[16:]), _crc(data)], "fds"
    except (IndexError, ValueError):
        ids = []
    if not ids:
        ids, kind = [_crc(data)], "raw"
    return RomInfo(tuple(dict.fromkeys(ids)), kind)


def _identify_zip(path):
    """RomInfo for the first NES file inside a zip, None when the zip holds no NES file."""
    with zipfile.ZipFile(path) as archive:
        entries = sorted(
            (i for i in archive.infolist()
             if not i.is_dir() and os.path.splitext(i.filename)[1].lower() in ROM_EXTENSIONS),
            key=lambda i: i.filename.casefold(),
        )
        if not entries:
            return None
        entry = entries[0]
        if entry.file_size > MAX_ROM_BYTES:
            return RomInfo(("%08X" % entry.CRC,), "zip")     # the zip already stores the CRC32 of the whole file
        info = identify_bytes(archive.read(entry))
    return RomInfo(info.ids, "zip")


def identify_file(path):
    """RomInfo for a file on disk. Never raises. Returns None for a .zip without any NES file inside."""
    extension = os.path.splitext(path)[1].lower()
    try:
        if extension == ".zip":
            return _identify_zip(path)
        if extension == ".7z":
            return RomInfo()
        if os.path.getsize(path) > MAX_ROM_BYTES:
            return RomInfo()
        with open(path, "rb") as fh:
            return identify_bytes(fh.read())
    except (OSError, zipfile.BadZipFile, RuntimeError, NotImplementedError, EOFError, zlib.error) as exc:
        logging.warning("DEV: NES file could not be read - %s (%s)", path, exc)
        # A broken or password-protected zip still gets a library entry (by name); other files too.
        return RomInfo()


# ---- names ---------------------------------------------------------------------------------------
def file_tags(filename):
    """The (...) and [...] groups of a file name, e.g. ['USA', 'Rev 1']."""
    return [(a or b).strip() for a, b in _TAG_RE.findall(os.path.basename(filename)) if (a or b).strip()]


def display_title(filename):
    """File name -> readable title: no extension or (region)/[dump] tags, 'Zelda, The' -> 'The Zelda'."""
    stem = os.path.basename(filename)
    dot = stem.rfind(".")        # titles can contain periods, so only the last one is the extension
    if dot > 0:
        stem = stem[:dot]
    cleaned = _TAG_RE.sub(" ", stem).replace("_", " ")
    cleaned = re.sub(r"\s{2,}", " ", cleaned).strip(" -_,")
    match = _ARTICLE_RE.match(cleaned)
    if match:
        article = match.group("article")
        article = article[0].upper() + article[1:].lower() if article.isupper() or article.islower() else article
        cleaned = "%s %s%s" % (article, match.group("main"), match.group("rest") or "")
    return cleaned or os.path.splitext(os.path.basename(filename))[0] or os.path.basename(filename)


def normalize_title(value):
    value = unicodedata.normalize("NFKD", value or "")
    value = "".join(ch for ch in value if not unicodedata.combining(ch)).casefold()
    return re.sub(r"[^\w]+", " ", value, flags=re.UNICODE).strip()


def name_game_id(title):
    """Stable ID for files that cannot be read (7z, damaged, oversized)."""
    digest = hashlib.sha1(normalize_title(title).encode("utf-8")).hexdigest()[:16].upper()
    return NAME_ID_PREFIX + digest


def disambiguate(games):
    """Games sharing one title get their file tag appended, e.g. 'Super Mario Bros. (Europe)'."""
    groups = {}
    for game in games:
        groups.setdefault(game.name.casefold(), []).append(game)
    for group in groups.values():
        if len(group) < 2:
            continue
        for game in group:
            tags = file_tags(game.path)
            if tags:
                game.name = "%s (%s)" % (game.name, tags[0])
