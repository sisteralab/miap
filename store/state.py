import json
from typing import List

from PyQt5.QtCore import QObject, QSettings, pyqtSignal, pyqtProperty

from api.structures import DAQSampleRate, DAQVoltage, DAQADCChannel


class ReadElementsCountModel(QObject):
    signal_value = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._value = 100

    @pyqtProperty("int", notify=signal_value)
    def value(self):
        return self._value

    @value.setter
    def value(self, value: int):
        if value > State.sample_rate.value:
            value = State.sample_rate.value
        self._value = value
        self.signal_value.emit(value)
        State.save_settings()


class State:
    settings = QSettings("Teralab", "DAQ122")
    _loading_settings: bool = False

    sample_rate: DAQSampleRate = DAQSampleRate.SampleRate500
    voltage: DAQVoltage = DAQVoltage.Voltage5V
    channel: DAQADCChannel = DAQADCChannel.AIN_ALL
    selected_channels: List[int] = []
    plot_mode: str = "time"
    plot_x_channel: int = 1
    plot_y_channel: int = 2
    is_measuring: bool = False
    plot_window: int = 200
    duration: int = 6000
    read_elements_count = ReadElementsCountModel()
    is_average: bool = True
    is_plot_data: bool = True
    store_data: bool = True

    @classmethod
    def _settings_value(cls, key: str, default, value_type=None):
        if value_type is None:
            return cls.settings.value(key, default)
        return cls.settings.value(key, default, type=value_type)

    @staticmethod
    def _clamp_channel(channel) -> int:
        try:
            channel = int(channel)
        except (TypeError, ValueError):
            channel = 1
        return min(max(channel, 1), 8)

    @classmethod
    def load_settings(cls):
        cls._loading_settings = True
        try:
            sample_rate = DAQSampleRate.get_by_value(cls._settings_value("sample_rate", cls.sample_rate.value, int))
            if sample_rate:
                cls.sample_rate = sample_rate

            voltage = DAQVoltage.__members__.get(cls._settings_value("voltage", cls.voltage.name, str))
            if voltage:
                cls.voltage = voltage

            try:
                selected_channels = json.loads(cls._settings_value("selected_channels", "[]", str))
            except (TypeError, ValueError):
                selected_channels = []
            cls.selected_channels = sorted(
                {
                    cls._clamp_channel(channel)
                    for channel in selected_channels
                    if str(channel).isdigit() and 1 <= int(channel) <= 8
                }
            )

            plot_mode = cls._settings_value("plot_mode", cls.plot_mode, str)
            cls.plot_mode = plot_mode if plot_mode in {"time", "channels"} else "time"
            cls.plot_x_channel = cls._clamp_channel(cls._settings_value("plot_x_channel", cls.plot_x_channel, int))
            cls.plot_y_channel = cls._clamp_channel(cls._settings_value("plot_y_channel", cls.plot_y_channel, int))

            cls.plot_window = cls._settings_value("plot_window", cls.plot_window, int)
            cls.duration = cls._settings_value("duration", cls.duration, int)
            cls.read_elements_count.value = cls._settings_value(
                "read_elements_count", cls.read_elements_count.value, int
            )
            cls.is_average = cls._settings_value("is_average", cls.is_average, bool)
            cls.is_plot_data = cls._settings_value("is_plot_data", cls.is_plot_data, bool)
            cls.store_data = cls._settings_value("store_data", cls.store_data, bool)
        finally:
            cls._loading_settings = False

    @classmethod
    def save_settings(cls):
        if cls._loading_settings:
            return
        cls.settings.setValue("sample_rate", cls.sample_rate.value)
        cls.settings.setValue("voltage", cls.voltage.name)
        cls.settings.setValue("selected_channels", json.dumps(sorted(set(cls.selected_channels))))
        cls.settings.setValue("plot_mode", cls.plot_mode)
        cls.settings.setValue("plot_x_channel", cls.plot_x_channel)
        cls.settings.setValue("plot_y_channel", cls.plot_y_channel)
        cls.settings.setValue("plot_window", cls.plot_window)
        cls.settings.setValue("duration", cls.duration)
        cls.settings.setValue("read_elements_count", cls.read_elements_count.value)
        cls.settings.setValue("is_average", cls.is_average)
        cls.settings.setValue("is_plot_data", cls.is_plot_data)
        cls.settings.setValue("store_data", cls.store_data)
        cls.settings.sync()
