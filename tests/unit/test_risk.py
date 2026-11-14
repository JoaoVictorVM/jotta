from __future__ import annotations

import pytest

from jotta.core.risk import risk_for


@pytest.mark.parametrize(
    "text",
    [
        "change the OAuth login flow",
        "alterar autenticacao, pagamentos e migracao destrutiva",
        "add a breaking change to the public API",
        "store dados pessoais",
    ],
)
def test_sensitive_work_is_high_risk(text: str) -> None:
    result = risk_for(text)
    assert result["level"] == "high"
    assert result["reasons"]


def test_ordinary_work_is_normal_risk() -> None:
    assert risk_for("ajustar texto vazio na tela inicial") == {"level": "normal", "reasons": []}


def test_reasons_are_unique_and_sorted() -> None:
    assert risk_for("Payment and payment and OAuth")["reasons"] == ["oauth", "payment"]


def test_keywords_match_whole_words_only() -> None:
    assert risk_for("update the author field")["level"] == "normal"
