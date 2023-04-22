Changelog
=========

SunsetSettings 0.5.0 (2023-04-22)
---------------------------------

  - Added ability to set a validator on Keys to limit their possible values.
  - Making a typo in a value when editing a settings file manually no longer causes the entry to be deleted on save.
  - Added ability to serialize Enum subclasses natively.
  - Deprecated now unnecessary SerializableEnum and -Flag classes.
  - Added ability to pass a custom serializer when instantiating a Key.
  - Added ability to store any type in a Key.
  - onUpdateCall() and onValueChangeCall() now accept callbacks with any return value.

SunsetSettings 0.4.0 (2023-03-22)
---------------------------------

  - Renamed Bundle to Bunch. Just makes more sense for something that holds Keys.
  - Added serializable Enum and Flag subclasses.
  - AutoSaver now expands '~' to the current user's home directory.
  - Added atomic updateValue() method to Keys.

SunsetSettings 0.3.2 (2022-12-22)
---------------------------------

  - Added AutoSaver context manager.

SunsetSettings 0.3.1 (2022-12-19)
---------------------------------

  - Updated documentation links.

SunsetSettings 0.3.0 (2022-12-19)
---------------------------------

  - Sphinx documentation added.
  - Renamed Setting class to Key.
  - Renamed Section class to Bundle.
  - List overhaul: it now supports both Bundle and Key instances.
  - Removed need for New* functions. Keys, Lists and Bundles can now be used directly in Settings definitions.
  - Removed need for explicit type annotations in Settings class definitions.
  - Renamed List.iterAll() to iter() and added order parameter.
  - Replaced derive() and deriveAs() with newSection() and assorted functions.
  - Renamed onKeyModifiedCall() to onUpdateCall().
  - Added float to supported Key value types.
  - Renamed Settings.name() to Settings.sectionName() and Settings.setName() to Settings.setSectionName().

SunsetSettings 0.2.0 (2022-08-03)
---------------------------------

  - Major docstring overhaul.
  - Minor API updates.

SunsetSettings 0.1.0 (2022-03-25)
---------------------------------

  - Initial release. Code-complete and functional, but undocumented.
