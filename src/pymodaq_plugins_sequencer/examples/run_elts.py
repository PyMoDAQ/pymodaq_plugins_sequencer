from qtpy import QtWidgets

from pymodaq.dashboard import create_load_dashboard
from pymodaq_data import DataToExport
from pymodaq_gui.utils.utils import mkQApp

from pymodaq_plugins_sequencer.utilities.element_factory import SeqEltFactory, SeqEltBase


if __name__ == "__main__":
    seq_fact = SeqEltFactory()

    app = mkQApp('Elements')

    shared_ui, dashboard = create_load_dashboard()

    def print_dte(dte: DataToExport):
        print(dte)

    widgets: list[QtWidgets.QWidget] = []
    elements: list[SeqEltBase] = []
    for ind_elt, elt in enumerate(seq_fact.elements):
        elements.append(seq_fact.get_seq_elt(elt)(ind_elt))
        widgets.append(elements[-1].create_widget())
        widgets[-1].show()
        elements[-1].done_signal.connect(print_dte)
        print(widgets[-1].sizeHint())

    shared_ui.show()

    app.exec()