API Reference
=============

.. autoclass:: sunset.Settings

    .. automethod:: load

    .. automethod:: save

    .. automethod:: autosave

    .. automethod:: newSection

    .. automethod:: getOrCreateSection

    .. automethod:: getSection

    .. automethod:: sections

    .. automethod:: sectionName

    .. automethod:: setSectionName

    .. automethod:: onUpdateCall

.. autoclass:: sunset.Key

    .. automethod:: set

    .. automethod:: get

    .. automethod:: isSet

    .. automethod:: updateValue

    .. automethod:: clear

    .. automethod:: setValidator

    .. automethod:: onValueChangeCall

    .. automethod:: onUpdateCall

.. autoclass:: sunset.Bunch

    .. automethod:: onUpdateCall

.. autoclass:: sunset.List

    .. automethod:: iter

    .. automethod:: appendOne

    .. automethod:: insertOne

    .. automethod:: onUpdateCall

.. autoclass:: sunset.AutoSaver

    .. automethod:: doLoad

    .. automethod:: doSave

    .. automethod:: saveIfNeeded

.. autoclass:: sunset.Serializer

    .. automethod:: toStr

    .. automethod:: fromStr

.. autoclass:: sunset.Serializable

    .. automethod:: toStr

    .. automethod:: fromStr
