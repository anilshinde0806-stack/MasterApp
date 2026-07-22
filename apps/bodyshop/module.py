"""MOS registration for the Body Shop business module."""

from apps.bodyshop.application.commands.create_claim import CreateClaimHandler
from apps.bodyshop.domain.claims.claim import Claim
from apps.bodyshop.domain.claims.events import ClaimCreated
from apps.bodyshop.domain.claims.repository import ClaimRepository
from apps.bodyshop.infrastructure.persistence.django_claim_repository import (
    DjangoClaimRepository,
)
from apps.core.platform.container import Container
from apps.core.platform.feature_flags import FeatureFlags
from apps.core.runtime.module import Module


class BodyShopModule(Module):
    """Entry point for Body Shop domain capabilities."""

    CLAIMS_V2_FEATURE = "bodyshop.claims.v2"

    def __init__(self) -> None:
        super().__init__(
            name="Body Shop",
            code="BODYSHOP",
            version="0.1.0",
            description="Body Shop claims and repair workflow.",
        )

    def initialize(self) -> None:
        self.register_business_object(Claim)
        self.register_service(CreateClaimHandler)
        self.register_event(ClaimCreated)
        self.register_permission("bodyshop.claim.create")

        Container.register(ClaimRepository, DjangoClaimRepository)
        if self.CLAIMS_V2_FEATURE not in FeatureFlags.all():
            FeatureFlags.disable(self.CLAIMS_V2_FEATURE)

