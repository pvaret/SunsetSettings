import dataclasses
import inspect
import sys
import weakref
from collections.abc import Callable, Iterator, MutableSet
from typing import TYPE_CHECKING, Any, cast

if sys.version_info < (3, 11):
    from typing_extensions import Self
else:
    from typing import Self

if TYPE_CHECKING:
    from types import GenericAlias

from sunset.notifier import Notifier
from sunset.protocols import BaseField, Field, ItemTemplate, UpdateNotifier
from sunset.sets import WeakNonHashableSet


class Bunch(BaseField):
    """
    A collection of related Keys.

    Under the hood, a Bunch is a dataclass, and can be used in the same manner,
    i.e. by defining attributes directly on the class itself.

    Example:

    >>> from sunset import Bunch, Key
    >>> class Appearance(Bunch):
    ...     class Font(Bunch):
    ...         name: Key[str] = Key(default="Arial")
    ...         size: Key[int] = Key(default=14)
    ...     main_font: Font      = Font()
    ...     secondary_font: Font = Font()
    >>> appearance = Appearance()
    >>> appearance.main_font.name.get()
    'Arial'
    >>> appearance.secondary_font.name.get()
    'Arial'
    >>> appearance.main_font.name.set("Times New Roman")
    True
    >>> appearance.secondary_font.name.set("Calibri")
    True
    >>> appearance.main_font.name.get()
    'Times New Roman'
    >>> appearance.secondary_font.name.get()
    'Calibri'
    """

    _parent_ref: weakref.ref["Bunch"] | None
    _children_set: MutableSet["Bunch"]
    _fields: dict[str, Field]
    _update_notifier: Notifier[[UpdateNotifier]]
    _loaded_notifier: Notifier[[]]

    def __new__(cls) -> Self:
        # Build and return a dataclass constructed from this class. Keep a
        # reference to that dataclass as a private class attribute, so that we
        # only construct it once. This allows type identity checks (as in
        # "type(a) is type(b)") to work.

        dataclass_attr = "__DATACLASS_CLASS"
        orig_class_attr = "__ORIG_CLASS"

        dataclass_class: type[Self] | None = None
        if dataclasses.is_dataclass(cls):
            # If this class is already a dataclass, then no need to construct a new one.
            # Just use this one directly.
            dataclass_class = cls
        else:
            # Else use the dataclass recorded on this class, if there is one. Note the
            # use of vars(), in order to look up the dataclass for this specific
            # class, and not one of its parents.
            dataclass_class = vars(cls).get(dataclass_attr, None)

        if dataclass_class is None:
            # We haven't yet constructed a dataclass from this class. Construct
            # one here.

            cls_parents = cls.__bases__
            dataclass_fields: list[tuple[str, type | GenericAlias, ItemTemplate]] = []
            potential_fields = [
                (name, getattr(cls, name, None))
                for name in dir(cls)
                if not name.startswith("__")
            ]

            for name, attr in potential_fields:
                if inspect.isclass(attr):
                    if attr.__name__ == name:
                        # This is probably a class definition that just happens
                        # to be located inside the containing Bunch definition.
                        # This is fine.

                        continue

                    msg = (
                        f"Field '{name}' in the definition of '{cls.__name__}' is"
                        " uninstantiated. Did you forget the parentheses?"
                    )
                    raise TypeError(msg)

                if isinstance(attr, ItemTemplate):
                    # Safety check: make sure the user isn't accidentally overriding an
                    # existing attribute. We do however allow overriding an attribute
                    # with an attribute of the same type, which allows the user to
                    # override a Key with a Key of the same type but a different
                    # default value, for instance.

                    for cls_parent in cls_parents:
                        if (
                            parent_attr := getattr(cls_parent, name, None)
                        ) is not None and type(parent_attr) is not type(attr):
                            msg = (
                                f"Field '{name}' in the definition of"
                                f" '{cls.__name__}' overrides attribute of the"
                                " same name declared in parent class"
                                f" '{cls_parent.__name__}'; consider renaming"
                                f" this field to '{name}_' for instance"
                            )
                            raise TypeError(msg)

                    # Create a proper field from the attribute.

                    field = dataclasses.field(default_factory=attr._newInstance)  # noqa: SLF001
                    dataclass_fields.append((name, attr._typeHint(), field))  # noqa: SLF001

            # Create a dataclass based on this class. Note that we will be
            # providing our own __init__() override below.

            kwargs: dict[str, Any] = (
                {} if sys.version_info < (3, 12) else {"module": cls.__module__}
            )
            dataclass_class = cast(
                type[Self],
                dataclasses.make_dataclass(
                    cls.__qualname__,
                    dataclass_fields,
                    init=False,
                    bases=(cls, *cls_parents),
                    **kwargs,
                ),
            )

            # And store it on the class itself so it can be reused if this class is
            # instantiated again.

            setattr(cls, dataclass_attr, dataclass_class)

            # Also keep a reference to the original class, so that's not lost.

            setattr(dataclass_class, orig_class_attr, cls)

        # Create an instance of the dataclass.

        new_cls = super().__new__(dataclass_class)

        # Set up the fields that were identified above as instance attributes.

        new_cls.__setup_fields__()
        return new_cls

    def __setup_fields__(self) -> None:
        # Set up the Bunch fields as instance attributes.
        # First, look up internal dataclass attribute names.

        fields_attr: str = getattr(dataclasses, "_FIELDS")  # noqa: B009
        field_type: Any = getattr(dataclasses, "_FIELD")  # noqa: B009
        fields: dict[str, dataclasses.Field[Any]] = getattr(self, fields_attr, {})

        # Then look up the fields stored in the dataclass.

        for field in fields.values():
            if getattr(field, "_field_type", None) is not field_type:
                continue

            if field.default_factory is dataclasses.MISSING:
                continue

            setattr(self, field.name, field.default_factory())

    def __init__(self) -> None:
        super().__init__()

        self._parent_ref = None
        self._children_set = WeakNonHashableSet[Bunch]()
        self._fields = {}
        self._update_notifier = Notifier()
        self._loaded_notifier = Notifier()

        for label, field in vars(self).items():
            if isinstance(field, Field):
                self._fields[label] = field
                field.meta().update(label=label, container=self)
                field._update_notifier.add(self._update_notifier.trigger)  # noqa: SLF001
                self._loaded_notifier.add(field._loaded_notifier.trigger)  # noqa: SLF001

        self.__post_init__()

    def __post_init__(self) -> None:
        """
        DEPRECATED. Will be removed in v1.0.

        Use __init__() instead.
        """

    def setParent(self, parent: Self | None) -> None:
        """
        Makes the given Bunch the parent of this one. If None, remove this
        Bunch's parent, if any.

        All the Key, List and Bunch fields defined on this Bunch instance
        will be recursively reparented to the corresponding Key / List / Bunch
        field on the given parent.

        This method is for internal purposes and you will typically not need to
        call it directly.

        Args:
            parent: Either a Bunch that will become this Bunch's parent, or
                None. The parent Bunch must have the same type as this
                Bunch.

        Note:
            A Bunch and its parent, if any, do not increase each other's
            reference count.
        """

        # Runtime check to affirm the type check of the method.

        if parent is not None and type(self) is not type(parent):
            return

        old_parent = self.parent()
        if old_parent is not None:
            old_parent._children_set.discard(self)  # noqa: SLF001

        if parent is None:
            self._parent_ref = None
        else:
            self._parent_ref = weakref.ref(parent)
            parent._children_set.add(self)  # noqa: SLF001

        for label, field in self._fields.items():
            if parent is None:
                field.setParent(None)
                continue

            parent_field = parent._fields.get(label)
            if parent_field is None:
                # This is a safety check, but it shouldn't happen. By
                # construction self should be of the same type as parent, so
                # they should have the same attributes.

                continue

            assert type(field) is type(parent_field)  # noqa: S101
            field.setParent(parent_field)

    def parent(self) -> Self | None:
        """
        Returns the parent of this Bunch, if any.

        Returns:
            A Bunch instance of the same type as this one, or None.
        """

        # Make the type of self._parent_ref more specific for the purpose of
        # type checking.

        parent = cast(weakref.ref[Self] | None, self._parent_ref)
        return parent() if parent is not None else None

    def children(self) -> Iterator[Self]:
        """
        Returns an iterator over the Bunch instances that have this Bunch
        as their parent.

        Returns:
            An iterator over Bunch instances of the same type as this one.
        """

        # Note that we iterate on a copy so that this will not break if a
        # different thread updates the contents during the iteration.

        for child in list(self._children_set):
            yield cast(Self, child)

    def onUpdateCall(self, callback: Callable[[Any], Any]) -> None:
        """
        Adds a callback to be called whenever this Bunch is updated. A Bunch
        is considered updated when any of its fields is updated.

        The callback will be called with as its argument whichever field was
        just updated.

        Args:
            callback: A callable that will be called with one argument of type
                :class:`~sunset.List`, :class:`~sunset.Bunch` or
                :class:`~sunset.Key`.

        Note:
            This method does not increase the reference count of the given
            callback.
        """

        self._update_notifier.add(callback)

    def onLoadedCall(self, callback: Callable[[], Any]) -> None:
        """
        Adds a callback to be called whenever settings were just loaded. This
        Bunch itself may or may not have been modified during the load.

        Args:
            callback: A callable that takes no argument.

        Note:
            This method does not increase the reference count of the given
            callback.
        """

        self._loaded_notifier.add(callback)

    def isSet(self) -> bool:
        """
        Indicates whether this Bunch holds any field that is set.

        Returns:
            True if any field set on this Bunch is set, else False.
        """

        return any(field.isSet() for field in self._fields.values())

    def dumpFields(self) -> Iterator[tuple[str, str | None]]:
        """
        Internal.
        """

        sep = self._PATH_SEPARATOR
        if not self.skipOnSave():
            for label, field in sorted(self._fields.items()):
                yield from (
                    (label + sep + path if path else label, item)
                    for path, item in field.dumpFields()
                )

    def restoreField(self, path: str, value: str | None) -> bool:
        """
        Internal.
        """

        with self._update_notifier.inhibit():
            if self._PATH_SEPARATOR in path:
                field_label, path = path.split(self._PATH_SEPARATOR, 1)
            else:
                field_label, path = path, ""

            if (field := self._fields.get(field_label)) is not None:
                return field.restoreField(path, value)

        return False

    def _typeHint(self) -> type:
        return type(self)

    def _newInstance(self) -> Self:
        """
        Internal. Returns a new instance of this Bunch with the same fields.

        Returns:
            A Bunch instance.
        """

        return self.__class__()
