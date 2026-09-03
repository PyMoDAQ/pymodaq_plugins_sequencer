import weakref
from typing import Any

from serializall import SerializableFactory

from qtpy import QtCore

from control_modules.enums import MoveType
from pymodaq.utils.managers.modules import ModuleType
from pymodaq.utils.scanner.scanner import Orientation
from pymodaq_data import DataToExport
from pymodaq_gui.parameter.pymodaq_ptypes.itemselect import ItemSelect
from pymodaq_gui.utils.widgets import SpinBox
from pymodaq_plugins_sequencer.utilities.element_factory import SeqEltBase, SeqEltFactory, ElementError
from pymodaq_plugins_sequencer.utilities.elements.repeat import RepeatElt
from pymodaq_plugins_sequencer.utilities.widget_with_toolbar import WidgetWithToolbar
from qt_themes import get_theme
from pymodaq.utils.managers.modules_manager import ModulesManager
from pymodaq.utils.scanner import Scanner


ser_factory = SerializableFactory()


@SerializableFactory.register_decorator()
@SeqEltFactory.register_elt()
class ScannerElt(SeqEltBase):

    elt_name = 'scanner'
    children_allowed = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._ind_execute = 0
        self.scanner = Scanner()
        self.scanner_ref: weakref.ref[Scanner] = None

    def initialize_element(self):
        self._ind_execute = 0

    def do_things_with_dashboard(self):
        self.scanner.actuators_all = self.dashboard.modules_manager.actuators_all

    def _create_widget(self, base_widget: WidgetWithToolbar) -> WidgetWithToolbar:
        self.scanner_ref = weakref.ref(Scanner(actuators=self.scanner.actuators_all,
                                               selected_actuators=self.scanner.actuators,
                                               orientation=Orientation.HORIZONTAL))
        base_widget.insert_widget(self.scanner_ref().parent_widget)
        self.scanner_ref().settings.child('actuators').show()

        self.scanner_ref().from_dict(self.scanner.to_dict(use_real_actuators=True))

        self.scanner_ref().settings_updated_signal.connect(self._on_scanner_editor_update)
        return base_widget

    def _on_scanner_editor_update(self):
        if self.scanner_ref is not None and self.scanner_ref() is not None:
            self.scanner.from_dict(self.scanner_ref().to_dict(use_real_actuators=True))

    def _execute(self, dte: DataToExport=None):
        if self._ind_execute == 0:
            self.scanner.set_scan()

        if self._ind_execute < self.scanner.n_steps:
            next_values = self.scanner.positions_at(self._ind_execute)
            self.dashboard.modules_manager.move_actuators_with_callback(
                dte_act = next_values,
                mode= MoveType.ABS,
                callback = None,
                do_connect_modules=True)

            """ This will execute the children state and its bundled elements n_repeat times"""
            self._ind_execute += 1
        else:
            self._ind_execute = 0
            self.done_signal.emit()

    def _on_move_done(self):
        self.children_signal.emit()

    def to_dict_custom(self) -> dict[str, Any]:
        """ adds attribute to a dict in order to produce a human readable
        representation/configuration for this element

        to be reimplemented
        """
        return self.scanner.to_dict()

    def from_dict_custom(self, dict_config: dict[str, Any]):
        """ Create/set the custom part of the element to finish initialization
        using setters, attribute assignment or methods
        """
        self.scanner.from_dict(dict_config)

    def _eq(self, other: 'ScannerElt'):
        """ Custom method to reimplement to assert two elements are equals"""
        return self.scanner.to_dict() == other.scanner.to_dict()

    def __repr__(self):
        return f'{super().__repr__()} - {self.scanner}'

    def check_set_is_valid(self):
        """ Check the validity of the element

        Will be called before executing the element. Try to make sure the element is valid or return None
        if the user may do something!
        """
        self.scanner.set_scan()
        if not (self.scanner.n_steps >= 1):
            raise ElementError(f'Element {self}: at least one scan step required')

    def size_hint(self) -> QtCore.QSize:
        return QtCore.QSize(200, 300)
