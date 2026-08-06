from typing import TYPE_CHECKING
import numpy as np

from qtpy import QtWidgets, QtCore

from serializall import SerializableFactory
from pymodaq_data import DataToExport, DataWithAxes, DataRaw
from pymodaq_gui.utils.widgets import SpinBox
from pymodaq_plugins_sequencer.utilities.element_factory import SeqEltBase, SeqEltFactory
from pymodaq_plugins_sequencer.utilities.widget_with_toolbar import WidgetWithToolbar


ser_factory = SerializableFactory()


@SeqEltFactory.register_elt()
class WaitElt(SeqEltBase):

    elt_name = 'wait'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.timer = QtCore.QTimer()
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.done)

        self._wait_time: int = 0

    @property
    def wait_time(self) -> int:
        return self._wait_time

    @wait_time.setter
    def wait_time(self, value: int):
        self._wait_time = value

    def _create_widget(self, base_widget:WidgetWithToolbar) -> WidgetWithToolbar:
        self.spin_box = SpinBox(int=False, suffix='s', siPrefix=True)
        self.add_widget('wait_time', self.spin_box,
                        tip='wait time',
                        toolbar=base_widget.toolbar)
        self.spin_box.editingFinished.connect(self.set_wait_time_from_spinbox)
        return base_widget

    def set_wait_time_from_spinbox(self):
        self.wait_time = self.spin_box.value()

    def execute(self, dte: DataToExport = None):
        self.timer.setInterval(int(self.spin_box.value() * 1000))
        self.timer.start()

    def done(self):
        self.done_signal.emit(
            DataToExport(self.__class__.__name__,
                         data=[DataRaw('wait_time',
                                       data=[np.atleast_1d(self.spin_box.value())],
                                       units='s')]))

    def serialize_custom(self) -> bytes:
        """Serialize the custom part of the element

        to be reimplemented
        """
        return ser_factory.get_apply_serializer(self.wait_time)

    def deserialize_custom(self, bytes_str: bytes) -> bytes:
        """Deserialize the custom part of the element to finish initialization using setters, attribute assignment
        or methods

        to be reimplemented

        Returns
        -------
        bytes: the remaining bytes string if any
        """
        wait_time, remaining_bytes = ser_factory.get_apply_deserializer(bytes_str, False)
        self.wait_time = wait_time
        return remaining_bytes

    def _eq(self, other: 'WaitElt'):
        """ Custom method to reimplement to assert two elements are equals"""
        return self.wait_time == other.wait_time
