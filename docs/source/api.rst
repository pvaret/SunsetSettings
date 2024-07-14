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

    .. automethod:: onLoadedCall
    
    .. automethod:: skipOnSave

    .. automethod:: setParent

    .. automethod:: parent

    .. automethod:: children

.. autoclass:: sunset.Key

    .. automethod:: set

    .. automethod:: get

    .. automethod:: isSet
    
    .. automethod:: fallback

    .. automethod:: updateValue

    .. automethod:: clear

    .. automethod:: setValidator

    .. automethod:: onValueChangeCall

    .. automethod:: onUpdateCall

    .. automethod:: onLoadedCall
    
    .. automethod:: skipOnSave

    .. automethod:: setParent

    .. automethod:: parent

    .. automethod:: children

.. autoclass:: sunset.Bunch

    .. automethod:: onUpdateCall

    .. automethod:: onLoadedCall
    
    .. automethod:: skipOnSave

    .. automethod:: setParent

    .. automethod:: parent

    .. automethod:: children

.. autoclass:: sunset.List

    .. automethod:: iter

    .. automethod:: appendOne

    .. automethod:: insertOne

    .. automethod:: onUpdateCall

    .. automethod:: onLoadedCall
    
    .. automethod:: skipOnSave

    .. automethod:: setParent

    .. automethod:: parent

    .. automethod:: children

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
