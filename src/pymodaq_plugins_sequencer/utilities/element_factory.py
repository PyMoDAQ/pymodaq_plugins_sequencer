from pathlib import Path
from importlib import import_module
from dataclasses import dataclass, Field, InitVar
from typing import Tuple, Callable, TYPE_CHECKING

from qtpy import QtCore, QtWidgets
from qtpy.QtWidgets import QWidget

from qt_themes import get_theme

from serializall import SerializableFactory, SerializableBase

from pymodaq_data import DataToExport
from pymodaq_gui.managers.action_manager import ActionManager
from pymodaq_gui.managers.parameter_manager import ParameterManager
from pymodaq_gui.qt_utils import mkQApp
from pymodaq_gui.utils.widgets import LabelWithFont
from pymodaq_plugins_sequencer.utilities.widget_with_toolbar import WidgetWithToolbar
from pymodaq_utils.abstract import abstract_attribute
from pymodaq_utils.logger import set_logger, get_module_name

logger = set_logger(get_module_name(__file__))

if TYPE_CHECKING:
    from pymodaq.dashboard import Dashboard


def register_elements(parent_module_name: str = 'pymodaq_plugins_sequencer.utilities'):
    elements = []
    try:
        elements_module = import_module(f'{parent_module_name}.elements')

        element_path = Path(elements_module.__path__[0])

        for file in element_path.iterdir():
            if file.is_file() and 'py' in file.suffix and file.stem != '__init__':
                try:
                    elements.append(import_module(f'.{file.stem}',
                                                  elements_module.__name__))
                except Exception as e:
                    logger.warning(str(e))
    except Exception as e:
        logger.warning(str(e))
    finally:
        return elements


class SeqEltBaseSer(SerializableFactory):
    """The Base serializable class for Sequencer Elements"""


class SeqEltBase(QtCore.QObject, SeqEltBaseSer, ActionManager, ParameterManager):
    """ Base class defining the interface of all elements handled by the Sequencer

    """
    elt_name = abstract_attribute()
    done_signal = QtCore.Signal(DataToExport)
    params = []

    def __init__(self, id: int, dashboard: 'Dashboard', **label_kwargs):
        QtCore.QObject.__init__(self)
        SeqEltBaseSer.__init__(self)
        ActionManager.__init__(self)
        ParameterManager.__init__(self)

        self._id = id
        self._go_to = id + 1
        self.dashboard: 'DashBoard' = dashboard

        font_name = label_kwargs.pop('font_name', 'Tahoma')
        font_size = label_kwargs.pop('font_size', 14)
        isbold = label_kwargs.pop('isbold', True)
        isitalic = label_kwargs.pop('isitalic', True)

        self.id_widget = LabelWithFont(f'{id}', font_name=font_name,
                              font_size=font_size, isbold=isbold,
                              isitalic=isitalic, color=get_theme().blue)


        self.name_widget = LabelWithFont(f'{self.name}', font_name=font_name,
                              font_size=font_size, isbold=isbold,
                              isitalic=isitalic, color=get_theme().magenta)

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
        return self.elt_name

    @name.setter
    def name(self, value: str):
        self.elt_name = value
        self.name_widget.setText(value)

    @property
    def go_to(self):
        """ Get/Set the next ID the Sequencer should go to """
        return self._go_to

    @go_to.setter
    def go_to(self,value: int):
        self._go_to = value

    def _create_base_widget(self) -> WidgetWithToolbar:
        """ Base Widget"""
        base_widget = WidgetWithToolbar(self.id, self.name)
        self.add_widget('id', self.id_widget, toolbar=base_widget.toolbar)
        self.add_widget('name', self.name_widget, toolbar=base_widget.toolbar)
        self.add_action('execute', 'Execute', 'start',
                        tip='Execute the Sequencer Element',
                        icon_color=get_theme().magenta,
                        toolbar=base_widget.toolbar)

        self.connect_action('execute', self.execute)
        return base_widget

    def add_action(self, *args, **kwargs):
        if 'execute' in self.actions_names:
            before = self.get_action('execute')
        else:
            before = None
        super().add_action(*args, before=before, **kwargs)

    def add_widget(self, *args, **kwargs):
        # if 'execute' in self.actions_names:
        #     before = self.get_action('execute')
        # else:
        #     before = None
        # super().add_widget(*args, before=before, **kwargs)
        super().add_widget(*args, **kwargs)

    def create_widget(self) -> QtWidgets.QWidget:
        """ Public API to be used to create the widget representing this elt """
        return self._create_widget(self._create_base_widget())

    def _create_widget(self, base_widget: WidgetWithToolbar) -> WidgetWithToolbar:
        """ Particular Widget allowing the edition of this Element

        Parameters
        ----------
        base_widget :
            You should build your widget based on base_widget
        """
        raise NotImplementedError

    def execute(self, dte: DataToExport = None):
        """ Execute the Element"""
        raise NotImplementedError

    @staticmethod
    def serialize(obj: "SerializableBase") -> bytes:
        raise NotImplementedError

    @staticmethod
    def deserialize(bytes_str: bytes) -> Tuple["SerializableBase", bytes]:
        raise NotImplementedError


class SeqEltFactory:
    """The factory class to get Sequencer Elements"""

    elements_registry = {}

    @classmethod
    def register_elt(cls) -> Callable:
        """Class decorator method to register SubEntryHandlers class to the internal
        registry.
        Must be used as a decorator above the definition of an SubEntryHandler inherited class.

        The entry class must implement specific class attributes and methods
        """

        def inner_wrapper(wrapped_class: type[SeqEltBase]) -> type[SeqEltBase]:
            elt_name = wrapped_class.elt_name

            if elt_name not in cls.elements_registry:
                cls.elements_registry[elt_name] = wrapped_class
            else:
                logger.info(f"Subentry {elt_name} already registered")
            # Return wrapped_class
            return wrapped_class

        # Return decorated function
        return inner_wrapper

    @classmethod
    def get_seq_elt(cls, name: str) -> type[SeqEltBase]:
        """Factory command to get registered subentry handler.

        This method gets the appropriate executor class from the registry
        """

        if name not in cls.elements_registry:
            raise KeyError(f".{name} is not a supported element.")

        return cls.elements_registry[name]

    @property
    def elements(self) -> list[str]:
        return [elt for elt in self.elements_registry.keys()]


