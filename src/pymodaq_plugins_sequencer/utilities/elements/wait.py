from typing import TYPE_CHECKING
import numpy as np

from qtpy import QtWidgets, QtCore

from pymodaq_data import DataToExport, DataWithAxes, DataRaw
from pymodaq_gui.utils.widgets import SpinBox
from pymodaq_plugins_sequencer.utilities.element_factory import SeqEltBase, SeqEltFactory
from pymodaq_plugins_sequencer.utilities.widget_with_toolbar import WidgetWithToolbar
from qt_themes import get_theme
from pymodaq.utils.managers.modules_manager import ModulesManager


@SeqEltFactory.register_elt()
class WaitElt(SeqEltBase):

    name = 'wait'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.timer = QtCore.QTimer()
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.done)

    def _create_widget(self, base_widget:WidgetWithToolbar) -> WidgetWithToolbar:
        self.spin_box = SpinBox(int=False, suffix='s', siPrefix=True)
        base_widget.add_widget('wait_time', self.spin_box,
                               tip='wait time')
        return base_widget

    def execute(self):
        self.timer.setInterval(int(self.spin_box.value() * 1000))
        self.timer.start()

    def done(self):
        self.done_signal.emit(
            DataToExport(self.__class__.__name__,
                         data=[DataRaw('wait_time',
                                       data=[np.atleast_1d(self.spin_box.value())],
                                       units='s')]))