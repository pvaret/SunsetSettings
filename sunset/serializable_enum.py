import enum
import functools

from typing import Optional, TypeVar, cast

# TODO: Replace with typing.Self when mypy finally supports that.
Self = TypeVar("Self", bound="_SerializableEnumMixin")


class _SerializableEnumMixin:
    def _compute_name(self) -> None:
        if isinstance(self, enum.Flag) and self._name_ is None:
            # WORKAROUND: In Python 3.10 and earlier, compound flags do not get
            # a name, which we need for serialization. So we have to compute one
            # ourselves.

            names: list[str] = []
            final_name: Optional[str] = None
            current_value: Optional[int] = None

            # Note how we sort the items by ascending value. This lets us keep
            # the name component order deterministic, as well as prioritize the
            # lowest-value members when compositing a compound flag.

            for name, member in sorted(
                self._members().items(), key=lambda item: item[1].value
            ):
                if member.value == self.value:
                    # We found a member whose value is exactly this instance's
                    # value. Let's use its name and end the process here.

                    final_name = name
                    break

                if member.value & self.value == member.value:
                    # This member potentially contributes its value to the value
                    # of this instance.

                    if current_value is not None:
                        if current_value | member.value == current_value:
                            # This member does not add a contribution to the
                            # overall value of this instance that isn't already
                            # contributed by already accounted for members. Skip
                            # it.

                            continue

                        current_value |= member.value

                    else:
                        current_value = member.value

                    names.append(name)

            if not final_name:
                if names:
                    final_name = "|".join(names)

            if final_name:
                # "_name_" is the internal attribute used to implement both
                # __repr__() and name(). We use setattr instead of directly
                # setting the attribute, because the attribute can have
                # different types (str or str|None) in the different possible
                # Enum subclasses this mixin can be used with, and so the
                # type checker would complain about the assignment breaking
                # inheritance no matter which way we type it.

                setattr(self, "_name_", final_name)

    @classmethod
    def _members(cls: type[Self]) -> dict[str, Self]:
        members: dict[str, Self] = {}

        # This helps the type checker understand what we're doing here with this
        # mixin. This assert Should™ never be raised, since we only compose this
        # mixin with enum.Enum subclasses.

        assert issubclass(cls, enum.Enum)

        for name, member in getattr(cls, "__members__", cls.__dict__).items():
            if isinstance(member, cls):
                members[name] = member

        return members

    @classmethod
    def fromStr(cls: type[Self], value: str) -> Optional[Self]:
        # value is either a single word, or, in the case of Flag enums, multiple
        # words separated by a pipe. We handle both cases together here.

        members = cls._members()
        names = value.split("|") if "|" in value else [value]
        named_members = [
            members[n] for name in names if (n := name.strip()) in members
        ]

        if not named_members:
            return None

        if issubclass(cls, enum.Flag):
            # At this point, we know that all the members are instances of this
            # class, and this class is a subclass of enum.Flag. So we can safely
            # cast to make the type checker happy, apply the OR operator to the
            # members we found, and return the result.

            flag_members = cast(list[enum.Flag], named_members)
            ret = functools.reduce(lambda f1, f2: f1 | f2, flag_members)
            return cast(Self, ret)

        # If this mixin is not used with a Flag, then there should be a single
        # member found on the class with the exact given name. If so, return
        # that, otherwise it's an error and we return None.

        return named_members[0] if len(named_members) == 1 else None

    def toStr(self) -> str:
        # This helps the type checker understand what we're doing here with this
        # mixin. This assert Should™ never be raised, since we only compose this
        # mixin with enum.Enum subclasses.

        assert isinstance(self, enum.Enum)

        if getattr(self, "_name_", None) is None:
            # We need to call this here because the Enum internals in Python
            # 3.10 and earlier set the name to None *after* the instance is
            # created. So this can't go in, say, __init__().

            self._compute_name()

        # Returning this instance's name suffices due to the setup work done in
        # self._compute_name().

        return self.name


class SerializableEnum(_SerializableEnumMixin, enum.Enum):
    """
    An `enum.Enum` subclass that implements the :class:`~sunset.Serializable`
    protocol and can therefore be used as a Key value.

    Example:

    >>> from sunset import Key, SerializableEnum
    >>> class Color(SerializableEnum):
    ...     RED = 1
    ...     GREEN = 2
    ...     BLUE = 3
    >>> key: Key[Color] = Key(Color.RED)
    >>> print(key.get().toStr())
    RED
    >>> key.set(Color.GREEN)
    >>> print(key.get().toStr())
    GREEN
    """


class SerializableFlag(_SerializableEnumMixin, enum.Flag):
    """
    An `enum.Flag` subclass that implements the :class:`~sunset.Serializable`
    protocol and can therefore be used as a Key value.

    Example:

    >>> import enum
    >>> from sunset import Key, SerializableFlag
    >>> class ColorFlag(SerializableFlag):
    ...     RED = enum.auto()
    ...     GREEN = enum.auto()
    ...     BLUE = enum.auto()
    ...     WHITE = RED | GREEN | BLUE
    >>> purple = ColorFlag.RED | ColorFlag.BLUE
    >>> key: Key[ColorFlag] = Key(purple)
    >>> print(key.get().toStr())
    RED|BLUE
    >>> white = purple | ColorFlag.GREEN
    >>> key.set(white)
    >>> print(key.get().toStr())
    WHITE
    """
