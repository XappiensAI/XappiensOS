"""Detección de CPU limitada por el firmware, con un sysfs falso."""

import configparser
import importlib.machinery
import importlib.util
from pathlib import Path
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[1]
OVERLAY = REPO / "config/xappiens-os/includes.chroot"
SCRIPT = OVERLAY / "usr/lib/xappiens/power-check"
LOADER = importlib.machinery.SourceFileLoader("power_check", str(SCRIPT))
SPEC = importlib.util.spec_from_loader(LOADER.name, LOADER)
check = importlib.util.module_from_spec(SPEC)
LOADER.exec_module(check)


def fake_cpu(root, cpu, low, high, cur):
    base = Path(root) / f"cpu{cpu}" / "cpufreq"
    base.mkdir(parents=True)
    (base / "cpuinfo_min_freq").write_text(f"{low}\n")
    (base / "scaling_max_freq").write_text(f"{high}\n")
    (base / "scaling_cur_freq").write_text(f"{cur}\n")


class FakeClock:
    def __init__(self, step=0.05):
        self.now = 0.0
        self.step = step

    def __call__(self):
        self.now += self.step
        return self.now


class PowerCheckTests(unittest.TestCase):
    def test_pinned_at_minimum_is_throttled(self):
        # Caso real: ASUS ProArt P16 tras quedarse sin batería.
        self.assertTrue(check.is_throttled([605000, 606577], 600983, 5157000))

    def test_boosting_cpu_is_not_throttled(self):
        self.assertFalse(check.is_throttled([4800000], 600983, 5157000))

    def test_policy_capped_by_the_user_is_not_throttled(self):
        # Un perfil de ahorro que limita la política no es culpa del firmware.
        self.assertFalse(check.is_throttled([800000], 600000, 1000000))

    def test_no_samples_is_not_throttled(self):
        self.assertFalse(check.is_throttled([], 600000, 5000000))

    def test_policy_reads_sysfs_and_tolerates_missing_cpufreq(self):
        with tempfile.TemporaryDirectory() as tmp:
            fake_cpu(tmp, 3, 600983, 5157000, 606000)
            self.assertEqual(check.policy(3, sysfs=tmp), (600983, 5157000))
            self.assertIsNone(check.policy(4, sysfs=tmp))

    def test_samples_skip_warmup_and_survive_pin_errors(self):
        def refuse(pid, cpus):
            raise OSError("sin permiso")

        with tempfile.TemporaryDirectory() as tmp:
            fake_cpu(tmp, 1, 600000, 5000000, 606000)
            samples = check.sample_under_load(
                1, duration=1.0, interval=0.1, sysfs=tmp,
                clock=FakeClock(), pin=refuse)
        self.assertTrue(samples)
        self.assertLessEqual(len(samples), 8)  # el primer cuarto se descarta
        self.assertEqual(set(samples), {606000})

    def test_picks_last_allowed_cpu(self):
        self.assertEqual(check.pick_cpu({0, 2, 7}), 7)

    def test_message_explains_the_recovery(self):
        body = check.BODY.format(cur=606, max=5157)
        self.assertIn("606 MHz", body)
        self.assertIn("40 segundos", body)


class BatteryPolicyTests(unittest.TestCase):
    CONF = OVERLAY / "etc/UPower/UPower.conf.d/60-xappiens-battery.conf"

    def test_drop_in_name_matches_upower_pattern(self):
        # UPower ignora en silencio los ficheros que no siguen este patrón.
        self.assertRegex(self.CONF.name, r"^([0-9][0-9])-([a-zA-Z0-9-_])*\.conf$")

    def test_powers_off_cleanly_with_margin(self):
        conf = configparser.ConfigParser()
        conf.optionxform = str
        conf.read(self.CONF)
        upower = conf["UPower"]
        self.assertEqual(upower["CriticalPowerAction"], "PowerOff")
        self.assertEqual(upower["UsePercentageForPolicy"], "true")
        action = float(upower["PercentageAction"])
        critical = float(upower["PercentageCritical"])
        low = float(upower["PercentageLow"])
        self.assertGreaterEqual(action, 5.0)
        self.assertLess(action, critical)
        self.assertLess(critical, low)


class SessionWiringTests(unittest.TestCase):
    def test_autostart_starts_the_user_service(self):
        desktop = configparser.ConfigParser(interpolation=None)
        desktop.optionxform = str
        desktop.read(OVERLAY / "etc/xdg/autostart/xappiens-power-check.desktop")
        entry = desktop["Desktop Entry"]
        self.assertIn("xappiens-power-check.service", entry["Exec"])
        self.assertEqual(entry["TryExec"], "/usr/lib/xappiens/power-check")

    def test_throttled_exit_code_is_not_a_service_failure(self):
        unit = configparser.ConfigParser(interpolation=None)
        unit.optionxform = str
        unit.read(OVERLAY / "usr/lib/systemd/user/xappiens-power-check.service")
        self.assertEqual(unit["Service"]["Type"], "oneshot")
        self.assertIn("1", unit["Service"]["SuccessExitStatus"].split())
        self.assertTrue(unit["Service"]["ExecStart"].startswith(
            "/usr/lib/xappiens/power-check"))


if __name__ == "__main__":
    unittest.main()
