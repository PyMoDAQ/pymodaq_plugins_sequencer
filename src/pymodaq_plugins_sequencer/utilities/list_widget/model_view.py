from pathlib import Path
from typing import Any, Union

from qtpy import QtWidgets, QtCore

from qtpy.QtCore import QModelIndex, QMimeData, Qt


from serializall import SerializableFactory

from pymodaq_gui.utils import select_file
from pymodaq_utils.array_manipulation import are_elements_contiguous

from pymodaq_gui.qvariant import QVariant

from ..element_factory import SeqEltFactory, SeqEltBase, MIME_TYPE
from ...utils import get_set_sequencer_path



seq_factory = SeqEltFactory()
ser_factory = SerializableFactory()


def elements_from_path(fname: Path) -> list[SeqEltBase]:
    if not fname.exists():
        return []
    with open(fname, 'rb') as file:
        lines = file.readlines()
    all_lines = b''
    for line in lines:
        all_lines += line
    data = []
    while len(all_lines) > 0:
        entry, all_lines = SeqEltBase.deserialize(all_lines)
        data.append(entry)
    return data


class SequenceWidgetDelegate(QtWidgets.QStyledItemDelegate):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def createEditor(self, parent, option, index: QModelIndex):
        seq_elt: SeqEltBase = index.data()
        widget = seq_elt.create_widget()
        widget.setParent(parent)

        # Set size policy to fill the cell
        widget.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Expanding,
        )

        # Force widget to fill cell height
        # available_height = option.rect.height()
        # widget.setMinimumHeight(available_height)
        # widget.setMaximumHeight(available_height)

        # # Remove layout margins if present
        # if widget.layout() is not None:
        #     widget.layout().setContentsMargins(0, 0, 0, 0)
        #     widget.layout().setSpacing(0)

        # Connect signals for auto-commit on value change or focus loss
        #self._connect_editor_signals(widget)

        return widget

    def _connect_editor_signals(self, widget):
        """Connect widget signals to auto-commit data changes"""
        # Try common value changed signals
        # if hasattr(widget, 'toggled'):
        #     widget.toggled.connect(lambda: self.commitData.emit(widget))
        # if hasattr(widget, 'currentIndexChanged'):  # For comboboxes
        #     widget.currentIndexChanged.connect(lambda: self.value_changed(widget))
        # elif hasattr(widget, 'editingFinished'):
        #     widget.editingFinished.connect(lambda: self.value_changed(widget))
        # elif hasattr(widget, 'stateChanged'):  # For checkboxes
        #     widget.stateChanged.connect(lambda: self.commitData.emit(widget))
        # elif hasattr(widget, 'checkStateChanged'):  # For checkboxes
        #     widget.checkStateChanged.connect(lambda: self.commitData.emit(widget))
        #
        # Install event filter to catch focus loss
        widget.installEventFilter(self)
        pass

    def value_changed(self, widget: QtWidgets.QWidget):
        QtWidgets.QApplication.processEvents()
        self.commitData.emit(widget)

    def setEditorData(self, editor: SeqEltBase, index: QModelIndex):
        try:
            super().setEditorData(editor, index)
        except:
            super().setEditorData(editor, index)

    def setModelData(self, editor, model, index: QModelIndex):
        pass
        #model.setData(index, copy.copy(editor.value()), Qt.ItemDataRole.EditRole)

    # def updateEditorGeometry(self, editor, option, index):
    #     """Ensure editor fills the cell completely"""
    #     rect = QtCore.QRect(option.rect)
    #     available_height = rect.height()
    #     editor.setMinimumHeight(available_height)
    #     editor.setMaximumHeight(available_height)
    #     editor.setGeometry(rect)

    def sizeHint(self, option, index):
        """Provide size hint for cells with widgets"""
        return QtCore.QSize(100, 60)


class SequenceModel(QtCore.QAbstractListModel):

    update_delegate = QtCore.Signal()

    def __init__(self, parent: QtWidgets.QWidget = None,
                 data: list[SeqEltBase] = None,
                 header=('Elt',),
                 show_checkbox = True
                 ):

        if data is None:
            data = []
        self._data: list[SeqEltBase] = data
        self._show_checkbox: bool = show_checkbox
        self._checked: list[bool] = [True for _ in range(len(self._data))]
        self.data_tmp: list[SeqEltBase] = []

        super().__init__(parent)

    def rowCount(self, *args, **kwargs):
        return len(self._data)

    def columnCount(self, *args, **kwargs):
        return 1

    def get_data(self, row) -> SeqEltBase:
        return self._data[row]

    def mimeTypes(self):
        types = super().mimeTypes()
        types.append(MIME_TYPE)
        return types

    def mimeData(self, items) -> QMimeData:
        data = QMimeData()
        rows = list(set([item.row() for item in items]))
        if are_elements_contiguous(rows):
            entries = [self._data[row] for row in rows]
            data.setData(MIME_TYPE, ser_factory.get_apply_serializer(entries))
        return data

    def data(self, index: QModelIndex, role: Qt.ItemDataRole) -> Any:
        if index.isValid():
            if role == Qt.ItemDataRole.DisplayRole or role == Qt.ItemDataRole.EditRole:
                return self._data[index.row()]
            elif role == Qt.ItemDataRole.CheckStateRole and index.column() == 0 and self._show_checkbox:
                if self._checked[index.row()]:
                    return Qt.CheckState.Checked
                else:
                    return Qt.CheckState.Unchecked
            elif role == Qt.ItemDataRole.ToolTipRole:
                entry: SeqEltBase = self._data[index.row()]
                return repr(entry)
        return QVariant()

    def flags(self, index):

        return Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsDragEnabled | Qt.ItemFlag.ItemIsEditable

    def dropMimeData(self, data: QMimeData, action: Qt.DropAction, row: int, column: int, parent: QModelIndex):
        if row == -1:
            row = self.rowCount(parent)
        if data.hasFormat(MIME_TYPE):
            elts: list[SeqEltBase] = (
                ser_factory.get_apply_deserializer(
                    data.data(MIME_TYPE).data()))
        else:
            elts = []

        if action == QtCore.Qt.DropAction.MoveAction:
            pass
            # this is strange if I move things around using drag/drop
            # sometimes the MoveRows is called immediately without calling drop???
            # the code below is therefore not needed (but is still called in case of a drop!!)
            # for ind, entry in enumerate(elts):
            #     self.data_tmp = entry
            #     start_row = self._data.index(entry)
            #     #self.moveRows(start_row, len(elts))
            #     self.moveRow(parent, start_row, parent, row)
        elif action == QtCore.Qt.DropAction.CopyAction:  #but only one item in the list in Copy mode
            self.data_tmp = elts
            for entry in self.data_tmp:  #make sure there is no duplicate
                if entry in self._data:
                    self.data_tmp.remove(entry)
            self.insertRows(row, len(self.data_tmp), parent)
        self.update_delegate.emit()
        return True

    def setData(self, index, value, role):
        if index.isValid():
            if role == Qt.ItemDataRole.EditRole:
                if self.validate_data(index.row(), index.column(), value):
                    #TODO self._data[index.row()].setting.parameter.setValue(value)
                    self.dataChanged.emit(index, index, [role])
                    return True
                else:
                    return False
            elif role == Qt.ItemDataRole.CheckStateRole:
                self._checked[index.row()] = True if value == Qt.CheckState.Checked else False
                self.dataChanged.emit(index, index, [role])
                return True
        return False

    def moveRow(self, sourceParent: QModelIndex, sourceRow: int,
                destinationParent: QModelIndex, destinationChild: int) -> bool:
        if (destinationChild > self.rowCount() or
                destinationChild < 0):
            return False
        self.beginMoveRows(sourceParent, sourceRow, sourceRow,
                           destinationParent, destinationChild)
        entry_to_be_moved = self._data.pop(sourceRow)
        self._data.insert(destinationChild if destinationChild < sourceRow else destinationChild -1,
                          entry_to_be_moved)
        self.endMoveRows()
        return True

    def moveRows(self, sourceParent: QModelIndex, sourceRow: int, count: int,
                 destinationParent: QModelIndex, destinationChild: int) -> bool:
        if count == 1:
            self.moveRow(sourceParent, sourceRow, destinationParent, destinationChild)
        else:
            super().moveRows(sourceParent, sourceRow, count,
                             destinationParent, destinationChild)

    def insertRows(self, row, count, parent):
        self.beginInsertRows(QtCore.QModelIndex(), row, row + count - 1)
        for ind in range(count):
            self._data.insert(row + ind, self.data_tmp[ind] if
            (hasattr(self.data_tmp, '__len__') and len(self.data_tmp) == count) else self.data_tmp)
            self._checked.insert(row + ind, False)
        self.endInsertRows()
        return True

    def clear(self):
        while self.rowCount() > 0:
            self.remove_row(0)

    def edit_data(self, index):
        entry = self._data[index.row()]
        dialog = QDialog()

        vlayout = QtWidgets.QVBoxLayout()
        dialog.setLayout(vlayout)

        module_index = get_module_index_from_param(entry.setting)
        vlayout.addWidget(QtWidgets.QLabel(
            f'Setting from module {entry.module_name} with path:\n {entry.setting.path[module_index+2:]}'))
        setting = Parameter.create(name='settings', type='group', children=[entry.setting.parameter.saveState()])
        tree = StateParameterTree(parent=dialog)
        tree.setParameters(setting, showTop=False)
        buttonBox = QDialogButtonBox(parent=dialog)
        buttonBox.addButton("Done", QDialogButtonBox.ButtonRole.AcceptRole)
        buttonBox.accepted.connect(dialog.accept)
        buttonBox.addButton("Cancel", QDialogButtonBox.ButtonRole.RejectRole)
        buttonBox.rejected.connect(dialog.reject)

        vlayout.addWidget(tree)
        vlayout.addWidget(buttonBox)
        dialog.setWindowTitle("Edit the setting")
        res = dialog.exec()

        if res:
            entry.setting.parameter.setValue(setting.children()[0].value())

    def add_data(self, row, data: SeqEltBase):
        if data is not None:
            if data in self._data:
                return
            self.insert_data(row, data)
            self.update_delegate.emit()

    def insert_data(self, row, data):
        self.data_tmp = data
        self.insertRows(row, 1, self.index(-1, -1))

    def remove_data(self, row):
        self.remove_row(row)
        self.update_delegate.emit()

    def load(self, fname: str | Path = None):
        if fname is None:
            fname = select_file(start_path=get_set_sequencer_path(), save=False, ext='*')
        if fname is not None and fname != '':
            while self.rowCount(self.index(-1, -1)) > 0:
                self.remove_row(0)
            data = elements_from_path(Path(fname))

            for row in data:
                self.insert_data(self.rowCount(self.index(-1, -1)), row)
        self.update_delegate.emit()

    def save(self, fname: str = None):
        if fname is None:
            fname = select_file(start_path=get_set_sequencer_path(), save=True, ext='seq',
                                force_save_extension=True)
        with open(fname, 'wb') as file:
            file.writelines([SeqEltBase.serialize(entry) for entry in self._data])


class SequenceListView(QtWidgets.QListView):
    """
    """

    valueChanged = QtCore.Signal(list)
    add_data_signal = QtCore.Signal(str)
    remove_row_signal = QtCore.Signal(int)
    load_data_signal = QtCore.Signal()
    save_data_signal = QtCore.Signal()

    def __init__(self, menu=False):
        super().__init__()
        self.setmenu(menu)
        #self.doubleClicked.connect(self.edit_row)

    def edit_row(self):
        index = self.currentIndex()
        index.model().edit_data(index)

    def setmenu(self, status):
        if status:
            self.menu = QtWidgets.QMenu()
            special_menu = self.menu.addMenu('Add Special Configuration')

            self.menu.addSeparator()
            self.menu.addAction('Remove selected row', self.remove)
            self.menu.addAction('Clear all', self.clear)
            self.menu.addSeparator()
            self.menu.addAction('Load Sequencer file', lambda: self.load_data_signal.emit())
            self.menu.addAction('Save Sequencer file', lambda: self.save_data_signal.emit())
        else:
            self.menu = None

    def create_menu_slot_special_entry(self, entry: str):
        return lambda: self.add(entry)

    def contextMenuEvent(self, event):
        if self.menu is not None:
            self.menu.exec(event.globalPos())

    def clear(self):
        self.model().clear()

    def add(self, special_entry: str):
        self.add_data_signal.emit(special_entry)

    def remove(self):
        """ Remove selected rows, starting from the last one (to not mess with indexing)"""
        rows = list(set([index.row() for index in self.selectedIndexes()]))
        rows.sort(key=lambda row: -row)
        for row in rows:
            self.remove_row_signal.emit(row)

    def data_has_changed(self, topleft, bottomright, roles):
        self.valueChanged.emit([topleft, bottomright, roles])

    def get_table_value(self):
        """

        """
        return self.model()

    def set_table_value(self, data_model):
        """

        """
        try:
            self.setModel(data_model)
            self.model().dataChanged.connect(self.data_has_changed)
        except Exception as e:
            pass


