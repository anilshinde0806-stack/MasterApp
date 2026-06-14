import re


VEHICLE_NUMBER_PATTERN = re.compile(
    r"^([A-Z]{2}[0-9]{2}[A-Z]{1,3}[0-9]{1,4}|(22|23|24|25|26)[A-Z]{2}[0-9]{1,4}[A-Z]?)$",
    re.IGNORECASE,
)


def normalize_vehicle_number(reg_no):
    return (reg_no or "").upper().replace(" ", "")


def is_valid_vehicle_number(reg_no):
    return bool(VEHICLE_NUMBER_PATTERN.match(normalize_vehicle_number(reg_no)))


VEHICLE_NUMBER_ERROR = (
    "Enter valid vehicle no. Example: GJ05AB1234 or 22BH1234A."
)
