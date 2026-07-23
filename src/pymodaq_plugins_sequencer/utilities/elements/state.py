from typing import TYPE_CHECKING

from PySide6.QtWidgets import QWidget
from qtpy import QtWidgets


from pymodaq_plugins_sequencer.utilities.element_factory import SeqEltBase, SeqEltFactory
from pymodaq_plugins_sequencer.utilities.widget_with_toolbar import WidgetWithToolbar

if TYPE_CHECKING:
    from pymodaq.utils.managers.state.state_manager import StateManager

@SeqEltFactory.register_elt()
class StateElt(SeqEltBase):

    name = 'state'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.state_manager: 'StateManager' = self.dashboard.state_manager

    def _create_widget(self, base_widget:WidgetWithToolbar) -> WidgetWithToolbar:
        ext_toolbar, _ = self.state_manager.get_external_toolbar_menu()
        base_widget.add_widget_top(ext_toolbar)
        ext_toolbar.setEnabled(True)
        return base_widget