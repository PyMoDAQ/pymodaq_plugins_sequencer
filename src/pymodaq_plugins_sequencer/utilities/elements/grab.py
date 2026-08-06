from serializall import SerializableFactory

from pymodaq.utils.managers.modules import ModuleType
from pymodaq_data import DataToExport
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

    def do_things_with_dashboard(self):
        self.modules_manager.detectors_all = self.dashboard.modules_manager.detectors_all
        self.modules_manager.actuators_all = self.dashboard.modules_manager.actuators_all

        for child_name in ('actuators', 'probe_data', 'test_actuator'):
            self.modules_manager.settings.child(child_name).show(False)
        self.modules_manager.settings_tree.setVisible(False)

        self.dashboard.experiment_manager.applied_entry.connect(self.update_detectors)

    def _create_widget(self, base_widget:WidgetWithToolbar) -> WidgetWithToolbar:
        # base_widget.insert_widget(self.modules_manager.settings_tree, 1)
        self.add_action('show_settings', 'Show Settings', 'settings', "Show Settings",
                        checkable=True, icon_checked_color=get_theme().green,
                        toolbar=base_widget.toolbar)
        self.connect_action('show_settings', self.modules_manager.settings_tree.setVisible)
        return base_widget

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
