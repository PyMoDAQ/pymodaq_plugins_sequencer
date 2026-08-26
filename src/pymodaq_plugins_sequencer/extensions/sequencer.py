from pymodaq_plugins_sequencer.utilities.sequencer.sequence import Sequence

from qtpy import QtWidgets, QtCore

from pymodaq_gui import utils as gutils
from pymodaq_gui.utils.shared_ui import MenuToolbarNames

from pymodaq_utils.config import Config, GlobalConfig
from pymodaq_utils.logger import set_logger, get_module_name

from pymodaq.extensions.utils import CustomExt

from pymodaq_plugins_sequencer.utilities.elements.sequence import SequenceElt

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

    def connect_things(self):
        """Connect actions and/or other widgets signal to methods"""
        self.connect_action('add_sequence',
                            lambda: self.add_sequence(f'Sequence{len(self.sequences):03.0f}'),)

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
