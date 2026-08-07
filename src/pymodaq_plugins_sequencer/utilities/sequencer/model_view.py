from pathlib import Path
import random
from typing import Any, Union, Iterable

from qtpy import QtWidgets, QtCore

from qtpy.QtCore import QModelIndex, QMimeData, Qt


from serializall import SerializableFactory

from pymodaq_gui.utils import select_file
from pymodaq_gui.utils.menu_utils import MenuButton
from pymodaq_gui.utils.styling import create_font
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
        self._editing_index = QModelIndex()

    def updateEditorGeometry(self, editor: QtWidgets.QWidget,
                             option: QtWidgets.QStyleOptionViewItem,
                             index: QModelIndex):
        view = editor.parentWidget()
        if not view:
            return

        # 3. Récupérer la position actuelle du curseur de la souris (Coordonnées globales de l'écran)
        mouse_global_pos = view.cursor().pos()

        # 4. Définir la taille (largeur/hauteur) basée sur la cellule, mais forcer la position X,Y sur la souris
        editor.resize(option.rect.width(), option.rect.height())

        # 5. Forcer le déplacement absolu sur l'écran à l'aide de .move()
        # (L'utilisation directe de setGeometry avec le rectangle parent échoue souvent sur les Popups)
        editor.move(mouse_global_pos)

    def createEditor(self, parent, option, index: QModelIndex):
        if not index.isValid():
            return super().createEditor(parent, option, index)
        self._editing_index = index
        index.model().layoutChanged.emit()

        seq_elt: SeqEltBase = index.data(QtCore.Qt.ItemDataRole.EditRole)

        if seq_elt:
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
        value = index.data(Qt.ItemDataRole.EditRole) or 0

    def setModelData(self, editor, model, index):
        # Save the custom widget's state back to the model
        # value = editor.slider.value()
        # model.setData(index, value, Qt.ItemDataRole.EditRole)
        pass

    def sizeHint(self, option, index):
        """Provide size hint for cells with widgets"""
        return QtCore.QSize(super().sizeHint(option, index).width(), 40)

    def destroyEditor(self, editor, index):
        self._editing_index = QModelIndex()
        index.model().layoutChanged.emit()
        super().destroyEditor(editor, index)

class RootNode(SeqEltBase):
    elt_name = 'root'
    def __init__(self, parent=None):
        # Pass a specific string or ID to distinguish it from standard data
        super().__init__(id=-1, parent=parent)

    def _eq(self, other: 'SeqEltBase'):
        return True

class AddButtonPlaceholder(SeqEltBase):
    elt_name = 'button'
    def __init__(self, parent=None):
        # Pass a specific string or ID to distinguish it from standard data
        super().__init__(id=-2, parent=parent)

    def create_widget(self, parent=None) -> QtWidgets.QWidget:
        return MenuButton('Add Element',
                          seq_factory.elements,
                          update_button_text=False,
                          parent=parent)

    def _eq(self, other: 'SeqEltBase'):
        return True


class SequenceTreeModel(QtCore.QAbstractItemModel):
    def __init__(self,
                 parent: QtCore.QObject = None,
                 ):

        super().__init__(parent)
        self.root_node =  RootNode()
        self.insert_data(QtCore.QModelIndex(), 0, AddButtonPlaceholder())

    def index(self, row, column, parent=QModelIndex()):
        if not self.hasIndex(row, column, parent):
            return QModelIndex()

        if not parent.isValid():
            parent_node = self.root_node
        else:
            parent_node = parent.internalPointer()

        child_node = parent_node.children[row]
        if child_node:
            return self.createIndex(row, column, child_node)
        return QModelIndex()

    def parent(self, child: QModelIndex):
        if not child.isValid():
            return QModelIndex()

        child_node = child.internalPointer()
        parent_node = child_node.parent

        if parent_node == self.root_node:
            return QModelIndex()

        grandparent_node = parent_node.parent
        row = grandparent_node.children.index(parent_node)
        return self.createIndex(row, 0, parent_node)

    def rowCount(self, parent=QModelIndex()):
        if parent.column() > 0:
            return 0

        if not parent.isValid():
            parent_node = self.root_node
        else:
            parent_node = parent.internalPointer()

        return len(parent_node.children)

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
            node = index.internalPointer()
            if node.name == AddButtonPlaceholder.elt_name:
                return Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable
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
        # 1. Retrieve the container object (either the invisible root or a visible object from the view)
        if not parent_index.isValid():
            parent_object = self.root_node
        else:
            parent_object = parent_index.internalPointer()

        # Safety check: If the row position is out of bounds, append to the end of the list
        if row == 0:  # because we are inserting a AddButton
            pass
        elif row < 0 or row > len(parent_object.children) -1:
            row = len(parent_object.children) -1 #-1 because we-ve inserted a AddButton

        self.beginInsertRows(parent_index, row, row)
        new_object.parent = parent_object
        parent_object.children.insert(row, new_object)
        self.endInsertRows()

        return True

    def insert_data_by_node(self, parent_node: SeqEltBase,
                            row: int, new_object: SeqEltBase) -> bool:
        """
        Inserts a new object using a raw Python parent node instead of a QModelIndex.
        """
        # 1. Generate the QModelIndex for this parent node
        if parent_node == self.root_node:
            # The invisible root node has no valid QModelIndex in Qt's eyes
            parent_index = QModelIndex()
        else:
            # To create the index, we need to know which row the parent occupies inside ITS own parent
            grandparent: SeqEltBase = parent_node.parent
            if grandparent is None:
                # Fallback safety if the parent node is detached
                parent_index = QModelIndex()
            else:
                parent_row = grandparent.children.index(parent_node)
                # Create the valid Qt index pointing to our parent node
                parent_index = self.createIndex(parent_row, 0, parent_node)

            self.insert_data(parent_index, row, new_object)

    @property
    def ids(self) -> list[int]:
        """ Get the ids of the existing elements"""
        return [elt.id for elt in self._data]

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
    def get_ids(self, parent_index: QModelIndex) -> list[int]:
        """ Get the ids of the existing elements"""
        parent_elt = parent_index.internalPointer()
        return [elt.id for elt in parent_elt]

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

    def __init__(self, menu=True):
        super().__init__()
        self.setmenu(menu)

    def model(self) -> SequenceTreeModel:
        return super().model()

    def setModel(self, model: SequenceTreeModel):
        super().setModel(model)
        if model:
            # RÈGLE 1 : Si le modèle ajoute des lignes (ex: au démarrage ou après un ajout), on applique les boutons
            model.rowsInserted.connect(self._on_rows_inserted)

            # RÈGLE 2 : Dès que l'utilisateur déplie une branche, on force l'application sur les enfants désormais visibles
            self.expanded.connect(self.update_section_buttons)

            # Premier rendu initial pour le niveau racine
            self.update_section_buttons(QModelIndex())

    def _on_rows_inserted(self, parent_index, start, end):
        """Triggered automatically whenever rows are added to the model."""
        self.update_section_buttons(parent_index)

    def update_section_buttons(self, parent_index=QModelIndex()):
        """Loops through immediate children of parent_index and injects buttons."""
        model = self.model()
        if not model:
            return

        # On ne boucle QUE sur les enfants directs de ce parent pour des raisons de performance
        for row in range(model.rowCount(parent_index)):
            current_index = model.index(row, 0, parent_index)
            node = current_index.internalPointer()

            if node.name == AddButtonPlaceholder.elt_name:
                if self.indexWidget(current_index) is not None:
                    continue
                btn = QtWidgets.QPushButton("+ Add Item")
                node._btn_reference = btn
                btn.show()
                # Connexion de l'action
                btn.clicked.connect(lambda path: self.create_and_add(path , current_index.parent()))

                # Injection immédiate dans la vue Qt
                self.setIndexWidget(current_index, btn)
                pass

    def create_and_add(self, path: Iterable[str],
                       parent_index: QtCore.QModelIndex = None):
        id = random.randint(0, 100)
        ids = self.model().get_ids(parent_index)
        while id in ids:
            id = random.randint(0, 100)
        element = seq_factory.get_seq_elt(path[0])(id, dashboard=self._dashboard)
        self.model().insert_data(parent_index=parent_index,
                                 row=-1,
                                 new_object=element)

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
