import sys
from pathlib import Path

SHORTCUT_BUILDER_DIR = Path(__file__).resolve().parents[2] / "shortcut" / "builder"
sys.path.insert(0, str(SHORTCUT_BUILDER_DIR))

from generate_shortcut import main as generate_shortcuts
from validate_shortcut import validate_shortcut_file


def test_generate_and_validate_shortcuts():
    generate_shortcuts()
    dist_dir = Path(__file__).resolve().parents[2] / "shortcut" / "dist"
    menu_file = dist_dir / "ClipSave.unsigned.shortcut"
    onetap_file = dist_dir / "ClipSave-1Tap.unsigned.shortcut"

    assert menu_file.is_file()
    assert onetap_file.is_file()
    assert validate_shortcut_file(menu_file) == []
    assert validate_shortcut_file(onetap_file) == []
