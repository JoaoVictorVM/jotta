"""Keyword-based risk classification for task descriptions."""

from __future__ import annotations

import re

from jotta.core.state import JSONDict

HIGH_RISK = re.compile(
    r"(?i)\b(auth|authentication|authorization|autenticacao|autenticação|login|oauth|payment|pagamento|billing|"
    r"security|secret|migration|migracao|migração|schema migration|migracao destrutiva|migração destrutiva|"
    r"personal data|dados pessoais|permissao|permissão|criptografia|production|infraestrutura|public api|"
    r"breaking change)\b"
)


def risk_for(text: str) -> JSONDict:
    reasons = sorted({match.group(0).lower() for match in HIGH_RISK.finditer(text)})
    return {"level": "high" if reasons else "normal", "reasons": reasons}
