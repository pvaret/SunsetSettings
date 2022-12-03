import weakref

from typing import (
    Callable,
    Iterator,
    Optional,
    Protocol,
    Sequence,
    Type,
    TypeVar,
    runtime_checkable,
)

from typing_extensions import Self

_T = TypeVar("_T")


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
    def fromStr(cls: Type[Self], value: str) -> Optional[Self]:
        """
        Takes a string that represents a serialized instance of this class, and
        returns a newly created instance that corresponds to that
        representation, or None is the string is not a valid serialized
        representation of an instance.
        """
        ...


@runtime_checkable
class Inheriter(Protocol[_T]):
    def setParent(self: _T, parent: Optional[_T]) -> None:
        ...

    def parent(self: _T) -> Optional[_T]:
        ...

    def children(self: _T) -> Iterator[_T]:
        ...


@runtime_checkable
class Dumpable(Protocol):
    def dump(self) -> Sequence[tuple[str, str]]:
        ...


@runtime_checkable
class Restorable(Protocol):
    def restore(self, data: Sequence[tuple[str, str]]) -> None:
        ...


@runtime_checkable
class UpdateNotifier(Protocol):
    def onUpdateCall(self, callback: Callable[[Self], None]) -> None:
        ...


@runtime_checkable
class ItemTemplate(Protocol):
    def newInstance(self: Self) -> Self:
        ...


@runtime_checkable
class Container(Protocol):
    def containsField(self, field: "Containable") -> bool:
        ...


@runtime_checkable
class Containable(Protocol):
    def setContainer(self, label: str, container: Optional[Container]) -> None:
        ...

    def container(self) -> Optional[Container]:
        ...

    def fieldLabel(self) -> str:
        ...


class ContainableImpl:
    """
    A ready-to-use implementation of the Containable protocol.
    """

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

        if not container.containsField(self):
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


assert isinstance(ContainableImpl, Containable)
