import logging
import os

import config
import gamesdb
import nesrom
from definitions import NesGame


def _rank(path):
    """When two files are the same game, launch the plain ROM before a zip."""
    return 1 if path.lower().endswith(".zip") else 0


class NesClient:
    def __init__(self):
        self.games = []

    def scan_games(self, cfg):
        """Scan the ROM folder in cfg. Blocking: run it in a worker thread."""
        rom_path = config.path_value(cfg, "Paths", "roms_path")
        self.games = []
        if not rom_path or not os.path.isdir(rom_path):
            logging.warning("DEV: NES ROM folder does not exist - %s", rom_path)
            return self.games
        extensions = set(nesrom.parse_extensions(cfg.get("Detection", "extensions", fallback="")))

        found = {}                                  # game id -> NesGame
        stats = {}
        scanned = 0
        for root, dirs, files in os.walk(rom_path):
            dirs.sort(key=str.casefold)
            for file in sorted(files, key=str.casefold):
                if file.startswith("._") or os.path.splitext(file)[1].lower() not in extensions:
                    continue
                path = os.path.normpath(os.path.join(root, file))
                info = nesrom.identify_file(path)
                if info is None:
                    logging.debug("DEV: zip without NES file skipped - %s", file)
                    continue
                scanned += 1
                name = nesrom.display_title(file)
                name_id = nesrom.name_game_id(name)
                if info.ids:
                    game = NesGame(info.ids[0], name, path, tuple(info.ids[1:]) + (name_id,), info.kind)
                else:
                    game = NesGame(name_id, name, path, (), "name")
                stats[game.source] = stats.get(game.source, 0) + 1
                logging.debug("DEV: NES file %s -> %s (%s)", file, game.id, game.source)
                self._keep(found, game)

        games = list(found.values())
        # Online names are optional and cached; failures never remove games.
        if cfg.getboolean("Metadata", "online_names", fallback=True):
            gamesdb.resolve(games)
        unique = {}
        for game in games:                           # an alternative CRC can make two files one game
            self._keep(unique, game)
        self.games = list(unique.values())
        nesrom.disambiguate(self.games)
        self.games.sort(key=lambda g: (g.name.casefold(), g.id))
        logging.info("DEV: NES scan summary - scanned=%d, by type=%s, imported=%d", scanned, stats, len(self.games))
        return self.games

    @staticmethod
    def _keep(found, game):
        current = found.get(game.id)
        if current is None or _rank(game.path) < _rank(current.path):
            if current is not None:
                game.legacy_ids = tuple(dict.fromkeys(game.legacy_ids + current.legacy_ids))
            found[game.id] = game
        else:
            logging.debug("DEV: duplicate NES game ignored - %s", game.path)
