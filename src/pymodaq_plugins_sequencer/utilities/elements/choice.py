from typing import TYPE_CHECKING
import numpy as np
from pyqtgraph import mkColor

from qtpy import QtWidgets, QtCore

from pymodaq_data import DataToExport, DataWithAxes, DataRaw
from pymodaq_gui.utils.widgets import SpinBox
from pymodaq_plugins_sequencer.utilities.element_factory import SeqEltBase, SeqEltFactory
from pymodaq_plugins_sequencer.utilities.widget_with_toolbar import WidgetWithToolbar
from qt_themes import get_theme
from pymodaq.utils.managers.modules_manager import ModulesManager


@SeqEltFactory.register_elt()
class ChoiceElt(SeqEltBase):

    elt_name = 'choice'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def _create_widget(self, base_widget:WidgetWithToolbar) -> WidgetWithToolbar:
        self.spin_box_true = SpinBox(int=True)
        self.spin_box_true.setMinimum(0)
        self.spin_box_true.setStyleSheet(
            f"background-color: #{hex(mkColor(get_theme().green).rgb())[2:]};")
        self.add_widget('true', self.spin_box_true,
                        tip='Go to if True',
                        toolbar=base_widget.toolbar)
        self.spin_box_false = SpinBox(int=True)
        self.spin_box_false.setMinimum(0)
        self.spin_box_false.setStyleSheet(
            f"background-color: #{hex(mkColor(get_theme().red).rgb())[2:]};")
        self.add_widget('false', self.spin_box_false,
                        tip='Go to if False',
                        toolbar=base_widget.toolbar)
        return base_widget

    def execute(self, dte: DataToExport = None):
        pass

