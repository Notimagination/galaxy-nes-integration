import json, os
with open(os.path.join(os.path.dirname(__file__), "manifest.json"), encoding="utf-8") as fh:
    __version__ = json.load(fh)["version"]
