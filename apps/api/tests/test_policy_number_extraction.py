"""
Regression Tests for Phase 5A.1: Document-Driven Policy Number Extraction.
Verifies that _synthesize_local:
1. Correctly extracts varied numerical policy values from retrieved evidence.
2. Supports alternative phrasing and sentence structures.
3. Explicitly refuses/reports inability to extract when numbers are missing.
4. Never silently substitutes old hardcoded Acme fallback constants (18, 5, 10, 36, 24, 300).
5. Correctly handles unparseable evidence while preserving citations.
"""

import pytest
from app.services.llm_service import LLMService


@pytest.fixture
def mock_llm_service():
    """Provides LLMService initialized in deterministic mock mode."""
    service = LLMService()
    service.provider = "mock"
    return service


def test_custom_vacation_entitlement_extracted(mock_llm_service):
    """Verifies that non-standard vacation days (e.g. 25 days) are extracted, not old fallback 18."""
    evidence = [{
        "document_title": "Custom Leave Policy",
        "section": "Vacation Entitlement",
        "text": "Full-time team members are entitled to 25 days of paid annual vacation leave per year.",
    }]
    res = mock_llm_service._synthesize_local(
        question="What is the annual vacation entitlement under company policy?",
        category="policy",
        policy_evidence=evidence,
        mcp_data={},
        is_sufficient=True,
        has_conflict=False,
    )
    assert "25 days" in res
    assert "18 days" not in res
    assert "[Custom Leave Policy, Vacation Entitlement]" in res


def test_alternative_sentence_structure_vacation(mock_llm_service):
    """Verifies vacation extraction with phrasing: 'accrue 22 days of annual leave'."""
    evidence = [{
        "document_title": "Alternative Policy",
        "section": "Leave Guidelines",
        "text": "Eligible staff accrue 22 days of annual leave each calendar year, with rollover permitted up to 7 days.",
    }]
    res_entitlement = mock_llm_service._synthesize_local(
        question="What is the annual vacation entitlement?",
        category="policy",
        policy_evidence=evidence,
        mcp_data={},
        is_sufficient=True,
        has_conflict=False,
    )
    assert "22 days" in res_entitlement
    assert "18" not in res_entitlement

    res_rollover = mock_llm_service._synthesize_local(
        question="How many unused vacation days can be carried over?",
        category="policy",
        policy_evidence=evidence,
        mcp_data={},
        is_sufficient=True,
        has_conflict=False,
    )
    assert "7 unused vacation days" in res_rollover
    assert "5" not in res_rollover


def test_custom_sick_leave_and_rollover(mock_llm_service):
    """Verifies non-standard sick leave (14 days accrual, 8 days rollover)."""
    evidence = [{
        "document_title": "Health & Sick Leave Policy",
        "section": "Sick Time",
        "text": "Employees accrue 14 days of paid sick leave annually. A maximum of 8 days rollover is allowed.",
    }]
    res = mock_llm_service._synthesize_local(
        question="How much sick leave do employees accrue?",
        category="policy",
        policy_evidence=evidence,
        mcp_data={},
        is_sufficient=True,
        has_conflict=False,
    )
    assert "14 days" in res
    assert "8 days" in res
    assert "10 days" not in res
    assert "5 days" not in res


def test_custom_laptop_refresh_period(mock_llm_service):
    """Verifies non-standard hardware refresh (e.g. 48 months or 24 months)."""
    evidence = [{
        "document_title": "IT Asset Policy",
        "section": "Refresh Cycles",
        "text": "Engineering laptops are eligible for replacement under a 48-month hardware refresh cycle.",
    }]
    res = mock_llm_service._synthesize_local(
        question="What is the laptop refresh period?",
        category="policy",
        policy_evidence=evidence,
        mcp_data={},
        is_sufficient=True,
        has_conflict=False,
    )
    assert "48-month" in res
    assert "36-month" not in res


def test_custom_screen_damage_reporting_timeframe(mock_llm_service):
    """Verifies non-standard reporting hours (e.g. 48 hours or 12 hours)."""
    evidence = [{
        "document_title": "Hardware Policy",
        "section": "Screen Damage",
        "text": "Damaged screens must be reported by submitting an IT support ticket within 48 hours of occurrence.",
    }]
    res = mock_llm_service._synthesize_local(
        question="What is the policy for reporting a broken laptop screen?",
        category="policy",
        policy_evidence=evidence,
        mcp_data={},
        is_sufficient=True,
        has_conflict=False,
    )
    assert "48 hours" in res
    assert "24 hours" not in res


def test_custom_ergonomic_stipend_amount(mock_llm_service):
    """Verifies non-standard home office stipend (e.g. $500 or $750)."""
    evidence = [{
        "document_title": "Remote Work Guidelines",
        "section": "Stipends",
        "text": "Approved remote staff receive a one-time ergonomic home office stipend of $500 upon hire.",
    }]
    res = mock_llm_service._synthesize_local(
        question="What is the ergonomic stipend amount?",
        category="policy",
        policy_evidence=evidence,
        mcp_data={},
        is_sufficient=True,
        has_conflict=False,
    )
    assert "$500" in res
    assert "$300" not in res


def test_missing_numbers_in_evidence_returns_explicit_inability(mock_llm_service):
    """Verifies that evidence with text but no numbers yields a safe inability-to-extract response, not fallback."""
    evidence = [{
        "document_title": "Vague Vacation Document",
        "section": "General Rules",
        "text": "Employees receive paid annual vacation leave subject to manager approval and business need.",
    }]
    res = mock_llm_service._synthesize_local(
        question="What is the annual vacation entitlement?",
        category="policy",
        policy_evidence=evidence,
        mcp_data={},
        is_sufficient=True,
        has_conflict=False,
    )
    assert "does not specify a clear numerical annual vacation entitlement" in res
    assert "18" not in res
    assert "[Vague Vacation Document, General Rules]" in res


def test_missing_stipend_number_returns_explicit_inability(mock_llm_service):
    """Verifies that evidence mentioning stipends without dollar amount does not fabricate $300."""
    evidence = [{
        "document_title": "Remote Policy",
        "section": "Stipend Overview",
        "text": "Remote employees may be eligible for an ergonomic stipend for home office purchases.",
    }]
    res = mock_llm_service._synthesize_local(
        question="What is the ergonomic stipend?",
        category="policy",
        policy_evidence=evidence,
        mcp_data={},
        is_sufficient=True,
        has_conflict=False,
    )
    assert "does not specify a numerical ergonomic stipend amount" in res
    assert "$300" not in res
    assert "300" not in res


def test_standard_acme_fixtures_still_correct(mock_llm_service):
    """Verifies backward compatibility with standard Acme Corporation fixtures."""
    # Standard Acme vacation (18 days, 5 rollover)
    ev_vacation = [{
        "document_title": "Acme Corporation Leave Policy",
        "section": "1. Purpose and Scope",
        "text": "Full-time employees are entitled to 18 days of paid annual vacation leave per calendar year. Up to 5 days can rollover.",
    }]
    res = mock_llm_service._synthesize_local(
        question="What is the annual vacation entitlement under company policy?",
        category="policy",
        policy_evidence=ev_vacation,
        mcp_data={},
        is_sufficient=True,
        has_conflict=False,
    )
    assert "18 days" in res

    # Standard Acme stipend ($300)
    ev_stipend = [{
        "document_title": "Acme Corporation Remote Work Policy",
        "section": "3. Home-Office Ergonomic Stipend",
        "text": "Eligible remote employees are provided a one-time ergonomic home office stipend of $300.",
    }]
    res_stipend = mock_llm_service._synthesize_local(
        question="What is the company's ergonomic stipend?",
        category="policy",
        policy_evidence=ev_stipend,
        mcp_data={},
        is_sufficient=True,
        has_conflict=False,
    )
    assert "$300" in res_stipend
