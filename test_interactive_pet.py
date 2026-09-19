import tempfile
import unittest
from pathlib import Path

from PIL import Image

from interactive_pet import (
    CODEX_SIZE_KEY,
    CodexPetBridge,
    harden_alpha_for_color_key,
)


class CodexPetBridgeTests(unittest.TestCase):
    def test_codex_size_is_read_from_desktop_config(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            pet_dir = root / "pets" / "graduate-zombie"
            pet_dir.mkdir(parents=True)
            (root / "config.toml").write_text(
                f'[desktop]\n{CODEX_SIZE_KEY} = 159\n',
                encoding="utf-8",
            )
            bridge = CodexPetBridge(pet_dir, codex_home=root)
            self.assertEqual(bridge.effective_width(), 159)

    def test_missing_codex_size_uses_default(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            pet_dir = root / "pets" / "graduate-zombie"
            pet_dir.mkdir(parents=True)
            bridge = CodexPetBridge(pet_dir, codex_home=root)
            self.assertEqual(bridge.effective_width(), 112)

    def test_color_key_frames_have_no_soft_alpha(self) -> None:
        source = Image.new("RGBA", (3, 1))
        source.putdata([(20, 30, 40, 0), (20, 30, 40, 80), (20, 30, 40, 255)])
        cleaned = harden_alpha_for_color_key(source)
        self.assertEqual(list(cleaned.getchannel("A").get_flattened_data()), [0, 255, 255])


if __name__ == "__main__":
    unittest.main()
