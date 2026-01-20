from __future__ import annotations

import datetime
import hashlib
import json
from typing import Any, Dict, List, Optional, Tuple

from app.core.database import memories_collection, story_collection
from app.questions.questions import QUESTION_BANK
from app.services.narrative_engine import narrative_engine


def _normalize_category(category: str) -> str:
    return (category or "").strip().lower()


def _stable_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


async def _get_category_source_fingerprint(user_id: str, session_id: str, category: str) -> str:
    """Fingerprint underlying source memories for a (user, session, category).

    This is used to decide whether a cached chapter is still valid.
    """
    category_norm = _normalize_category(category)

    cursor = memories_collection.find(
        {"user_id": user_id, "session_id": session_id, "category": category_norm},
        {
            "question": 1,
            "response": 1,
            "photos": 1,
            "photo_caption": 1,
        },
    )

    # Sort for stability across calls.
    cursor = cursor.sort([("question", 1), ("response", 1), ("_id", 1)])
    docs: List[Dict[str, Any]] = await cursor.to_list(None)

    hasher = hashlib.sha256()
    hasher.update(user_id.encode("utf-8"))
    hasher.update(b"|")
    hasher.update(session_id.encode("utf-8"))
    hasher.update(b"|")
    hasher.update(category_norm.encode("utf-8"))

    for doc in docs:
        payload = {
            "question": doc.get("question") or "",
            "response": doc.get("response") or "",
            "photos": doc.get("photos") or [],
            "photo_caption": doc.get("photo_caption") or "",
        }
        hasher.update(b"\n")
        hasher.update(_stable_json(payload).encode("utf-8"))

    return hasher.hexdigest()


async def _get_session_source_fingerprint(user_id: str, session_id: str) -> str:
    """Fingerprint underlying source memories for a (user, session) across all categories.

    Intentionally ignores timestamps so "same content" stays the same across calls.
    """
    cursor = memories_collection.find(
        {"user_id": user_id, "session_id": session_id},
        {
            "category": 1,
            "question": 1,
            "response": 1,
            "photos": 1,
            "photo_caption": 1,
        },
    )

    # Sort for stability across calls.
    cursor = cursor.sort([("category", 1), ("question", 1), ("response", 1), ("_id", 1)])
    docs: List[Dict[str, Any]] = await cursor.to_list(None)

    hasher = hashlib.sha256()
    hasher.update(user_id.encode("utf-8"))
    hasher.update(b"|")
    hasher.update(session_id.encode("utf-8"))

    for doc in docs:
        payload = {
            "category": _normalize_category(doc.get("category") or ""),
            "question": doc.get("question") or "",
            "response": doc.get("response") or "",
            "photos": doc.get("photos") or [],
            "photo_caption": doc.get("photo_caption") or "",
        }
        hasher.update(b"\n")
        hasher.update(_stable_json(payload).encode("utf-8"))

    return hasher.hexdigest()


async def get_or_generate_chapter(
    *,
    user_id: str,
    session_id: str,
    category: str,
    style: str,
) -> Tuple[str, bool, str]:
    """Return chapter text with cache.

    Returns: (chapter_text, from_cache, source_fingerprint)

    Cache key: user_id + session_id + normalized category + style
    Cache validity: cached.source_fingerprint must match current fingerprint
    """
    category_norm = _normalize_category(category)
    source_fingerprint = await _get_category_source_fingerprint(user_id, session_id, category_norm)

    existing: Optional[Dict[str, Any]] = None
    existing = await story_collection.find_one(
        {
            "user_id": user_id,
            "session_id": session_id,
            "category": category_norm,
            "style": style,
        }
    )

    if existing and existing.get("source_fingerprint") == source_fingerprint and existing.get("chapter"):
        return existing["chapter"], True, source_fingerprint

    chapter = await narrative_engine.generate_chapter(user_id, session_id, category_norm, style)

    # Match the route behavior: do not persist error-ish generations.
    if chapter.startswith("No ") or chapter.startswith("Error"):
        return chapter, False, source_fingerprint

    # Keep the route behavior: error-ish strings are returned to caller to decide HTTP status.
    now_iso = datetime.datetime.now().isoformat()

    await story_collection.update_one(
        {
            "user_id": user_id,
            "session_id": session_id,
            "category": category_norm,
            "style": style,
        },
        {
            "$set": {
                "user_id": user_id,
                "session_id": session_id,
                "category": category_norm,
                "style": style,
                "chapter": chapter,
                "source_fingerprint": source_fingerprint,
                "updated_at": now_iso,
            }
        },
        upsert=True,
    )

    return chapter, False, source_fingerprint


async def get_or_generate_full_story(
    *,
    user_id: str,
    session_id: str,
    style: str,
) -> Tuple[str, bool, str]:
    """Return full story text with cache.

    Cache key: user_id + session_id + style + category="__full__"
    Cache validity: cached.source_fingerprint must match current session fingerprint
    """
    source_fingerprint = await _get_session_source_fingerprint(user_id, session_id)

    existing: Optional[Dict[str, Any]] = await story_collection.find_one(
        {
            "user_id": user_id,
            "session_id": session_id,
            "category": "__full__",
            "style": style,
        }
    )

    if existing and existing.get("source_fingerprint") == source_fingerprint and existing.get("story"):
        return existing["story"], True, source_fingerprint

    categories_raw: List[str] = await memories_collection.distinct(
        "category",
        {"user_id": user_id, "session_id": session_id},
    )
    categories = [_normalize_category(c) for c in categories_raw if c]
    categories_set = set(categories)

    if not categories_set:
        return "No memories found for this session.", False, source_fingerprint

    # Deterministic ordering: QUESTION_BANK order first, then any extras alphabetically.
    ordered_categories: List[str] = [c for c in QUESTION_BANK.keys() if _normalize_category(c) in categories_set]
    extras = sorted([c for c in categories_set if c not in {_normalize_category(k) for k in QUESTION_BANK.keys()}])
    ordered_categories.extend(extras)

    chapters: Dict[str, str] = {}
    for category in ordered_categories:
        chapter, _from_cache, _cat_fp = await get_or_generate_chapter(
            user_id=user_id,
            session_id=session_id,
            category=category,
            style=style,
        )
        if not chapter.startswith("No ") and not chapter.startswith("Error"):
            chapters[category] = chapter

    if not chapters:
        return "No chapters found", False, source_fingerprint

    story_text = await narrative_engine.combine_chapters_with_transitions(chapters, style)
    if not story_text or story_text.startswith("No ") or story_text.startswith("Error"):
        return story_text or "No story content available.", False, source_fingerprint

    now_iso = datetime.datetime.now().isoformat()
    await story_collection.update_one(
        {
            "user_id": user_id,
            "session_id": session_id,
            "category": "__full__",
            "style": style,
        },
        {
            "$set": {
                "user_id": user_id,
                "session_id": session_id,
                "category": "__full__",
                "style": style,
                "story": story_text,
                "source_fingerprint": source_fingerprint,
                "updated_at": now_iso,
            }
        },
        upsert=True,
    )

    return story_text, False, source_fingerprint


def deterministic_full_story(chapters_dict: Dict[str, str]) -> str:
    """Combine chapters without changing their content.

    This intentionally does NOT call an LLM so the chapter text stays identical
    to what /chapter returns.
    """
    if not chapters_dict:
        return "No story content available."

    parts: List[str] = []
    for category, chapter in chapters_dict.items():
        title = (category or "").replace("_", " ").title()
        parts.append(f"{title}:\n{chapter}")

    return "\n\n".join(parts).strip()
