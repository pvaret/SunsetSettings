# SunsetSettings

SunsetSettings is a Python library that lets you define, load and save settings
in a *type-safe* manner.

It is mainly intended for software where the user can change settings on the
fly, for instance with a settings dialog, and those settings need to be
preserved between sessions.

## Features

### Type safety

SunsetSettings is type-safe; that is to say, if you are holding it wrong, type
checkers will tell you.

### Extensibility

You can store arbitrary types in your SunsetSettings provided they implement a
simple serialization protocol.

### Inheritance

SunsetSettings lets the user have a general set of settings that can be
partially overriden for specific cases (much like your VSCode settings can be
overriden by workspace, for instance). The hierarchy of inheritance can be
arbitrarily deep.

### Callbacks

Each setting can be given callbacks to be called when its value changes.

## Requirements

- Python 3.9 or later.
- The `typing_extensions` module.
- `flit` for installation from sources.

## Installation

### Installing from PyPI

This is not yet available.

### Installing from sources

1. Download the code:

    git clone https://github.com/pvaret/SunsetSettings

2. Install the library:

    flit install

That's it.

## API documentation

In progress! Honestly you should not be using SunsetSettings just YET, it's a
work in progress and the API is not stable yet.