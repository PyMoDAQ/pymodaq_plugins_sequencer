from typing import Any
import weakref

from serializall import SerializableFactory

from qtpy import QtCore

from control_modules.daq_viewer import DAQ_Viewer
from control_modules.daq_viewer_ui.ui_base import ActionIconNames
from pymodaq_utils.logger import set_logger, get_module_name

from pymodaq_data import DataToExport
from pymodaq_gui.parameter.pymodaq_ptypes.itemselect import ItemSelect


from pymodaq_plugins_sequencer.utilities.element_factory import SeqEltBase, SeqEltFactory
from pymodaq_plugins_sequencer.utilities.widget_with_toolbar import WidgetWithToolbar
from qt_themes import get_theme
from pymodaq.utils.managers.modules_manager import ModulesManager
from utils.managers.modules import ModuleType

ser_factory = SerializableFactory()
logger = set_logger(get_module_name(__file__))


@SerializableFactory.register_decorator()
@SeqEltFactory.register_elt()
class GrabElt(SeqEltBase):

    elt_name = 'grab'
    children_allowed = False

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.modules_manager = ModulesManager()
        self._detectors: list[str] = []
        self._selected: list[str] = []

        self._is_continuous_grab = False
        self._stop_status = False

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

    @property
    def is_continuous_grab(self) -> bool:
        return self._is_continuous_grab

    @is_continuous_grab.setter
    def is_continuous_grab(self, continuous: bool):
        self._is_continuous_grab = continuous

    def set_grab_state(self, continuous: bool):
        self.is_continuous_grab = continuous

    @property
    def stop_status(self) -> bool:
        return self._stop_status

    @stop_status.setter
    def stop_status(self, stop_status: bool):
        self._stop_status = stop_status

    def set_stop_status(self, stop_status: bool):
        self.stop_status = stop_status


    def do_things_with_dashboard(self):
        self.dashboard.experiment_manager.applied_entry.connect(self.update_modules)
        self.update_modules()

    def update_modules(self):
        self.modules_manager.detectors_all = self.dashboard.modules_manager.detectors_all
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

    def _create_widget(self, base_widget: WidgetWithToolbar) -> WidgetWithToolbar:
        item_select = ItemSelect(hasCheckbox=True, parent=base_widget)
        self._items = weakref.ref(item_select)
        item_select.set_value(dict(all_items=self.detectors,
                                   selected = self.selected,))
        item_select.itemChanged.connect(self.update_detectors_from_combo)
        base_widget.insert_widget(item_select)

        base_widget.add_action('snap', 'Snap/Grab',
                        icon_name=ActionIconNames.SNAP,
                        icon_checked=ActionIconNames.GRAB,
                        checked=self.is_continuous_grab,
                        tip='Snap or continuous Grab',
                        toolbar=base_widget.toolbar)

        base_widget.connect_action('snap', self.set_grab_state)

        base_widget.add_action('stop', 'Stop',
                        icon_name='stop_circle',
                        tip='Stop any current Grab on the selected detectors',
                        icon_checked_color=get_theme().red,
                        checkable=True,
                        checked=self.stop_status,
                        toolbar=base_widget.toolbar)

        base_widget.connect_action('stop', self.set_stop_status)

        return base_widget

    def update_detectors_from_combo(self):
        if self._items is not None and self._items() is not None:
            self.selected = self._items().get_value()['selected']

    def clean_signals(self):
        for mod in self.get_selected_detectors():
            try:
                mod.grab_done_signal.disconnect(self._save_data)
            except TypeError as e:
                pass

    def get_selected_detectors(self) -> list[DAQ_Viewer]:
        return [self.modules_manager.get_mod_from_name(det, mod=ModuleType.Detector) for det in self.selected]

    def _execute(self, dte: DataToExport=None):
        self.filter_selected_wrt_manager()
        self.clean_signals()

        if len(self.selected) > 0:
            if self.stop_status:
                for mod in self.get_selected_detectors():
                    mod.stop()
                self.clean_signals()
                self.done_signal.emit()

            else:
                if not self.is_continuous_grab:
                    self.modules_manager.selected_detectors_name = self.selected
                    self.modules_manager.connect_detectors()
                    dte = self.modules_manager.grab_data()
                    self.modules_manager.connect_detectors(False)
                    self.save_signal.emit(dte)
                else:
                    for mod in self.get_selected_detectors():
                        mod.grab_done_signal.connect(self._save_data)
                        mod.grab()
                    self.done_signal.emit()
        else:
            self.done_signal.emit()


    def _save_data(self, dte: DataToExport):
        #todo: do whatever is needed with those data,
        # probably add them in a Queue (like the ramping extension)
        # could also be done into another state (saving_state for instance), to do the saving. However
        # it is not necessary to hold the machine to save if using the Queue mechanism
        pass

    def to_dict_custom(self) -> dict[str, Any]:
        """ adds attribute to a dict in order to produce a human readable
        representation/configuration for this element

        to be reimplemented
        """
        return {'detectors': self.detectors,
                'selected': self.selected,
                'continuous_grab': self.is_continuous_grab,
                'stop': self.stop_status,}

    def from_dict_custom(self, dict_config: dict[str, Any]):
        """ Create/set the custom part of the element to finish initialization
        using setters, attribute assignment or methods
        """
        self.detectors = dict_config.pop('detectors', [])
        self.selected = dict_config.pop('selected', [])
        self.is_continuous_grab = dict_config.pop('continuous_grab', False)
        self.stop_status = dict_config.pop('stop', False)

    def _eq(self, other: 'GrabElt'):
        """ Custom method to reimplement to assert two elements are equals"""
        return (self.detectors == other.detectors and
                self.selected == other.selected)

    def __repr__(self):
        return f"{super().__repr__()} - {self.selected} - {'Stop' if self.stop_status else 'Grab' if self.is_continuous_grab else 'Snap'}"

    def size_hint(self) -> QtCore.QSize:
        return QtCore.QSize(250, 250)

    def check_set_is_valid(self):
        """ Check the validity of the element

        Will be called before executing the element. Try to make sure the element is valid or return None
        if the user may do something!
        """
        return None
