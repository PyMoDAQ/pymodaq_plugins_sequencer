from collections.abc import Iterable
import random
from typing import TYPE_CHECKING
from qtpy import QtWidgets, QtCore

from pymodaq.dashboard import create_load_dashboard

from pymodaq.utils.shared_ui import SharedUI
from pymodaq_data import DataToExport
from pymodaq_gui.qt_utils import mkQApp
from pymodaq_gui.utils.menu_utils import MenuButton
from pymodaq_gui.utils.styling import Font
from pymodaq_gui.utils.widgets.window import make_window

from pymodaq_plugins_sequencer.utilities.sequencer.model_view import (
    SequenceTreeView, SequenceModel, SequenceWidgetDelegate, SequenceTreeModel)
from pymodaq_plugins_sequencer.utilities.element_factory import SeqEltFactory, SeqEltBase

if TYPE_CHECKING:
    from pymodaq.dashboard import DashBoard

seq_factory = SeqEltFactory()


class SequenceWidget(QtWidgets.QWidget):

    def __init__(self, parent=None,
                 dashboard: 'DashBoard' = None,
                 elements: list[SeqEltBase] = None):

        super().__init__(parent)

        if elements is None:
            elements = []

        self._dashboard = dashboard

        self.view = SequenceTreeView(parent=parent, dashboard=dashboard)
        self._model = SequenceTreeModel(dashboard=dashboard)
        self.view.setModel(self._model)

        self.setup_ui()

        for elt in elements:
            self._model.insert_data(QtCore.QModelIndex(), -1, elt)

    def setup_ui(self):
        self.setLayout(QtWidgets.QVBoxLayout())
        self.layout().setContentsMargins(1,1,1,1)
        self.layout().addWidget(self.view)

        self.delegate = SequenceWidgetDelegate()
        self.view.setItemDelegate(self.delegate)

        self.view.setSelectionMode(self.view.SelectionMode.SingleSelection)
        self.view.setDragEnabled(True)
        self.view.setDefaultDropAction(QtCore.Qt.DropAction.MoveAction)
        self.view.setAcceptDrops(True)
        self.view.setDragDropMode(self.view.DragDropMode.DragDrop)
        self.view.expandAll()
        self.view.setHeaderHidden(True)


if __name__ == '__main__':
    import sys
    app = mkQApp('Sequencer')
    window, area = make_window(title='SequenceWidget')

    shared_ui_dash, dashboard = create_load_dashboard(show_dashboard=True)


    def print_dte(dte: DataToExport):
        print(dte)

    def create_dashboard_lambda(elt: SeqEltBase, dashboard):
        return lambda: elt.set_dashboard(dashboard)

    elements = [seq_factory.get_seq_elt('wait')(12),
                seq_factory.get_seq_elt('state')(20),
                seq_factory.get_seq_elt('grab')(5),
                ]

    list_widget = SequenceWidget(elements=elements,
                                 dashboard=dashboard)
    list_widget.show()

    for element in elements:
        element.done_signal.connect(print_dte)
        dashboard.experiment_manager.applied_entry.connect(create_dashboard_lambda(element, dashboard))


    sys.exit(app.exec())