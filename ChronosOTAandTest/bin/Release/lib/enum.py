class Enum:
    @classmethod
    def getname(cls, lookupValue):
        reverseDict = dict((value, key) for (key, value) in cls.__dict__.iteritems())
        if not reverseDict.has_key(lookupValue):
            raise Exception("The value does not exist in the collection")
        return reverseDict[lookupValue]

    @classmethod
    def containsvalue(cls, lookupValue):
        reverseDict = dict((value, key) for (key, value) in cls.__dict__.iteritems())
        hasValue = reverseDict.has_key(lookupValue)
        return hasValue

    @classmethod
    def has_key(cls, lookupValue):
        _dict = dict((value, key) for (key, value) in cls.__dict__.iteritems())
        hasKey = _dict.has_key(lookupValue)