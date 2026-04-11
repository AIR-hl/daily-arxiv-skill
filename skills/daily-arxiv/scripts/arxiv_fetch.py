#!/usr/bin/env python3
"""Fetch recent arXiv candidates and emit normalized JSON."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Iterable

try:
    import arxiv
except ImportError as exc:
    arxiv = None
    ARXIV_IMPORT_ERROR = exc
else:
    ARXIV_IMPORT_ERROR = None


_INVALID_QUERY_TERM_RE = re.compile(r'[")(]')
_VERSION_SUFFIX_RE = re.compile(r"v\d+$")

DEFAULT_KEYWORDS = [
    "agent",
    "reinforcement learning",
    "reward model",
    "reward modeling",
    "data synthesis",
    "dpo",
]

DEFAULT_CATEGORIES = [
    "cs.AI",
    "cs.CL",
    "cs.LG",
    "cs.IR"
]

DEFAULT_HOURS = 24
DEFAULT_CANDIDATE_POOL = 100


@dataclass
class FetchConfig:
    keywords: list[str]
    categories: list[str]
    hours: int
    candidate_pool: int


def parse_args() -> FetchConfig:
    parser = argparse.ArgumentParser(
        description="Fetch recent arXiv candidates and print normalized JSON."
    )
    parser.add_argument("--hours", type=int, default=DEFAULT_HOURS, help="Look-back window in hours.")
    parser.add_argument(
        "--candidate-pool",
        type=int,
        default=DEFAULT_CANDIDATE_POOL,
        help="Maximum number of recent arXiv entries to inspect before local filtering.",
    )
    parser.add_argument(
        "--keyword",
        action="append",
        dest="keywords",
        help="Additional keyword to match against title and abstract. Repeatable.",
    )
    parser.add_argument(
        "--category",
        action="append",
        dest="categories",
        help="Additional arXiv category filter. Repeatable.",
    )
    args = parser.parse_args()

    keywords = args.keywords if args.keywords else list(DEFAULT_KEYWORDS)
    categories = args.categories if args.categories else list(DEFAULT_CATEGORIES)
    return FetchConfig(
        keywords=keywords,
        categories=categories,
        hours=args.hours,
        candidate_pool=args.candidate_pool,
    )


def unique_nonempty(values: Iterable[str]) -> list[str]:
    items: list[str] = []
    seen: set[str] = set()

    for value in values:
        normalized = " ".join(value.split()).strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        items.append(normalized)

    return items


def ensure_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def quote_term(value: str, *, quote: bool) -> str:
    if _INVALID_QUERY_TERM_RE.search(value):
        raise ValueError('query term cannot contain double quotes or parentheses')

    if " " in value:
        if not quote:
            raise ValueError(f"query term with spaces requires quoting: {value!r}")
        return f'"{value}"'

    return value


def raw_field_query(prefix: str, value: str, *, quote: bool = True) -> str:
    return f"{prefix}:{quote_term(value, quote=quote)}"


def raw_submitted_date_query(start: datetime, end: datetime) -> str:
    start_utc = ensure_utc(start).strftime("%Y%m%d%H%M")
    end_utc = ensure_utc(end).strftime("%Y%m%d%H%M")
    return f"submittedDate:[{start_utc} TO {end_utc}]"


def combine_queries(clauses: list[str], operator: str) -> str:
    if not clauses:
        raise ValueError("clauses cannot be empty")

    query = clauses[0]
    for clause in clauses[1:]:
        query = f"({query} {operator} {clause})"
    return query


def build_keyword_clause(keyword: str) -> str:
    title_query = raw_field_query("ti", keyword)
    abstract_query = raw_field_query("abs", keyword)
    return f"({title_query} OR {abstract_query})"


def build_category_clause(category: str) -> str:
    return raw_field_query("cat", category, quote=False)


def build_search_query(
    keywords: Iterable[str],
    categories: Iterable[str],
    start: datetime,
    end: datetime,
) -> str:
    keyword_clauses = [build_keyword_clause(keyword) for keyword in unique_nonempty(keywords)]
    category_clauses = [build_category_clause(category) for category in unique_nonempty(categories)]

    clauses = [raw_submitted_date_query(start, end)]
    if keyword_clauses:
        clauses.append(combine_queries(keyword_clauses, "OR"))
    if category_clauses:
        clauses.append(combine_queries(category_clauses, "OR"))

    return combine_queries(clauses, "AND")


def normalized_arxiv_id(result: arxiv.Result) -> str:
    short_id = result.get_short_id() if hasattr(result, "get_short_id") else result.entry_id.rsplit("/", 1)[-1]
    return _VERSION_SUFFIX_RE.sub("", short_id)


def matched_keywords(text: str, keywords: Iterable[str]) -> list[str]:
    lowered = text.lower()
    return [keyword for keyword in unique_nonempty(keywords) if keyword.lower() in lowered]


def result_to_record(
    result: arxiv.Result,
    config: FetchConfig,
    cutoff: datetime,
) -> dict[str, object] | None:
    published_at = ensure_utc(result.published)
    if published_at < cutoff:
        return None

    combined_text = f"{result.title}\n{result.summary}"
    hits = matched_keywords(combined_text, config.keywords)

    categories = sorted(result.categories) if hasattr(result, "categories") else []
    if config.categories and result.primary_category not in config.categories:
        return None

    arxiv_id = normalized_arxiv_id(result)
    abs_url = f"https://arxiv.org/abs/{arxiv_id}"
    pdf_url = result.pdf_url or f"https://arxiv.org/pdf/{arxiv_id}.pdf"
    source_url = f"https://arxiv.org/e-print/{arxiv_id}"

    return {
        "id": arxiv_id,
        "title": result.title,
        "authors": [author.name for author in result.authors],
        "url": abs_url,
        "pdf_url": pdf_url,
        "source_url": source_url,
        "published": published_at.isoformat().replace("+00:00", "Z"),
        "categories": categories,
        "matched_keywords": hits,
        "match_type": "exact" if hits else "potential",
        "comment": result.comment if result.comment is not None else "",
        "abstract": result.summary,
    }


def collect_records(config: FetchConfig) -> dict[str, list[dict[str, object]]]:
    if arxiv is None:
        raise RuntimeError(
            "missing dependency 'arxiv'; install it with `python3 -m pip install -r requirements.txt`"
        ) from ARXIV_IMPORT_ERROR
    if config.hours <= 0:
        raise ValueError("hours must be a positive integer")
    if config.candidate_pool <= 0:
        return {
            "exact_keyword_matches": [],
            "potential_keyword_matches": [],
        }

    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=config.hours)
    query = build_search_query(config.keywords, config.categories, cutoff, now)

    client = arxiv.Client(num_retries=3, delay_seconds=3)
    search = arxiv.Search(query=query, max_results=config.candidate_pool)

    exact_records: list[dict[str, object]] = []
    potential_records: list[dict[str, object]] = []
    for result in client.results(search):
        record = result_to_record(result, config, cutoff)
        if record:
            if record["match_type"] == "exact":
                exact_records.append(record)
            else:
                potential_records.append(record)
        if len(exact_records) + len(potential_records) >= config.candidate_pool:
            break

    return {
        "exact_keyword_matches": exact_records,
        "potential_keyword_matches": potential_records,
    }


def main() -> int:
    config = parse_args()
    try:
        records = collect_records(config)
    except (RuntimeError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 1

    json.dump(records, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
