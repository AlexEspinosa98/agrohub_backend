from enum import Enum


class AccessTypes(Enum):
    FULL_ACCESS = "Full Access"
    LIMITED_ACCESS = "Limited Access"
    OWNER = "Owner"


class InvitationMethods(Enum):
    """
    Enum for the possible invitation methods.
    """

    EMAIL = "Email"
    PHONE = "Phone"


class InvitationStatus(Enum):
    """
    Enum for the possible invitation statuses.
    """

    PENDING = "Pending"
    ACCEPTED = "Accepted"
    DECLINED = "Declined"


class RelationshipGuests(Enum):
    """
    Enum for the possible relationship guest.
    """

    DAD_MOM = "Dad/Mom"
    BROTHER_SISTER = "Brother/Sister"
    UNCLE_AUNT = "Uncle/Aunt"
    COUSIN = "Cousin"
    GRANDPARENT = "Grandparent"
    FRIEND = "Friend"
    ANOTHER_FAMILY_MEMBER = "Another family member"
