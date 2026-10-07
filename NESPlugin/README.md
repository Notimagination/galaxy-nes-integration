# Galaxy NES Integration

GOG Galaxy 2.1+ integration for a local NES / Famicom library, launched through an emulator (Mesen 2; any emulator that takes the ROM path as an argument also works). By Notimagination.

## Features
- Every file type Mesen 2 opens: `.nes`, `.fds`, `.qd`, `.unf`, `.unif`, `.studybox`, `.nsf`, `.nsfe`, `.zip` and `.7z`. Subfolders are scanned.
- Games are identified by the ROM itself (CRC32 of its contents, the ID GOG's game database uses), so renaming or moving a file never creates a duplicate or loses playtime. ROMs inside `.zip` files are read too; zips without a NES file are ignored.
- Official names from GOG's public game database, cached on disk (an offline PC just keeps the names from the file names). File names are cleaned up: `Legend of Zelda, The (USA) (Rev 1).nes` becomes `The Legend of Zelda`. When several files end up with the same title, their region/revision tag is added.
- Playtime tracking, saved while you play (every 15 s) and when the emulator closes.
- Fullscreen option and custom launch arguments.

## Install
Close Galaxy, put the `NESPlugin` folder in `%LOCALAPPDATA%\GOG.com\Galaxy\plugins\installed\`, start Galaxy and connect NES from the integrations list. Do not use "Disconnect" on the integration afterwards: Galaxy discards custom covers and edits made to the games when a platform is disconnected and reconnected.

## config.ini
Stored in `%LOCALAPPDATA%\GOG.com\Galaxy\Configuration\plugins\nes\config.ini` and edited from the plugin's settings page. Extra options that only exist in the file:

```ini
[EmuSettings]
; replaces the built-in options; {game} is the game path (appended if missing)
launch_args = --fullscreen {game}

[Detection]
; the complete list of file types to import; remove .nsf,.nsfe to hide music files
extensions = .nes,.fds,.qd,.unf,.unif,.studybox,.nsf,.nsfe,.zip,.7z

[Metadata]
; False = never contact GOG's game database (names come from the file names)
online_names = True
```

## Notes
- `.7z` archives cannot be read by the plugin, so they are identified by their file name only (no cover lookup by ROM). Keep the ROM folder limited to NES files.
- Covers, dates and descriptions come from GOG's GamesDB, which plugins cannot edit. Use Edit in Galaxy for games it does not know (ROM hacks, translations, homebrew).
- Online lookups are limited to about a minute per scan; whatever is left continues at the next Galaxy start.

## Data sources
- Names: GOG GamesDB (`gamesdb.gog.com`), public endpoint, queried by ROM CRC32.

## License
MIT. See LICENSE.md.
