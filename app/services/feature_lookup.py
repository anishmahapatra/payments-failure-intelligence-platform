from typing import Any

from app.api.schemas.payment import PaymentScoreRequest
from app.core.config import get_settings
from app.core.exceptions import FeatureLookupError


class FeatureLookupService:
    """v1 feature provider.

    Uses request-supplied operational fields directly and leaves a Feast hook in place for
    local feature repo evolution without making local startup depend on an online store.
    """

    def __init__(self):
        self.settings = get_settings()

    def build_feature_vector(self, request: PaymentScoreRequest) -> dict[str, Any]:
        try:
            features = request.model_dump()
        except Exception as exc:
            raise FeatureLookupError("Unable to build feature vector from request payload") from exc
        features["peak_hour_flag"] = 1 if request.hour_of_day in {11, 12, 13, 18, 19, 20} else 0
        features["payment_amount_bucket"] = self._bucket_amount(request.amount)
        return features

    @staticmethod
    def _bucket_amount(amount: float) -> str:
        if amount < 20:
            return "small"
        if amount < 75:
            return "medium"
        if amount < 200:
            return "large"
        return "enterprise"
