from collections.abc import Iterable

from qtpy import QtWidgets, QtCore

from pymodaq_gui.qt_utils import mkQApp
from pymodaq_gui.utils.menu_utils import MenuButton
from pymodaq_gui.utils.styling import Font

from pymodaq_plugins_sequencer.utilities.list_widget.model_view import SequenceListView, SequenceModel, SequenceWidgetDelegate
from pymodaq_plugins_sequencer.utilities.element_factory import SeqEltFactory, SeqEltBase

seq_factory = SeqEltFactory()


class ListWidget(QtWidgets.QWidget):

    def __init__(self, parent=None, elements: list[SeqEltBase] = None):
        super().__init__(parent)
        if elements is None:
            elements = []
        self.list_view = SequenceListView()
        self.model = SequenceModel(data=elements)
        self.list_view.setModel(self.model)

        self.menu_button = MenuButton('add', seq_factory.elements)
        self.menu_button.triggered.connect(self.add_element)

        font = Font('Tahoma', 14, True, False)
        font.apply_to_widget(self.menu_button)
        font.apply_to_widget(self.menu_button.add_menu)


        self.setup_ui()

    def add_element(self, path: Iterable[str]):
        element = seq_factory.get_seq_elt(path[0])(self.model.rowCount())
        self.model.add_data(self.model.rowCount(),
                            element)
        for row in range(self.model.rowCount()):
            index = self.model.index(row, 0)
            self.list_view.openPersistentEditor(index)

    def setup_ui(self):
        self.setLayout(QtWidgets.QVBoxLayout())
        self.layout().setContentsMargins(0,0,0,0)
        self.layout().addWidget(self.list_view)
        self.layout().addWidget(self.menu_button)

        #self.list_view.add_data_signal[str].connect(self.add_subentry)
        self.list_view.remove_row_signal[int].connect(self.model.remove_data)
        self.list_view.load_data_signal.connect(self.model.load)
        self.list_view.save_data_signal.connect(self.model.save)
        self.delegate = SequenceWidgetDelegate()
        self.list_view.setItemDelegate(self.delegate)
        self.list_view.setUniformItemSizes(False)
        self.list_view.setResizeMode(QtWidgets.QListView.ResizeMode.Adjust)

        for row in range(self.model.rowCount()):
            index = self.model.index(row, 0)
            self.list_view.openPersistentEditor(index)


if __name__ == '__main__':
    app = mkQApp('MenuButton')

    list_widget = ListWidget(elements=[seq_factory.get_seq_elt('wait')(12),
                                       seq_factory.get_seq_elt('state')(20),
                                       seq_factory.get_seq_elt('wait')(5),])
    list_widget.show()


    app.exec()