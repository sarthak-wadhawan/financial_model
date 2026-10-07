"""Deterministic SEC evidence extraction; unknown is preferable to invented facts."""
from __future__ import annotations

import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from html.parser import HTMLParser
from xml.etree import ElementTree as ET


class _Text(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []
        self.hidden = 0

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style"}:
            self.hidden += 1
        if tag in {"p", "div", "br", "tr", "h1", "h2", "h3"}:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in {"script", "style"}:
            self.hidden = max(0, self.hidden - 1)
        if tag in {"p", "div", "tr"}:
            self.parts.append("\n")

    def handle_data(self, data):
        if not self.hidden:
            self.parts.append(data)


def filing_text(raw: str) -> str:
    parser = _Text()
    parser.feed(raw)
    return "\n".join(re.sub(r"\s+", " ", x).strip() for x in "".join(parser.parts).splitlines()
                     if x.strip())


def sections(text: str) -> list[dict]:
    """Keep repeated headings (including TOC) and offsets; don't guess canonical sections."""
    matches = list(re.finditer(r"\b(?:ITEM\s+\d+(?:\.\d{2}|[A-C])?|PART\s+[IVX]+)\b", text, re.I))
    return [{"heading": m.group(), "start": m.start(),
             "end": matches[i + 1].start() if i + 1 < len(matches) else len(text),
             "text": text[m.start():matches[i + 1].start() if i + 1 < len(matches) else len(text)]}
            for i, m in enumerate(matches)]


def leadership(text: str) -> list[dict]:
    """Narrow explicit subject/action/role/date grammar. Ambiguous prose remains raw evidence.

    Requires an explicit effective date; no date inference from filing time, no
    signature/title inference, no sentiment, and no assumption an announcement is effective.

    Only extracts affirmative appointments/departures for the **issuer** (not subsidiaries
    or quoted/negated statements). Replacement names are captured when explicitly stated.
    """
    name = r"(?P<name>[A-Z][A-Za-z'-]+(?: [A-Z][A-Za-z.'-]+){1,4})"
    role = r"(?P<role>(?i:Chief Executive Officer|Chief Financial Officer)|CEO|CFO)"
    explicit_date = (r"(?P<date>\d{4}-\d{2}-\d{2}|(?:January|February|March|April|May|June|July|"
                     r"August|September|October|November|December) \d{1,2}, \d{4})")
    effective = r"(?:,|;)? \s*(?:effective|effective as of) " + explicit_date + r"(?=[.\s,;]|$)"
    patterns = [
        re.compile(
            name + r" (?P<action>was appointed|has been appointed|resigned|departed) "
            + r"(?:as |as the )?" + role + effective),
        re.compile(
            r"(?P<action>appointed) " + name + r" (?:as |as the |to serve as |to serve as the )"
            + role + effective),
    ]
    # Negation/uncertainty markers that invalidate an otherwise-matching clause.
    negation = re.compile(
        r"\b(not|never|denied|denies|denial|false|falsely|incorrect|inaccurate|"
        r"no appointment|no change|if|may|might|would|could|proposed|contingent|subject to)\b", re.I)
    result = []
    for pattern in patterns:
        for match in pattern.finditer(text):
            # Reject quoted/hypothetical or explicitly negated clauses.
            # Check the sentence-level context before the match.
            sent_start = max(text.rfind(".", 0, match.start()), text.rfind("\n", 0, match.start())) + 1
            prefix = text[sent_start:match.start()]
            if negation.search(prefix):
                continue
            # Reject if the match appears inside quotation marks.
            before = text[:match.start()]
            after = text[match.end():]
            if before.count('"') % 2 == 1 or after.count('"') % 2 == 1:
                continue
            try:
                value = (date.fromisoformat(match["date"]) if match["date"][0].isdigit()
                         else datetime.strptime(match["date"], "%B %d, %Y").date())
            except ValueError:
                continue
            # Capture explicit replacement if present in the surrounding text.
            replacement = None
            surrounding = text[max(0, match.start() - 200):match.end() + 200]
            repl_match = re.search(
                r"replac(?:ing|ed|ement of)\s+(?P<repl_name>[A-Z][A-Za-z'-]+(?: [A-Z][A-Za-z.'-]+){1,4})",
                surrounding, re.I)
            if repl_match:
                replacement = repl_match["repl_name"]
            result.append({"name": match["name"],
                           "role": "CEO" if match["role"].lower() in {"ceo", "chief executive officer"} else "CFO",
                           "action": "appointment" if "appointed" in match["action"] else "departure",
                           "effective_date": value.isoformat(), "evidence": match.group(),
                           "evidence_start": match.start(), "evidence_end": match.end(),
                           "replacement": replacement})
    return sorted(result, key=lambda change: change["evidence_start"])


def _value(node, path):
    found = node.find(path)
    return "".join(found.itertext()).strip() or None if found is not None else None


def _boolean(value):
    return True if value in {"1", "true"} else False if value in {"0", "false"} else None


def parse_form4(raw: bytes) -> dict:
    # Reject DTDs/entities before parsing, including UTF-16/32 encoded declarations.
    if len(raw) > 20_000_000 or re.search(br"<!\s*(DOCTYPE|ENTITY)", raw.replace(b"\x00", b""), re.I):
        raise ValueError("Unsafe SEC ownership XML")
    root = ET.fromstring(raw)
    # Strip namespaces from all tags for consistent querying.
    for node in root.iter():
        if "}" in node.tag:
            node.tag = node.tag.rsplit("}", 1)[-1]
    if root.tag != "ownershipDocument":
        raise ValueError("Expected SEC ownershipDocument XML")
    footnotes = {n.attrib["id"]: "".join(n.itertext()).strip()
                 for n in root.findall(".//footnote") if "id" in n.attrib}
    owners = []
    for node in root.findall("reportingOwner"):
        owners.append({"cik": _value(node, "reportingOwnerId/rptOwnerCik"),
                       "name": _value(node, "reportingOwnerId/rptOwnerName"),
                       "officer_title": _value(node, "reportingOwnerRelationship/officerTitle"),
                       **{key: _boolean(_value(node, "reportingOwnerRelationship/" + tag))
                          for key, tag in {"is_director": "isDirector", "is_officer": "isOfficer",
                                           "is_ten_percent_owner": "isTenPercentOwner", "is_other": "isOther"}.items()}})
    classifications = {"P": "purchase_open_market_or_private", "S": "sale_open_market_or_private",
                       "M": "option_exercise_or_conversion", "A": "grant_award_or_acquisition",
                       "G": "gift", "F": "tax_or_exercise_price_disposition",
                       "C": "conversion", "D": "disposition_to_issuer"}
    transactions = []
    for table, tag, derivative in [("nonDerivativeTable", "nonDerivativeTransaction", False),
                                   ("derivativeTable", "derivativeTransaction", True)]:
        for node in root.findall(f"{table}/{tag}"):
            code = _value(node, "transactionCoding/transactionCode")
            fields = {"security_title": "securityTitle/value", "transaction_date": "transactionDate/value",
                      "shares": "transactionAmounts/transactionShares/value",
                      "price": "transactionAmounts/transactionPricePerShare/value",
                      "acquired_disposed": "transactionAmounts/transactionAcquiredDisposedCode/value",
                      "holdings_after": "postTransactionAmounts/sharesOwnedFollowingTransaction/value",
                      "ownership": "ownershipNature/directOrIndirectOwnership/value",
                      "ownership_nature": "ownershipNature/natureOfOwnership/value",
                      "exercise_price": "conversionOrExercisePrice/value",
                      "exercise_date": "exerciseDate/value", "expiration_date": "expirationDate/value",
                      "underlying_security": "underlyingSecurity/underlyingSecurityTitle/value",
                      "underlying_shares": "underlyingSecurity/underlyingSecurityShares/value"}
            tx = {key: _value(node, path) for key, path in fields.items()}
            tx.update({"index": len(transactions), "derivative": derivative, "code": code,
                       "buy_sell_other": "buy" if code == "P" else "sell" if code == "S" else "other",
                       "classification": classifications.get(code, "other"),
                       "footnote_ids": [n.attrib.get("id") for n in node.iter("footnoteId")],
                       "footnote_references": [{"field": parent.tag, "id": child.attrib.get("id")}
                                               for parent in node.iter() for child in parent
                                               if child.tag == "footnoteId"],
                       "transaction_value": None})
            try:
                if tx["shares"] is not None and tx["price"] is not None:
                    value = Decimal(tx["shares"]) * Decimal(tx["price"])
                    if value.is_finite():
                        tx["transaction_value"] = str(value)
            except InvalidOperation:
                pass
            transactions.append(tx)
    return {"issuer_cik": _value(root, "issuer/issuerCik"), "owners": owners,
            "transactions": transactions, "footnotes": footnotes,
            "ten_b5_one": _boolean(_value(root, "aff10b5One")),
            "period_of_report": _value(root, "periodOfReport"),
            "remarks": _value(root, "remarks"),
            "ownership_scope": "joint_filing; transactions not allocated to individual owners"}
