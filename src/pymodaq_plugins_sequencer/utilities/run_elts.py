from qtpy import QtWidgets

from pymodaq.dashboard import create_load_dashboard
from pymodaq_gui.utils.utils import mkQApp

from pymodaq_plugins_sequencer.utilities.element_factory import SeqEltFactory


if __name__ == "__main__":
    seq_fact = SeqEltFactory()

    app = mkQApp('Elements')

    shared_ui, dashboard = create_load_dashboard()

    widgets: list[QtWidgets.QWidget] = []
    for ind_elt, elt in enumerate(seq_fact.elements):
        widgets.append(seq_fact.get_seq_elt(elt)(ind_elt, dashboard).create_widget())
        widgets[-1].show()

    shared_ui.show()

    app.exec()