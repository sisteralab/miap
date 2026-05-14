from typing import List, Dict

from PyQt5 import QtWidgets
import pyqtgraph as pg

from store.state import State


class PlotWidget(QtWidgets.QWidget):
    colors = [
        "#1f77b4",
        "#ff7f0e",
        "#2ca02c",
        "#d62728",
        "#9467bd",
        "#8c564b",
        "#e377c2",
        "#7f7f7f",
        "#bcbd22",
        "#17becf",
    ]

    def __init__(self, parent):
        super().__init__(parent)
        layout = QtWidgets.QVBoxLayout(self)

        self.plot = pg.PlotWidget(self)
        self.prepare_plot()

        layout.addWidget(self.plot)
        self.setLayout(layout)

    def prepare_plot(self):
        self.plot.setBackground("w")
        self.plot.addLegend()
        self.plot.showGrid(x=True, y=True)
        self.set_time_mode()

    def set_axis_labels(self, x_label: str, y_label: str):
        styles = {"color": "#413C58", "font-size": "15px"}
        self.plot.setLabel("left", y_label, **styles)
        self.plot.setLabel("bottom", x_label, **styles)

    def set_time_mode(self):
        self.set_axis_labels("Time, s", "Voltage, V")

    def set_channels_mode(self, x_channel: int, y_channel: int):
        self.set_axis_labels(f"AI{x_channel}, V", f"AI{y_channel}, V")

    def clear(self):
        self.plot.clear()

    def get_plot_items(self):
        plot_item = self.plot.getPlotItem()
        return {item.name(): item for item in plot_item.items}

    def add_plots(self, data: List[Dict]):
        if State.plot_mode == "channels":
            self.add_channel_plot(data)
            return

        items = self.get_plot_items()
        for dat in data:
            graph_id = f"AI{dat['channel']}"
            if items.get(graph_id):
                item = items.get(graph_id)
                x_data = list(item.xData)
                x_data.append(dat["time"])
                y_data = list(item.yData)
                y_data.append(dat["voltage"])
                if len(x_data) > State.plot_window:
                    del x_data[0]
                    del y_data[0]
                item.setData(x_data, y_data)
                continue

            pen = pg.mkPen(color=self.colors[dat["channel"] - 1], width=2)
            self.plot.plot(
                [dat["time"]], [dat["voltage"]], name=f"{graph_id}", pen=pen, symbolSize=6, symbolBrush=pen.color()
            )

    def add_channel_plot(self, data: List[Dict]):
        data_by_channel = {dat["channel"]: dat for dat in data}
        x_dat = data_by_channel.get(State.plot_x_channel)
        y_dat = data_by_channel.get(State.plot_y_channel)
        if not x_dat or not y_dat:
            return

        graph_id = f"AI{State.plot_y_channel}/AI{State.plot_x_channel}"
        x_value = x_dat["voltage"]
        y_value = y_dat["voltage"]
        items = self.get_plot_items()
        if items.get(graph_id):
            item = items.get(graph_id)
            x_data = list(item.xData)
            x_data.append(x_value)
            y_data = list(item.yData)
            y_data.append(y_value)
            if len(x_data) > State.plot_window:
                del x_data[0]
                del y_data[0]
            item.setData(x_data, y_data)
            return

        color_ind = (State.plot_y_channel - 1) % len(self.colors)
        pen = pg.mkPen(color=self.colors[color_ind], width=2)
        self.plot.plot([x_value], [y_value], name=graph_id, pen=pen, symbolSize=6, symbolBrush=pen.color())
