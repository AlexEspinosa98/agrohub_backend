from datetime import date, datetime, timedelta
from typing import Optional

from common.domain import enums as common_enums
from common.infrastructure.database import models as common_database_models


class SubscriptionModelBuilder:
    """Builder for creating SubscriptionModel instances in tests."""

    def __init__(self) -> None:
        self._id: Optional[int] = None
        self._user_id: int = 1
        self._product_id: int = 1
        self._start_date: date = date.today()
        self._end_date: date = date.today() + timedelta(days=365)
        self._status: common_enums.SubscriptionStatus = (
            common_enums.SubscriptionStatus.incomplete
        )
        self._stripe_subscription_id: Optional[str] = None
        self._stripe_customer_id: Optional[str] = None
        self._is_active: bool = True
        self._created_at: datetime = datetime.now()
        self._updated_at: datetime = datetime.now()
        self._deleted_at: Optional[datetime] = None

    def with_id(self, id: int) -> "SubscriptionModelBuilder":
        """Set subscription ID."""
        self._id = id
        return self

    def with_user_id(self, user_id: int) -> "SubscriptionModelBuilder":
        """Set user ID for the subscription."""
        self._user_id = user_id
        return self

    def with_product_id(self, product_id: int) -> "SubscriptionModelBuilder":
        """Set product ID for the subscription."""
        self._product_id = product_id
        return self

    def with_start_date(self, start_date: date) -> "SubscriptionModelBuilder":
        """Set start date for the subscription."""
        self._start_date = start_date
        return self

    def with_end_date(self, end_date: date) -> "SubscriptionModelBuilder":
        """Set end date for the subscription."""
        self._end_date = end_date
        return self

    def with_status(
        self, status: common_enums.SubscriptionStatus
    ) -> "SubscriptionModelBuilder":
        """Set status for the subscription."""
        self._status = status
        return self

    def with_stripe_subscription_id(
        self, stripe_subscription_id: str
    ) -> "SubscriptionModelBuilder":
        """Set Stripe subscription ID for the subscription."""
        self._stripe_subscription_id = stripe_subscription_id
        return self

    def with_stripe_customer_id(
        self, stripe_customer_id: str
    ) -> "SubscriptionModelBuilder":
        """Set Stripe customer ID for the subscription."""
        self._stripe_customer_id = stripe_customer_id
        return self

    def with_is_active(self, is_active: bool) -> "SubscriptionModelBuilder":
        """Set whether the subscription is active."""
        self._is_active = is_active
        return self

    def with_created_at(self, created_at: datetime) -> "SubscriptionModelBuilder":
        """Set creation timestamp for the subscription."""
        self._created_at = created_at
        return self

    def with_updated_at(self, updated_at: datetime) -> "SubscriptionModelBuilder":
        """Set last updated timestamp for the subscription."""
        self._updated_at = updated_at
        return self

    def with_deleted_at(
        self, deleted_at: Optional[datetime]
    ) -> "SubscriptionModelBuilder":
        """Set deletion timestamp for the subscription."""
        self._deleted_at = deleted_at
        return self

    def build(self) -> common_database_models.SubscriptionModel:
        """Build the SubscriptionModel instance."""
        return common_database_models.SubscriptionModel(
            id=self._id,
            user_id=self._user_id,
            product_id=self._product_id,
            start_date=self._start_date,
            end_date=self._end_date,
            status=self._status,
            stripe_subscription_id=self._stripe_subscription_id,
            stripe_customer_id=self._stripe_customer_id,
            is_active=self._is_active,
            created_at=self._created_at,
            updated_at=self._updated_at,
            deleted_at=self._deleted_at,
        )

    @staticmethod
    def active_subscription(
        user_id: int = 123,
    ) -> common_database_models.SubscriptionModel:
        """Create a standard active subscription."""
        return (
            SubscriptionModelBuilder()
            .with_user_id(user_id)
            .with_status(common_enums.SubscriptionStatus.active)
            .with_start_date(date.today())
            .with_end_date(date.today() + timedelta(days=30))
            .build()
        )

    @staticmethod
    def expired_subscription(
        user_id: int = 123,
    ) -> common_database_models.SubscriptionModel:
        """Create a standard expired subscription."""
        return (
            SubscriptionModelBuilder()
            .with_user_id(user_id)
            .with_status(common_enums.SubscriptionStatus.expired)
            .with_start_date(date.today() - timedelta(days=60))
            .with_end_date(date.today() - timedelta(days=30))
            .build()
        )

    @staticmethod
    def incomplete_subscription(
        user_id: int = 123,
    ) -> common_database_models.SubscriptionModel:
        """Create a standard incomplete subscription."""
        return (
            SubscriptionModelBuilder()
            .with_user_id(user_id)
            .with_status(common_enums.SubscriptionStatus.incomplete)
            .with_start_date(date.today())
            .with_end_date(date.today() + timedelta(days=30))
            .build()
        )
