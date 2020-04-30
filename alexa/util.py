# -*- coding: utf-8 -*-

"""Utilities to translate floating point numbers to Specific Gravity jargon"""

class sgCase(object):
    
    argParts = {}
    
    def digitsToSpeech(self, argument):
        
        # split the SG into two parts e.g. 1050 to 10 and 50
        self.argParts = self.splitString(str(argument))
        
        # Build the methodName from the first part of the measurement
        methodName = 'speech' + self.argParts['first']
        
        method = getattr(self, methodName, lambda: "Invalid measurement")
        
        # Call the method as we return it
        return method()
        
    def speech9(self):
        return "nine " + self.argParts['second']
        
    def speech10(self):
        return "ten " + self.argParts['second']
        
    def speech11(self):
        return "eleven " + self.argParts['second']
        
    def splitString(self, argument):
        """Split the measurement into two strings so the correct method can be invoked"""
        argString = str(argument)
        argLen = len(argString)
        result = {}
        
        if argLen == 3:
            result['first'] = argString[0: 1:]
            result['second'] = argString[1: 3:]
        elif argLen == 4:
            result['first'] = argString[0: 2:]
            result['second'] = argString[2: 4:]
        else:
            result['first'] = "0"
            
        return result
# end of sgCase class    
    
def saySpecificGravity(reading):
    
    case = sgCase()
    
    speech = case.digitsToSpeech(reading)
    
    return speech

def validateSG(reading):
    
    # Assume the worst
    result = 0.0
    
    if (reading >= 0.99 and
        reading <= 1.170):
        result = reading * 1000.0
    elif (reading >= 990 and
        reading <= 1170):
        result = reading
        
    return result


def validateTemp(temp):
    
    # Assume the worst
    result = 0.0
    
    # If the temperature is between 10 and 40, assume it is Celsius and convert to
    # Fahrenheit
    if (temp >= 10.0 and
        temp <= 40.0):
        temp = CelsiusToF(temp)
    
    if (temp > 32.0 and
        temp <= 120.0):
        result = temp
    
    return result

def CelsiusToF(Celsius):
    
    return (Celsius * 1.8) + 32.0

        
        
