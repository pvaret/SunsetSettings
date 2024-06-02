import weakref

from dataclasses import dataclass
from types import GenericAlias
from typing import (
    Generic,
    Iterator,
    Optional,
    Protocol,
    TypeVar,
    Union,
    runtime_checkable,
)

try:
    from typing import Self
except ImportError:
    # TODO: Remove once we deprecate support for Python 3.10.
    from typing_extensions import Self

from sunset.notifier import Notifier


_T = TypeVar("_T")


# pylint: disable=unnecessary-ellipsis
# The ellipses in the protocol definitions below are in fact necessary: they let
# the type checker know it's fine we're not returning values.


@runtime_checkable
class Serializable(Protocol):
    """
    A protocol to be implemented by a class in order to enable storing instances
    of that class in a Key.

    The two methods to be implemented are :meth:`toStr()` and (classmethod)
    :meth:`fromStr()`.
    """

    def toStr(self) -> str:
        """
        Returns a string representation of this instance that can be used by
        :meth:`fromStr()` to reconstruct a copy of this instance.
        """
        ...

    @classmethod
    def fromStr(cls: type[Self], string: str) -> Optional[Self]:
        """
        Takes a string that represents a serialized instance of this class, and
        returns a newly created instance that corresponds to that
        representation, or None if the string is not a valid serialized
        representation of an instance of this class.
        """
        ...


class Serializer(Generic[_T], Protocol):
    """
    A protocol that describes a way to serialize and deserialize an arbitrary
    type.

    SunsetSettings provides its own serializers for common types (int, float,
    bool, str, enum.Enum). In order to store an arbitrary type in a Key, users
    need to provide a serializer for that type when instantiating a Key. That
    serializer should be an implementation of this protocol.
    """

    def toStr(self, value: _T) -> str:
        """
        Returns a string representation of the given value, that can be used by
        :meth:`fromStr()` to reconstruct a copy of that value.
        """
        ...

    def fromStr(self, string: str) -> Optional[_T]:
        """
        Takes a string that represents a serialized instance of a value, and
        returns a newly created instance that corresponds to that string, or
        None if the string is not a valid representation of a value for this
        serializer's type.
        """
        ...


@runtime_checkable
class Inheriter(Protocol):
    def setParent(self, parent: Optional[Self]) -> None: ...

    def parent(self) -> Optional[Self]: ...

    def children(self) -> Iterator[Self]: ...


@runtime_checkable
class Dumpable(Protocol):
    def dumpFields(self) -> Iterator[tuple[str, Optional[str]]]: ...

    def restoreField(self, path: str, value: Optional[str]) -> bool: ...

    def isSet(self) -> bool: ...


@runtime_checkable
class UpdateNotifier(Protocol):
    _update_notifier: Notifier["UpdateNotifier"]


@runtime_checkable
class ItemTemplate(Protocol):
    def _typeHint(self) -> Union[type, GenericAlias]: ...

    def _newInstance(self) -> Self: ...


@runtime_checkable
class HasMetadata(Protocol):
    _PATH_SEPARATOR: str

    def meta(self) -> "Metadata": ...


@dataclass
class Metadata:
    container: Optional[weakref.ref[HasMetadata]] = None
    label: str = ""

    def clear(self) -> None:
        self.container = None
        self.label = ""

    def update(
        self,
        label: Optional[str] = None,
        container: Optional[HasMetadata] = None,
    ) -> None:
        if container is not None:
            self.container = weakref.ref(container)
        if label is not None:
            self.label = label

    def path(self) -> str:
        if self.container is None or (container := self.container()) is None:
            # Should be the empty string, in theory.
            return self.label

        path = container.meta().path()

        if not path:
            return self.label

        return path + container._PATH_SEPARATOR + self.label


@runtime_checkable
class Field(
    Dumpable, HasMetadata, Inheriter, ItemTemplate, UpdateNotifier, Protocol
): ...


class BaseField:
    _PATH_SEPARATOR: str = "."

    _metadata: Optional[Metadata] = None

    def skipOnSave(self) -> bool:
        """
        Internal.

        Returns whether this entity should be disregarded when saving these
        settings. For entities with an attribute name, it's equivalent to
        checking if the attribute is private (its name starts with an
        underscore). For entities with a section name, it's equivalent to
        checking if the section name is empty.

        Can be overridden in subclasses.

        Returns:
           A bool used internally by the settings saving logic.
        """

        return self.meta().label.startswith("_")

    def meta(self) -> Metadata:
        """
        Internal.

        Get the metadata object associated with this entity.

        Returns:
            A metadata object.
        """

        if self._metadata is None:
            self._metadata = Metadata()
        return self._metadata
