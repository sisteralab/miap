import logging
import time
from multiprocessing import Process, Manager
from typing import Dict, List

import numpy as np
from PyQt5 import QtWidgets, QtCore
from PyQt5.QtCore import pyqtSignal

from api import get_daq_class
from api.exceptions import DeviceError
from api.structures import DAQADCChannel
from store.data import MeasureManager
from store.state import State

logger = logging.getLogger(__name__)


class ReceiverProcess(Process):
    def __init__(self, duration: int, data_queue, log_queue, state):
        super().__init__()
        self.duration = duration
        self.data_queue = data_queue
        self.log_queue = log_queue
        self.state = state
        self.read_elements_count = int(State.read_elements_count.value)
        self.sample_rate = State.sample_rate
        self.voltage = State.voltage
        self.selected_channels = sorted([_ for _ in State.selected_channels])

    def run(self) -> None:
        DAQ122 = get_daq_class()
        try:
            with DAQ122() as daq:
                self.log_queue.put("Device initialized and created!")
                if not daq.is_connected():
                    self.finish()
                    return

                self.log_queue.put("Device state is connected!")

                if not daq.configure_sampling_parameters(self.voltage, self.sample_rate):
                    self.finish()
                    return

                self.log_queue.put("Device sampling parameters configured!")

                if not daq.config_adc_channel(DAQADCChannel.AIN_ALL):
                    self.finish()
                    return

                self.log_queue.put("Device ADC channel configured!")

                daq.start_collection()
                self.log_queue.put("Device started collection!")
                time.sleep(1)  # Wait for data to accumulate

                start = time.time()
                while self.state["is_measuring"]:
                    for channel in self.selected_channels:
                        success, data = daq.read_data(
                            read_elements_count=self.read_elements_count, channel_number=channel - 1, timeout=5000
                        )
                        if success:
                            duration = time.time() - start
                            self.data_queue.put({"channel": channel, "voltage": list(data), "time": duration})
                            if duration > self.duration:
                                self.finish()

            self.log_queue.put("Device disconnected!")
        except DeviceError as e:
            self.log_queue.put(f"!ERROR! {str(e)}")
            self.finish()

    def finish(self):
        self.log_queue.put("Receiver finished.")
        self.state["is_measuring"] = False


class ProcessorProcess(Process):
    def __init__(self, data_queue, processed_queue, measure, state):
        super().__init__()
        self.data_queue = data_queue
        self.processed_queue = processed_queue
        self.is_average = State.is_average
        self.measure = measure
        self.state = state

    def run(self):
        def function():
            data = self.data_queue.get()
            mean_voltage = np.mean(data["voltage"])
            self.processed_queue.put({"channel": data["channel"], "voltage": mean_voltage, "time": data["time"]})
            if self.is_average:
                self.measure.data["data"][data["channel"]]["voltage"].append(mean_voltage)
            else:
                self.measure.data["data"][data["channel"]]["voltage"].append(data["voltage"])
            self.measure.data["data"][data["channel"]]["time"].append(data["time"])

        while self.state["is_measuring"]:
            if not self.data_queue.empty():
                function()

        time.sleep(1)
        while not self.data_queue.empty():
            function()
            time.sleep(0.1)


class PlotterThread(QtCore.QThread):
    plot_data = pyqtSignal(list)

    def __init__(self, processed_queue):
        super().__init__()
        self.processed_queue = processed_queue
        self.data = []

    def run(self):
        def function():
            self.plot_data.emit([self.processed_queue.get()])

        while State.is_measuring:
            if not self.processed_queue.empty():
                function()

        time.sleep(0.5)
        while not self.processed_queue.empty():
            function()
            time.sleep(0.2)

        self.finished.emit()


class MeasureGroup(QtWidgets.QGroupBox):
    def __init__(self, parent):
        super().__init__(parent)
        self.process_receiver = None
        self.process_processor = None
        self.thread_plotter = None
        self.data_queue = None
        self.processed_queue = None
        self.log_queue = None
        self.measure = None
        self.manager = Manager()
        self.state = self.manager.dict()
        self.state["is_measuring"] = False

        self.setTitle("Measure")

        vlayout = QtWidgets.QVBoxLayout()
        hlayout = QtWidgets.QHBoxLayout()
        flayout = QtWidgets.QFormLayout()

        self.duration = QtWidgets.QSpinBox(self)
        self.duration.setRange(10, 3600)
        self.duration.setValue(State.duration)
        self.duration.valueChanged.connect(self.set_duration)

        self.plot_window = QtWidgets.QSpinBox(self)
        self.plot_window.setRange(10, 500)
        self.plot_window.setValue(State.plot_window)
        self.plot_window.valueChanged.connect(self.set_plot_window)

        self.read_elements = QtWidgets.QSpinBox(self)
        self.read_elements.setRange(10, 1000)
        self.read_elements.setValue(State.read_elements_count.value)
        self.read_elements.valueChanged.connect(self.set_read_elements)
        State.read_elements_count.signal_value.connect(lambda val: self.read_elements.setValue(int(val)))

        self.is_average = QtWidgets.QCheckBox(self)
        self.is_average.setText("Average EpR")
        self.is_average.setToolTip("Averaging Elements per Request")
        self.is_average.setChecked(State.is_average)
        self.is_average.stateChanged.connect(self.set_average)

        flayout.setLabelAlignment(QtCore.Qt.AlignmentFlag.AlignLeft)
        flayout.setFormAlignment(QtCore.Qt.AlignmentFlag.AlignLeft)
        flayout.addRow("Measuring Time, s:", self.duration)
        flayout.addRow("Plot points count:", self.plot_window)
        flayout.addRow("Elements per Request:", self.read_elements)
        flayout.addRow(self.is_average)

        self.btn_start = QtWidgets.QPushButton("Start", self)
        self.btn_start.clicked.connect(self.start_measure)
        self.btn_stop = QtWidgets.QPushButton("Stop", self)
        self.btn_stop.clicked.connect(self.stop_measure)
        hlayout.addWidget(self.btn_start)
        hlayout.addWidget(self.btn_stop)

        vlayout.addLayout(flayout)
        vlayout.addLayout(hlayout)

        self.setLayout(vlayout)

    def start_measure(self):
        if not len(State.selected_channels):
            return
        self.parent().plot_widget.clear()

        self.data_queue = self.manager.Queue()
        self.processed_queue = self.manager.Queue()
        self.log_queue = self.manager.Queue()

        data = {channel: {"voltage": [], "time": []} for channel in State.selected_channels}
        self.measure = MeasureManager.create(
            data={
                "sample_rate": State.sample_rate.value,
                "voltage": State.voltage.Voltage5V.name,
                "elements_per_request": int(State.read_elements_count.value),
                "data": data,
            }
        )
        self.measure.save(finish=False)

        self.process_receiver = ReceiverProcess(
            duration=int(self.duration.value()), data_queue=self.data_queue, log_queue=self.log_queue, state=self.state
        )
        self.process_receiver.start()

        self.process_processor = ProcessorProcess(
            data_queue=self.data_queue, processed_queue=self.processed_queue, measure=self.measure, state=self.state
        )
        self.process_processor.start()

        self.thread_plotter = PlotterThread(processed_queue=self.processed_queue)
        self.thread_plotter.plot_data.connect(self.plot_data)
        self.thread_plotter.finished.connect(self.finish_measure)
        self.thread_plotter.finished.connect(lambda: self.btn_start.setEnabled(True))

        self.btn_start.setEnabled(False)
        self.state["is_measuring"] = True
        self.thread_plotter.start()

        self.log_timer = QtCore.QTimer(self)
        self.log_timer.timeout.connect(self.check_log_queue)
        self.log_timer.start(100)

    def check_log_queue(self):
        while not self.log_queue.empty():
            message = self.log_queue.get()
            logger.info(message)
            if message == "Receiver finished.":
                self.stop_measure()

    def stop_measure(self):
        State.is_measuring = False
        if self.state:
            self.state["is_measuring"] = False
        logger.info("Wait to finish measuring...")

    def finish_measure(self):
        self.measure.save(finish=True)
        self.process_receiver = None
        self.process_processor = None
        self.thread_plotter = None
        State.is_measuring = False
        logger.info("Measure finished!")

    def plot_data(self, data: List[Dict]):
        self.parent().plot_widget.add_plots(data)

    @staticmethod
    def set_duration(value):
        State.duration = int(value)

    @staticmethod
    def set_plot_window(value):
        State.plot_window = int(value)

    @staticmethod
    def set_read_elements(value):
        State.read_elements_count.value = int(value)

    @staticmethod
    def set_average(state):
        value = state == QtCore.Qt.CheckState.Checked
        State.is_average = value
