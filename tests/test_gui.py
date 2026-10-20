"""Opt-in GTK regression checks; simulated devices, not hardware validation."""
import os
import time
import unittest
from unittest.mock import patch

@unittest.skipUnless(os.environ.get('ANDROID_LINK_GUI_TESTS') == '1', 'requires real GTK desktop; opt in explicitly')
class GuiTests(unittest.TestCase):
    def test_selection_loss_does_not_query_another_phone(self):
        from android_link.app import AndroidLink, Gio, GLib
        from android_link.core import DeviceChoice, BatteryInfo
        target = DeviceChoice('target', 'target', '', 'device', 'Test', 'Target')
        other = DeviceChoice('other', 'other', '', 'device', 'Test', 'Other')
        app = AndroidLink()
        app.set_application_id('net.regiani.AndroidLink.GuiRegression')
        app.set_flags(Gio.ApplicationFlags.NON_UNIQUE)
        def drain():
            deadline = time.monotonic() + 2
            while time.monotonic() < deadline:
                while GLib.MainContext.default().pending():
                    GLib.MainContext.default().iteration(False)
                if not app.busy and not app.battery_inflight:
                    return
                time.sleep(.01)
            self.fail('GTK worker did not finish')
        with patch('android_link.core.snapshot', return_value=([target, other], '', '')) as snapshot, patch('android_link.core.read_battery', return_value=BatteryInfo(42, 'Descarregando', False)) as battery:
            app.register(None)
            app.activate()
            try:
                drain()
                self.assertEqual(app.battery_label.get_text(), '42% · Descarregando')
                snapshot.return_value = ([other], '', '')
                app.refresh()
                drain()
                self.assertIsNone(app.selected_choice())
                self.assertEqual(app.battery_label.get_text(), 'Indisponível · desconectado')
                self.assertEqual([call.args[0] for call in battery.call_args_list], ['target'])
                snapshot.return_value = ([other, target], '', '')
                app.refresh()
                drain()
                self.assertEqual(app.selected_choice().serial, 'target')
                app.window.close()
                count = battery.call_count
                app.poll_while_open()
                app.refresh_battery(force=True)
                self.assertEqual(battery.call_count, count)
            finally:
                if not app.closed:
                    app.window.close()
                app.quit()
