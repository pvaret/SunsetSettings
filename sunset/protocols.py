import weakref

from dataclasses import dataclass

from types import GenericAlias
from typing import (
    Any,
    Callable,
    Generic,
    Iterator,
    Optional,
    Protocol,
    TypeVar,
    Union,
    runtime_checkable,
)


Self = TypeVar("Self")
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
    def setParent(self: Self, parent: Optional[Self]) -> None:
        ...

    def parent(self: Self) -> Optional[Self]:
        ...

    def children(self: Self) -> Iterator[Self]:
        ...


@runtime_checkable
class Dumpable(Protocol):
    def dumpFields(self) -> Iterator[tuple[str, Optional[str]]]:
        ...

    def restoreField(self, path: str, value: Optional[str]) -> bool:
        ...

    def isSet(self) -> bool:
        ...


@runtime_checkable
class UpdateNotifier(Protocol):
    def onUpdateCall(self, callback: Callable[[Any], Any]) -> None:
        ...


@runtime_checkable
class ItemTemplate(Protocol):
    def _typeHint(self) -> Union[type, GenericAlias]:
        ...

    def _newInstance(self: Self) -> Self:
        ...


@runtime_checkable
class Containable(Protocol):
    _PATH_SEPARATOR: str

    def _setContainer(
        self, label: str, container: Optional["Container"]
    ) -> None:
        ...

    def _container(self) -> Optional["Container"]:
        ...

    def skipOnSave(self) -> bool:
        ...

    def meta(self) -> "Metadata":
        ...


@runtime_checkable
class Container(Containable, UpdateNotifier, Protocol):
    def _containsFieldWithLabel(self, label: str, field: "Containable") -> bool:
        ...

    def _triggerUpdateNotification(
        self, field: "Optional[UpdateNotifier]"
    ) -> None:
        ...


@dataclass
class Metadata:
    container: Optional[weakref.ref[Container]] = None
    label: str = ""

    def clear(self) -> None:
        self.container = None
        self.label = ""

    def path(self) -> str:
        if self.container is None or (container := self.container()) is None:
            # Should be empty, actually.
            return self.label

        path = container.meta().path()

        if not path:
            return self.label

        return path + container._PATH_SEPARATOR + self.label


class ContainableImpl:
    """
    A ready-to-use implementation of the Containable protocol.
    """

    _PATH_SEPARATOR: str = "."

    _container_ref: Optional[weakref.ref[Container]] = None
    _metadata: Optional[Metadata] = None

    def _setContainer(self, label: str, container: Optional[Container]) -> None:
        """
        Internal.
        """

        metadata = self.meta()
        metadata.clear()
        if container is None:
            self._container_ref = None
        else:
            self._container_ref = weakref.ref(container)
            metadata.label = label
            metadata.container = weakref.ref(container)

    def _container(self) -> Optional[Container]:
        """
        Internal.
        """

        if self._container_ref is None:
            return None

        container = self._container_ref()
        if container is None:
            return None

        # Make sure this Containable is in fact still held in its supposed
        # Container. Else update the situation.

        if not container._containsFieldWithLabel(self.meta().label, self):
            self._setContainer("", None)
            return None

        return container

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


assert isinstance(ContainableImpl, Containable)


@runtime_checkable
class Field(
    Containable,
    Dumpable,
    Inheriter,
    ItemTemplate,
    UpdateNotifier,
    Protocol,
):
    ...
