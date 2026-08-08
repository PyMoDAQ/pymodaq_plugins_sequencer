import weakref

from qtpy import QtCore
from qt_themes import get_theme
from serializall import SerializableFactory

from pymodaq_data import DataToExport
from pymodaq.utils.managers.state.state_manager import StateManager
from pymodaq_gui.managers.manager_base import ManagerActions
from pymodaq_gui.utils.widgets.combo import ComboBox

from pymodaq_plugins_sequencer.utilities.element_factory import SeqEltBase, SeqEltFactory
from pymodaq_plugins_sequencer.utilities.widget_with_toolbar import WidgetWithToolbar


ser_factory = SerializableFactory()


@SeqEltFactory.register_elt()
class StateElt(SeqEltBase):

    elt_name = 'state'
    children_allowed = False

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.state_manager = StateManager()

        self._state = self.state_manager.entry
        self._combo: weakref.ref[ComboBox] | None = None  # weakref to the combobox holding the states

    @property
    def state(self) -> str:
        return self._state

    @state.setter
    def state(self, value: str):
        self._state = value

    @property
    def states(self) -> list[str]:
        return self.state_manager.entries[:]

    def update_states(self):
        if self._combo is not None and self._combo() is not None:
            self._combo().set_items(self.states)

    @QtCore.Slot(str)
    def set_state(self, value: str):
        self.state = value

    def do_things_with_dashboard(self):
        self.state_manager: 'StateManager' = self.dashboard.state_manager
        self.state_manager.applied_entry.connect(
            lambda: self.done_signal.emit(DataToExport('StateElt')))
        self.state_manager.new_entry.connect(self.update_states)


    def _create_widget(self, base_widget:WidgetWithToolbar) -> WidgetWithToolbar:

        self.add_action('show_state', 'Show Manager', self.state_manager.icon_name,
                        "Show State Manager",
                        checkable=True, icon_checked_color=get_theme().green,
                        toolbar=base_widget.toolbar)
        self.connect_action('show_state', self.state_manager.force_show)
        combo = ComboBox(base_widget)
        combo.set_items(self.state_manager.entries)
        base_widget.add_widget_top(combo)
        combo.setCurrentText(self.state)
        combo.currentTextChanged.connect(self.set_state)
        self._combo = weakref.ref(combo)
        self.state_manager.parent.closeEvent = lambda event: self.set_action_checked('show_state', False)

        return base_widget

    def execute(self, dte: DataToExport):
        self.state_manager.entry = self.state
        self.state_manager.execute_entry()

    def serialize_custom(self) -> bytes:
        """Serialize the custom part of the element

        to be reimplemented
        """
        bytes = ser_factory.get_apply_serializer(self.state_manager.entry)
        bytes += ser_factory.get_apply_serializer(self.state_manager.experiment_filename)
        return bytes

    def deserialize_custom(self, bytes_str: bytes) -> bytes:
        """Deserialize the custom part of the element to finish initialization using setters, attribute assignment
        or methods

        to be reimplemented

        Returns
        -------
        bytes: the remaining bytes string if any
        """
        entry, remaining_bytes = ser_factory.get_apply_deserializer(bytes_str, False)
        experiment, remaining_bytes = ser_factory.get_apply_deserializer(remaining_bytes, False)
        self.state_manager.experiment_filename = experiment
        self.state_manager.entry = entry

        return remaining_bytes


    def _eq(self, other: 'StateElt'):
        """ Custom method to reimplement to assert two elements are equals"""
        return (self.state_manager.entry == other.state_manager.entry and
                self.state_manager.experiment_filename == other.state_manager.experiment_filename)

    def __repr__(self):
        return f'{super().__repr__()} - {self.state}'


    def size_hint(self) -> QtCore.QSize:
        size = super().size_hint()
        return QtCore.QSize(250, size.height())