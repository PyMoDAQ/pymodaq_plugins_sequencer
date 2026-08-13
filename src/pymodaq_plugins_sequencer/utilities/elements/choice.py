from typing import TYPE_CHECKING
import numpy as np
import weakref
from pyqtgraph import mkColor

from qtpy import QtWidgets, QtCore
from serializall import SerializableFactory


from pymodaq_data import DataToExport, DataWithAxes, DataRaw
from pymodaq_gui.managers.parameter_manager import ParameterManager
from pymodaq_gui.utils.widgets import SpinBox

from qt_themes import get_theme
from pymodaq.utils.managers.modules_manager import ModulesManager
from pymodaq_gui.utils.widgets.combo import ComboBox
from pymodaq_plugins_sequencer.utilities.choice_models.model import ChoiceModelBase
from pymodaq_plugins_sequencer.utilities.choice_models.factory import ChoiceModelFactory
from pymodaq_plugins_sequencer.utilities.element_factory import SeqEltBase, SeqEltFactory
from pymodaq_plugins_sequencer.utilities.elements.grab import GrabElt
from pymodaq_plugins_sequencer.utilities.states import ValueTransition
from pymodaq_plugins_sequencer.utilities.widget_with_toolbar import WidgetWithToolbar


ser_factory = SerializableFactory()
choice_factory = ChoiceModelFactory()


@SerializableFactory.register_decorator()
@SeqEltFactory.register_elt()
class ChoiceElt(GrabElt):

    elt_name = 'choice'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._choice_model: ChoiceModelBase = None
        self.settings: weakref.ref = None

        self._go_to_true: int = 1
        self._go_to_false: int = 2

        self.value_true_transition = ValueTransition(
            self.go_to_signal, True,
            self.get_elt_from_id(self.go_to_true).mstate)

        self.value_false_transition = ValueTransition(
            self.go_to_signal, False,
            self.get_elt_from_id(self.go_to_false).mstate)



        self.mstate.addTransition(self.value_true_transition)
        self.mstate.addTransition(self.value_false_transition)

    @property
    def choice_model(self) -> ChoiceModelBase:
        if self._choice_model is None:
            self._choice_model = choice_factory.get_model(choice_factory.models[0])()
        return self._choice_model

    @choice_model.setter
    def choice_model(self, value: str):
        self._choice_model = choice_factory.get_model(value)()
        if self.settings is not None and self.settings() is not None:
            self.settings().settings = self._choice_model.settings
            self.settings().tree.setMinimumHeight(len(self.settings().settings.children()) * 50)

    def set_choice_model(self, value: str):
        self.choice_model = value

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

        combo = ComboBox()
        combo.addItems(choice_factory.models)
        combo.setCurrentText(choice_factory.models[0])
        base_widget.add_widget_top(combo)

        parameter = ParameterManager()
        self.settings = weakref.ref(parameter)
        parameter.settings = self.choice_model.settings
        parameter.tree.setMinimumHeight(len(parameter.settings.children()) * 50)
        base_widget.insert_widget(parameter.settings_tree, 2)
        combo.currentTextChanged.connect(self.set_choice_model)

        return base_widget

    def set_go_to_true_from_spinbox(self, spinbox: SpinBox):
        self.go_to_true = spinbox.value()

    def set_go_to_false_from_spinbox(self, spinbox: SpinBox):
        self.go_to_false = spinbox.value()

    def _save_data(self, dte: DataToExport = None):
        choice_bool = self.choice_model.process_dte(dte)
        self.go_to_signal.emit(self.go_to_true if choice_bool else self.go_to_false)

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

    def set_value_transition(self):
        self.value_false_transition.value = self.go_to_false
        self.value_true_transition.value = self.go_to_true

    def _execute(self, dte: DataToExport=None):
        self.set_value_transition()

        # get data from detectors if needed by the model
        self.filter_selected_wrt_manager()
        if len(self.selected) > 0:
            self.modules_manager.selected_detectors_name = self.selected
            self.modules_manager.connect_detectors()
            dte = self.modules_manager.grab_data()
            self.modules_manager.connect_detectors(False)
        else:
            dte = DataToExport('Grab')

        boolean_result = self.choice_model.process_dte(dte)
        self.go_to_signal.emit(self.go_to_true if boolean_result else self.go_to_false)


