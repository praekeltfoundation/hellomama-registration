import datetime
import json
import requests

from celery.task import Task
from celery.utils.log import get_task_logger
from django.conf import settings

from .models import Registration, SubscriptionRequest


logger = get_task_logger(__name__)


LANG_CODES = {
    "english": "eng_NG",
    "hausa": "hau_NG",
    "igbo": "ibo_NG",
    "yoruba": "yor_NG",
    "pidgin": "pcm_NG"
}


def get_today():
    return datetime.datetime.today()


def is_valid_date(date):
    try:
        datetime.datetime.strptime(date, "%Y%m%d")
        return True
    except:
        return False


def is_valid_uuid(id):
    return len(id) == 36 and id[14] == '4' and id[19] in ['a', 'b', '8', '9']


def is_valid_lang(lang):
    return lang in ["english", "hausa", "igbo", "pidgin", "yoruba"]


def is_valid_msg_type(msg_type):
    return msg_type in ["sms", "voice"]


def is_valid_msg_receiver(msg_receiver):
    return msg_receiver in ["mother_father", "mother_only", "father_only",
                            "mother_family", "mother_friend", "friend_only",
                            "family_only"]


def is_valid_loss_reason(loss_reason):
    return loss_reason in ['miscarriage', 'stillborn', 'baby_died']


def calc_pregnancy_week_lmp(today, lmp):
    """ Calculate how far along the mother's prenancy is in weeks.
    """
    last_period_date = datetime.datetime.strptime(lmp, "%Y%m%d")
    time_diff = today - last_period_date
    preg_weeks = int(time_diff.days / 7)
    # You can't be one week pregnant (smaller numbers will be rejected)
    if preg_weeks == 1:
        preg_weeks = 2
    return preg_weeks


def calc_baby_age(today, baby_dob):
    """ Calculate the baby's age in weeks.
    """
    baby_dob_date = datetime.datetime.strptime(baby_dob, "%Y%m%d")
    time_diff = today - baby_dob_date
    if time_diff.days >= 0:
        age_weeks = int(time_diff.days / 7)
        return age_weeks
    else:
        # Return -1 if the date is in the future
        return -1


def get_messageset_shortname(stage, recipient, msg_type, weeks):

    subscription_type_map = {
        "sms": "text",
        "voice": "audio"
    }
    if recipient == "household":
        subscription_msg_type = "text"
    else:
        subscription_msg_type = subscription_type_map[msg_type]

    if stage == "prebirth":
        week_range = "10_42"
    elif stage == "postbirth":
        if 0 <= weeks <= 12:
            week_range = "0_12"
        elif 13 <= weeks <= 52:
            week_range = "13_52"
    elif stage == "loss":
        week_range = "0_2"

    shortname = "%s_%s_%s_%s" % (
        stage, recipient, subscription_msg_type, week_range)

    return shortname


def get_messageset_id(shortname):
    url = settings.MESSAGESET_URL
    params = {'shortname': shortname}
    headers = {'Authorization': ['Token %s' % settings.MESSAGESET_TOKEN],
               'Content-Type': ['application/json']}
    r = requests.get(url, params=params, headers=headers)

    return r.json()["id"]


class ValidateRegistration(Task):
    """ Task to validate a registration model entry's registration
    data.
    """
    name = "hellomama_registration.registrations.tasks.validate_registration"

    def check_field_values(self, fields, registration_data):
        failures = []
        for field in fields:
            if field in ["receiver_id", "operator_id"]:
                if not is_valid_uuid(registration_data[field]):
                    failures.append(field)
            if field == "language":
                if not is_valid_lang(registration_data[field]):
                    failures.append(field)
            if field == "msg_type":
                if not is_valid_msg_type(registration_data[field]):
                    failures.append(field)
            if field in ["last_period_date", "baby_dob"]:
                if not is_valid_date(registration_data[field]):
                    failures.append(field)
                elif field == "last_period_date":
                    # Check last_period_date is in valid week range
                    preg_weeks = calc_pregnancy_week_lmp(
                        get_today(), registration_data[field])
                    if not (settings.PREBIRTH_MIN_WEEKS <= preg_weeks <=
                            settings.PREBIRTH_MAX_WEEKS):
                        print(preg_weeks)
                        failures.append("last_period_date out of range")
                elif field == "baby_dob":
                    # Check baby_dob is in valid week range
                    preg_weeks = calc_baby_age(
                        get_today(), registration_data[field])
                    if not (settings.POSTBIRTH_MIN_WEEKS <= preg_weeks <=
                            settings.POSTBIRTH_MAX_WEEKS):
                        failures.append("baby_dob out of range")
            if field == "msg_receiver":
                if not is_valid_msg_receiver(registration_data[field]):
                    failures.append(field)
            if field == "loss_reason":
                if not is_valid_loss_reason(registration_data[field]):
                    failures.append(field)
        return failures

    def validate(self, registration):
        """ Validates that all the required info is provided for a
        registration.
        """
        data_fields = registration.data.keys()
        fields_general = ["receiver_id", "operator_id",
                          "language", "msg_type"]
        fields_prebirth = ["last_period_date", "msg_receiver"]
        fields_postbirth = ["baby_dob", "msg_receiver"]
        fields_loss = ["loss_reason"]

        hw_pre = list(set(fields_general) | set(fields_prebirth))
        hw_post = list(set(fields_general) | set(fields_postbirth))
        pbl_loss = list(set(fields_general) | set(fields_loss))

        # Check if mother_id is a valid UUID
        if not is_valid_uuid(registration.mother_id):
            registration.data["invalid_fields"] = "Invalid UUID mother_id"
            registration.save()
            return False

        if "msg_receiver" in registration.data.keys():
            # Reject registrations on behalf of mother that does not have a
            # unique id for the mother
            if (registration.data["msg_receiver"] in [
                "father_only", "friend_only", "family_only"] and
               registration.mother_id == registration.data["receiver_id"]):
                registration.data["invalid_fields"] = "mother requires own id"
                registration.save()
                return False
            # Reject registrations where the mother is the receiver but the
            # mother_id and receiver_id differs
            elif (registration.data["msg_receiver"] == "mother_only" and
                  registration.mother_id != registration.data["receiver_id"]):
                registration.data["invalid_fields"] = "mother_id should be " \
                    "the same as receiver_id"
                registration.save()
                return False

        # HW registration, prebirth
        if (registration.stage == "prebirth" and
                registration.source.authority in ["hw_limited", "hw_full"] and
                set(hw_pre).issubset(data_fields)):  # ignore extra data

            invalid_fields = self.check_field_values(
                hw_pre, registration.data)
            if invalid_fields == []:
                registration.data["reg_type"] = "hw_pre"
                registration.data["preg_week"] = calc_pregnancy_week_lmp(
                    get_today(), registration.data["last_period_date"])
                print(registration.data["preg_week"])
                registration.validated = True
                registration.save()
                return True
            else:
                registration.data["invalid_fields"] = invalid_fields
                registration.save()
                return False
        # HW registration, postbirth
        elif (registration.stage == "postbirth" and
              registration.source.authority in ["hw_limited", "hw_full"] and
              set(hw_post).issubset(data_fields)):
            invalid_fields = self.check_field_values(
                hw_post, registration.data)
            if invalid_fields == []:
                registration.data["reg_type"] = "hw_post"
                registration.data["baby_age"] = calc_baby_age(
                    get_today(), registration.data["baby_dob"])
                registration.validated = True
                registration.save()
                return True
            else:
                registration.data["invalid_fields"] = invalid_fields
                registration.save()
                return False
        # Loss registration
        elif (registration.stage == "loss" and
              registration.source.authority in ["patient", "advisor"] and
              set(pbl_loss).issubset(data_fields)):
            invalid_fields = self.check_field_values(
                pbl_loss, registration.data)
            if invalid_fields == []:
                registration.data["reg_type"] = "pbl_loss"
                registration.validated = True
                registration.save()
                return True
            else:
                registration.data["invalid_fields"] = invalid_fields
                registration.save()
                return False
        else:
            registration.data[
                "invalid_fields"] = "Invalid combination of fields"
            registration.save()
            return False

    def create_subscriptionrequests(self, registration):
        """ Create SubscriptionRequest(s) based on the
        validated registration.
        """

        mother_shortname = get_messageset_shortname(
            registration.stage, 'mother', registration.data["msg_type"],
            registration.data["preg_week"]
        )
        mother_sub = {
            "contact": registration.mother_id,
            "messageset_id": get_messageset_id(mother_shortname),
            "next_sequence_number": 1,  # TODO
            "lang": LANG_CODES[registration.data["language"]],
            "schedule": 1,  # TODO
        }
        SubscriptionRequest.objects.create(**mother_sub)

        if registration.data["msg_receiver"] != 'mother_only':
            household_shortname = get_messageset_shortname(
                registration.stage,
                'household',
                registration.data["msg_type"],
                registration.data["preg_week"],
            )
            household_sub = {
                "contact": registration.data["receiver_id"],
                "messageset_id": get_messageset_id(household_shortname),
                "next_sequence_number": 1,  # TODO
                "lang": LANG_CODES[registration.data["language"]],
                "schedule": 1,  # TODO
            }
            SubscriptionRequest.objects.create(**household_sub)
            return "2 SubscriptionRequests created"

        return "1 SubscriptionRequest created"

    def run(self, registration_id, **kwargs):
        """ Sets the registration's validated field to True if
        validation is successful.
        """
        l = self.get_logger(**kwargs)
        l.info("Looking up the registration")
        registration = Registration.objects.get(id=registration_id)
        reg_validates = self.validate(registration)

        validation_string = "Validation completed - "
        if reg_validates:
            self.create_subscriptionrequests(registration)
            validation_string += "Success"
        else:
            validation_string += "Failure"

        return validation_string

validate_registration = ValidateRegistration()


class DeliverHook(Task):
    def run(self, target, payload, instance=None, hook=None, **kwargs):
        """
        target:     the url to receive the payload.
        payload:    a python primitive data structure
        instance:   a possibly null "trigger" instance
        hook:       the defining Hook object
        """
        requests.post(
            url=target,
            data=json.dumps(payload),
            headers={
                'Content-Type': 'application/json',
                'Authorization': 'Token %s' % settings.HOOK_AUTH_TOKEN
            }
        )

deliver_hook_wrapper = DeliverHook.delay
