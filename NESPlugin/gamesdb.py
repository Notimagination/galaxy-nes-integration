"""Official NES names from GOG's public game database (GamesDB), cached on disk.

Galaxy finds covers and descriptions through the same database, keyed by the ID the plugin reports
(for NES: the ROM's CRC32). Network trouble never removes games or changes their IDs.
"""
import json
import logging
import os
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

import config
from version import __version__

URL = "https://gamesdb.gog.com/platforms/nes/external_releases/"
FOUND_TTL = 30 * 24 * 60 * 60
MISSING_TTL = 7 * 24 * 60 * 60          # IDs the database does not know (404) are retried weekly, not on every scan
TIMEOUT = 3.5
BUDGET = 60.0                            # seconds one scan may spend online; the rest continues at the next scan
MAX_NETWORK_FAILURES = 3                 # consecutive timeouts/errors before giving up for this scan
_KEEP = ("name", "missing", "fetched_at")


def _load_cache():
    try:
        with open(config.expand(config.METADATA_CACHE_LOC), encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError):
        return {}
    if not isinstance(data, dict):
        return {}
    return {str(k).upper(): {f: v[f] for f in _KEEP if f in v} for k, v in data.items() if isinstance(v, dict)}


def _save_cache(cache):
    path = config.expand(config.METADATA_CACHE_LOC)
    directory = os.path.dirname(path)
    os.makedirs(directory, exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix="metadata_", suffix=".json", dir=directory)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(cache, fh, ensure_ascii=False, indent=1)
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            try:
                os.unlink(temp)
            except OSError:
                pass


def _fetch(external_id):
    """Title GamesDB has for an ID, or None when it does not know it (HTTP 404)."""
    request = urllib.request.Request(
        URL + urllib.parse.quote(external_id, safe=""),
        headers={"User-Agent": "GOG-Galaxy-NESPlugin/" + __version__, "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            data = json.loads(response.read(2 * 1024 * 1024).decode("utf-8"))
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return None
        raise
    title = data.get("title") if isinstance(data, dict) else None
    if isinstance(title, dict):
        title = title.get("*") or title.get("en-US") or next((v for v in title.values() if isinstance(v, str)), None)
    return title.strip() if isinstance(title, str) and title.strip() else None


def _is_fresh(entry, now):
    if not entry:
        return False
    ttl = MISSING_TTL if entry.get("missing") else FOUND_TTL
    return now - int(entry.get("fetched_at", 0) or 0) <= ttl


def _refresh(cache, ids, now, fetch=None, budget=None):
    """Look the given IDs up (several at a time) into cache. Returns True when the cache changed."""
    fetch = fetch or _fetch
    deadline = time.monotonic() + (BUDGET if budget is None else budget)
    state = {"failures": 0}

    def work(external_id):
        if state["failures"] >= MAX_NETWORK_FAILURES or time.monotonic() > deadline:
            raise ConnectionAbortedError("offline or out of time")
        try:
            result = fetch(external_id)
        except Exception:
            state["failures"] += 1
            raise
        state["failures"] = 0
        return result

    changed, skipped = False, 0
    with ThreadPoolExecutor(max_workers=min(6, len(ids))) as pool:
        futures = {pool.submit(work, i): i for i in ids}
        for future in as_completed(futures):
            external_id = futures[future]
            try:
                title = future.result()
            except ConnectionAbortedError:
                skipped += 1
                continue
            except Exception as exc:
                logging.warning("DEV: GamesDB lookup failed - %s (%s)", external_id, exc)
                continue
            cache[external_id] = {"name": title, "fetched_at": now} if title else {"missing": True, "fetched_at": now}
            changed = True
    if skipped:
        logging.warning("DEV: GamesDB lookups paused (offline or out of time), %d IDs wait for the next scan", skipped)
    return changed


def _name_of(cache, external_id):
    name = (cache.get(external_id) or {}).get("name")
    return name.strip() if isinstance(name, str) and name.strip() else None


def resolve(games, fetch=None, budget=None):
    """Give each game its official name and, when only a variant CRC is known to GamesDB, that ID.

    A game's candidates are its own ID followed by its alternative CRC32s (legacy_ids that look like
    CRCs). Alternatives are only asked for when the earlier candidate is known to be missing. The
    first candidate GamesDB knows wins; its ID becomes the game's ID (the old one moves to
    legacy_ids so playtime follows) and the log says which alternative matched.
    """
    now = int(time.time())
    cache = _load_cache()
    candidates = {
        game.id: [game.id] + [i for i in game.legacy_ids if _is_crc(i) and i != game.id]
        for game in games if game.source != "name"
    }
    dirty, queued = False, 0
    for position in range(max((len(c) for c in candidates.values()), default=0)):
        wanted = set()
        for ids in candidates.values():
            if position >= len(ids) or any(_name_of(cache, i) for i in ids[:position]):
                continue
            if position and not all((cache.get(i) or {}).get("missing") for i in ids[:position]):
                continue            # an earlier lookup failed or is still pending: do not guess
            if not _is_fresh(cache.get(ids[position]), now):
                wanted.add(ids[position])
        if wanted:
            queued += len(wanted)
            dirty = _refresh(cache, sorted(wanted), now, fetch, budget) or dirty
    if queued:
        logging.info("DEV: GamesDB looked up %d NES IDs", queued)
    if dirty:
        try:
            _save_cache(cache)
        except OSError:
            logging.exception("DEV: Could not save NES metadata cache")

    matched = 0
    for game in games:
        ids = candidates.get(game.id, ())
        for position, cand in enumerate(ids):
            name = _name_of(cache, cand)
            if name:
                if cand != game.id:
                    game.legacy_ids = tuple(dict.fromkeys([game.id] + [i for i in game.legacy_ids if i != cand]))
                    logging.info("DEV: NES %s matched GamesDB through alternative CRC #%d (%s)", game.path, position, cand)
                    game.id = cand
                game.name = name
                matched += 1
                break
    logging.info("DEV: GamesDB recognised %d/%d NES games", matched, len(games))
    return games


def _is_crc(value):
    return len(value) == 8 and all(c in "0123456789ABCDEF" for c in value)
