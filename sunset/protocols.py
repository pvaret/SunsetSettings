import weakref

from typing import (
    Any,
    Callable,
    Generic,
    Iterable,
    Iterator,
    Optional,
    Protocol,
    TypeVar,
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
    def dumpFields(self) -> Iterable[tuple[str, Optional[str]]]:
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
    def newInstance(self: Self) -> Self:
        ...


@runtime_checkable
class Containable(Protocol):
    _PATH_SEPARATOR: str

    def setContainer(
        self, label: str, container: Optional["Container"]
    ) -> None:
        ...

    def container(self) -> Optional["Container"]:
        ...

    def fieldLabel(self) -> str:
        ...

    def fieldPath(self) -> str:
        ...

    def isPrivate(self) -> bool:
        ...


@runtime_checkable
class Container(Containable, UpdateNotifier, Protocol):
    def containsFieldWithLabel(self, label: str, field: "Containable") -> bool:
        ...

    def triggerUpdateNotification(
        self, field: "Optional[UpdateNotifier]"
    ) -> None:
        ...


class ContainableImpl:
    """
    A ready-to-use implementation of the Containable protocol.
    """

    _PATH_SEPARATOR: str = "."

    _field_label: str
    _container: Optional[weakref.ref[Container]]

    def __init__(self) -> None:
        super().__init__()

        self._field_label = ""
        self._container = None

    def setContainer(self, label: str, container: Optional[Container]) -> None:
        """
        Internal.
        """

        if container is None:
            self._container = None
            self._field_label = ""
        else:
            self._container = weakref.ref(container)
            self._field_label = label

    def container(self) -> Optional[Container]:
        """
        Internal.
        """

        if self._container is None:
            return None

        container = self._container()
        if container is None:
            return None

        # Make sure this Containable is in fact still held in its supposed
        # Container. Else update the situation.

        if not container.containsFieldWithLabel(self._field_label, self):
            self.setContainer("", None)
            return None

        return container

    def fieldLabel(self) -> str:
        """
        Internal.
        """

        if self.container() is None:
            self._field_label = ""

        return self._field_label

    def fieldPath(self) -> str:
        """
        Internal.
        """

        path = (
            ""
            if (container := self.container()) is None
            else container.fieldPath()
        )

        return path + self.fieldLabel()

    def isPrivate(self) -> bool:
        """
        Internal.
        """

        return self.fieldLabel().startswith("_")


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
