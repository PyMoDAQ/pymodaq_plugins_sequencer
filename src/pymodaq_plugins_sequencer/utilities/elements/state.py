from typing import TYPE_CHECKING

from PySide6.QtWidgets import QWidget
from qtpy import QtWidgets

from pymodaq_data import DataToExport
from pymodaq_plugins_sequencer.utilities.element_factory import SeqEltBase, SeqEltFactory
from pymodaq_plugins_sequencer.utilities.widget_with_toolbar import WidgetWithToolbar

if TYPE_CHECKING:
    from pymodaq.utils.managers.state.state_manager import StateManager

@SeqEltFactory.register_elt()
class StateElt(SeqEltBase):

    elt_name = 'state'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.state_manager: 'StateManager' = self.dashboard.state_manager
        self.state_manager.applied_entry.connect(
            lambda: self.done_signal.emit(DataToExport('StateElt')))

    def _create_widget(self, base_widget:WidgetWithToolbar) -> WidgetWithToolbar:
        self.state_manager.get_external_toolbar_menu(toolbar=base_widget.toolbar)
        self.set_action_visible('execute', False)
        return base_widget

    def execute(self, dte: DataToExport):
        pass # no need here as the execution is handled by the State Manager execute action