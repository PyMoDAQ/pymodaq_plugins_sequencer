from pathlib import Path
import yaml

from pymodaq_gui.utils import select_file
from pymodaq_plugins_sequencer.utilities.sequencer.sequence import Sequence

from qtpy import QtWidgets, QtCore

from pymodaq_gui import utils as gutils
from pymodaq_gui.utils.shared_ui import MenuToolbarNames

from pymodaq_utils.config import Config, GlobalConfig
from pymodaq_utils.logger import set_logger, get_module_name

from pymodaq.extensions.utils import CustomExt

from pymodaq_plugins_sequencer.utilities.elements.sequence import SequenceElt
from pymodaq_plugins_sequencer.utils import get_set_sequencer_path
from pymodaq_plugins_sequencer.utilities.yaml_utils import PrettyListDumper

logger = set_logger(get_module_name(__file__))

main_config = GlobalConfig()


EXTENSION_NAME = 'Sequencer'
CLASS_NAME = 'Sequencer'


class Sequencer(CustomExt):

    params = []

    def __init__(self, parent: gutils.DockArea, dashboard):
        super().__init__(parent, dashboard, add_toolbar_break=False)

        self.sequences: dict[str, Sequence] = {}
        self.sequence_container: QtWidgets.QWidget = None
        self.setup_ui()

        self._current_path: Path = get_set_sequencer_path()

    def setup_docks_and_widgets(self):
        """Mandatory method to be subclassed to setup the docks layout

        See Also
        --------
        pyqtgraph.dockarea.Dock
        """


        self.sequence_container = QtWidgets.QWidget()
        self.sequence_container.setLayout(QtWidgets.QHBoxLayout())
        self.mainwindow.setCentralWidget(self.sequence_container)

        self.add_sequence('Main')

    def add_sequence(self, name: str = 'Main'):
        widget = QtWidgets.QWidget()
        self.sequences[name.lower()] = Sequence(name, widget, self.dashboard)
        self.sequence_container.layout().addWidget(widget)
        SequenceElt.sequences.append(self.sequences[name.lower()])

    def remove_sequence(self, name: str = None):
        if name is None:
            name = list(self.sequences.keys())[-1]

        seq = self.sequences.pop(name.lower())
        self.sequence_container.layout().removeWidget(seq.parent)
        seq.parent.setParent(None)
        seq.parent.deleteLater()

    def setup_menus_and_toolbars(self, menubar: QtWidgets.QMenuBar = None):
        """Non mandatory method to be subclassed in order to create a menubar

        create menu for actions contained into the self._actions, for instance:

        See Also
        --------
        pymodaq.utils.managers.action_manager.ActionManager
        """
        self.add_menu(MenuToolbarNames.FILE, MenuToolbarNames.FILE.capitalize(), parent_menu=menubar)
        self.add_menu(MenuToolbarNames.TOOLS, MenuToolbarNames.TOOLS.capitalize(), parent_menu=menubar)

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

        self.add_action('show_file', 'Show file content', 'folder_data',
                        tip='Browse the content of the current HDF5 file')
        self.toolbar.addSeparator()
        self.add_action('add_sequence', 'Add Sequence', 'add_circle',
                        tip='Add a sequence',
                        )
        self.add_action('remove_sequence', 'Remove Sequence', 'remove',
                        tip='Remove last sequence',
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
