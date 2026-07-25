from pyqtgraph import mkColor
from qtpy import QtWidgets

from pymodaq_gui.utils.utils import mkQApp
from pymodaq_gui.utils.widgets.label import LabelWithFont
from pymodaq_gui.managers.action_manager import ActionManager
from qt_themes import get_theme


class WidgetWithToolbar(QtWidgets.QWidget):
    """ Create a Widget with a vertical layout containing a title and
    subwidgets
    """

    def __init__(self, id: int, name: str, subwidget:QtWidgets.QWidget = None, parent=None,
                 **label_kwargs):
        QtWidgets.QWidget.__init__(self, parent)

        self._id = id
        self._name = name

        font_name = label_kwargs.pop('font_name', 'Tahoma')
        font_size = label_kwargs.pop('font_size', 14)
        isbold = label_kwargs.pop('isbold', True)
        isitalic = label_kwargs.pop('isitalic', True)

        self.top_widget = QtWidgets.QWidget()
        self.top_widget.setLayout(QtWidgets.QHBoxLayout())

        self.setLayout(QtWidgets.QVBoxLayout())
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.layout().addWidget(self.top_widget)

        self.toolbar = QtWidgets.QToolBar(self)
        self.top_widget.layout().addWidget(self.toolbar)
        self.top_widget.layout().addStretch()

        if subwidget is not None:
            self.layout().addWidget(subwidget)
        self.layout().addStretch()

    @property
    def top_layout(self) -> QtWidgets.QHBoxLayout:
        return self.top_widget.layout()

    def add_widget_top(self, widget: QtWidgets.QWidget):
        ind = self.top_widget.layout().count()
        ind = ind - 1 if ind > 0 else 0
        self.top_widget.layout().insertWidget(ind, widget)

    def insert_widget(self, widget=QtWidgets.QWidget, ind=1):
        self.layout().insertWidget(ind, widget)




if __name__ == '__main__':
    from qt_themes import get_theme
    app = mkQApp('WidgetToolbar')
    widget = WidgetWithToolbar(123, 'State')

    widget.add_action('quit', 'Quit', icon_name="cancel",
                        tip="Quit PyMoDAQ", icon_color=get_theme().red)
    widget.connect_action('quit', widget.close)
    widget.show()

    app.exec()