"""
Tests for Memory Monitor - Peak memory tracking.
"""

import unittest
import time
from unittest.mock import patch, MagicMock
from core.memory_monitor import MemoryMonitor


class TestMemoryMonitor(unittest.TestCase):
    def test_initial_peak_values(self):
        """Test that peak values start at 0."""
        monitor = MemoryMonitor()

        values = monitor.get_peak_values()

        self.assertEqual(values["peak_vram_mb"], 0.0)
        self.assertEqual(values["peak_system_ram_mb"], 0.0)

    def test_peak_updates_on_higher_value(self):
        """Test that peak updates when new value is higher."""
        monitor = MemoryMonitor()

        # Mock the _get_vram_usage method
        with patch.object(monitor, "_get_vram_usage", return_value=100.0):
            with patch.object(monitor, "_get_system_ram_usage", return_value=2000.0):
                monitor.start()
                time.sleep(0.5)
                monitor.stop()

        values = monitor.get_peak_values()

        self.assertEqual(values["peak_vram_mb"], 100.0)
        self.assertEqual(values["peak_system_ram_mb"], 2000.0)

    def test_peak_does_not_update_on_lower_value(self):
        """Test that peak doesn't update when new value is lower."""
        monitor = MemoryMonitor()

        # First sample: 100 MB
        with patch.object(monitor, "_get_vram_usage", return_value=100.0):
            with patch.object(monitor, "_get_system_ram_usage", return_value=2000.0):
                monitor.start()
                time.sleep(0.5)

        # Second sample: 50 MB (should not update peak)
        with patch.object(monitor, "_get_vram_usage", return_value=50.0):
            with patch.object(monitor, "_get_system_ram_usage", return_value=1500.0):
                time.sleep(0.5)

        monitor.stop()

        values = monitor.get_peak_values()

        # Peak should remain at 100 MB
        self.assertEqual(values["peak_vram_mb"], 100.0)

    def test_sample_history(self):
        """Test that samples are recorded in history."""
        monitor = MemoryMonitor(sample_interval=0.1)

        with patch.object(monitor, "_get_vram_usage", return_value=100.0):
            with patch.object(monitor, "_get_system_ram_usage", return_value=2000.0):
                monitor.start()
                time.sleep(0.3)
                monitor.stop()

        history = monitor.get_sample_history()

        self.assertGreaterEqual(len(history), 2)

        # Check sample structure
        sample = history[0]
        self.assertIn("timestamp", sample)
        self.assertIn("vram_mb", sample)
        self.assertIn("system_ram_mb", sample)

    def test_stop_without_start(self):
        """Test that stop() works even if start() was not called."""
        monitor = MemoryMonitor()

        # Should not raise exception
        monitor.stop()

        values = monitor.get_peak_values()
        self.assertEqual(values["peak_vram_mb"], 0.0)


if __name__ == "__main__":
    unittest.main()
