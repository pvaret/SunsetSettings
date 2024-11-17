Changelog
=========

SunsetSettings 0.6.1 (2024-11-17)
---------------------------------

  - Added Python 3.13 to officially supported versions.
  - Migrated to Hatch as the build and environment management system.
  - Arguments after the first position in :code:`Settings.save()` and
    :code:`Settings.autosave()` methods are now keyword-only arguments.
  - Fixed several subtle bugs that could occur when creating a :code:`Bunch` as a
    subclass of another :code:`Bunch`.
  - Deprecated :code:`Bunch.__post_init__()` and :code:`Settings.__post_init__()`.

SunsetSettings 0.6.0 (2024-07-16)
---------------------------------

  - Dropped support for Python 3.9.
  - Fixed a race condition in :code:`NonHashableSet`.
  - Added :code:`onLoadedCall()` to :code:`Key`, :code:`List` and :code:`Bunch` types,
    to call a callback after settings were just loaded. API is experimental, and may
    change.

SunsetSettings 0.5.6 (2024-06-17)
---------------------------------

  - Removed :code:`Self` type workaround now that mypy handles it properly.
  - Fixed notification inhibitation issue that caused update notifications to fail
    to fire.

SunsetSettings 0.5.5 (2024-02-18)
---------------------------------

  - Moved some internal field properties into a new metadata attribute.
  - Major internals cleanup.

SunsetSettings 0.5.4 (2024-02-01)
---------------------------------

  - Added Python 3.12 to officially supported versions.
  - Fixed regression where changing a section's name might silently fail.

SunsetSettings 0.5.3 (2024-01-29)
---------------------------------

  - Made some internal methods private to de-clutter the API namespace.
  - Documented some internal methods where it may make to expose them publically.
  - Renamed internal method :code:`isPrivate()` into :code:`skipOnSave()`.
  - :code:`onUpdateCall()` callbacks are now called for entities for which
    :code:`skipOnSave()` is true.
  - Improved notification logic when a section is renamed or reparented.
  - Added :code:`fallback()` method to :code:`Key`.

SunsetSettings 0.5.2 (2023-08-14)
---------------------------------

  - Added more logging when :code:`AutoSaver` loads/saves.
  - Added ability to create a :code:`Key` with an explicit runtime type.
  - Rolled back undocumented :code:`Bunch` default value override feature. It's not
    dependable.

SunsetSettings 0.5.1 (2023-04-26)
---------------------------------

  - Made deserializing an enum case-insensitive when the result is
    non-ambiguous.
  - Added ability to instantiate :code:`Bunch` with default value overrides. This is
    still experimental and undocumented.

SunsetSettings 0.5.0 (2023-04-22)
---------------------------------

  - Added ability to set a validator on a :code:`Key` to restrict its possible values.
  - Making a typo in a value when editing a settings file manually no longer
    causes the entry to be deleted on save.
  - Added ability to serialize :code:`Enum` subclasses natively.
  - Deprecated now unnecessary :code:`SerializableEnum` and :code:`SerializableFlag`
    classes.
  - Added ability to pass a custom serializer when instantiating a :code:`Key`.
  - Added ability to store any type in a :code:`Key`.
  - :code:`onUpdateCall()` and :code:`onValueChangeCall()` now accept callbacks with any
    return value.

SunsetSettings 0.4.0 (2023-03-22)
---------------------------------

  - Renamed :code:`Bundle` to :code:`Bunch`. Just makes more sense for something that
    holds :code:`Keys`.
  - Added serializable :code:`Enum` and :code:`Flag` subclasses.
  - :code:`AutoSaver` now expands '~' to the current user's home directory.
  - Added atomic :code:`updateValue()` method to :code:`Key`.

SunsetSettings 0.3.2 (2022-12-22)
---------------------------------

  - Added :code:`AutoSaver` context manager.

SunsetSettings 0.3.1 (2022-12-19)
---------------------------------

  - Updated documentation links.

SunsetSettings 0.3.0 (2022-12-19)
---------------------------------

  - Sphinx documentation added.
  - Renamed :code:`Setting` class to :code:`Key`.
  - Renamed :code:`Section` class to :code:`Bundle`.
  - :code:`List` overhaul: it now supports both :code:`Bundle` and :code:`Key`
    instances.
  - Removed need for :code:`New*` functions. :code:`Key`, :code:`List` and
    :code:`Bundle` instances can now be used directly in :code:`Settings` definitions.
  - Removed need for explicit type annotations in :code:`Settings` class definitions.
  - Renamed :code:`List.iterAll()` to :code:`iter()` and added order parameter.
  - Replaced :code:`derive()` and :code:`deriveAs()` with :code:`newSection()` and
    assorted functions. - Renamed :code:`onKeyModifiedCall()` to :code:`onUpdateCall()`.
  - Added float to supported :code:`Key` value types.
  - Renamed :code:`Settings.name()` to :code:`Settings.sectionName()` and
    :code:`Settings.setName()` to :code:`Settings.setSectionName()`.

SunsetSettings 0.2.0 (2022-08-03)
---------------------------------

  - Major docstring overhaul.
  - Minor API updates.

SunsetSettings 0.1.0 (2022-03-25)
---------------------------------

  - Initial release. Code-complete and functional, but undocumented.
