"""LLM Provider Abstraction -- optional local LLM extraction enhancement.

Supports:
- DisabledLLMProvider (default, zero-LLM baseline)
- LocalLLMProvider (Ollama or compatible local inference)

LLM_ENABLED=false must pass all product tests.
"""
from __future__ import annotations

import json
import logging
import os
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Optional

import httpx

from trading_copilot.models.news import (
    EvidenceSpan,
    ManagementStatement,
    NewsDocument,
    NewsSourceType,
    StatementType,
    ExtractionMethod,
)

logger = logging.getLogger(__name__)


class LLMProvider(ABC):
    """Abstract base for LLM providers."""

    @abstractmethod
    def extract_statements(self, document: NewsDocument) -> list[ManagementStatement]:
        """Extract management statements using LLM."""
        ...

    @abstractmethod
    def health_check(self) -> bool:
        """Check if LLM provider is available."""
        ...

    @abstractmethod
    def close(self) -> None:
        """Close provider resources."""
        ...


class DisabledLLMProvider(LLMProvider):
    """LLM provider that always returns empty results (zero-LLM baseline)."""

    def extract_statements(self, document: NewsDocument) -> list[ManagementStatement]:
        return []

    def health_check(self) -> bool:
        return True

    def close(self) -> None:
        pass


class LocalLLMProvider(LLMProvider):
    """
    Local LLM provider using Ollama-compatible API.

    Requires:
    - OLLAMA_BASE_URL (default: http://localhost:11434)
    - OLLAMA_MODEL (default: llama3.1)
    - LLM_ENABLED=true environment variable

    Falls back to deterministic extraction on any failure.
    """

    SYSTEM_PROMPT = """You are a financial analyst extracting management statements from company documents.

Extract ONLY verifiable, attributable statements made by named executives.

For each statement, output a JSON object with:
{
  "speaker": "exact name or UNKNOWN",
  "speaker_role": "CEO/CFO/COO/CTO/President/VP/etc or null",
  "statement": "exact statement text",
  "statement_type": "guidance|demand|margins|costs|capital_spending|competition|product|regulation|supply|pricing|strategy|risks|macro_conditions|other",
  "evidence_text": "exact span from source text supporting this",
  "confidence": 0.0-1.0
}

Rules:
- ONLY extract statements with clear speaker attribution
- Evidence_text MUST exist verbatim in source
- Speaker must be named executive (CEO, CFO, etc.) or UNKNOWN
- Reject statements without evidence span
- Numbers/dates must match source exactly
- Output valid JSON array only, no extra text"""

    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
        timeout: int = 60,
        max_tokens: int = 2048,
        temperature: float = 0.0,
    ):
        self.base_url = base_url or os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
        self.model = model or os.environ.get("OLLAMA_MODEL", "llama3.1")
        self.timeout = timeout
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.client: httpx.Client | None = None
        self._enabled = os.environ.get("LLM_ENABLED", "false").lower() == "true"

    def _get_client(self) -> httpx.Client:
        if self.client is None:
            self.client = httpx.Client(timeout=self.timeout)
        return self.client

    def extract_statements(self, document: NewsDocument) -> list[ManagementStatement]:
        if not self._enabled:
            logger.debug("LLM extraction disabled (LLM_ENABLED=false)")
            return []

        try:
            prompt = self._build_prompt(document)
            response = self._call_llm(prompt)
            statements = self._parse_response(response, document)
            return statements
        except Exception as exc:
            logger.warning(f"LLM extraction failed, falling back to deterministic: {exc}")
            return []

    def _build_prompt(self, document: NewsDocument) -> str:
        """Build prompt for LLM extraction."""
        return f"""{self.SYSTEM_PROMPT}

Source Document:
Title: {document.headline}
Publisher: {document.publisher}
Published: {document.published_at.isoformat()}
Source Type: {document.source_type.value}
URL: {document.source_url}

Full Text:
{document.body[:8000]}"""

    def _call_llm(self, prompt: str) -> str:
        """Call local LLM API (Ollama-compatible)."""
        client = self._get_client()
        response = client.post(
            f"{self.base_url}/api/generate",
            json={
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": self.temperature,
                    "num_predict": self.max_tokens,
                },
            },
        )
        response.raise_for_status()
        data = response.json()
        return data.get("response", "")

    def _parse_response(self, response: str, document: NewsDocument) -> list[ManagementStatement]:
        """Parse and validate LLM response."""
        from trading_copilot.models.news import ManagementStatement, StatementType, ExtractionMethod, EvidenceSpan

        statements: list[ManagementStatement] = []

        # Try to extract JSON from response
        try:
            # Find JSON array in response
            start = response.find("[")
            end = response.rfind("]") + 1
            if start >= 0 and end > start:
                json_str = response[start:end]
                extracted = json.loads(json_str)
            else:
                extracted = json.loads(response)
        except (json.JSONDecodeError, ValueError) as exc:
            logger.warning(f"LLM response not valid JSON: {exc}")
            return []

        if not isinstance(extracted, list):
            logger.warning("LLM response not a JSON array")
            return []

        for item in extracted:
            try:
                stmt = self._validate_and_create(item, document)
                if stmt:
                    statements.append(stmt)
            except Exception as exc:
                logger.warning(f"Failed to validate LLM extraction: {exc}")
                continue

        return statements

    def _validate_and_create(self, item: dict, document: NewsDocument) -> ManagementStatement | None:
        """Validate and create ManagementStatement from LLM output."""
        from trading_copilot.models.news import ManagementStatement, StatementType, ExtractionMethod, EvidenceSpan

        required_fields = ["speaker", "statement", "statement_type", "evidence_text"]
        for field in required_fields:
            if field not in item or not item[field]:
                return None

        # Validate evidence_text exists in source
        evidence_text = item["evidence_text"]
        if evidence_text not in document.body:
            logger.warning(f"Evidence text not found in source: {evidence_text[:50]}")
            return None

        # Find evidence span
        evidence_span = self._find_evidence_span(evidence_text, document.body)
        if not evidence_span:
            return None

        # Validate statement_type
        try:
            stmt_type = StatementType(item["statement_type"])
        except ValueError:
            stmt_type = StatementType.OTHER

        # Confidence
        confidence = float(item.get("confidence", 0.7))
        confidence = max(0.0, min(1.0, confidence))

        # Speaker role
        speaker_role = item.get("speaker_role")

        content_hash = _sha256(item["statement"])
        stmt_id = f"llm:{document.symbol}:{content_hash[:16]}"

        return ManagementStatement(
            statement_id=stmt_id,
            symbol=document.symbol or "UNKNOWN",
            speaker=item["speaker"],
            speaker_role=speaker_role,
            statement=item["statement"],
            statement_type=stmt_type,
            source_document_id=document.document_id,
            source_url=document.source_url,
            published_at=document.published_at,
            event_date=document.published_at,
            retrieved_at=datetime.now(timezone.utc),
            evidence_span=evidence_span,
            extraction_method=ExtractionMethod.LLM,
            confidence=confidence,
            source_type=document.source_type,
            provider_id=f"{document.provider_id}_llm",
        )

    def _find_evidence_span(self, evidence: str, full_text: str) -> EvidenceSpan | None:
        """Find character span of evidence in full text."""
        from trading_copilot.models.news import EvidenceSpan
        idx = full_text.find(evidence)
        if idx >= 0:
            return EvidenceSpan(start=idx, end=idx + len(evidence), text=evidence)
        return None

    def health_check(self) -> bool:
        if not self._enabled:
            return True  # Disabled is healthy
        try:
            client = self._get_client()
            response = client.get(f"{self.base_url}/api/tags", timeout=5)
            return response.status_code == 200
        except Exception:
            return False

    def close(self) -> None:
        if self.client:
            self.client.close()
            self.client = None


def create_llm_provider() -> LLMProvider:
    """Factory function to create appropriate LLM provider."""
    if os.environ.get("LLM_ENABLED", "false").lower() == "true":
        return LocalLLMProvider()
    return DisabledLLMProvider()


def _sha256(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


if __name__ == "__main__":
    # Quick test
    provider = create_llm_provider()
    print(f"Provider: {type(provider).__name__}")
    print(f"Health check: {provider.health_check()}")
    provider.close()
