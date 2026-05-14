from PyQt5 import QtWidgets, QtCore

from api.structures import DAQSampleRate, DAQVoltage
from application.widgets.channel_checkbox import ChannelCheckBox
from store.state import State


class ConfigGroup(QtWidgets.QGroupBox):
    def __init__(self, parent):
        super().__init__(parent)

        self.setTitle("Config")

        hlayout = QtWidgets.QHBoxLayout()
        grid_layout = QtWidgets.QGridLayout()
        grid_layout2 = QtWidgets.QGridLayout()

        self.check_boxes = []
        for i in range(2):
            for j in range(4):
                ind = i * 4 + j + 1
                cb = ChannelCheckBox(self, channel=ind)
                grid_layout.addWidget(cb, i, j)
                self.check_boxes.append(cb)

        self.sample_rate = QtWidgets.QComboBox(self)
        self.sample_rate.addItems([str(it.value) for it in DAQSampleRate])
        self.sample_rate.currentIndexChanged.connect(self.set_sample_rate)
        self.sample_rate.setCurrentText(str(State.sample_rate.value))
        grid_layout2.addWidget(
            QtWidgets.QLabel("Sample Rate, Hz:", self), 0, 0, alignment=QtCore.Qt.AlignmentFlag.AlignRight
        )
        grid_layout2.addWidget(self.sample_rate, 0, 1)

        self.voltage = QtWidgets.QComboBox(self)
        self.voltage.addItems([str(it.name) for it in DAQVoltage])
        self.voltage.currentIndexChanged.connect(self.set_voltage)
        self.voltage.setCurrentText(str(State.voltage.name))
        grid_layout2.addWidget(
            QtWidgets.QLabel("Voltage, V:", self), 1, 0, alignment=QtCore.Qt.AlignmentFlag.AlignRight
        )
        grid_layout2.addWidget(self.voltage, 1, 1)

        hlayout.addLayout(grid_layout)
        hlayout.addLayout(grid_layout2)

        self.setLayout(hlayout)

    @staticmethod
    def set_sample_rate(index):
        State.sample_rate = DAQSampleRate.get_by_index(index)
        if State.read_elements_count.value > State.sample_rate.value:
            State.read_elements_count.value = State.sample_rate.value
        State.save_settings()

    @staticmethod
    def set_voltage(index):
        State.voltage = DAQVoltage.get_by_index(index)
        State.save_settings()
