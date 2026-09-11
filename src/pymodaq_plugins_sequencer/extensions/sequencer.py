from pathlib import Path
import yaml

from pymodaq.utils.h5modules.module_saving import LoggerSaver
from pymodaq_data import DataToExport
from pymodaq_gui.managers.h5manager import FileAction
from pymodaq_gui.managers.runner_thread_manager import WorkerThreadManager
from pymodaq_gui.utils import select_file
from pymodaq_plugins_sequencer.utilities.sequencer.sequence import Sequence

from qtpy import QtWidgets, QtCore

from pymodaq_gui import utils as gutils
from pymodaq_gui.utils.enums import MenuToolbarNames

from pymodaq_utils.config import Config, GlobalConfig
from pymodaq_utils.logger import set_logger, get_module_name

from pymodaq.extensions.utils import CustomExt
from pymodaq_gui.utils.widgets import QLED
from pymodaq_plugins_sequencer.utilities.elements.sequence import SequenceElt
from pymodaq_plugins_sequencer.utils import get_set_sequencer_path
from pymodaq_plugins_sequencer.utilities.yaml_utils import PrettyListDumper

logger = set_logger(get_module_name(__file__))

main_config = GlobalConfig()


EXTENSION_NAME = 'Sequencer'
CLASS_NAME = 'Sequencer'


class StatusBarManager:
    def __init__(self, app: 'Sequencer'):
        self.app = app

        self._running_led: QLED = None

    @property
    def statusbar(self):
        return self.app.statusbar

    def set_permanent_status(self, status: str):
        self.app.set_permanent_status(status)

    def create_permanent_widgets(self):
        self._running_led = QLED()
        self._running_led.setToolTip('logging status: green (running), red (idle)')
        self._running_led.clickable = False
        self.statusbar.addPermanentWidget(self._running_led)


class SaverWorker(QtCore.QObject):
    """ Worker in separated thread receiving the data from a DataGenerator
    and adding them into the enlargeable arrays with the H5file using the
     LoggerModuleSaver """

    n_saved = QtCore.Signal(int)
    data_to_save_signal = QtCore.Signal(DataToExport)


    def __init__(self, saver: LoggerSaver, parent=None):
        super().__init__(parent)
        self.saver = saver
        self._n_saved = 0
        self._show_thread = True

        self.data_to_save_signal.connect(self.save_data, QtCore.Qt.ConnectionType.QueuedConnection)

    @QtCore.Slot(DataToExport)
    def save_data(self, dte: DataToExport):
        if self._show_thread:
            print(f'Saving data in Qthread{self.thread()}')
            self._show_thread = False
        self.saver.add_data(dte,)
        self._n_saved += 1
        self.n_saved.emit(self._n_saved)



class Sequencer(CustomExt):
    show_h5file_statusbar_widgets = True
    _worker_done = QtCore.Signal()
    params = [
        {'title': 'Worker:', 'name': 'worker', 'type': 'group', 'children': [
            {'title': 'Worker Running:', 'name': 'worker_running', 'type': 'led', 'value': False, 'readonly': True},
            {'title': 'Worker tasks:', 'name': 'worker_tasks', 'type': 'int', 'value': 0, 'readonly': True},
        ]},
    ]

    def __init__(self, parent: gutils.DockArea, dashboard):
        super().__init__(parent, dashboard, add_toolbar_break=False)

        self.sequences: dict[str, Sequence] = {}
        self.sequence_names: list[str] = []
        self.sequence_container: QtWidgets.QWidget = None
        self.status_manager = StatusBarManager(self)

        self._module_and_data_saver = LoggerSaver(self)
        self.saver_worker: SaverWorker = None
        self._n_emitted = 0

        self.setup_ui()

        self._current_path: Path = get_set_sequencer_path()

    def do_things_after_ui_setup(self):
        self.add_sequence('Main')

    @property
    def module_and_data_saver(self) -> LoggerSaver:
        return super().module_and_data_saver

    def setup_docks_and_widgets(self):
        """Mandatory method to be subclassed to setup the docks layout

        See Also
        --------
        pyqtgraph.dockarea.Dock
        """
        self.hor_widget = QtWidgets.QWidget()
        self.hor_widget.setLayout(QtWidgets.QHBoxLayout())
        self.sequence_container = QtWidgets.QWidget()
        self.sequence_container.setLayout(QtWidgets.QHBoxLayout())
        self.hor_widget.layout().addWidget(self.sequence_container)

        settings_widget = QtWidgets.QWidget()
        settings_widget.setLayout(QtWidgets.QVBoxLayout())

        self.hor_widget.layout().addWidget(settings_widget)
        settings_widget.layout().addWidget(self.settings_tree)
        settings_widget.layout().addWidget(self.h5_manager.h5saver.settings_tree)

        self.mainwindow.setCentralWidget(self.hor_widget)
        self.h5_manager.h5saver.settings_tree.setVisible(False)
        self.settings_tree.setVisible(False)
        self.settings_tree.setMinimumHeight(150)

        self.populate_status_bar()

    def populate_status_bar(self):
        super().populate_status_bar()
        self.status_manager.create_permanent_widgets()
        self.status_manager.set_permanent_status('')

    def add_sequence(self, name: str = 'Main'):

        widget = QtWidgets.QWidget()
        self.sequence_names.append(name.lower())
        self.sequences[name.lower()] = Sequence(name, widget, self.dashboard)
        self.sequence_container.layout().addWidget(widget)
        SequenceElt.sequences.append(self.sequences[name.lower()])
        self.set_action_enabled('remove_sequence', len(self.sequences) > 1)

    def remove_sequence(self, name: str = None):
        if name is None:
            name = list(self.sequences.keys())[-1]

        seq = self.sequences.pop(name.lower())
        self.sequence_container.layout().removeWidget(seq.parent)
        seq.parent.setParent(None)
        seq.parent.deleteLater()
        self.set_action_enabled('remove_sequence', len(self.sequences) > 1)

    def setup_menus_and_toolbars(self, menubar: QtWidgets.QMenuBar = None):
        """Non mandatory method to be subclassed in order to create a menubar

        create menu for actions contained into the self._actions, for instance:

        See Also
        --------
        pymodaq.utils.managers.action_manager.ActionManager
        """
        self.add_toolbar(MenuToolbarNames.FILE, MenuToolbarNames.FILE.capitalize(), self.mainwindow,
                         toolbar=self.h5_manager.toolbar, add_break=False)
        self.add_menu(MenuToolbarNames.FILE, MenuToolbarNames.FILE.capitalize(), parent_menu=menubar)
        self.add_menu(MenuToolbarNames.TOOLS, MenuToolbarNames.TOOLS.capitalize(), parent_menu=menubar)
        self.add_menu('actions', 'Actions', parent_menu=menubar)

        self.create_dashboard_toolbar(add_break=False)

    def do_things_after_experiment_set(self, experiment_name: str, show_dashboard: bool = None):
        super().do_things_after_experiment_set(experiment_name, show_dashboard)

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

        self.add_action('start', 'Start Logging', 'motion_play',
                        "Start the Global Sequence",
                        menu='actions', icon_color=self.get_theme().green)
        self.add_action('stop', 'Stop Logging', 'stop_circle', "Stop the Global Sequence",
                        menu='actions', icon_color=self.get_theme().red)
        self.add_action('pause', 'Pause Logging', 'pause_circle', "Pause/resume the Global Sequence",
                        checkable=True, menu='actions',
                        icon_checked_color=self.get_theme().orange)
        self.toolbar.addSeparator()
        self.add_action('add_sequence', 'Add Sequence', 'add_circle',
                        tip='Add a sequence',
                        )
        self.add_action('remove_sequence', 'Remove Sequence', 'remove',
                        tip='Remove last sequence', enabled=False,
                        )
        self.toolbar.addSeparator()
        self.add_action('load_sequence', 'Load Sequence', 'file_open',
                        tip='Load a sequence file',
                        )
        self.add_action('save_sequence', 'Save Sequence', 'file_save',
                        tip='Save as a sequence file',
                        )

    def connect_things(self):
        """Connect actions and/or other widgets signal to methods"""
        self.connect_action('add_sequence',
                            lambda: self.add_sequence(f'Sequence{len(self.sequences):03.0f}'),)
        self.connect_action('remove_sequence', lambda: self.remove_sequence(),)
        self.connect_action('load_sequence', lambda: self.load_sequence())
        self.connect_action('save_sequence', lambda: self.save_sequence())

        self.connect_action('start', self.start)
        self.connect_action('stop', self.stop)
        self.connect_action('pause', self.pause)

        self.h5_manager.connect_action(FileAction.SHOW_SETTINGS, self.show_settings)

    def show_settings(self, show=True):
        self.settings_tree.setVisible(show)

    def load_sequence(self, path: Path = None):
        if path is None:
            path = select_file(self._current_path,
                               filter='Sequence file (*.seq)',
                               save=False, ext='seq', force_save_extension=True)
        if path is not None and path != '':
            self._current_path = path.parent

            with open(path, 'r') as file:
                sequence_dict = yaml.safe_load(file)
        if 'sequences' in sequence_dict:
            while len(self.sequences) > 0:
                self.remove_sequence()
            for seq_name, sequence_dict in sequence_dict['sequences'].items():
                self.add_sequence(seq_name)
                self.sequences[seq_name].load_sequence(sequence_dict)
        else:
            while len(self.sequences) > 1:
                self.remove_sequence()
            self.sequences[list(self.sequences.keys())[0]].load_sequence(sequence_dict)

    def save_sequence(self, path: Path = None):
        if path is None:
            path = select_file(self._current_path,
                               filter='Sequence file (*.seq)',
                               save=True, ext='seq', force_save_extension=True)
        if path is not None and path != '':
            self._current_path = path.parent
            sequence_dict = {'sequences': {}}
            for sequence_name, sequence in self.sequences.items():
                sequence_dict['sequences'][sequence_name] = sequence.root_elt.to_dict()

            with open(path, 'w') as file:
                yaml.dump(
                    sequence_dict,
                    file,
                    Dumper=PrettyListDumper,
                    default_flow_style=False,
                    sort_keys=False,
                    allow_unicode=True
                )
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
    def main_sequence(self) -> Sequence:
        return self.sequences[self.sequence_names[0]]

    def start(self):
        self._init_logging()
        for sequence in self.sequences.values():
            sequence.set_log_callback(self.saver_worker.save_data)

        self._n_emitted = 0

        self.set_action_enabled('start', False)
        self.main_sequence.sequence_finished.connect(self.stopped)
        self.main_sequence.get_action('start').trigger()

    def pause(self):
        for sequence in self.sequences.values():
            sequence.get_action('pause').trigger()

    def stop(self):
        for sequence in self.sequences.values():
            sequence.get_action('stop').trigger()

    def stopped(self, msg: str = None):
        #1 Stop the emission of data immediately
        for sequence in self.sequences.values():
            sequence.recursive_disconnect_elts()

        #2 terminate the saver worker once its queue is empty
        if self.settings['worker', 'worker_tasks'] == 0:
            self.terminate_worker()
        else:
            self._worker_done.connect(self.terminate_worker)

        #3 update the GUI
        self.set_action_checked('pause', False)
        self.set_action_enabled('start', True)
        if msg is not None:
            self.update_status(msg)
            self.status_manager.set_permanent_status(msg)

    def _init_logging(self):
        try:
            self._worker_done.disconnect(self.terminate_worker)
        except TypeError:
            pass
        self.module_and_data_saver.h5saver = self.h5saver
        self.module_and_data_saver.get_set_node(new=True)

        # managing saver worker
        self.saver_worker = SaverWorker(saver=self.module_and_data_saver,)
        self.thread_manager.create_thread_for_worker('saver', self.saver_worker)
        self.saver_worker.n_saved.connect(self.update_worker_ntask)
        self.thread_manager.start_thread('saver')
        self.settings['worker', 'worker_running'] = self.thread_manager.get_thread('saver').isRunning()

    @QtCore.Slot(int)
    def update_worker_ntask(self, n_saved: int):
        n_tasks = self._n_emitted - n_saved
        self.settings['worker', 'worker_tasks'] = n_tasks

        if n_tasks == 0:
            self._worker_done.emit()

    def terminate_worker(self):
        """ Will terminate/close/stops a few things when the worker is done working"""
        # stopping the plotting before flushing/closing the file
        #1 disconnecting the connection to here (fired once)
        try:
            self._worker_done.disconnect(self.terminate_worker)
        except TypeError:
            pass
        try: #2 disconnect the data production from the saving
            self.saver_worker.data_to_save_signal.disconnect(self.saver_worker.save_data)
        except TypeError:
            pass

        #3 quit the thread managing the data saving (nothing left in the loop and no more connection)
        self.thread_manager.exit_worker_thread('saver', delete_worker=True)

        #4 flushing/closing the file to be able to create new groups...
        self.h5_manager.close_file()

        #5 updating GUI info
        self.settings['worker', 'worker_running'] = self.thread_manager.get_thread('saver').isRunning()




def main():
    import sys
    from pymodaq_gui.qt_utils import mkQApp
    from pymodaq.dashboard import load_dashboard_with_arguments
    from pymodaq.utils.gui_utils.loader_utils import create_extension

    app = mkQApp('Custom Ext')

    win, dashboard, ext = load_dashboard_with_arguments(show_dashboard=False,
                                                        load_extension=False,
                                                        )
    win.mainwindow.setVisible(False)

    win_ext, ext = create_extension(dashboard, Sequencer)
    win_ext.show()

    sys.exit(app.exec())


if __name__ == '__main__':
    main()
