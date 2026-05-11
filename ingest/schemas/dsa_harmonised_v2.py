"""Pydantic schemas for the EU's harmonised DSA Transparency Report template.

Per Implementing Regulation 2024/2835 (effective 1 July 2025). Spotify's
2025 reports (published Feb 2026) are the first generation under this template.

All four Spotify product lines (Main, Artists, Authors, Creators) ship the
SAME 9-sheet structure with IDENTICAL column headers — verified empirically
against the four 2025 H2 XLSX files. One schema module covers all four reports.

Each row schema models ONE row from one sheet. The parser validates row-by-row
with pydantic and writes the validated rows out as Parquet.

A small abuse: we keep `populate_by_name` + alias-based field naming so that
the raw Excel header strings (with their irregular trailing spaces, slashes,
and quotes) map cleanly to snake_case Python attributes. This matters because
some Excel headers contain characters like `'` and `/` that aren't legal in
Python identifiers.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

# ---------------------------------------------------------------------------
# Shared types
# ---------------------------------------------------------------------------

NullableStr = Annotated[str | int | float | None, Field(default=None)]
NullableNum = Annotated[float | int | str | None, Field(default=None)]
# Bronze layer preserves source fidelity — Spotify occasionally writes 0 into
# free-text "Contextual information" columns and vice versa. Strict typing
# belongs in dbt staging where we coerce explicitly.


class _Base(BaseModel):
    """Common config: accept Excel-header aliases, allow trailing whitespace, keep extras strict."""

    model_config = ConfigDict(
        populate_by_name=True,
        extra="forbid",
        str_strip_whitespace=False,  # preserve "Number of notices received " trailing space in source
    )

    # Provenance — every row carries where it came from
    source_product: str
    source_period: str
    source_sheet: str
    source_row_index: int  # 1-based, matches the row number you'd see in Excel
    source_sha256: str

    @field_validator("source_product")
    @classmethod
    def _valid_product(cls, v: str) -> str:
        if v not in {"main", "artists", "authors", "creators"}:
            raise ValueError(f"Unknown product: {v!r}")
        return v


def _norm(v: Any) -> Any:
    """Normalise raw Excel cell values:

    - empty strings / 'n/a' / 'na' → None
    - datetimes / dates → ISO 8601 string (preserves date publication fields like
      'Date of the publication of the report' which openpyxl returns as datetime)
    - numerics and real strings pass through
    """
    if v is None:
        return None
    if isinstance(v, datetime):
        return v.date().isoformat() if v.time().isoformat() == "00:00:00" else v.isoformat()
    if isinstance(v, date):
        return v.isoformat()
    if isinstance(v, str):
        s = v.strip()
        if s == "" or s.lower() in {"n/a", "na"}:
            return None
        return v
    return v


# ---------------------------------------------------------------------------
# Sheet 1: report_identification — 4 columns
# ---------------------------------------------------------------------------


class ReportIdentificationRow(_Base):
    applicability: NullableStr = Field(default=None, alias="Applicability")
    service: NullableStr = Field(default=None, alias="Service")
    indicator: NullableStr = Field(default=None, alias="Indicator")
    value: NullableStr = Field(default=None, alias="Value")


# ---------------------------------------------------------------------------
# Sheet 2: categories_names — 4 columns
# ---------------------------------------------------------------------------


class CategoriesNamesRow(_Base):
    category_label: NullableStr = Field(default=None, alias="Category label")
    category_description: NullableStr = Field(default=None, alias="Category description")
    category_of_illegal_or_tc: NullableStr = Field(
        default=None,
        alias="Category of illegal content / incompatible with the terms and conditions",
    )
    contextual_information: NullableStr = Field(
        default=None, alias="Contextual information"
    )


# ---------------------------------------------------------------------------
# Sheet 3: member_states_orders — 20 columns
# ---------------------------------------------------------------------------


class MemberStatesOrdersRow(_Base):
    applicability: NullableStr = Field(default=None, alias="Applicability")
    service: NullableStr = Field(default=None, alias="Service")
    reporting_period: NullableStr = Field(default=None, alias="Reporting period")
    category_of_illegal_content: NullableStr = Field(
        default=None, alias="Category of illegal content"
    )
    description_subcategory_other: NullableStr = Field(
        default=None, alias='Description of the sub-category "Other"'
    )
    scope: NullableStr = Field(default=None, alias="Scope")
    n_orders_to_act: NullableNum = Field(
        default=None, alias="Number of orders to act against illegal content received"
    )
    n_items_in_orders_to_act: NullableNum = Field(
        default=None,
        alias="Number of specific items of information included in the total number of orders to act against illegal content",
    )
    median_time_to_inform_act: NullableNum = Field(
        default=None,
        alias="Median time to inform the authority of the receipt of the order to act against illegal content",
    )
    median_time_to_give_effect_act: NullableNum = Field(
        default=None,
        alias="Median time to give effect to the order to act against illegal content",
    )
    n_orders_to_provide_info: NullableNum = Field(
        default=None, alias="Number of orders to provide information"
    )
    median_time_to_inform_info: NullableNum = Field(
        default=None,
        alias="Median time to inform the authority of the receipt of the order to provide information",
    )
    median_time_to_give_effect_info: NullableNum = Field(
        default=None,
        alias="Median time to give effect to the order to provide information",
    )
    ctx_n_orders_to_act: NullableStr = Field(
        default=None,
        alias="Contextual information on number of orders to act against illegal content received",
    )
    ctx_n_items_in_orders_to_act: NullableStr = Field(
        default=None,
        alias="Contextual information on number of specific items of information included in the total number of orders to act against illegal content",
    )
    ctx_median_time_to_inform_act: NullableStr = Field(
        default=None,
        alias="Contextual information on Median time to inform the authority of the receipt of the order to act against illegal content",
    )
    ctx_median_time_to_give_effect_act: NullableStr = Field(
        default=None,
        alias="Contextual information on Median time to give effect to the order to act against illegal content",
    )
    ctx_n_orders_to_provide_info: NullableStr = Field(
        default=None,
        alias="Contextual information on Number of orders to provide information",
    )
    ctx_median_time_to_inform_info: NullableStr = Field(
        default=None,
        alias="Contextual information on Median time to inform the authority of the receipt of the order to provide information",
    )
    ctx_median_time_to_give_effect_info: NullableStr = Field(
        default=None,
        alias="Contextual information on Median time to give effect to the order to provide information",
    )


# ---------------------------------------------------------------------------
# Sheet 4: notices — 25 columns
# ---------------------------------------------------------------------------


class NoticesRow(_Base):
    applicability: NullableStr = Field(default=None, alias="Applicability")
    service: NullableStr = Field(default=None, alias="Service")
    reporting_period: NullableStr = Field(default=None, alias="Reporting period")
    category_of_illegal_content: NullableStr = Field(
        default=None, alias="Category of illegal content"
    )
    description_subcategory_other: NullableStr = Field(
        default=None, alias='Description of the sub-category "Other"'
    )
    n_notices_received: NullableNum = Field(
        default=None, alias="Number of notices received "
    )
    n_notices_from_trusted_flaggers: NullableNum = Field(
        default=None, alias="Number of notices received from Trusted flaggers"
    )
    n_items_in_notices: NullableNum = Field(
        default=None,
        alias="Number of specific items of information included in the total number of notices",
    )
    n_items_in_tf_notices: NullableNum = Field(
        default=None,
        alias="Number of specific items of information included in the total number of notices by Trusted Flaggers (Trusted Flagger notices)",
    )
    median_time_to_take_action: NullableNum = Field(
        default=None, alias="Median time to take action"
    )
    median_time_to_take_action_tf: NullableNum = Field(
        default=None, alias="Median time to take action (Trusted Flagger notices)"
    )
    n_actions_on_law: NullableNum = Field(
        default=None, alias="Number of actions taken on the basis of the law"
    )
    n_actions_on_law_tf: NullableNum = Field(
        default=None,
        alias="Number of actions taken on the basis of the law (Trusted Flagger notices)",
    )
    n_actions_on_tc: NullableNum = Field(
        default=None,
        alias="Number of actions taken on the basis of the terms and conditions of the service",
    )
    n_actions_on_tc_tf: NullableNum = Field(
        default=None,
        alias="Number of actions taken on the basis of the terms and conditions of the service (Trusted Flagger notices)",
    )
    ctx_n_notices_received: NullableStr = Field(
        default=None, alias="Contextual information on Number of notices received "
    )
    ctx_n_notices_from_trusted_flaggers: NullableStr = Field(
        default=None,
        alias="Contextual information on Number of notices received from Trusted flaggers",
    )
    ctx_n_items_in_notices: NullableStr = Field(
        default=None,
        alias="Contextual information on Number of specific items of information included in the total number of notices",
    )
    ctx_n_items_in_tf_notices: NullableStr = Field(
        default=None,
        alias="Contextual information on Number of specific items of information included in the total number of notices by Trusted Flaggers (Trusted Flagger notices)",
    )
    ctx_median_time_to_take_action: NullableStr = Field(
        default=None, alias="Contextual information on Median time to take action"
    )
    ctx_median_time_to_take_action_tf: NullableStr = Field(
        default=None,
        alias="Contextual information on Median time to take action (Trusted Flagger notices)",
    )
    ctx_n_actions_on_law: NullableStr = Field(
        default=None,
        alias="Contextual information on Number of actions taken on the basis of the law",
    )
    ctx_n_actions_on_law_tf: NullableStr = Field(
        default=None,
        alias="Contextual information on Number of actions taken on the basis of the law (Trusted Flagger notices)",
    )
    ctx_n_actions_on_tc: NullableStr = Field(
        default=None,
        alias="Contextual information on Number of actions taken on the basis of the terms and conditions of the service",
    )
    ctx_n_actions_on_tc_tf: NullableStr = Field(
        default=None,
        alias="Contextual information on Number of actions taken on the basis of the terms and conditions of the service (Trusted Flagger notices)",
    )


# ---------------------------------------------------------------------------
# Sheets 5 & 6: own_initiative_illegal + own_initiative_tc — 37 columns each
#
# Identical column counts and structure; only header D differs:
#   sheet 5: "Category of illegal content"
#   sheet 6: "Category of incompatibility with the provider's terms and conditions"
#
# We model them as two thin subclasses of a shared base so the schemas stay
# in lock-step with what we observed in the XLSX.
# ---------------------------------------------------------------------------


class _OwnInitiativeBase(_Base):
    applicability: NullableStr = Field(default=None, alias="Applicability")
    service: NullableStr = Field(default=None, alias="Service")
    reporting_period: NullableStr = Field(default=None, alias="Reporting period")
    # Subclasses override the alias for column D
    description_subcategory_other: NullableStr = Field(
        default=None, alias='Description of the sub-category "Other"'
    )
    n_measures_own_initiative: NullableNum = Field(
        default=None, alias="Number of measures taken at the provider's own initiative "
    )
    n_measures_automated_detection: NullableNum = Field(
        default=None,
        alias="Number of measures taken after detection with solely automated means ",
    )
    vis_restriction_removal: NullableNum = Field(
        default=None, alias="Visibility restriction Removal"
    )
    vis_restriction_disable: NullableNum = Field(
        default=None, alias="Visibility restriction Disable"
    )
    vis_restriction_demoted: NullableNum = Field(
        default=None, alias="Visibility restriction Demoted"
    )
    vis_restriction_age_restricted: NullableNum = Field(
        default=None, alias="Visibility restriction Age restricted"
    )
    vis_restriction_interaction_restricted: NullableNum = Field(
        default=None, alias="Visibility restriction Interaction restricted"
    )
    vis_restriction_labelled: NullableNum = Field(
        default=None, alias="Visibility restriction Labelled "
    )
    vis_restriction_other: NullableNum = Field(
        default=None, alias="Visibility restriction Other"
    )
    mon_restriction_suspension: NullableNum = Field(
        default=None, alias="Monetary restriction Suspension"
    )
    mon_restriction_termination: NullableNum = Field(
        default=None, alias="Monetary restriction Termination"
    )
    mon_restriction_other: NullableNum = Field(
        default=None, alias="Monetary restriction Other"
    )
    provision_suspension: NullableNum = Field(
        default=None, alias="Provision of the service Suspension"
    )
    provision_termination: NullableNum = Field(
        default=None, alias="Provision of the service Termination"
    )
    account_suspension: NullableNum = Field(
        default=None, alias="Account restriction Suspension"
    )
    account_termination: NullableNum = Field(
        default=None, alias="Account restriction Termination"
    )
    ctx_n_measures_own_initiative: NullableStr = Field(
        default=None,
        alias="Contextual Information on Number of measures taken at the provider's own initiative ",
    )
    ctx_n_measures_automated_detection: NullableStr = Field(
        default=None,
        alias="Contextual Information on Number of measures taken after detection with solely automated means ",
    )
    ctx_vis_restriction_removal: NullableStr = Field(
        default=None, alias="Contextual Information on Visibility restriction Removal"
    )
    ctx_vis_restriction_disable: NullableStr = Field(
        default=None, alias="Contextual Information on Visibility restriction Disable"
    )
    ctx_vis_restriction_demoted: NullableStr = Field(
        default=None, alias="Contextual Information on Visibility restriction Demoted"
    )
    ctx_vis_restriction_age_restricted: NullableStr = Field(
        default=None,
        alias="Contextual Information on Visibility restriction Age restricted",
    )
    ctx_vis_restriction_interaction_restricted: NullableStr = Field(
        default=None,
        alias="Contextual Information on Visibility restriction Interaction restricted",
    )
    ctx_vis_restriction_labelled: NullableStr = Field(
        default=None,
        alias="Contextual Information on Visibility restriction Labelled ",
    )
    ctx_vis_restriction_other: NullableStr = Field(
        default=None, alias="Contextual Information on Visibility restriction Other"
    )
    ctx_mon_restriction_suspension: NullableStr = Field(
        default=None,
        alias="Contextual Information on Monetary restriction Suspension",
    )
    ctx_mon_restriction_termination: NullableStr = Field(
        default=None,
        alias="Contextual Information on Monetary restriction Termination",
    )
    ctx_mon_restriction_other: NullableStr = Field(
        default=None, alias="Contextual Information on Monetary restriction Other"
    )
    ctx_provision_suspension: NullableStr = Field(
        default=None,
        alias="Contextual Information on Provision of the service Suspension",
    )
    ctx_provision_termination: NullableStr = Field(
        default=None,
        alias="Contextual Information on Provision of the service Termination",
    )
    ctx_account_suspension: NullableStr = Field(
        default=None, alias="Contextual Information on Account restriction Suspension"
    )
    ctx_account_termination: NullableStr = Field(
        default=None,
        alias="Contextual Information on Account restriction Termination",
    )


class OwnInitiativeIllegalRow(_OwnInitiativeBase):
    category_of_illegal_content: NullableStr = Field(
        default=None, alias="Category of illegal content"
    )


class OwnInitiativeTCRow(_OwnInitiativeBase):
    category_of_incompatibility_tc: NullableStr = Field(
        default=None,
        alias="Category of incompatibility with the provider's terms and conditions",
    )


# ---------------------------------------------------------------------------
# Sheet 7: appeals_and_recidivism — 8 columns
# ---------------------------------------------------------------------------


class AppealsAndRecidivismRow(_Base):
    applicability: NullableStr = Field(default=None, alias="Applicability")
    service: NullableStr = Field(default=None, alias="Service")
    reporting_period: NullableStr = Field(default=None, alias="Reporting period")
    section: NullableStr = Field(default=None, alias="Section")
    indicator: NullableStr = Field(default=None, alias="Indicator")
    scope: NullableStr = Field(default=None, alias="Scope")
    value: NullableNum = Field(default=None, alias="Value")
    contextual_information: NullableStr = Field(
        default=None, alias="Contextual Information"
    )


# ---------------------------------------------------------------------------
# Sheet 8: automated_means — 8 columns (same shape as sheet 7)
# ---------------------------------------------------------------------------


class AutomatedMeansRow(_Base):
    applicability: NullableStr = Field(default=None, alias="Applicability")
    service: NullableStr = Field(default=None, alias="Service")
    reporting_period: NullableStr = Field(default=None, alias="Reporting period")
    section: NullableStr = Field(default=None, alias="Section")
    indicator: NullableStr = Field(default=None, alias="Indicator")
    scope: NullableStr = Field(default=None, alias="Scope")
    value: NullableNum = Field(default=None, alias="Value")
    contextual_information: NullableStr = Field(
        default=None, alias="Contextual Information"
    )


# ---------------------------------------------------------------------------
# Sheet 9: qualitative — 5 columns
# ---------------------------------------------------------------------------


class QualitativeRow(_Base):
    applicability: NullableStr = Field(default=None, alias="Applicability")
    service: NullableStr = Field(default=None, alias="Service")
    reporting_period: NullableStr = Field(default=None, alias="Reporting period")
    indicator: NullableStr = Field(default=None, alias="Indicator")
    value: NullableStr = Field(default=None, alias="Value")


# ---------------------------------------------------------------------------
# Sheet registry — maps Excel sheet name → (slug, row schema, expected_headers)
# ---------------------------------------------------------------------------


SHEET_REGISTRY: dict[str, tuple[str, type[_Base], tuple[str, ...]]] = {
    "1_report_identification": (
        "report_identification",
        ReportIdentificationRow,
        ("Applicability", "Service", "Indicator", "Value"),
    ),
    "2_categories_names": (
        "categories_names",
        CategoriesNamesRow,
        (
            "Category label",
            "Category description",
            "Category of illegal content / incompatible with the terms and conditions",
            "Contextual information",
        ),
    ),
    "3_member_states_orders": (
        "member_states_orders",
        MemberStatesOrdersRow,
        (
            "Applicability",
            "Service",
            "Reporting period",
            "Category of illegal content",
            'Description of the sub-category "Other"',
            "Scope",
            "Number of orders to act against illegal content received",
            "Number of specific items of information included in the total number of orders to act against illegal content",
            "Median time to inform the authority of the receipt of the order to act against illegal content",
            "Median time to give effect to the order to act against illegal content",
            "Number of orders to provide information",
            "Median time to inform the authority of the receipt of the order to provide information",
            "Median time to give effect to the order to provide information",
            "Contextual information on number of orders to act against illegal content received",
            "Contextual information on number of specific items of information included in the total number of orders to act against illegal content",
            "Contextual information on Median time to inform the authority of the receipt of the order to act against illegal content",
            "Contextual information on Median time to give effect to the order to act against illegal content",
            "Contextual information on Number of orders to provide information",
            "Contextual information on Median time to inform the authority of the receipt of the order to provide information",
            "Contextual information on Median time to give effect to the order to provide information",
        ),
    ),
    "4_notices": (
        "notices",
        NoticesRow,
        (
            "Applicability",
            "Service",
            "Reporting period",
            "Category of illegal content",
            'Description of the sub-category "Other"',
            "Number of notices received ",
            "Number of notices received from Trusted flaggers",
            "Number of specific items of information included in the total number of notices",
            "Number of specific items of information included in the total number of notices by Trusted Flaggers (Trusted Flagger notices)",
            "Median time to take action",
            "Median time to take action (Trusted Flagger notices)",
            "Number of actions taken on the basis of the law",
            "Number of actions taken on the basis of the law (Trusted Flagger notices)",
            "Number of actions taken on the basis of the terms and conditions of the service",
            "Number of actions taken on the basis of the terms and conditions of the service (Trusted Flagger notices)",
            "Contextual information on Number of notices received ",
            "Contextual information on Number of notices received from Trusted flaggers",
            "Contextual information on Number of specific items of information included in the total number of notices",
            "Contextual information on Number of specific items of information included in the total number of notices by Trusted Flaggers (Trusted Flagger notices)",
            "Contextual information on Median time to take action",
            "Contextual information on Median time to take action (Trusted Flagger notices)",
            "Contextual information on Number of actions taken on the basis of the law",
            "Contextual information on Number of actions taken on the basis of the law (Trusted Flagger notices)",
            "Contextual information on Number of actions taken on the basis of the terms and conditions of the service",
            "Contextual information on Number of actions taken on the basis of the terms and conditions of the service (Trusted Flagger notices)",
        ),
    ),
    "5_own_initiative_illegal": (
        "own_initiative_illegal",
        OwnInitiativeIllegalRow,
        (
            "Applicability",
            "Service",
            "Reporting period",
            "Category of illegal content",
            'Description of the sub-category "Other"',
            "Number of measures taken at the provider's own initiative ",
            "Number of measures taken after detection with solely automated means ",
            "Visibility restriction Removal",
            "Visibility restriction Disable",
            "Visibility restriction Demoted",
            "Visibility restriction Age restricted",
            "Visibility restriction Interaction restricted",
            "Visibility restriction Labelled ",
            "Visibility restriction Other",
            "Monetary restriction Suspension",
            "Monetary restriction Termination",
            "Monetary restriction Other",
            "Provision of the service Suspension",
            "Provision of the service Termination",
            "Account restriction Suspension",
            "Account restriction Termination",
            "Contextual Information on Number of measures taken at the provider's own initiative ",
            "Contextual Information on Number of measures taken after detection with solely automated means ",
            "Contextual Information on Visibility restriction Removal",
            "Contextual Information on Visibility restriction Disable",
            "Contextual Information on Visibility restriction Demoted",
            "Contextual Information on Visibility restriction Age restricted",
            "Contextual Information on Visibility restriction Interaction restricted",
            "Contextual Information on Visibility restriction Labelled ",
            "Contextual Information on Visibility restriction Other",
            "Contextual Information on Monetary restriction Suspension",
            "Contextual Information on Monetary restriction Termination",
            "Contextual Information on Monetary restriction Other",
            "Contextual Information on Provision of the service Suspension",
            "Contextual Information on Provision of the service Termination",
            "Contextual Information on Account restriction Suspension",
            "Contextual Information on Account restriction Termination",
        ),
    ),
    "6_own_initiative_TC": (
        "own_initiative_tc",
        OwnInitiativeTCRow,
        (
            "Applicability",
            "Service",
            "Reporting period",
            "Category of incompatibility with the provider's terms and conditions",
            'Description of the sub-category "Other"',
            "Number of measures taken at the provider's own initiative ",
            "Number of measures taken after detection with solely automated means ",
            "Visibility restriction Removal",
            "Visibility restriction Disable",
            "Visibility restriction Demoted",
            "Visibility restriction Age restricted",
            "Visibility restriction Interaction restricted",
            "Visibility restriction Labelled ",
            "Visibility restriction Other",
            "Monetary restriction Suspension",
            "Monetary restriction Termination",
            "Monetary restriction Other",
            "Provision of the service Suspension",
            "Provision of the service Termination",
            "Account restriction Suspension",
            "Account restriction Termination",
            "Contextual Information on Number of measures taken at the provider's own initiative ",
            "Contextual Information on Number of measures taken after detection with solely automated means ",
            "Contextual Information on Visibility restriction Removal",
            "Contextual Information on Visibility restriction Disable",
            "Contextual Information on Visibility restriction Demoted",
            "Contextual Information on Visibility restriction Age restricted",
            "Contextual Information on Visibility restriction Interaction restricted",
            "Contextual Information on Visibility restriction Labelled ",
            "Contextual Information on Visibility restriction Other",
            "Contextual Information on Monetary restriction Suspension",
            "Contextual Information on Monetary restriction Termination",
            "Contextual Information on Monetary restriction Other",
            "Contextual Information on Provision of the service Suspension",
            "Contextual Information on Provision of the service Termination",
            "Contextual Information on Account restriction Suspension",
            "Contextual Information on Account restriction Termination",
        ),
    ),
    "7_appeals_and_recidivism": (
        "appeals_and_recidivism",
        AppealsAndRecidivismRow,
        (
            "Applicability",
            "Service",
            "Reporting period",
            "Section",
            "Indicator",
            "Scope",
            "Value",
            "Contextual Information",
        ),
    ),
    "8_automated_means": (
        "automated_means",
        AutomatedMeansRow,
        (
            "Applicability",
            "Service",
            "Reporting period",
            "Section",
            "Indicator",
            "Scope",
            "Value",
            "Contextual Information",
        ),
    ),
    "09_qualitative": (
        "qualitative",
        QualitativeRow,
        ("Applicability", "Service", "Reporting period", "Indicator", "Value"),
    ),
}


__all__ = [
    "AppealsAndRecidivismRow",
    "AutomatedMeansRow",
    "CategoriesNamesRow",
    "MemberStatesOrdersRow",
    "NoticesRow",
    "OwnInitiativeIllegalRow",
    "OwnInitiativeTCRow",
    "QualitativeRow",
    "ReportIdentificationRow",
    "SHEET_REGISTRY",
    "_norm",
]
