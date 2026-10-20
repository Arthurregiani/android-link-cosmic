"""Build regression: restrictive caller umask must not leak into the package."""
from pathlib import Path
import io
import shutil
import subprocess
import tarfile
import tempfile
import unittest

@unittest.skipUnless(shutil.which('dpkg-deb'), 'dpkg-deb unavailable')
class PackagingTests(unittest.TestCase):
    def test_package_modes_under_private_umask(self):
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as dest:
            subprocess.run(['bash', '-c', 'umask 077; exec ./packaging/build_deb.sh "$1"', 'build', dest], cwd=root, check=True, capture_output=True)
            package = next(Path(dest).glob('*.deb'))
            data = subprocess.check_output(['dpkg-deb', '--fsys-tarfile', str(package)])
            with tarfile.open(fileobj=io.BytesIO(data)) as archive:
                entries = archive.getmembers()
                for entry in entries:
                    expected = 0o755 if entry.isdir() or entry.name == './usr/bin/android-link' else 0o644
                    self.assertEqual(entry.mode, expected, entry.name)
                self.assertTrue(any(e.name.endswith('/applications/net.regiani.AndroidLink.desktop') for e in entries))
