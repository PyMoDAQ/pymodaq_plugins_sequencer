from typing import TYPE_CHECKING
import numpy as np
from pyqtgraph import mkColor

from qtpy import QtWidgets, QtCore
from serializall import SerializableFactory


from pymodaq_data import DataToExport, DataWithAxes, DataRaw
from pymodaq_gui.utils.widgets import SpinBox

from qt_themes import get_theme
from pymodaq.utils.managers.modules_manager import ModulesManager
from pymodaq_plugins_sequencer.utilities.element_factory import SeqEltBase, SeqEltFactory
from pymodaq_plugins_sequencer.utilities.elements.grab import GrabElt
from pymodaq_plugins_sequencer.utilities.widget_with_toolbar import WidgetWithToolbar


ser_factory = SerializableFactory()


@SerializableFactory.register_decorator()
@SeqEltFactory.register_elt()
class ChoiceElt(GrabElt):

    elt_name = 'choice'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._go_to_true: int = 100
        self._go_to_false: int = 100

    @property
    def go_to_true(self) -> int:
        return self._go_to_true

    @go_to_true.setter
    def go_to_true(self, value: int):
        self._go_to_true = value

    @property
    def go_to_false(self) -> int:
        return self._go_to_false

    @go_to_false.setter
    def go_to_false(self, value: int):
        self._go_to_false = value

    def _create_widget(self, base_widget:WidgetWithToolbar) -> WidgetWithToolbar:
        base_widget = super()._create_widget(base_widget)
        spin_box_true = SpinBox(int=True, value=self.go_to_true)
        spin_box_true.setMinimum(0)
        spin_box_true.setStyleSheet(
            f"background-color: #{hex(mkColor(get_theme().green).rgb())[2:]};")
        spin_box_true.setToolTip('Go to this elt number if True')
        spin_box_true.sigValueChanged.connect(self.set_go_to_true_from_spinbox)
        base_widget.add_widget_top(spin_box_true)

        spin_box_false = SpinBox(int=True, value=self.go_to_false)
        spin_box_false.setMinimum(0)
        spin_box_false.setStyleSheet(
            f"background-color: #{hex(mkColor(get_theme().red).rgb())[2:]};")
        spin_box_false.setToolTip('Go to this elt number if False')
        base_widget.add_widget_top(spin_box_false)
        spin_box_false.sigValueChanged.connect(self.set_go_to_false_from_spinbox)

        return base_widget

    def set_go_to_true_from_spinbox(self, spinbox: SpinBox):
        self.go_to_true = spinbox.value()

    def set_go_to_false_from_spinbox(self, spinbox: SpinBox):
        self.go_to_false = spinbox.value()

    def _save_data(self, dte: DataToExport = None):
        pass

    def serialize_custom(self) -> bytes:
        """Serialize the custom part of the element

        to be reimplemented
        """
        bytes_to_ser = super().serialize_custom()
        bytes_to_ser += ser_factory.get_apply_serializer(self.go_to_true)
        bytes_to_ser += ser_factory.get_apply_serializer(self.go_to_false)
        return bytes_to_ser

    def deserialize_custom(self, bytes_str: bytes) -> bytes:
        """Deserialize the custom part of the element to finish initialization using setters, attribute assignment
        or methods

        to be reimplemented

        Returns
        -------
        bytes: the remaining bytes string if any
        """
        remaining_bytes = super().deserialize_custom(bytes_str)

        go_true, remaining_bytes = ser_factory.get_apply_deserializer(remaining_bytes, False)
        go_false, remaining_bytes = ser_factory.get_apply_deserializer(remaining_bytes, False)
        self.go_to_false = go_false
        self.go_to_true = go_true
        return remaining_bytes

    def _eq(self, other: 'ChoiceElt') -> bool:
        """ Custom method to reimplement to assert two elements are equals"""
        status =  super()._eq(other)
        if not (hasattr(other, 'go_to_true') or hasattr(other, 'go_to_false')):
            return False
        return self.go_to_false == other.go_to_false and self.go_to_true == other.go_to_true

    def __repr__(self):
        return f'{super().__repr__()} - True: {self.go_to_true} - False: {self.go_to_false}'


