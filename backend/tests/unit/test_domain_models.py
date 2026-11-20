from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from subwise.api.schemas.subscriptions import SubscriptionIn
from subwise.core.costing import EQUAL_COST_MESSAGE
from subwise.domain.catalog import Entitlement, Plan, Prerequisite
from subwise.domain.enums import BillingCycle, BindingMethod, Category, ExtractedBy
from subwise.domain.evidence import DimensionBinding, PlanObservation, PriceBinding
from subwise.domain.optimization import OptimizerInput
from subwise.domain.request import RequestSpec


def _plan(**kw: object) -> Plan:
    base: dict[str, object] = {
        "id": "netflix_basic", "provider_id": "netflix", "service_line_id": "netflix_streaming",
        "name": "Basic", "billing_cycle": BillingCycle.MONTHLY,
        "entitlements": [Entitlement(service_line_id="netflix_streaming", tier="basic")],
    }  # fmt: skip
    base.update(kw)
    return Plan.model_validate(base)


def _bound(method: BindingMethod = BindingMethod.SAME_DOM_BLOCK) -> DimensionBinding:
    return DimensionBinding(method=method, matched_text="x")


def test_ta1_equal_cost_sentence_preserved_verbatim() -> None:
    assert EQUAL_COST_MESSAGE == "There is no difference between the plans."


def test_exclusion_group_defaults_to_service_line_not_provider() -> None:
    assert _plan().effective_exclusion_group == "netflix_streaming"
    assert _plan(exclusion_group="custom").effective_exclusion_group == "custom"


def test_bundle_detection_counts_distinct_service_lines() -> None:
    prime = _plan(
        id="prime_monthly", provider_id="amazon", service_line_id="prime_membership",
        entitlements=[
            Entitlement(service_line_id="prime_membership"),
            Entitlement(service_line_id="prime_video"),
            Entitlement(service_line_id="prime_music"),
        ],
    )  # fmt: skip
    assert prime.is_bundle and not _plan().is_bundle


def test_prerequisite_must_name_something() -> None:
    with pytest.raises(ValidationError):
        Prerequisite()


def test_price_binding_requires_all_five_dimensions() -> None:
    full = PriceBinding(
        provider=_bound(BindingMethod.DOMAIN_MAP), plan=_bound(), billing_cycle=_bound(),
        currency=_bound(BindingMethod.ADJACENT_TOKEN), region=_bound(BindingMethod.URL_LOCALE),
    )  # fmt: skip
    assert full.fully_bound
    partial = full.model_copy(update={"region": DimensionBinding(method=BindingMethod.UNBOUND)})
    assert not partial.fully_bound


def test_observation_rejects_negative_and_absurd_prices() -> None:
    binding = PriceBinding(
        provider=_bound(), plan=_bound(), billing_cycle=_bound(), currency=_bound(),
        region=_bound(),
    )  # fmt: skip
    common = {
        "plan_id": "p", "source_document_id": "doc_1", "billing_cycle": 1,
        "evidence_snippet": "₹199/month", "binding": binding, "extracted_by": ExtractedBy.ADAPTER,
        "observed_at": datetime.now(UTC),
    }  # fmt: skip
    assert PlanObservation(price_paise=19_900, **common).price_paise == 19_900  # type: ignore[arg-type]
    for bad in (-1, 5_000_001):
        with pytest.raises(ValidationError):
            PlanObservation(price_paise=bad, **common)  # type: ignore[arg-type]


def test_billing_cycle_must_be_supported() -> None:
    with pytest.raises(ValidationError):
        SubscriptionIn(custom_name="X", price_paise=100, billing_cycle=2)  # type: ignore[arg-type]


def test_subscription_needs_exactly_one_of_plan_or_custom() -> None:
    with pytest.raises(ValidationError):
        SubscriptionIn(price_paise=100, billing_cycle=BillingCycle.MONTHLY)
    with pytest.raises(ValidationError):
        SubscriptionIn(plan_id="p", custom_name="X", price_paise=100, billing_cycle=1)  # type: ignore[arg-type]


def test_optimizer_weights_must_be_in_unit_interval() -> None:
    with pytest.raises(ValidationError):
        OptimizerInput(candidates=[], budget_paise=100_000, weights={"uhd_4k": 1.5})


def test_request_spec_needs_a_category() -> None:
    with pytest.raises(ValidationError):
        RequestSpec(categories=[])
    assert RequestSpec(categories=[Category.VIDEO]).mode.value == "best"
