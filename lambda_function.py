import json
import logging
import os
import boto3

# Use an S3 repository bucket to save slot values
from ask_sdk_s3.adapter import S3Adapter

# Set up the bucket adapter so that we can interact with the repository
# TODO: Figure out if each user gets his/her own file within this bucket. May need to modify the path_prefix?
bucket_name = "gravresponse"
s3_client = boto3.client('s3', config=boto3.session.Config(signature_version='s3v4',s3={'addressing_style': 'path'}))
s3_adapter = S3Adapter(bucket_name=bucket_name, path_prefix=None, s3_client=s3_client)

# We need the CustomSkillBuilder in order to access the S3 repository
from ask_sdk_core.skill_builder import CustomSkillBuilder
from ask_sdk_core.handler_input import HandlerInput
from ask_sdk_core.serialize import DefaultSerializer
from ask_sdk_core.dispatch_components import (
    AbstractRequestHandler, AbstractExceptionHandler,
    AbstractResponseInterceptor, AbstractRequestInterceptor)
from ask_sdk_core.utils import is_intent_name, is_request_type
from ask_sdk_core.response_helper import (
    get_plain_text_content, get_rich_text_content)

from ask_sdk_model.interfaces.display import (
    ImageInstance, Image, RenderTemplateDirective, ListTemplate1,
    BackButtonBehavior, ListItem, BodyTemplate2, BodyTemplate1)
from ask_sdk_model import ui, Response, DialogState
from ask_sdk_model.ui import SimpleCard
from ask_sdk_model.dialog import ElicitSlotDirective, DelegateDirective
from ask_sdk_model import (
    Intent , IntentConfirmationStatus, Slot, SlotConfirmationStatus)
from ask_sdk_model.slu.entityresolution.resolution import Resolution
from ask_sdk_model.slu.entityresolution import StatusCode

from alexa import data, util

sb = CustomSkillBuilder(persistence_adapter=s3_adapter)

# Set the skill id so not just anyone can invoke this function
sb.skill_id = "amzn1.ask.skill.92878a4c-6715-4eed-9b71-7805480315a0"

gravIntent = Intent()
calIntent = Intent(name="CalibrateIntent")

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class LaunchRequestHandler(AbstractRequestHandler):
    """Determine if this is a Launch Request."""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        # Indicate can handle Launch requests
        logger.info("In LaunchRequestHandler.can_handle request is {} ".format(handler_input.request_envelope.request))
        return is_request_type("LaunchRequest")(handler_input)

    def handle(self, handler_input):
        """Handler for Skill Launch."""
        # type: (HandlerInput) -> Response
        logger.info("In LaunchRequestHandler.")
        
        handler_input.response_builder.speak(data.WELCOME_MESSAGE).ask(data.REPROMPT_SPEECH).set_card(
            SimpleCard(data.SKILL_TITLE, data.CARD_WELCOME))
        
        logger.info("Leaving LaunchRequestHandler.")
        return handler_input.response_builder.response
        
class SessionEndedRequestHandler(AbstractRequestHandler):
    """Handler for skill session end."""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return is_request_type("SessionEndedRequest")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        logger.info("In SessionEndedRequestHandler")
        print("Session ended with reason: {}".format(
            handler_input.request_envelope))
        return handler_input.response_builder.response


class HelpIntentHandler(AbstractRequestHandler):
    """Handler for help intent."""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return is_intent_name("AMAZON.HelpIntent")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        logger.info("In HelpIntentHandler")
        
        # Create a GravityIntent object so we can get back to the GravityIntentHandler
        gravIntent = Intent(name = "GravityIntent")
        
        # extract our saved values from the S3 repository
        savedAttrs = handler_input.attributes_manager.persistent_attributes
        logger.info("In HelpIntentHandler: savedAttrs is {}. ".format(savedAttrs))
        
        # Get any slot values from the user
        slots = handler_input.request_envelope.request.intent.slots
        logger.info("In HelpIntentHandler: slots={}".format(slots))
        
        handler_input.response_builder.speak(
            data.HELP_MESSAGE).ask(data.HELP_MESSAGE).set_card(
            SimpleCard(data.SKILL_TITLE, data.CARD_HELP))
            
        handler_input.response_builder.add_directive(DelegateDirective(updated_intent = gravIntent))
            
        return handler_input.response_builder.response


class ExitIntentHandler(AbstractRequestHandler):
    """Single Handler for Cancel, Stop and Pause intents."""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return (is_intent_name("AMAZON.CancelIntent")(handler_input) or
                is_intent_name("AMAZON.StopIntent")(handler_input) or
                is_intent_name("AMAZON.PauseIntent")(handler_input))

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        logger.info("In ExitIntentHandler")
        handler_input.response_builder.speak(
            data.EXIT_SKILL_MESSAGE).set_should_end_session(True)
        return handler_input.response_builder.response

class GravityIntentHandler(AbstractRequestHandler):
    """Determine if this is a Gravity Intent request"""
    def can_handle(self, handler_input):
        logger.info("In GravityIntentHandler.can_handle request is {} ".format(handler_input.request_envelope.request))
        return is_intent_name("GravityIntent")(handler_input)
    
    def handle(self, handler_input):
        """Handler for Processing the gravity correction"""
        # Create an Intent object for GravityIntent
        gravIntent = handler_input.request_envelope.request.intent
        logger.info("In GravityIntentHandler: gravIntent is {}. ".format(gravIntent))
        
        # Obtain the request object
        request = handler_input.request_envelope.request
        
        # Get any slot values from the user
        slots = handler_input.request_envelope.request.intent.slots
        logger.info("In GravityIntentHandler: slots={}".format(slots))
        
        # extract slot values
        gravity = slots["gravity"].value
        temp = slots["temperature"].value
        calTemp = slots["calibration"].value
        logger.info("In GravityIntentHandler: gravity is {} and temp {}".format(gravity, temp))
        
        # extract any saved values from the S3 repository
        savedAttrs = handler_input.attributes_manager.persistent_attributes
        try:
            defaultAsked = savedAttrs["defaultAsked"]
        except:
            defaultAsked = False
            
        # In an effort to vary the user experience, keep track of the number of times we have asked for gravity
        # so that we can escalate our responses
        try:
            gravityAsked = savedAttrs["gravityAsked"]
        except:
            gravityAsked = 0
            
        # In an effort to vary the user experience, keep track of the number of times we have asked for temperature
        # so that we can escalate our responses
        try:
            tempAsked = savedAttrs["tempAsked"]
        except:
            tempAsked = 0
            
        # In an effort to vary the user experience, keep track of the number of times we have asked for calibration
        # so that we can escalate our responses
        try:
            caliAsked = savedAttrs["caliAsked"]
        except:
            caliAsked = 0
            
        logger.info("In GravityIntentHandler: gravityAsked is {}, tempAsked {}, and caliAsked {}".format(
            gravityAsked, tempAsked, caliAsked))
        
        # See if we have a default calibration temperature
        try:
            savedCalibration = savedAttrs["calibration"]
            calDefault = True
        except:
            calDefault = False
        
        try:
            gravityFloat = float(gravity)
        except:
            gravityAsked += 1
            speech = data.GRAVITY_MESSAGES[gravityAsked].format(gravity)
            reprompt = "What was the gravity measure again? "
            
            if gravityAsked >= 3:
                gravityAsked = 0
            savedAttrs['gravityAsked'] = gravityAsked
            handler_input.attributes_manager.persistent_attributes = savedAttrs
            handler_input.attributes_manager.save_persistent_attributes()
            
            handler_input.response_builder.speak(speech).ask(reprompt)
            handler_input.response_builder.add_directive(ElicitSlotDirective(slot_to_elicit = "gravity", updated_intent = gravIntent))
            handler_input.response_builder.set_should_end_session(False)
            return handler_input.response_builder.response
            
        try:
            tempFloat = float(temp)
        except:
            tempAsked += 1
            if tempAsked < 3:
                speech = data.TEMPERATURE_MESSAGES[tempAsked].format(util.saySpecificGravity(gravity))
            else:
                speech = data.TEMPERATURE_MESSAGES[tempAsked].format(temp)
            reprompt = "at what temperature was your gravity measurement taken?"
            
            if tempAsked >= 3:
                tempAsked = 0
            savedAttrs['tempAsked'] = tempAsked
            handler_input.attributes_manager.persistent_attributes = savedAttrs
            handler_input.attributes_manager.save_persistent_attributes()

            handler_input.response_builder.speak(speech).ask(reprompt).set_should_end_session(False)
            handler_input.response_builder.add_directive(ElicitSlotDirective(slot_to_elicit = "temperature", updated_intent = gravIntent))
            return handler_input.response_builder.response
        
        # Try to use a specified calibration temperature.
        # if there is none, try to use a saved calibration temperature.
        # if that fails, ask the user for a calibration temperature
        logger.info("in GravityIntentHandler: calTemp is {} and calDefault is {} ".format(calTemp, calDefault))

        # If we have not yet asked about the calibration temperature, delegate control to the Calibrate Intent
        if not defaultAsked and calDefault:
            # Save the responses we have to the S3 repository, so the Calibration Intent can return them back to us
            savedAttrs['gravity'] = gravity
            savedAttrs['temperature'] = temp
            savedAttrs['defaultAsked'] = False
            handler_input.attributes_manager.persistent_attributes = savedAttrs
            handler_input.attributes_manager.save_persistent_attributes()
            
            # build an Intent object for CalibrateIntent
            calIntent = Intent(name = "CalibrateIntent")
            calSlots = {}
            calSlot = Slot(name = "caliDefault", value = savedCalibration)
            calSlots[calSlot.name] = {
                        'confirmation_status': calSlot.confirmation_status,
                        'name': calSlot.name,
                        'resolutions': calSlot.resolutions,
                        'value': calSlot.value}
            calIntent.slots = calSlots
            
            # Delegate CalibrateIntent
            logger.info("in GravityIntentHandler: about to delegate CalibrateIntent. Intent is {} ".format(calIntent))
            handler_input.response_builder.add_directive(DelegateDirective(updated_intent = calIntent))
            return handler_input.response_builder.response
        # end of "if not defaultAsked:"
        
        try:
            calTempFloat = float(calTemp)
        except:
            caliAsked += 1
            speech = data.CALIBRATE_MESSAGES[caliAsked].format(
                util.saySpecificGravity(gravity), temp)
            reprompt = "You can say something like, '60'"
            
            if caliAsked >= 3:
                caliAsked = 0
            savedAttrs['caliAsked'] = caliAsked
            handler_input.attributes_manager.persistent_attributes = savedAttrs
            handler_input.attributes_manager.save_persistent_attributes()
            
#            cardText = "Okay, I have a measured gravity of {} at {} degrees. What is your hydrometer's calibration temperature. ".format(
#                gravityFloat, temp)
#            handler_input.response_builder.speak(speech).ask(reprompt).set_should_end_session(False).set_card(
#                SimpleCard(data.SKILL_TITLE, cardText))
            handler_input.response_builder.speak(speech).ask(reprompt).set_should_end_session(False)
            
            handler_input.response_builder.add_directive(ElicitSlotDirective(slot_to_elicit = "calibration", updated_intent = gravIntent))
            return handler_input.response_builder.response
        
        if util.validateSG(gravityFloat) == 0:
            speech = data.GRAVITY_MESSAGES[3].format(gravity)
            reprompt = "Please enter a valid specific gravity. "
#            cardText = "Please enter a valid gravity. "
#            handler_input.response_builder.speak(speech).ask(reprompt).set_should_end_session(False).set_card(
#                SimpleCard(data.SKILL_TITLE, cardText))
            handler_input.response_builder.speak(speech).ask(reprompt).set_should_end_session(False)
            handler_input.response_builder.add_directive(ElicitSlotDirective(slot_to_elicit = "gravity", updated_intent = gravIntent))
            return handler_input.response_builder.response
            
        tempFloat = util.validateTemp(tempFloat)
        calTempFloat = util.validateTemp(calTempFloat)
        
        if tempFloat == 0:
            speech = data.TEMPERATURE_MESSAGES[3].format(temp)
            reprompt = "Please enter a valid temperature. "
#            cardText = "Please enter a valid temperature. "
#            handler_input.response_builder.speak(speech).ask(reprompt).set_should_end_session(False).set_card(
#                SimpleCard(data.SKILL_TITLE, cardText))
            handler_input.response_builder.speak(speech).ask(reprompt).set_should_end_session(False)
            handler_input.response_builder.add_directive(ElicitSlotDirective(slot_to_elicit = "temperature", updated_intent = gravIntent))
            return handler_input.response_builder.response
            
        if calTempFloat == 0:
            speech = data.CALIBRATE_MESSAGES[3].format(calTemp)
            reprompt = "Please enter a valid calibration temperature. "
#            cardText = "Please enter a valid calibration temperature. "
#            handler_input.response_builder.speak(speech).ask(reprompt).set_should_end_session(False).set_card(
#                SimpleCard(data.SKILL_TITLE, cardText))
            handler_input.response_builder.speak(speech).ask(reprompt).set_should_end_session(False)
            handler_input.response_builder.add_directive(ElicitSlotDirective(slot_to_elicit = "calibration", updated_intent = gravIntent))
            return handler_input.response_builder.response
        
        # We have all the validated values, save them in the S3 repository
        savedAttrs['gravity'] = gravity
        savedAttrs['temperature'] = temp
        savedAttrs['calibration'] = calTemp
        savedAttrs['defaultAsked'] = False
        savedAttrs['gravityAsked'] = 0
        savedAttrs['tempAsked'] = 0
        savedAttrs['caliAsked'] = 0
        handler_input.attributes_manager.persistent_attributes = savedAttrs
        handler_input.attributes_manager.save_persistent_attributes()
        logger.info("In GravityIntentHandler: Saved response in S3 repository")
        
        # Calculate the corrected gravity
        numeratorValue = 1.00130346 - (0.000134722124 * tempFloat) + (0.00000204052596 * tempFloat**2) - (0.00000000232820948 * tempFloat**3)
        denominatorValue = 1.00130346 - (0.000134722124 * calTempFloat) + (0.00000204052596 * calTempFloat**2) - (0.00000000232820948 * calTempFloat**3)
        
        corrGravity = gravityFloat * (numeratorValue / denominatorValue)
        
        logger.info("In GravityIntentHandler: corrected gravity is {}. ".format(corrGravity))
        
        speech = "your corrected gravity is {}. ".format(util.saySpecificGravity(round(corrGravity)))
        speech += data.EXIT_SKILL_MESSAGE
        cardText = "your corrected gravity is {}. ".format((round(corrGravity)*0.001))
        
        handler_input.response_builder.speak(speech).set_should_end_session(True).set_card(
            SimpleCard(data.SKILL_TITLE, cardText))
        
        return handler_input.response_builder.response
        
class CalibrateIntentHandler(AbstractRequestHandler):
    """Determine if this is a Calibration value Intent request"""
    def can_handle(self, handler_input):
        # attr = handler_input.request_envelope.request.intent.slots
        logger.info("In CalibrateIntentHandler.can_handle request is {} ".format(handler_input.request_envelope.request))
        return is_intent_name("CalibrateIntent")(handler_input)

    def handle(self, handler_input):
        """Handler for Processing a saved calibration value"""
        # save our current Intent so we can get back here if we have to
        calIntent = handler_input.request_envelope.request.intent
        logger.info("In CalibrateIntentHandler: calIntent is {}. ".format(calIntent))
        
        # Create a GravityIntent object so we can get back to the GravityIntentHandler
        gravIntent = Intent(name = "GravityIntent")
        
        # extract our saved values from the S3 repository
        savedAttrs = handler_input.attributes_manager.persistent_attributes
        logger.info("In CalibrateIntentHandler: savedAttrs is {}. ".format(savedAttrs))
        try:
            defaultAsked = savedAttrs['defaultAsked']
        except:
            # Something is wrong here, just assume we did not ask if the user wants the default
            defaultAsked = False
        
        # Get any slot values from the user
        slots = handler_input.request_envelope.request.intent.slots
        logger.info("In CalibrateIntentHandler: slots={}".format(slots))
        
        # if we have a slot, get its value
        if slots:
            calTemp = slots["caliDefault"].value
        else:
            calTemp = None
        
        # if we already asked the user, then the reply is in the caliDefault slot
        # it could be a number, or something else
        if defaultAsked:
            # See if it is a number
            try:
                calTempFloat = float(calTemp)
                # Yes, we have a number. Return it to GravityIntent as the new calibration temperature
                savedAttrs['calibration'] = calTemp             # return the new calibration in GravityIntent's slot
                gravSlots = {}
                for name, value in savedAttrs.items():
                    gravSlot = Slot(name = name, value = value)
                    if name == "gravity" or name == "temperature" or name == "calibration":
                        gravSlots[gravSlot.name] = {
                            'confirmation_status': gravSlot.confirmation_status,
                            'name': gravSlot.name,
                            'resolutions': gravSlot.resolutions,
                            'value': gravSlot.value}
                gravIntent.slots = gravSlots
                logger.info("In CalibrateIntentHandler: Returning new calibration to {}. ". format(gravIntent))
                handler_input.response_builder.add_directive(DelegateDirective(updated_intent = gravIntent))
                return handler_input.response_builder.response
            except:
                # This intent's slot was not a number. If it is some form of agreement, pass the save calibration back to GravityIntent
                calResolutions = slots["caliDefault"].resolutions
                userResponse = calResolutions.resolutions_per_authority[0].status.code
                # Did the user say something we recognize as an affirmative?
                if userResponse == StatusCode.ER_SUCCESS_MATCH:
                    gravSlots = {}
                    for name, value in savedAttrs.items():
                        gravSlot = Slot(name = name, value = value)
                        if name == "gravity" or name == "temperature" or name == "calibration":
                            gravSlots[gravSlot.name] = {
                                'confirmation_status': gravSlot.confirmation_status,
                                'name': gravSlot.name,
                                'resolutions': gravSlot.resolutions,
                                'value': gravSlot.value}
                    gravIntent.slots = gravSlots
                    logger.info("In CalibrateIntentHandler: Using default calibration to {}. ". format(gravIntent))
                    handler_input.response_builder.add_directive(DelegateDirective(updated_intent = gravIntent))
                    return handler_input.response_builder.response
                else:
                    # Otherwise, try to get something we understand
                    speech = "Sorry, you said {}. Please reply with a new calibration temperature or reply 'yes' to use the default.".format(calTemp)
                    reprompt = "Please say 'yes' or reply with a new calibration temperature."
                    handler_input.response_builder.speak(speech).ask(reprompt).set_should_end_session(False).set_card(
                        SimpleCard(data.SKILL_TITLE, reprompt))
                    handler_input.response_builder.add_directive(ElicitSlotDirective(slot_to_elicit = "caliDefault", updated_intent = calIntent))
                    return handler_input.response_builder.response
        
        # At this point, we haven't ask the user anything
        # Set the "asked" flag
        savedAttrs['defaultAsked'] = True
        handler_input.attributes_manager.persistent_attributes = savedAttrs
        handler_input.attributes_manager.save_persistent_attributes()
        
        # Ask the user to confirm the default or provide a new calibration temperature
        speech = "You have a default calibration temperature of {}. Do you want to use the default? ".format(calTemp)
        reprompt = "Please say 'yes' or reply with a new calibration temperature."
        handler_input.response_builder.speak(speech).ask(reprompt).set_should_end_session(False).set_card(
        SimpleCard(data.SKILL_TITLE, reprompt))
        handler_input.response_builder.add_directive(ElicitSlotDirective(slot_to_elicit = "caliDefault", updated_intent = calIntent))
        return handler_input.response_builder.response
        
class RepeatHandler(AbstractRequestHandler):
    """Handler for repeating the response to the user."""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return is_intent_name("AMAZON.RepeatIntent")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        logger.info("In RepeatHandler")
        attr = handler_input.attributes_manager.session_attributes
        response_builder = handler_input.response_builder
        if "recent_response" in attr:
            cached_response_str = json.dumps(attr["recent_response"])
            cached_response = DefaultSerializer().deserialize(
                cached_response_str, Response)
            return cached_response
        else:
            response_builder.speak(data.FALLBACK_ANSWER).ask(data.HELP_MESSAGE)

            return response_builder.response


class CatchAllExceptionHandler(AbstractExceptionHandler):
    """Generic error handling to capture any syntax or routing errors. If you receive an error
    stating the request handler chain is not found, you have not implemented a handler for
    the intent being invoked or included it in the skill builder below.
    """
    def can_handle(self, handler_input, exception):
        # type: (HandlerInput, Exception) -> bool
        return True

    def handle(self, handler_input, exception):
        # type: (HandlerInput, Exception) -> Response
        logger.info("In CatchAllExceptionHandler")
        logger.error(exception, exc_info=True)
        
        speech = "Sorry, there was some problem. Please try again!!"
        handler_input.response_builder.speak(speech).ask(speech)
        
        return handler_input.response_builder.response


# The SkillBuilder object acts as the entry point for your skill, routing all request and response
# payloads to the handlers above. Make sure any new handlers or interceptors you've
# defined are included below. The order matters - they're processed top to bottom.

    
sb.add_request_handler(LaunchRequestHandler())
sb.add_request_handler(GravityIntentHandler())
sb.add_request_handler(CalibrateIntentHandler())
sb.add_request_handler(RepeatHandler())
sb.add_request_handler(HelpIntentHandler())
sb.add_request_handler(ExitIntentHandler())
sb.add_request_handler(SessionEndedRequestHandler())

sb.add_exception_handler(CatchAllExceptionHandler())

# sb.add_global_request_interceptor(RequestLogger())
# sb.add_global_request_interceptor(ResponseLogger())


lambda_handler = sb.lambda_handler()
