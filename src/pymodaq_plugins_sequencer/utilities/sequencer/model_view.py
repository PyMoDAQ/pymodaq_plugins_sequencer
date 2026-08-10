from pathlib import Path
import random
from typing import Any, Iterable, TYPE_CHECKING

from qtpy.QtWidgets import QStyle
from qtpy import QtWidgets, QtCore

from qtpy.QtCore import QModelIndex, QMimeData, Qt
from qt_themes import get_theme

from serializall import SerializableFactory

from pymodaq_data import DataToExport
from pymodaq_gui.utils import select_file
from pymodaq_gui.utils.menu_utils import MenuButton, IterableMenu
from pymodaq_utils.array_manipulation import are_elements_contiguous

from ..element_factory import SeqEltFactory, SeqEltBase, MIME_TYPE
from ..styling import button_style, menu_style, color_from_depth
from ...utils import get_set_sequencer_path

if TYPE_CHECKING:
    from pymodaq.scripting import Dashboard

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

def elt_level(index: QModelIndex) -> int:
    """ Calculate nesting depth of the element with the specified index """
    depth = 0
    parent = index.parent()
    while parent.isValid():
        depth += 1
        parent = parent.parent()
    return depth


class SequenceWidgetDelegate(QtWidgets.QStyledItemDelegate):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.base_bg = get_theme().mantle

    def updateEditorGeometry(self, editor: QtWidgets.QWidget,
                             option: QtWidgets.QStyleOptionViewItem,
                             index: QModelIndex):
        view = editor.parentWidget()
        if not view:
            return

        if index.isValid():
            elt = index.internalPointer()
            if elt.name == AddButtonPlaceholder.elt_name:
                super().updateEditorGeometry(editor, option, index)
                return
            else:
                mouse_global_pos = view.cursor().pos()
                editor.resize(option.rect.width(), option.rect.height())
                editor.move(mouse_global_pos)

    def createEditor(self, parent, option, index: QModelIndex):
        if not index.isValid():
            return super().createEditor(parent, option, index)

        seq_elt: SeqEltBase = index.internalPointer()
        if seq_elt:
            if seq_elt.name == AddButtonPlaceholder.elt_name:
                return None
            container = QtWidgets.QFrame(parent)
            container.setWindowFlags(Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
            widget = seq_elt.create_widget(container)
            container.setObjectName("container")
            container.setStyleSheet("""
                #container {
                    border: 2px solid #888888;
                    border-radius: 4px;
                    background-color: palette(window);
                }
            """)
            layout = QtWidgets.QVBoxLayout(container)
            layout.setContentsMargins(1, 1, 1, 1)
            layout.addWidget(widget)
            container.setFocusProxy(widget)
            return container

        return super().createEditor(parent, option, index)

    def setEditorData(self, editor, index):
        # Get data from model and populate the custom widget
        pass

    def setModelData(self, editor, model, index):
        pass

    def sizeHint(self, option, index):
        """Provide size hint for cells with widgets"""
        # 1. Obtenir la largeur de colonne actuelle fournie par Qt (ou 100px par défaut si 0)
        view_width = option.rect.width() if option.rect.width() > 0 else 100

        if index.isValid():
            elt = index.internalPointer()
            if elt and elt.name == AddButtonPlaceholder.elt_name:
                return QtCore.QSize(view_width, 35)
            qt_width = super().sizeHint(option, index).width()
            final_width = qt_width if qt_width > 0 else view_width
            return QtCore.QSize(final_width, 40)
        return QtCore.QSize(view_width, 40)

    def paint(self, painter, option, index):
        painter.save()

        # Calculate nesting depth
        depth = elt_level(index)

        level_color = color_from_depth(self.base_bg, depth)

        # Draw level background unless the row is currently highlighted/selected
        if not (option.state & QStyle.StateFlag.State_Selected):
            painter.fillRect(option.rect, level_color)

        painter.restore()
        super().paint(painter, option, index)

class RootElt(SeqEltBase):
    elt_name = 'root'
    def __init__(self, id: int = -1, parent=None):  # should keep the signature of the base
        # Pass a specific string or ID to distinguish it from standard data
        super().__init__(id=-1, parent=parent)

    def _eq(self, other: 'SeqEltBase'):
        return True


@SeqEltFactory.register_elt()
class AddButtonPlaceholder(SeqEltBase):
    elt_name = 'button'
    children_allowed = False

    def __init__(self, id: int = -2, parent=None):  # should keep the signature of the base
        # Pass a specific string or ID to distinguish it from standard data
        super().__init__(id=-2, parent=parent)

    def create_widget(self, parent=None) -> QtWidgets.QWidget:
        return MenuButton('Add Element',
                          [elt.capitalize() for elt in seq_factory.elements if elt != AddButtonPlaceholder.elt_name],
                          update_button_text=False,
                          parent=parent)

    def _eq(self, other: 'SeqEltBase'):
        return True

    def execute(self, dte: DataToExport = None):
        self.done_signal.emit(DataToExport('button'))

    def serialize_custom(self) -> bytes:
        """Serialize the custom part of the element

        to be reimplemented
        """
        return b''

    def deserialize_custom(self, bytes_str: bytes) -> bytes:
        """Deserialize the custom part of the element to finish initialization using setters, attribute assignment
        or methods

        to be reimplemented

        Returns
        -------
        bytes: the remaining bytes string if any
        """
        return bytes_str


class SequenceTreeModel(QtCore.QAbstractItemModel):
    def __init__(self,
                 parent: QtCore.QObject = None,
                 dashboard: 'Dashboard' = None
                 ):

        super().__init__(parent)
        self.root_elt =  RootElt()
        self.insert_data(QtCore.QModelIndex(), 0, AddButtonPlaceholder())
        self._dashboard = dashboard

    @property
    def dashboard(self) -> 'Dashboard':
        return self._dashboard

    def index(self, row, column, parent=QModelIndex()):
        if not self.hasIndex(row, column, parent):
            return QModelIndex()

        if not parent.isValid():
            parent_elt = self.root_elt
        else:
            parent_elt = parent.internalPointer()

        child_elt = parent_elt.children[row]
        if child_elt:
            return self.createIndex(row, column, child_elt)
        return QModelIndex()

    def parent(self, child: QModelIndex) -> QModelIndex:
        if not child.isValid():
            return QModelIndex()

        child_elt: SeqEltBase = self.get_elt_from_index(child)
        parent_elt = child_elt.parent

        if parent_elt == self.root_elt:
            return QModelIndex()

        grandparent_elt = parent_elt.parent
        row = grandparent_elt.children.index(parent_elt)
        return self.createIndex(row, 0, parent_elt)

    def rowCount(self, parent=QModelIndex()):
        if parent.column() > 0:
            return 0

        parent_elt = self.get_elt_from_index(parent)

        if parent_elt is None:
            return 0
        return len(parent_elt.children)

    def columnCount(self, parent=QModelIndex()):
        return 1

    def data(self, index, role=Qt.ItemDataRole):
        if not index.isValid():
            return None

        elt: SeqEltBase = index.internalPointer()
        # --- HANDLE THE BUTTON PLACEHOLDER ---
        if elt.elt_name == AddButtonPlaceholder.elt_name:
            if role == Qt.ItemDataRole.DisplayRole:
                return None
            if role == Qt.ItemDataRole.SizeHintRole:
                return QtCore.QSize(100, 28)
            return None

        if role == Qt.ItemDataRole.DisplayRole:
            return repr(elt)
        elif role == Qt.ItemDataRole.EditRole:
            return elt
        return None

    def flags(self, index):
        default_flags = super().flags(index)
        if index.isValid():
            node: SeqEltBase = index.internalPointer()
            if node.name == AddButtonPlaceholder.elt_name:
                return Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable
            if node.children_allowed:
                return (default_flags |
                        Qt.ItemFlag.ItemIsEnabled |
                        Qt.ItemFlag.ItemIsSelectable |
                        Qt.ItemFlag.ItemIsDragEnabled |
                        Qt.ItemFlag.ItemIsEditable |
                        Qt.ItemFlag.ItemIsDropEnabled)

            return (default_flags |
                    Qt.ItemFlag.ItemIsEnabled |
                    Qt.ItemFlag.ItemIsSelectable |
                    Qt.ItemFlag.ItemIsDragEnabled |
                    Qt.ItemFlag.ItemIsEditable)
        else:
            return default_flags | Qt.ItemFlag.ItemIsDropEnabled

    def insert_data(self, parent_index: QModelIndex,
                    row: int,
                    new_object: SeqEltBase) -> bool:
        """
        Inserts an instance of SeqEltBase (or real implementation) under the given parent item.
        """
        parent_object = self.get_elt_from_index(parent_index)
        has_add_button = False
        for child in parent_object.children:
            if child.elt_name == AddButtonPlaceholder.elt_name:
                has_add_button = True
                break

        index_to_subtract = 1 if has_add_button else 0

        if row < 0 or row > len(parent_object.children) - index_to_subtract:
            row = len(parent_object.children) - index_to_subtract #-1 because there is a AddButton

        self.beginInsertRows(parent_index, row, row)
        new_object.parent = parent_object
        parent_object.children.insert(row, new_object)
        self.endInsertRows()

        return True

    def clear(self):
        """ remove all elements but the AddButton"""
        self.removeRows(0, len(self.root_elt.children) - 1, parent=QModelIndex())

    def clear_children(self, parent: QModelIndex):
        while self.rowCount(parent) > 1:
            self.removeRow(0, parent)

    def removeRow(self, row: int, parent = QModelIndex()):
        parent_elt = self.get_elt_from_index(parent)
        child = parent_elt.children[row]
        if child.name == AddButtonPlaceholder.elt_name:
            return False

        self.beginRemoveRows(parent, row, row)
        if row - 1 < len(parent_elt.children):
            del parent_elt.children[row]
        self.endRemoveRows()
        return True

    def removeRows(self, row, count, parent=QModelIndex()):
        parent_elt = self.get_elt_from_index(parent)

        self.beginRemoveRows(parent, row, row + count - 1)
        if row + count - 1 < len(parent_elt.children):
            del parent_elt.children[row: row + count]
        self.endRemoveRows()
        return True

    def insert_data_by_elt(self, parent_elt: SeqEltBase,
                            row: int, new_object: SeqEltBase) -> bool:
        """
        Inserts a new object using a raw Python parent node instead of a QModelIndex.
        """
        parent_index = self.index_from_element(parent_elt)
        if parent_index.isValid():
            self.insert_data(parent_index, row, new_object)

    def index_from_element(self, elt: SeqEltBase) -> QModelIndex:
        if elt == self.root_elt:
            index = QModelIndex()
        else:
            # To create the index, we need to know which row the parent occupies inside ITS own parent
            parent: SeqEltBase = elt.parent
            if parent is None:
                index = QModelIndex()
            else:
                elt_row = parent.children.index(elt)
                index = self.createIndex(elt_row, 0, elt)
        return index

    def get_ids(self, parent_elt: SeqEltBase = None) -> list[int]:
        """ Get the ids of the existing elements"""
        ids = []
        if parent_elt is None:
            parent_elt = self.root_elt
        for child in parent_elt.children:
            ids.append(child.id)
            ids.extend(self.get_ids(child))
        return ids

    def get_new_id(self) -> int:
        new_id = random.randint(0, 100)
        ids = self.get_ids()
        while new_id in ids:
            new_id = random.randint(0, 100)
        return new_id

    def supportedDropActions(self):
        return Qt.DropAction.MoveAction | Qt.DropAction.CopyAction

    def mimeTypes(self):
        types = super().mimeTypes()
        types.append(MIME_TYPE)
        return types

    def mimeData(self, indexes: list[QModelIndex]) -> QMimeData:
        data = QMimeData()
        if indexes[0].isValid():
            elt: SeqEltBase = indexes[0].internalPointer()
            data.setData(MIME_TYPE, ser_factory.get_apply_serializer(elt))
        return data

    def dropMimeData(self, data: QMimeData,
                     action: Qt.DropAction,
                     row: int,
                     column: int,
                     parent: QModelIndex):
        if action == Qt.DropAction.IgnoreAction:
            return True

        if not data.hasFormat(MIME_TYPE):
            return False

        if row == -1:
            row = parent.row() if parent.isValid() else self.rowCount(parent)


        elt: SeqEltBase = ser_factory.get_apply_deserializer(data.data(MIME_TYPE).data())
        elt.dashboard = self.dashboard

        if action == Qt.DropAction.CopyAction:
            new_id = self.get_new_id()
            elt.id = new_id

        children: list[SeqEltBase] = []
        while len(elt.children) > 0:
            children.append(elt.children.pop(0))
        self.insert_data(parent_index=parent, row=row, new_object=elt)
        parent_index = self.index(row, 0, parent)
        for child in children:
            child.dashboard = self.dashboard
            self.insert_data(parent_index, -1, child)
        return True

    def get_elt_from_index(self, index: QModelIndex) -> SeqEltBase:
        return index.internalPointer() if index.isValid() else self.root_elt

class SequenceModel(QtCore.QAbstractListModel):

    def __init__(self, parent: QtWidgets.QWidget = None,
                 data: list[SeqEltBase] = None,
                 header=('Elt',),
                 show_checkbox = False
                 ):

        if data is None:
            data = []
        self._data: list[SeqEltBase] = data
        self._show_checkbox: bool = show_checkbox
        self._checked: list[bool] = [True for _ in range(len(self._data))]
        self.data_tmp: list[SeqEltBase] = []

        super().__init__(parent)

    def double_clicked(self, index: QModelIndex):
        self._data[index.row()].setup_dialog()

    @property
    def ids(self) -> list[int]:
        """ Get the ids of the existing elements"""
        return [elt.id for elt in self._data]

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
            if role == Qt.ItemDataRole.DisplayRole:
                return repr(self._data[index.row()])
            elif role == Qt.ItemDataRole.EditRole:
                return self._data[index.row()]
            elif role == Qt.ItemDataRole.CheckStateRole and index.column() == 0 and self._show_checkbox:
                if self._checked[index.row()]:
                    return Qt.CheckState.Checked
                else:
                    return Qt.CheckState.Unchecked
            elif role == Qt.ItemDataRole.ToolTipRole:
                entry: SeqEltBase = self._data[index.row()]
                return repr(entry)
            elif role == Qt.ItemDataRole.FontRole:
                return self._data[index.row()].font.get_font()
        return None

    def flags(self, index):
        default_flags = super().flags(index)
        if index.isValid():
            return (default_flags |
                    Qt.ItemFlag.ItemIsEnabled |
                    Qt.ItemFlag.ItemIsSelectable |
                    Qt.ItemFlag.ItemIsDragEnabled |
                    Qt.ItemFlag.ItemIsEditable)
        else:
            return default_flags | Qt.ItemFlag.ItemIsDropEnabled

    def supportedDropActions(self):
        return Qt.DropAction.MoveAction | Qt.DropAction.CopyAction

    def dropMimeData(self, data: QMimeData, action: Qt.DropAction, row: int, column: int, parent: QModelIndex):
        if action == Qt.DropAction.IgnoreAction:
            return True

        if not data.hasFormat(MIME_TYPE):
            return False

        # Si le dépôt se fait directement SUR un élément, on ajuste la ligne
        if row == -1:
            row = parent.row() if parent.isValid() else self.rowCount()

        elts: list[SeqEltBase] = (
            ser_factory.get_apply_deserializer(
                data.data(MIME_TYPE).data()))
        # Insertion des nouveaux éléments dans notre structure de données
        self.beginInsertRows(QModelIndex(), row, row + len(elts) - 1)
        for i, item in enumerate(elts):
            self._data.insert(row + i, item)
            self._checked.insert(row+ i, True)
        self.endInsertRows()

        return True

    def setData(self, index, value, role):
        if index.isValid():
            if role == Qt.ItemDataRole.EditRole:
                self._data[index.row()] = value
                self.dataChanged.emit(index, index, [role])
                return True

            elif role == Qt.ItemDataRole.CheckStateRole:
                self._checked[index.row()] = True if value == Qt.CheckState.Checked else False
                self.dataChanged.emit(index, index, [role])
                return True
        return False

    def validate_data(self, row, col, data: QMimeData):
        pass

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
            return self.moveRow(sourceParent, sourceRow, destinationParent, destinationChild)
        else:
            return super().moveRows(sourceParent, sourceRow, count,
                                    destinationParent, destinationChild)

    def removeRows(self, row, count, parent=QModelIndex()):
        self.beginRemoveRows(parent, row, row + count - 1)
        for _ in range(count):
            if row < len(self._data):
                del self._data[row]
                del self._checked[row]
        self.endRemoveRows()
        return True

    def clear(self):
        while self.rowCount() > 0:
            self.remove_row(0)


    def add_data(self, row, data: SeqEltBase):
        if data is not None:
            if data in self._data:
                return
            self.insert_data(row, data)
            self.layoutChanged.emit()

    def insert_data(self, row, data):
        self.beginInsertRows(self.index(-1, -1), row, row+1)
        self._data.insert(row, data)
        self._checked.insert(row, True)
        self.endInsertRows()

    def remove_data(self, row):
        self.remove_row(row)

    def remove_row(self, row: int):
        self.beginRemoveRows(self.index(row), row, row)
        self._data.pop(row)
        self._checked.pop(row)
        self.endRemoveRows()

    def load(self, fname: str | Path = None):
        if fname is None:
            fname = select_file(start_path=get_set_sequencer_path(), save=False, ext='*')
        if fname is not None and fname != '':
            while self.rowCount(self.index(-1, -1)) > 0:
                self.remove_row(0)
            data = elements_from_path(Path(fname))

            for row in data:
                self.insert_data(self.rowCount(self.index(-1, -1)), row)

    def save(self, fname: str = None):
        if fname is None:
            fname = select_file(start_path=get_set_sequencer_path(), save=True, ext='seq',
                                force_save_extension=True)
        with open(fname, 'wb') as file:
            file.writelines([SeqEltBase.serialize(entry) for entry in self._data])


class SequenceTreeView(QtWidgets.QTreeView):
    """
    """

    valueChanged = QtCore.Signal(list)
    add_data_signal = QtCore.Signal(str)
    remove_row_signal = QtCore.Signal(int)
    load_data_signal = QtCore.Signal()
    save_data_signal = QtCore.Signal()

    def __init__(self, menu=True, dashboard: 'Dashboard' = None, parent=None):
        super().__init__(parent)
        self.setmenu(menu)
        self._dashboard = dashboard

    @property
    def dashboard(self) -> 'Dashboard':
        return self._dashboard

    def model(self) -> SequenceTreeModel:
        return super().model()

    def setModel(self, model: SequenceTreeModel):
        super().setModel(model)
        if model:
            model.rowsInserted.connect(self._on_rows_inserted)
            self.expanded.connect(self.update_section_buttons)
            self.doItemsLayout()
            self.update_section_buttons(QModelIndex())

    def _on_rows_inserted(self, parent_index, start, end):
        """Triggered automatically whenever rows are added to the model."""
        self.update_section_buttons(parent_index)
        #self.expand(parent_index)

    def update_section_buttons(self, parent_index=QModelIndex()):
        """Loops through immediate children of parent_index and injects buttons."""
        model = self.model()
        if not model:
            return

        for row in range(model.rowCount(parent_index)):
            current_index = model.index(row, 0, parent_index)
            elt: SeqEltBase = current_index.internalPointer()

            if elt.name == AddButtonPlaceholder.elt_name:
                if self.indexWidget(current_index) is not None:
                    continue
                container = QtWidgets.QWidget(self.viewport())
                container.setStyleSheet("background-color: transparent;")
                layout = QtWidgets.QHBoxLayout(container)
                layout.setContentsMargins(0, 0, 0, 0)
                layout.setSpacing(0)

                btn: MenuButton = elt.create_widget(parent=container)
                btn.setFixedHeight(30)

                depth = elt_level(parent_index) + 1

                btn.setStyleSheet(button_style(depth))
                btn.menu.setStyleSheet(menu_style(depth))
                layout.addWidget(btn)
                layout.addStretch()
                #elt._btn_reference = container
                container.show()
                btn.triggered.connect(lambda path: self.create_and_add(path , current_index.parent()))

                self.setIndexWidget(current_index, container)
                pass

    def get_new_id(self) -> int:
        return self.model().get_new_id()

    def create_and_add(self, path: Iterable[str],
                       parent_index: QtCore.QModelIndex = None,
                       row: int = -1):

        new_id = self.get_new_id()
        element = seq_factory.get_seq_elt(path[0].lower())(new_id,)
        element.dashboard = self.dashboard
        self.model().insert_data(parent_index=parent_index,
                                 row=row,
                                 new_object=element)
        parent_elt = self.elt_from_index(parent_index)
        elt_index = self.model().index(row if row != -1 else len(parent_elt.children) - 2, 0, parent_index)
        if element.children_allowed:
            self.model().insert_data(elt_index, 0, AddButtonPlaceholder())

    def elt_from_index(self, index: QtCore.QModelIndex) -> SeqEltBase:
        return index.internalPointer() if index.isValid() else self.model().root_elt

    def edit_row(self):
        index = self.currentIndex()
        index.model().edit_data(index)

    def setmenu(self, status):
        if status:
            self.menu = QtWidgets.QMenu()
            self.menu.addMenu(IterableMenu('Add Element',
                                           seq_factory.elements,
                                           self.add_element))
            self.menu.addSeparator()
            self.menu.addAction('Remove Element', self.remove)
            self.menu.addAction('Clear Children', self.clear_children)
            self.menu.addSeparator()
            self.menu.addAction('Load Sequencer file', lambda: self.load_data_signal.emit())
            self.menu.addAction('Save Sequencer file', lambda: self.save_data_signal.emit())
        else:
            self.menu = None

    def add_element(self, name: str, path:tuple[str] = ()):
        current_elt = self.model().get_elt_from_index(self.currentIndex())
        if current_elt.children_allowed:
            self.create_and_add(path, self.currentIndex(), row=0)
        else:
            self.create_and_add(path, self.currentIndex().parent(), self.currentIndex().row() + 1)

    def contextMenuEvent(self, event):
        if self.menu is not None:
            self.menu.exec(event.globalPos())

    def clear_children(self):
        current_elt = self.model().get_elt_from_index(self.currentIndex())
        if current_elt.children_allowed:
            self.model().clear_children(self.currentIndex())
        else:
            self.model().clear_children(self.currentIndex().parent())

    def remove(self):
        """ Remove selected elements, only one at the time otherwise will mess with indexing"""
        for index in self.selectedIndexes():
            self.model().removeRow(index.row(), parent=self.model().parent(index))

    def sizeHint(self):
        # Taille de base si le modèle est vide
        if not self.model() or self.model().rowCount() == 0:
            return QtCore.QSize(200, 50)

        total_height = 0
        count = self.model().rowCount()
        max_width = 0
        for ind in range(count):
            index = self.model().index(ind, 0)
            total_height += self.sizeHintForIndex(index).height()
            max_width = max(max_width,self.sizeHintForIndex(index).width() )

        margins = self.contentsMargins()
        frame_width = self.frameWidth() * 2

        final_height = total_height + margins.top() + margins.bottom() + frame_width
        final_width = max_width + margins.left() + margins.right() + frame_width

        return QtCore.QSize(final_width, final_height)
