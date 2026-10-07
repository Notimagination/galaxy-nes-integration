import os
import shlex


def build_launch_args(emu_path, game_path, fullscreen=False, custom_args=""):
    """argv for Mesen (or any emulator that takes the ROM path), or for the user's own template.

    custom_args (config.ini: [EmuSettings] launch_args) replaces the built-in options.
    "{game}" is replaced by the game path, also inside a token (--rom={game});
    without a placeholder the game path is appended.
    """
    if custom_args.strip():
        tokens, used = [], False
        for token in shlex.split(custom_args, posix=False):
            token = token.strip('"')
            if "{game}" in token:
                token = token.replace("{game}", game_path)
                used = True
            tokens.append(token)
        if not used:
            tokens.append(game_path)
        return [emu_path] + tokens

    args = [emu_path]
    if fullscreen and "mesen" in os.path.basename(emu_path).casefold():
        args.append("--fullscreen")
    args.append(game_path)
    return args
