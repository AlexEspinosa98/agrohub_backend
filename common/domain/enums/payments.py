import enum


class DeviceOS(enum.Enum):
    """
    Represents the possible device operating systems.
    """

    IPHONE = "iPhone"
    ANDROID = "Android"


class PaymentStatus(enum.Enum):
    """
    Enum representing the payment status.
    """

    canceled = "canceled"
    processing = "processing"
    requires_action = "requires_action"
    requires_capture = "requires_capture"
    requires_confirmation = "requires_confirmation"
    requires_payment_method = "requires_payment_method"
    succeeded = "succeeded"


class SubscriptionStatus(enum.Enum):
    """
    Enum representing status in subscriptions
    """

    active = "active"
    canceled = "canceled"
    incomplete = "incomplete"
    incomplete_expired = "incomplete_expired"
    past_due = "past_due"
    paused = "paused"
    trialing = "trialing"
    unpaid = "unpaid"


class PaymentCurrencies(enum.Enum):
    """
    Enum representing the payment currencies.
    """

    USD = enum.auto()
    EUR = enum.auto()
    COP = enum.auto()


class DiscountType(enum.Enum):
    """
    Enum representing the type of discount for promo codes.
    """

    PERCENTAGE = "percentage"
    FIXED_AMOUNT = "fixed_amount"
