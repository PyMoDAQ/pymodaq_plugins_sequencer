from pymodaq_plugins_sequencer.utilities.states import (
    QStateMachine, MyQFinalState, QHistoryState, QState, QAbstractTransition)

from qtpy import QtWidgets, QtCore

from pymodaq_gui import utils as gutils
from pymodaq_gui.utils.shared_ui import MenuToolbarNames
from pymodaq_plugins_sequencer.utilities.element_factory import SeqEltBase
from pymodaq_plugins_sequencer.utilities.sequencer.model_view import SequenceTreeView, SequenceTreeModel, \
    SequenceWidgetDelegate, RootElt
from pymodaq_utils.config import Config, GlobalConfig
from pymodaq_utils.logger import set_logger, get_module_name

from pymodaq.extensions.utils import CustomExt

logger = set_logger(get_module_name(__file__))

main_config = GlobalConfig()


EXTENSION_NAME = 'Sequencer'
CLASS_NAME = 'Sequencer'

class Sequencer(CustomExt):

    params = []

    def __init__(self, parent: gutils.DockArea, dashboard):
        super().__init__(parent, dashboard, add_toolbar_break=False)

        self.view: SequenceTreeView = None
        self._model: SequenceTreeModel = None

        self.machine = QStateMachine()
        self.done_state = MyQFinalState()
        self.history_state = QHistoryState()

        self.setup_ui()
        self.setup_machine()

    def setup_docks_and_widgets(self):
        """Mandatory method to be subclassed to setup the docks layout

        See Also
        --------
        pyqtgraph.dockarea.Dock
        """

        self.view = SequenceTreeView(parent=self.mainwindow, dashboard=self.dashboard)
        self._model = SequenceTreeModel(dashboard=self.dashboard)
        self.view.setModel(self._model)

        self.mainwindow.setCentralWidget(self.view)

        self.delegate = SequenceWidgetDelegate()
        self.view.setItemDelegate(self.delegate)

        self.view.setSelectionMode(self.view.SelectionMode.SingleSelection)
        self.view.setDragEnabled(True)
        self.view.setDefaultDropAction(QtCore.Qt.DropAction.MoveAction)
        self.view.setAcceptDrops(True)
        self.view.setDragDropMode(self.view.DragDropMode.DragDrop)
        self.view.expandAll()
        self.view.setHeaderHidden(True)

        self.label = QtWidgets.QLabel('')
        self.statusbar.addPermanentWidget(self.label)

    def setup_menus_and_toolbars(self, menubar: QtWidgets.QMenuBar = None):
        """Non mandatory method to be subclassed in order to create a menubar

        create menu for actions contained into the self._actions, for instance:

        See Also
        --------
        pymodaq.utils.managers.action_manager.ActionManager
        """
        self.add_menu(MenuToolbarNames.FILE, MenuToolbarNames.FILE.capitalize(), parent_menu=menubar)
        self.add_menu(MenuToolbarNames.TOOLS, MenuToolbarNames.TOOLS.capitalize(), parent_menu=menubar)
        self.add_menu('actions', 'Actions', parent_menu=menubar)

    def do_things_after_ui_setup(self):
        self.create_dashboard_toolbar(add_break=False)

    def do_things_after_experiment_set(self, experiment_name: str, show_dashboard: bool = None):
        pass

    def setup_actions(self):
        """Method where to create actions to be subclassed. Mandatory

        Examples
        --------
        >>> self.add_action('quit', 'Quit', 'close2', "Quit program")
        >>> self.add_action('grab', 'Grab', 'camera', "Grab from camera", checkable=True)
        >>> self.add_action('load', 'Load', 'Open', "Load target file (.h5, .png, .jpg) or data from camera"
            , checkable=False)
        >>> self.add_action('save', 'Save', 'SaveAs', "Save current data", checkable=False)

        See Also
        --------
        ActionManager.add_action
        """
        self.add_action('start', 'Start', 'motion_play', "Start the Sequence",
                        menu='actions',
                        icon_color=self.get_theme().green, toolbar=self.toolbar)
        self.add_action('stop', 'Stop Scan', 'stop_circle', "Stop the Sequence",
                        menu='actions',
                        icon_color=self.get_theme().red, toolbar=self.toolbar)
        self.add_action('pause', 'Pause Scan', 'pause_circle',
                        menu='actions', tip="Pause/resume the sequence",
                        checkable=True, toolbar=self.toolbar,
                        icon_checked_color=self.get_theme().orange)
        self._toolbar.addSeparator()
        self.add_action('show_file', 'Show file content', 'folder_data',
                        tip='Browse the content of the current HDF5 file')

    def connect_things(self):
        """Connect actions and/or other widgets signal to methods"""
        self.connect_action('start', self.start_sequence)
        self.connect_action('stop', self.stop_sequence)
        self.connect_action('pause', self.pause_sequence)

        self.root_elt.mstate.addTransition(self.get_action('stop').triggered, self.done_state)
        self.root_elt.mstate.addTransition(self.get_action('pause').triggered, self.history_state)
        self.done_state.exited.connect(self.stop_sequence)

    def value_changed(self, param):
        """ Actions to perform when one of the param's value in self.settings is changed from the
        user interface

        For instance:
        if param.name() == 'do_something':
            if param.value():
                print('Do something')
                self.settings.child('main_settings', 'something_done').setValue(False)

        Parameters
        ----------
        param: (Parameter) the parameter whose value just changed
        """
        pass

    @property
    def root_elt(self) -> RootElt:
        return self._model.root_elt

    def setup_machine(self):
        for child in self.machine.children():
            if isinstance(child, QAbstractTransition):
                self.machine.removeTransition(child)
            elif isinstance(child, QState):
                self.machine.removeState(child)

        self.machine.addState(self.root_elt.mstate)
        self.machine.addState(self.done_state)
        self.machine.addState(self.history_state)
        self.machine.setInitialState(self.root_elt.mstate)
        self.root_elt.mstate.addTransition(self.root_elt.mstate.finished, self.done_state)

    def recursive_connect_elts(self, elt: SeqEltBase = None):
        if elt is None:
            elt = self.root_elt

        for ind_child, child in enumerate(elt.children_without_add):
            child.mstate.clear_state_and_transitions()
            child.mstate.setParent(elt.mstate.children_state)
            if ind_child == 0:
                elt.mstate.children_state.setInitialState(child.mstate)
            if ind_child == len(elt.children_without_add) - 1:
                child.mstate.add_external_transition(child.mstate.finished, elt.mstate.execute_state)
            else:
                child.mstate.add_external_transition(child.mstate.finished, elt.children[ind_child+1].mstate)
            child.mstate.assignProperty(self.label, 'text', repr(child))
            if child.children_allowed:
                self.recursive_connect_elts(child)

    def is_valid(self):
        for elt in self.root_elt.get_elts(without=(-2,)):
            if not elt.check_set_is_valid():
                return False
        return True

    def start_sequence(self):
        self.label.setText('Machine starting')
        self.recursive_connect_elts()
        self.setup_machine()
        if not self.is_valid():
            self.label.setText('Some elements are not valid, check the log')
            return

        self.machine.finished.connect(self.stop_sequence)
        self.machine.start()

    def stop_sequence(self):
        self.machine.stop()
        self.label.setText('Machine finished')

    def pause_sequence(self):
        pass


def main():
    import sys
    from pymodaq_gui.qt_utils import mkQApp
    from pymodaq.dashboard import create_load_dashboard
    from pymodaq.utils.gui_utils.loader_utils import create_extension

    app = mkQApp('Custom Ext')

    win, dashboard = create_load_dashboard()
    win.mainwindow.setVisible(False)

    win_ext, ext = create_extension(dashboard, Sequencer)
    win_ext.show()

    sys.exit(app.exec())


if __name__ == '__main__':
    main()
