# -*- coding: utf-8 -*-

SKILL_TITLE = "Hydrometer Correction Skill"

WELCOME_MESSAGE = ("Welcome to the hydrometer correction skill.  "
                   "You can say things like, 'gravity is ten fifty.' ")

CARD_WELCOME = ("Welcome to the Hydrometer Correction Skill. ")

EXIT_SKILL_MESSAGE = "Thank you for using the hydrometer correction skill. "

REPROMPT_SPEECH = "You can say things like, 'gravity is ten fifty.' "

HELP_MESSAGE = "Your hydrometer was calibrated to display specific gravity at a particular temperature. When you take a gravity reading of a wort sample at some temperature other than its calibration temperature, that gravity reading needs to be corrected. Please tell me your specific gravity measurement without the decimal point. For example, you can say gravity is ten forty five. I will then ask you for the temperature of the sample at the time you took the gravity reading. "

CARD_HELP = "You can say things like 'gravity is 1.050.' "

GRAVITY_MESSAGES = {1: "Sorry, I didn't catch the gravity. Please say your gravity reading without the decimal point. For example, you can say, ten fifty six. ", 2: "I didn't understand that gravity reading. Specific gravity without the decimal point would be something like, ten forty two. ", 3: "Most hydrometers measure specific gravity in the range of nine nine zero to eleven seventy. You told me, {}. Please say a gravity reading without a decimal point within the valid range." }

TEMPERATURE_MESSAGES = {1: "Okay, gravity is {}. What was the temperature of the sample when this was taken? ", 2: "Please tell me the temperature of your {} reading. ", 3: "I can only handle temperature readings between 33 and 120 degrees Farenheit or between 1 and 49 degrees Celsius. You told me {}. Please say a wort sample temperature within the valid range. "}

CALIBRATE_MESSAGES = {1: "Okay, I have a measured gravity of {} at {} degrees. What is your hydrometer's calibration temperature? ", 2: "Please refer to your hydrometer's documentation and tell me its calibration temperature. ", 3: "I can only handle temperature readings between 32 and 120 degrees Farenheit or between 0 and 49 degrees Celsius. You told me {}. Please say a calibration temperature within the valid range."}

FALLBACK_ANSWER = (
    "Sorry. I can't help you with that. {}".format(HELP_MESSAGE))
