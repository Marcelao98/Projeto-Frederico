"""A versão é a mesma nos 6 arquivos (scripts/versao.py)."""

import subprocess
import sys
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]


class TestVersao(unittest.TestCase):
    def test_todos_os_arquivos_com_a_mesma_versao(self):
        r = subprocess.run([sys.executable, str(RAIZ / "scripts" / "versao.py"), "--conferir"], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)


if __name__ == "__main__":
    unittest.main()
