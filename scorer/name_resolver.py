from dataclasses import dataclass
import re
from typing import Optional


_SOURCE_WEIGHTS = {
    "override": 1.0,
    "onchain_identity": 0.82,
    "cached_consensus": 0.72,
    "taostats_public": 0.58,
    "tao_app_public": 0.58,
    "seed_name": 0.42,
}
_MIN_ACCEPTABLE_CONFIDENCE = 0.58


def canonical_name_key(value: Optional[str]) -> str:
    if not value:
        return ""
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def looks_low_confidence_subnet_name(name: Optional[str]) -> bool:
    if not name:
        return True

    value = str(name).strip()
    if not value:
        return True

    lower = value.lower()
    if lower in {"unknown", "for sale"}:
        return True
    if "..." in value or "…" in value:
        return True
    if len(canonical_name_key(value)) < 3:
        return True

    if re.fullmatch(r"[A-Z][a-z]+(?:[A-Z][a-z]{1,3})", value):
        return True
    if "." in value:
        if re.fullmatch(r"[A-Za-z]+\.[A-Za-z]{1}", value):
            return True
        if value[0].islower() and len(value) <= 10:
            return True
    if " " in value and len(value) <= 10:
        tokens = [token for token in value.split(" ") if token]
        if len(tokens) == 2:
            if any(len(token) <= 4 for token in tokens[1:]) and all(token[:1].isupper() or token.isupper() for token in tokens):
                return True

    return False


def _same_name_family(left: Optional[str], right: Optional[str]) -> bool:
    left_key = canonical_name_key(left)
    right_key = canonical_name_key(right)
    if not left_key or not right_key:
        return False
    if left_key == right_key:
        return True

    shorter, longer = sorted((left_key, right_key), key=len)
    return len(shorter) >= 4 and longer.startswith(shorter)


@dataclass
class _Cluster:
    representative: str
    confidence: float
    source_count: int


def resolve_subnet_name(netuid: int, candidates_by_source: dict[str, Optional[str]]) -> Optional[str]:
    override = candidates_by_source.get("override")
    if override:
        return override

    clusters: list[_Cluster] = []
    for source, candidate in candidates_by_source.items():
        if source == "override" or not candidate:
            continue

        weight = _SOURCE_WEIGHTS.get(source, 0.35)
        matched = False
        for cluster in clusters:
            if not _same_name_family(cluster.representative, candidate):
                continue
            cluster.confidence += weight
            cluster.source_count += 1
            if len(candidate) > len(cluster.representative):
                cluster.representative = candidate
            matched = True
            break

        if not matched:
            clusters.append(_Cluster(representative=candidate, confidence=weight, source_count=1))

    if not clusters:
        return None

    best = max(
        clusters,
        key=lambda cluster: (
            cluster.confidence + (0.08 if cluster.source_count > 1 else 0.0),
            len(cluster.representative),
        ),
    )

    if looks_low_confidence_subnet_name(best.representative):
        return None
    if best.confidence < _MIN_ACCEPTABLE_CONFIDENCE:
        return None
    return best.representative
