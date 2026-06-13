"""
Load file nguon `cl10_v2.txt` (duoi .txt thay vi .py) thanh module Python
de cac test co the import truc tiep cac ham logic Tu Tru.

Dung importlib voi SourceFileLoader nen khong phu thuoc duoi file.
`main()` duoc bao ve boi `if __name__ == "__main__"` nen import an toan,
khong khoi dong bot.
"""
import os
import importlib.util
import importlib.machinery
import sys

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
_SRC = os.path.join(_HERE, "bot.py")


def _load_bot_module():
    loader = importlib.machinery.SourceFileLoader("bot_tu_tru", _SRC)
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    sys.modules[loader.name] = module
    loader.exec_module(module)
    return module


@pytest.fixture(scope="session")
def bot():
    """Module logic Tu Tru da load tu cl10_v2.txt."""
    return _load_bot_module()
