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
    def toStr(self) -> str:
        ...

    @classmethod
    def fromStr(cls: Type[Self], value: str) -> Optional[Self]:
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
    def onSettingModifiedCall(self, callback: Callable[[Self], None]) -> None:
        ...
