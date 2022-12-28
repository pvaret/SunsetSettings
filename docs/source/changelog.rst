Changelog
=========

Latest
------

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