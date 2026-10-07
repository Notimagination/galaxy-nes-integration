from dataclasses import dataclass
from typing import Tuple


@dataclass
class NesGame:
    id: str                              # Galaxy game ID: 8-digit CRC32 (what GOG's database uses) or NES-NAME-<hash>
    name: str
    path: str                            # file launched by the emulator
    legacy_ids: Tuple[str, ...] = ()     # other IDs of the same game (playtime is moved from them)
    source: str = ""                     # ines | unif | fds | raw | zip | name
