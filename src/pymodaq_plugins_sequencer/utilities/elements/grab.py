import weakref
from serializall import SerializableFactory

from qtpy import QtCore

from pymodaq_utils.logger import set_logger, get_module_name
from pymodaq.utils.managers.modules import ModuleType
from pymodaq_data import DataToExport
from pymodaq_gui.parameter.pymodaq_ptypes.itemselect import ItemSelect
from pymodaq_gui.utils.widgets import SpinBox
from pymodaq_plugins_sequencer.utilities.element_factory import SeqEltBase, SeqEltFactory
from pymodaq_plugins_sequencer.utilities.widget_with_toolbar import WidgetWithToolbar
from qt_themes import get_theme
from pymodaq.utils.managers.modules_manager import ModulesManager

ser_factory = SerializableFactory()
logger = set_logger(get_module_name(__file__))

@SeqEltFactory.register_elt()
class GrabElt(SeqEltBase):

    elt_name = 'grab'
    children_allowed = False

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.modules_manager = ModulesManager()
        self._detectors: list[str] = []
        self._selected: list[str] = []

        self._items: weakref.ref[ItemSelect] = None
        for child_name in ('actuators', 'probe_data', 'test_actuator'):
            self.modules_manager.settings.child(child_name).show(False)
        self.modules_manager.settings_tree.setVisible(False)

    @property
    def detectors(self) -> list[str]:
        return self._detectors

    @detectors.setter
    def detectors(self, value: list[str]):
        self._detectors = value

    @property
    def selected(self) -> list[str]:
        return self._selected

    @selected.setter
    def selected(self, value: list[str]):
        self._selected = value

    def do_things_with_dashboard(self):
        self.dashboard.experiment_manager.applied_entry.connect(self.update_detectors)
        self.update_detectors()

    def update_detectors(self):
        self.modules_manager.detectors_all = self.dashboard.modules_manager.detectors_all
        self.modules_manager.selected_detectors_name = self.dashboard.modules_manager.detectors_all
        self.detectors = self.modules_manager.detectors_name
        self.filter_selected_wrt_manager()

    def filter_selected_wrt_manager(self):
        """  Filter selected given the presence of the detector in the manager """
        selected = []
        for sel in self.selected:
            if sel in self.modules_manager.detectors_name:
                selected.append(sel)
            else:
                logger.warning(f'Could not select the detector: {sel} as not declared in '
                               f'the ModulesManager instance/ DashBoard')
        self.selected = selected

    def _create_widget(self, base_widget:WidgetWithToolbar) -> WidgetWithToolbar:
        item_select = ItemSelect(hasCheckbox=True, parent=base_widget)
        self._items = weakref.ref(item_select)
        item_select.set_value(dict(all_items=self.modules_manager.detectors_name,
                                   selected = self.modules_manager.selected_detectors_name,))
        item_select.itemChanged.connect(self.update_detectors_from_combo)
        base_widget.insert_widget(item_select)
        return base_widget

    def update_detectors_from_combo(self):
        if self._items is not None and self._items() is not None:
            self.selected = self._items().get_value()['selected']

    def execute(self, dte: DataToExport=None):
        self.filter_selected_wrt_manager()
        if len(self.selected) > 0:
            self.modules_manager.selected_detectors_name = self.selected
            self.modules_manager.connect_detectors()
            dte = self.modules_manager.grab_data()
            self.modules_manager.connect_detectors(False)
            self.done_signal.emit(dte)
        else:
            self.done_signal.emit(DataToExport('GrabElt'))

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
        selected, remaining_bytes = ser_factory.get_apply_deserializer(remaining_bytes, False)
        self.detectors = detectors
        self.selected = selected

        return remaining_bytes

    def _eq(self, other: 'GrabElt'):
        """ Custom method to reimplement to assert two elements are equals"""
        return (self.detectors == other.detectors and
                self.selected == other.selected)

    def __repr__(self):
        return f'{super().__repr__()} - {self.selected}'

    def size_hint(self) -> QtCore.QSize:
        return QtCore.QSize(250, 250)