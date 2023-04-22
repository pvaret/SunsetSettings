import enum
import functools

from typing import Generic, Optional, TypeVar, cast

_EnumT = TypeVar("_EnumT", bound=enum.Enum)


class EnumSerializer(Generic[_EnumT]):
    _type: type[_EnumT]

    def __init__(self, type_: type[_EnumT]) -> None:
        super().__init__()

        self._type = type_

    def _compute_and_set_name(self, value: _EnumT) -> None:
        if (
            not isinstance(value, enum.Flag)
            or getattr(value, "_name_", None) is not None
        ):
            return

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
            if member.value == value.value:
                # We found a member whose value is exactly this instance's
                # value. Let's use its name and end the process here.

                final_name = name
                break

            if member.value & value.value == member.value:
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
            # pylint: disable-next=protected-access
            value._name_ = final_name

    def _members(self) -> dict[str, _EnumT]:
        members: dict[str, _EnumT] = {}

        # Note that we use the __members__ attribute and not dir() in order to
        # get the members in order of declaration.

        for name, member in self._type.__members__.items():
            if isinstance(member, self._type):
                members[name] = member

        return members

    def fromStr(self, string: str) -> Optional[_EnumT]:
        # value is either a single word, or, in the case of Flag enums, multiple
        # words separated by a pipe. We handle both cases together here.

        members = self._members()
        names = string.split("|") if "|" in string else [string]
        named_members = [
            members[n] for name in names if (n := name.strip()) in members
        ]

        if not named_members:
            return None

        if issubclass(self._type, enum.Flag):
            # At this point, we know that all the members are instances of this
            # class, and this class is a subclass of enum.Flag. So we can safely
            # cast to make the type checker happy, apply the OR operator to the
            # members we found, and return the result.

            flag_members = cast(list[enum.Flag], named_members)
            ret = functools.reduce(lambda f1, f2: f1 | f2, flag_members)
            return cast(_EnumT, ret)

        # If this serializer is not used with a Flag, then there should be a
        # single member found on the class with the exact given name. If so,
        # return that, otherwise it's an error and we return None.

        return named_members[0] if len(named_members) == 1 else None

    def toStr(self, value: _EnumT) -> str:
        if getattr(value, "_name_", None) is None:
            # We need to call this here because the Enum internals in Python
            # 3.10 and earlier set the name to None *after* the instance is
            # created. So this call can't go in, say, __init__().

            self._compute_and_set_name(value)

        # Returning this instance's name property suffices due to the setup work
        # done in self._compute_and_set_name().

        return value.name


# LEGACY: In SunsetSettings 0.4, these custom Enum/Flag subclasses were made
# available. They are no longer necessary since we now can serialize Enums
# directly, but we keep providing them for backward compatibility.

SerializableEnum = enum.Enum
SerializableFlag = enum.Flag
