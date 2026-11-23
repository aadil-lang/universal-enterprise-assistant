"""
Regression Tests for Phase 5.2: Multi-Chunk Policy Retrieval and Evaluation.
Verifies that _synthesize_local:
1. Evaluates multiple retrieved chunks rather than relying solely on the first chunk.
2. Correctly extracts Q05 annual vacation entitlement from Section 2 when Section 1 ranks first.
3. Correctly extracts Q06 rollover (maximum 5 days) with accurate citation to Section 2.
4. Correctly synthesizes hybrid responses combining policy entitlement (18 days) and personal balances (8.00 days).
5. Correctly extracts changed/custom policy values (e.g., 25 days) from evidence without magic constants.
6. Returns an explicit inability response when numerical evidence is absent across all chunks.
7. Ignores irrelevant or introductory leading chunks without preventing extraction from later chunks.
8. Ensures citation metadata strictly matches the chunk containing the supporting evidence:
   [Acme Leave Policy, 2. Annual Vacation Leave Accrual and Rollover].
"""

import pytest
from app.services.llm_service import LLMService


@pytest.fixture
def mock_llm_service():
    """Provides LLMService initialized in deterministic mock mode."""
    service = LLMService()
    service.provider = "mock"
    return service


def test_q05_annual_entitlement_extracted_from_section_2_when_section_1_ranks_first(mock_llm_service):
    """
    Test 1: Q05 annual entitlement extracted from Section 2 when Section 1 ranks first.
    Recreates the exact production retrieval order observed in ChromaDB where Section 1
    (Purpose and Scope) ranked ahead of Section 2 (Accrual and Rollover).
    """
    evidence = [
        {
            "document_title": "Acme Leave Policy",
            "section": "1. Purpose and Scope",
            "text": "1. Purpose and Scope\nAcme Corporation recognizes the importance of personal time off, rest, and recuperation for employee well-being and sustained productivity. This Leave Policy establishes clear, equitable, and transparent guidelines governing the accrual, request, approval, and management of employee leave entitlements.",
        },
        {
            "document_title": "Acme Leave Policy",
            "section": "2. Annual Vacation Leave Accrual and Rollover",
            "text": "2. Annual Vacation Leave Accrual and Rollover\nFull-time permanent employees of Acme Corporation accrue annual vacation leave at a rate of 18 days per calendar year. Part-time employees accrue vacation leave on a pro-rata basis proportional to their scheduled hours.",
        },
    ]

    res = mock_llm_service._synthesize_local(
        question="What is the annual vacation entitlement under company policy?",
        category="policy",
        policy_evidence=evidence,
        mcp_data={},
        is_sufficient=True,
        has_conflict=False,
    )

    assert "18 days" in res
    assert "[Acme Leave Policy, 2. Annual Vacation Leave Accrual and Rollover]" in res
    assert "1. Purpose and Scope" not in res


def test_q06_rollover_extracted_from_section_2_with_correct_citation(mock_llm_service):
    """
    Test 2: Q06 rollover returning maximum 5 days with correct citation.
    Verifies that vacation rollover extraction targets Section 2 and reports 5 days.
    """
    evidence = [
        {
            "document_title": "Acme Leave Policy",
            "section": "1. Purpose and Scope",
            "text": "1. Purpose and Scope\nThis Leave Policy establishes clear guidelines for employees.",
        },
        {
            "document_title": "Acme Leave Policy",
            "section": "2. Annual Vacation Leave Accrual and Rollover",
            "text": "Employees may carry over a maximum of 5 unused vacation days into the following calendar year. Any additional accrued but unused vacation days exceeding this 5-day rollover cap will be forfeited.",
        },
    ]

    res = mock_llm_service._synthesize_local(
        question="How many unused vacation days can an employee carry over to the next year under Acme policy?",
        category="policy",
        policy_evidence=evidence,
        mcp_data={},
        is_sufficient=True,
        has_conflict=False,
    )

    assert "5 unused vacation days" in res or "maximum of 5" in res
    assert "[Acme Leave Policy, 2. Annual Vacation Leave Accrual and Rollover]" in res
    assert "1. Purpose and Scope" not in res


def test_hybrid_policy_plus_personal_response(mock_llm_service):
    """
    Test 3: Hybrid policy-plus-personal response returning both 18 policy days and Bob's 8 available days.
    """
    evidence = [
        {
            "document_title": "Acme Leave Policy",
            "section": "1. Purpose and Scope",
            "text": "1. Purpose and Scope\nGeneral purpose statement.",
        },
        {
            "document_title": "Acme Leave Policy",
            "section": "2. Annual Vacation Leave Accrual and Rollover",
            "text": "Full-time permanent employees of Acme Corporation accrue annual vacation leave at a rate of 18 days per calendar year.",
        },
    ]
    mcp_data = {
        "employee_id": "EMP-00102",
        "fiscal_year": 2026,
        "balances": [
            {
                "leave_type": "annual",
                "accrued_days": 18.00,
                "used_days": 10.00,
                "available_days": 8.00,
            }
        ],
    }

    res = mock_llm_service._synthesize_local(
        question="What is the company vacation policy and how many days do I have left?",
        category="hybrid",
        policy_evidence=evidence,
        mcp_data=mcp_data,
        is_sufficient=True,
        has_conflict=False,
    )

    # Asserts policy entitlement
    assert "18 days" in res
    assert "[Acme Leave Policy, 2. Annual Vacation Leave Accrual and Rollover]" in res
    # Asserts personal record
    assert "8.00 days" in res or "8 days" in res
    assert "Personal Records:" in res


def test_changed_policy_value_extracted_without_magic_constants(mock_llm_service):
    """
    Test 4: Changed policy value (e.g., 25 days) extracted from changed evidence without magic constants.
    Ensures no hardcoded '18' is injected when the document specifies 25 days.
    """
    evidence = [
        {
            "document_title": "Global Tech Policy",
            "section": "Intro",
            "text": "Introductory scope statement.",
        },
        {
            "document_title": "Global Tech Policy",
            "section": "Vacation Terms",
            "text": "All personnel accrue annual vacation leave at a rate of 25 days per calendar year.",
        },
    ]

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
    assert "[Global Tech Policy, Vacation Terms]" in res


def test_missing_numerical_evidence_returns_explicit_inability(mock_llm_service):
    """
    Test 5: Missing numerical evidence returning explicit inability.
    When multiple chunks discuss vacation but neither contains a numerical entitlement,
    a safe inability response must be returned instead of inventing or falling back to numbers.
    """
    evidence = [
        {
            "document_title": "Acme Leave Policy",
            "section": "1. Purpose and Scope",
            "text": "1. Purpose and Scope\nAcme Corporation recognizes the importance of personal time off.",
        },
        {
            "document_title": "Acme Leave Policy",
            "section": "Eligibility",
            "text": "Vacation leave is subject to management approval based on operational needs.",
        },
    ]

    res = mock_llm_service._synthesize_local(
        question="What is the annual vacation entitlement under company policy?",
        category="policy",
        policy_evidence=evidence,
        mcp_data={},
        is_sufficient=True,
        has_conflict=False,
    )

    assert "does not specify a clear numerical annual vacation entitlement" in res
    assert "18" not in res
    assert "25" not in res


def test_irrelevant_first_chunk_not_preventing_extraction(mock_llm_service):
    """
    Test 6: Irrelevant first chunk not preventing extraction from later relevant chunk.
    Tests with a completely irrelevant first chunk (e.g., Code of Conduct or IT disclaimer).
    """
    evidence = [
        {
            "document_title": "Acme Code of Conduct",
            "section": "General Standards",
            "text": "Employees must treat all colleagues with respect and adhere to business ethics.",
        },
        {
            "document_title": "Acme Leave Policy",
            "section": "2. Annual Vacation Leave Accrual and Rollover",
            "text": "Full-time permanent employees of Acme Corporation accrue annual vacation leave at a rate of 18 days per calendar year.",
        },
    ]

    res = mock_llm_service._synthesize_local(
        question="What is the annual vacation entitlement under company policy?",
        category="policy",
        policy_evidence=evidence,
        mcp_data={},
        is_sufficient=True,
        has_conflict=False,
    )

    assert "18 days" in res
    assert "[Acme Leave Policy, 2. Annual Vacation Leave Accrual and Rollover]" in res
    assert "General Standards" not in res


def test_citation_correctness_asserting_exact_section(mock_llm_service):
    """
    Test 7: Citation correctness asserting [Acme Leave Policy, 2. Annual Vacation Leave Accrual and Rollover].
    Ensures that when chunk 0 is Section 1 and chunk 1 is Section 2, the citation generated
    precisely matches chunk 1's title and section.
    """
    evidence = [
        {
            "document_title": "Acme Leave Policy",
            "section": "1. Purpose and Scope",
            "text": "Purpose and scope chunk.",
        },
        {
            "document_title": "Acme Leave Policy",
            "section": "2. Annual Vacation Leave Accrual and Rollover",
            "text": "Permanent employees accrue annual vacation leave at a rate of 18 days per calendar year.",
        },
    ]

    res = mock_llm_service._synthesize_local(
        question="What is the annual vacation entitlement under company policy?",
        category="policy",
        policy_evidence=evidence,
        mcp_data={},
        is_sufficient=True,
        has_conflict=False,
    )

    exact_expected_citation = "[Acme Leave Policy, 2. Annual Vacation Leave Accrual and Rollover]"
    assert exact_expected_citation in res
