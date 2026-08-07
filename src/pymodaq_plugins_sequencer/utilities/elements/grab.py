import weakref
from serializall import SerializableFactory

from qtpy import QtCore

from pymodaq.utils.managers.modules import ModuleType
from pymodaq_data import DataToExport
from pymodaq_gui.parameter.pymodaq_ptypes.itemselect import ItemSelect
from pymodaq_plugins_sequencer.utilities.element_factory import SeqEltBase, SeqEltFactory
from pymodaq_plugins_sequencer.utilities.widget_with_toolbar import WidgetWithToolbar
from qt_themes import get_theme
from pymodaq.utils.managers.modules_manager import ModulesManager

ser_factory = SerializableFactory()


@SeqEltFactory.register_elt()
class GrabElt(SeqEltBase):

    elt_name = 'grab'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.modules_manager = ModulesManager()
        self._items: weakref.ref[ItemSelect] = None

    def do_things_with_dashboard(self):
        self.modules_manager.detectors_all = self.dashboard.modules_manager.detectors_all
        self.modules_manager.actuators_all = self.dashboard.modules_manager.actuators_all

        for child_name in ('actuators', 'probe_data', 'test_actuator'):
            self.modules_manager.settings.child(child_name).show(False)
        self.modules_manager.settings_tree.setVisible(False)

        self.dashboard.experiment_manager.applied_entry.connect(self.update_detectors)

    def _create_widget(self, base_widget:WidgetWithToolbar) -> WidgetWithToolbar:
        item_select = ItemSelect(hasCheckbox=True, parent=base_widget)
        self._items = weakref.ref(item_select)
        item_select.set_value(dict(all_items=self.modules_manager.detectors_name,
                                   selected = self.modules_manager.selected_detectors_name,))
        item_select.itemChanged.connect(self.update_detectors_from_combo)
        base_widget.top_layout.addWidget(item_select)
        return base_widget

    def update_detectors_from_combo(self):
        if self._items is not None and self._items() is not None:
            self.modules_manager.selected_detectors_name = self._items().get_value()['selected']

    def execute(self, dte: DataToExport=None):
        self.modules_manager.connect_detectors()
        dte = self.modules_manager.grab_data()
        self.modules_manager.connect_detectors(False)
        self.done_signal.emit(dte)

    def update_detectors(self):
        self.modules_manager.detectors_all = self.dashboard.modules_manager.detectors_all
        self.modules_manager.selected_detectors_name = self.dashboard.modules_manager.detectors_all
        self.modules_manager.actuators_all = self.dashboard.modules_manager.actuators_all
        self.modules_manager.selected_actuators_name = self.dashboard.modules_manager.actuators_all

    def serialize_custom(self) -> bytes:
        """Serialize the custom part of the element

        to be reimplemented
        """
        detectors = self.modules_manager.detectors_name
        selected = self.modules_manager.selected_detectors_name

        bytes = ser_factory.get_apply_serializer(detectors)
        bytes += ser_factory.get_apply_serializer(selected)
        return bytes

    def deserialize_custom(self, bytes_str: bytes) -> bytes:
        """Deserialize the custom part of the element to finish initialization using setters, attribute assignment
        or methods

        to be reimplemented

        Returns
        -------
        bytes: the remaining bytes string if any
        """
        detectors, remaining_bytes = ser_factory.get_apply_deserializer(bytes_str, False)
        selected, remaining_bytes = ser_factory.get_apply_deserializer(bytes_str, False)
        self.modules_manager.detectors_all = [self.modules_manager.get_mod_from_name(det, ModuleType.Detector)
                                              for det in detectors]
        self.modules_manager.selected_detectors_name = selected

        return remaining_bytes

    def _eq(self, other: 'GrabElt'):
        """ Custom method to reimplement to assert two elements are equals"""
        return (self.modules_manager.detectors_name == other.modules_manager.detectors_name and
                self.modules_manager.selected_detectors_name == other.modules_manager.selected_detectors_name)

    def __repr__(self):
        return f'{super().__repr__()} - {self.modules_manager.selected_detectors_name}'

    def size_hint(self) -> QtCore.QSize:
        size = super().size_hint()
        return QtCore.QSize(250, 100)