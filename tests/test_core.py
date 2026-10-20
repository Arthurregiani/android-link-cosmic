import unittest
from unittest.mock import patch
from android_link.core import (
    AdbDevice, MdnsService, parse_mdns, parse_devices, group_devices,
    new_pairing, find_pair_endpoint, scrcpy_args, connect_after_pairing, pair_with_qr,
    MDNS_CONNECT_TYPE, MDNS_PAIR_TYPE, parse_battery, read_battery,
)

MDNS = """List of discovered mdns services
adb-TESTDEVICE001-ExampleId    _adb-tls-connect._tcp    192.0.2.10:45721
"""
DEVICES = """List of devices attached
192.0.2.10:45721 device product:a54xnsxx model:SM_A546E device:a54x transport_id:2
adb-TESTDEVICE001-ExampleId._adb-tls-connect._tcp device product:a54xnsxx model:SM_A546E device:a54x transport_id:1
"""

class CoreTests(unittest.TestCase):
    def test_battery_status_charging(self):
        info = parse_battery("""Current Battery Service state:
  AC powered: false
  USB powered: false
  Wireless powered: true
  status: 2
  health: 2
  level: 78
  scale: 100
  temperature: 307
""")
        self.assertEqual(info.percent, 78)
        self.assertTrue(info.charging)
        self.assertEqual(info.status, "Carregando")
        self.assertEqual(info.temperature_c, 30.7)

    def test_battery_discharging(self):
        info = parse_battery("status: 3\nlevel: 21\nscale: 100\n")
        self.assertEqual(info.percent, 21)
        self.assertFalse(info.charging)
        self.assertEqual(info.status, "Descarregando")

    def test_battery_full_and_custom_scale(self):
        info = parse_battery("status: 5\nlevel: 85\nscale: 85")
        self.assertEqual(info.percent, 100)
        self.assertEqual(info.status, "Carga completa")

    def test_battery_missing_or_invalid(self):
        for text in ("", "error: device offline", "level: 50\nscale: 0", "level: 200\nscale: 100"):
            with self.subTest(text=text), self.assertRaises(RuntimeError):
                parse_battery(text)

    @patch("android_link.core.run_adb")
    def test_battery_targets_selected_serial(self, fake_adb):
        from subprocess import CompletedProcess
        fake_adb.return_value = CompletedProcess([], 0, "level: 42\nscale: 100\nstatus: 3", "")
        info = read_battery("adb-TESTDEVICE001-ExampleId._adb-tls-connect._tcp")
        self.assertEqual(info.percent, 42)
        fake_adb.assert_called_once_with("-s", "adb-TESTDEVICE001-ExampleId._adb-tls-connect._tcp",
                                         "shell", "dumpsys", "battery", timeout=10)

    @patch("android_link.core.run_adb")
    def test_battery_error(self, fake_adb):
        from subprocess import CompletedProcess
        fake_adb.return_value = CompletedProcess([], 1, "", "device offline")
        with self.assertRaisesRegex(RuntimeError, "device offline"):
            read_battery("serial")

    @patch("android_link.core.subprocess.run")
    @patch("android_link.core.get_adb", return_value="/adb")
    def test_pair_secret_uses_stdin(self, _get_adb, run):
        from android_link.core import run_adb
        run_adb("pair", "192.0.2.10:39000", input_text="synthetic-secret\n")
        args, kwargs = run.call_args
        self.assertEqual(args[0], ["/adb", "pair", "192.0.2.10:39000"])
        self.assertEqual(kwargs["input"], "synthetic-secret\n")

    @patch("android_link.core.run_adb")
    def test_pair_failure_redacts_secret(self, fake_adb):
        from subprocess import CompletedProcess
        fake_adb.side_effect = [
            CompletedProcess([], 0, "studio-test _adb-tls-pairing._tcp 192.0.2.10:39000"),
            CompletedProcess([], 1, "synthetic-secret", "")]
        with self.assertRaises(RuntimeError) as raised:
            pair_with_qr("studio-test", "synthetic-secret", lambda: False, lambda _: None)
        self.assertNotIn("synthetic-secret", str(raised.exception))

    def test_mdns(self):
        s = parse_mdns(MDNS)
        self.assertEqual(len(s), 1)
        self.assertEqual(s[0].endpoint, "192.0.2.10:45721")

    def test_devices(self):
        d = parse_devices(DEVICES)
        self.assertEqual(len(d), 2)
        self.assertEqual(d[0].model, "SM_A546E")

    def test_duplicates_collapse(self):
        choices = group_devices(parse_devices(DEVICES), parse_mdns(MDNS))
        self.assertEqual(len(choices), 1)
        self.assertEqual(choices[0].state, "device")
        self.assertTrue(choices[0].serial.startswith("adb-"))

    def test_different_devices_preserved(self):
        choices = group_devices(parse_devices(DEVICES + "192.0.2.99:3562 device model:SM_A546E\n"), parse_mdns(MDNS))
        self.assertEqual(len(choices), 2)

    def test_discovered_only(self):
        choices = group_devices([], parse_mdns(MDNS))
        self.assertEqual(len(choices), 1)
        self.assertEqual(choices[0].state, "discovered")
        self.assertEqual(choices[0].endpoint, "192.0.2.10:45721")

    def test_pairing_qr_payload(self):
        name, password, qr = new_pairing()
        self.assertRegex(name, r"^studio-[0-9a-f]{16}$")
        self.assertEqual(len(password), 12)
        self.assertEqual(qr, f"WIFI:T:ADB;S:{name};P:{password};;")

    def test_pairing_matches_exact_service(self):
        s = [MdnsService("studio-test", MDNS_PAIR_TYPE, "192.0.2.10:32798"),
             MdnsService("studio-other", MDNS_PAIR_TYPE, "192.0.2.23:3000")]
        self.assertEqual(find_pair_endpoint(s, "studio-test"), "192.0.2.10:32798")
        self.assertEqual(find_pair_endpoint(s, "studio-tes"), "")

    @patch("android_link.core.get_scrcpy", return_value="/scrcpy")
    def test_scrcpy_commands(self, get_scrcpy):
        actual = scrcpy_args("serial", "camera", "front", 1920, 30)
        self.assertIn("--video-source=camera", actual)
        self.assertIn("--camera-facing=front", actual)
        self.assertIn("--camera-fps=30", actual)
        webcam = scrcpy_args("serial", "webcam")
        self.assertIn("--v4l2-sink=/dev/video42", webcam)
        self.assertIn("--no-video-playback", webcam)
        mirror = scrcpy_args("serial", "mirror")
        self.assertNotIn("--video-source=camera", mirror)

    @patch("android_link.core.get_scrcpy", return_value="/scrcpy")
    def test_bad_options_rejected(self, get_scrcpy):
        with self.assertRaises(ValueError):
            scrcpy_args("serial", "camera", "front;rm -rf /", 1920, 0)

    @patch("android_link.core.connect_after_pairing", return_value="Dispositivo pareado.")
    @patch("android_link.core.run_adb")
    def test_qr_pair_workflow(self, fake_adb, fake_connect):
        from subprocess import CompletedProcess
        fake_adb.side_effect = [
            CompletedProcess(["adb", "mdns", "services"], 0, "List of discovered mdns services\n"),
            CompletedProcess(["adb", "mdns", "services"], 0,
                             "studio-abc\t_adb-tls-pairing._tcp\t192.0.2.10:39000\n"),
            CompletedProcess(["adb", "pair"], 0, "Successfully paired to 192.0.2.10:39000")
        ]
        with patch("android_link.core.time.sleep", return_value=None):
            result = pair_with_qr("studio-abc", "SecretABC123", lambda: False, lambda _: None, timeout=5)
        self.assertEqual(result, "Dispositivo pareado.")
        fake_adb.assert_any_call("pair", "192.0.2.10:39000", timeout=25, input_text="SecretABC123\n")
        fake_connect.assert_called_once()

    def test_qr_does_not_pair_other_advertisement(self):
        services = parse_mdns("studio-other\t_adb-tls-pairing._tcp\t192.0.2.55:31000\n")
        self.assertEqual(find_pair_endpoint(services, "studio-me"), "")

    def test_parse_non_matching(self):
        self.assertEqual(parse_mdns("List of discovered mdns services"), [])
        self.assertEqual(parse_devices("List of devices attached"), [])

    @patch("android_link.core.snapshot")
    def test_connect_after_pairing_does_not_use_other_ip(self, fake_snapshot):
        fake_snapshot.return_value = ([
            group_devices([AdbDevice("192.0.2.10:4123", "device", "SM_A546E", "")], [])[0]
        ], "", "")
        self.assertEqual(connect_after_pairing("192.0.2.10:1223", timeout=1),
                         "Dispositivo pareado e conectado automaticamente.")

if __name__ == "__main__":
    unittest.main()
