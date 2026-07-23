from pathlib import Path
from importlib import import_module
from dataclasses import dataclass, Field, InitVar
from typing import Tuple, Callable, TYPE_CHECKING

from qtpy import QtCore, QtWidgets
from qtpy.QtWidgets import QWidget
from serializall import SerializableFactory, SerializableBase

from pymodaq_gui.managers.action_manager import ActionManager
from pymodaq_gui.qt_utils import mkQApp
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


class SeqEltBase(QtCore.QObject, SeqEltBaseSer):
    """ Base class defining the interface of all elements handled by the Sequencer

    """
    name = abstract_attribute()
    done_signal = QtCore.Signal()

    def __init__(self, id: int, dashboard: 'Dashboard'):
        QtCore.QObject.__init__(self)
        SeqEltBaseSer.__init__(self)

        self.id = id
        self.dashboard = dashboard

    def _create_base_widget(self) -> WidgetWithToolbar:
        """ Base Widget"""
        return WidgetWithToolbar(self.id, self.name)

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

    def execute(self):
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
            elt_name = wrapped_class.name

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


