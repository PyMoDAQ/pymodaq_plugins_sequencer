from pyqtgraph import mkColor
from qtpy import QtWidgets

from pymodaq_gui.utils.utils import mkQApp
from pymodaq_gui.utils.widgets.label import LabelWithFont
from pymodaq_gui.managers.action_manager import ActionManager
from qt_themes import get_theme


class WidgetWithToolbar(QtWidgets.QWidget, ActionManager):
    """ Create a Widget with a vertical layout containing a title and
    subwidgets
    """

    def __init__(self, id: int, name: str, subwidget:QtWidgets.QWidget = None, parent=None,
                 **label_kwargs):
        ActionManager.__init__(self)
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

        self.add_toolbar('top', 'TopToolbar', parent=self)
        self.top_widget.layout().addWidget(self.toolbar)
        self.top_widget.layout().addStretch()
        self.id_widget = LabelWithFont(f'{id}', font_name=font_name,
                              font_size=font_size, isbold=isbold,
                              isitalic=isitalic, color=get_theme().blue)


        self.name_widget = LabelWithFont(f'{name}', font_name=font_name,
                              font_size=font_size, isbold=isbold,
                              isitalic=isitalic, color=get_theme().magenta)

        self.add_widget('id', self.id_widget)
        self.add_widget('name', self.name_widget)
        self.add_action('execute', 'Execute', 'start',
                        tip='Execute the Sequencer Element',
                        icon_color=get_theme().magenta,)

        if subwidget is not None:
            self.layout().addWidget(subwidget)
        self.layout().addStretch()

    def add_action(self, *args, **kwargs):
        if 'execute' in self.actions_names:
            before = self.get_action('execute')
        else:
            before = None
        super().add_action(*args, before=before, **kwargs)

    @property
    def top_layout(self) -> QtWidgets.QHBoxLayout:
        return self.top_widget.layout()

    def add_widget_top(self, widget: QtWidgets.QWidget):
        ind = self.top_widget.layout().count()
        ind = ind - 1 if ind > 0 else 0
        self.top_widget.layout().insertWidget(ind, widget)

    def insert_widget(self, widget=QtWidgets.QWidget, ind=1):
        self.layout().insertWidget(ind, widget)

    def set_id_visible(self, visible=True):
        self.id_widget.setVisible(visible)

    def set_name_visible(self, visible=True):
        self.name_widget.setVisible(visible)

    @property
    def id(self):
        return self._id

    @id.setter
    def id(self, value: int):
        self._id = value
        self.id_widget.setText(str(value))

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, value: str):
        self._name = value
        self.name_widget.setText(value)


if __name__ == '__main__':
    from qt_themes import get_theme
    app = mkQApp('WidgetToolbar')
    widget = WidgetWithToolbar(123, 'State')

    widget.add_action('quit', 'Quit', icon_name="cancel",
                        tip="Quit PyMoDAQ", icon_color=get_theme().red)
    widget.connect_action('quit', widget.close)
    widget.show()

    app.exec()