import weakref

from dataclasses import dataclass, field
from typing import (
    Callable,
    Iterator,
    MutableSet,
    Optional,
    Sequence,
    Type,
    TypeVar,
)

from typing_extensions import Self

from .non_hashable_set import WeakNonHashableSet
from .protocols import Dumpable, Inheriter, Restorable, ModificationNotifier
from .registry import CallbackRegistry

SectionT = TypeVar("SectionT", bound="Section")


class Section:
    def __new__(cls: Type[Self]) -> Self:

        wrapped = dataclass()(cls)
        return super().__new__(wrapped)

    def __post_init__(self: Self) -> None:

        self._parent: Optional[weakref.ref[Self]] = None
        self._children: MutableSet[Self] = WeakNonHashableSet[Self]()
        self._modification_notification_callbacks: CallbackRegistry[
            Self
        ] = CallbackRegistry()

        for attr in vars(self).values():

            if isinstance(attr, ModificationNotifier):
                attr.onSettingModifiedCall(self._notifyModification)

    def derive(self: Self) -> Self:

        new = self.__class__()
        new.inheritFrom(self)
        return new

    def inheritFrom(self: Self, parent: Optional[Self]) -> None:

        old_parent = self.parent()
        if old_parent is not None:
            old_parent._children.discard(self)
        if parent is None:
            self._parent = None
        else:
            self._parent = weakref.ref(parent)
            parent._children.add(self)

        for attrName, attr in vars(self).items():

            if not isinstance(attr, Inheriter):
                continue

            if parent is None:
                attr.inheritFrom(None)  # type: ignore
                continue

            parentAttr = getattr(parent, attrName, None)
            if parentAttr is None:
                # This is a safety check, but it shouldn't happen. By
                # construction self should be of the same type as parent, so
                # they should have the same attributes.
                continue

            assert isinstance(parentAttr, Inheriter)
            assert type(attr) is type(parentAttr)  # type: ignore
            attr.inheritFrom(parentAttr)  # type: ignore

    def parent(self: Self) -> Optional[Self]:

        return self._parent() if self._parent is not None else None

    def children(self: Self) -> Iterator[Self]:

        yield from self._children

    def onSettingModifiedCall(self, callback: Callable[[Self], None]) -> None:

        self._modification_notification_callbacks.add(callback)

    def dump(self) -> Sequence[tuple[str, str]]:

        ret: list[tuple[str, str]] = []

        for attrName, attr in sorted(vars(self).items()):
            if not isinstance(attr, Dumpable):
                continue

            if attrName.startswith("_"):
                continue

            for subAttrName, dump in attr.dump():
                name = ".".join(s for s in (attrName, subAttrName) if s)
                ret.append((name, dump))

        return ret

    def restore(self, data: Sequence[tuple[str, str]]) -> None:

        for name, dump in data:
            if "." in name:
                item_name, subname = name.split(".", 1)
            else:
                item_name, subname = name, ""

            try:
                item = getattr(self, item_name)
            except AttributeError:
                continue

            if not isinstance(item, Restorable):
                continue

            item.restore([(subname, dump)])

    def _notifyModification(self, value: ModificationNotifier) -> None:

        self._modification_notification_callbacks.callAll(self)


def NewSection(section: Type[SectionT]) -> SectionT:

    return field(default_factory=section)
