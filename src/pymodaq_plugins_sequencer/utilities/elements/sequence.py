import weakref
from typing import TYPE_CHECKING, Any
import numpy as np

from qtpy import QtWidgets, QtCore

from serializall import SerializableFactory
from pymodaq_data import DataToExport, DataWithAxes, DataRaw
from pymodaq_gui.utils.widgets import SpinBox
from pymodaq_gui.utils.widgets.combo import ComboBox
from pymodaq_plugins_sequencer.utilities.element_factory import SeqEltBase, SeqEltFactory, ElementError
from pymodaq_plugins_sequencer.utilities.widget_with_toolbar import WidgetWithToolbar


ser_factory = SerializableFactory()

@SerializableFactory.register_decorator()
@SeqEltFactory.register_elt()
class SequenceElt(SeqEltBase):

    elt_name = 'sequence'
    children_allowed = False
    sequences: list[str] = []

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._sequence: str = None if len(self.get_sequences()) == 0 else self.get_sequences()[0]

        self._combo: weakref.ref[ComboBox] | None = None  # weakref to the combobox holding the states

    def get_sequences(self):
        """ Get the list of Sequences that can be started, removing the one this element belong to"""
        sequences = self.sequences[:]
        if self.parent_app is not None:
            sequences.remove(self.parent_app.title)
        return sequences

    def do_things_with_parent_app(self):
        """ If this Element is using the Dashboard, once its setter has been called, this method will be executed

        Do whatever is needed to instantiate your element with the Dashboard
        """
        self._sequence: str = None if len(self.get_sequences()) == 0 else self.get_sequences()[0]

    @property
    def sequence(self) -> str:
        return self._sequence

    @sequence.setter
    def sequence(self, value: str):
        self._sequence = value

    def update_combo_sequences(self):
        if self._combo is not None and self._combo() is not None:
            self._combo().set_items(self.sequences)

    @QtCore.Slot(str)
    def set_sequence(self, value: str):
        self.sequence = value

    def do_things_with_dashboard(self):
        pass

    def _create_widget(self, base_widget:WidgetWithToolbar) -> WidgetWithToolbar:

        combo = ComboBox(base_widget)
        combo.set_items(self.get_sequences())
        base_widget.add_widget_top(combo)
        combo.setCurrentText(self.sequence)
        combo.currentTextChanged.connect(self.set_sequence)
        self._combo = weakref.ref(combo)

        return base_widget

    def _execute(self, dte: DataToExport = None):
        # to do connect to other Sequence State Machine...
        pass

    def to_dict_custom(self) -> dict[str, Any]:
        """ adds attribute to a dict in order to produce a human readable
        representation/configuration for this element

        to be reimplemented
        """
        return {'sequence': self.sequence,
                'sequences': self.sequences, }

    def from_dict_custom(self, dict_config: dict[str, Any]):
        """ Create/set the custom part of the element to finish initialization
        using setters, attribute assignment or methods
        """
        self.sequences = dict_config.pop('sequences')
        self.sequence = dict_config.pop('sequence')

    def _eq(self, other: 'SequenceElt'):
        """ Custom method to reimplement to assert two elements are equals"""
        return (self.sequences == other.sequences and
                self.sequence == other.sequence)

    def __repr__(self):
        return f'{super().__repr__()} - {self.sequence}'

    def check_set_is_valid(self) -> bool:
        """ Check the validity of the element

        Will be called before executing the element. Try to make sure the element is valid or return None
        if the user may do something!
        """
        pass