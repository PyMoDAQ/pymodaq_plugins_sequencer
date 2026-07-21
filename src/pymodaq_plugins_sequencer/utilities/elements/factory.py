
from dataclasses import dataclass
from typing import Tuple, Callable

from qtpy import QtCore, QtWidgets
from qtpy.QtWidgets import QWidget
from serializall import SerializableFactory, SerializableBase

from pymodaq_utils.logger import set_logger, get_module_name

logger = set_logger(get_module_name())


@dataclass
class SeqEltBase(SerializableBase, QtCore.QObject):
    """ Base class defining the interface of all elements handled by the Sequencer

    """
    id: int
    name: str
    data: bytes = b''

    done_signal = QtCore.Signal()

    def __post_init__(self):
        QtCore.QObject.__init__(self)

    def _create_base_widget(self) -> QWidget:
        """ Base Widget"""
        pass

    def create_widget(self) -> QWidget:
        """ Particular Widget allowing the edition of this Element"""
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

