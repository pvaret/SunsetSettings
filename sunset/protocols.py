from typing import (
    Iterator,
    Optional,
    Protocol,
    Sequence,
    TypeVar,
    runtime_checkable,
)

_T = TypeVar("_T")
_T_co = TypeVar("_T_co", covariant=True)


@runtime_checkable
class Serializable(Protocol[_T_co]):
    def toStr(self) -> str:
        ...

    @staticmethod
    def fromStr(value: str) -> tuple[bool, _T_co]:
        ...


@runtime_checkable
class Inheriter(Protocol[_T]):
    def inheritFrom(self: _T, parent: Optional[_T]) -> None:
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
