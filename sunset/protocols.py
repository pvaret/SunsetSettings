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
class ModificationNotifier(Protocol):
    def onKeyModifiedCall(self, callback: Callable[[Self], None]) -> None:
        ...
