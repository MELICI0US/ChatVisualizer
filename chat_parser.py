from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional
from urllib.parse import unquote

ROUND_PATTERN = re.compile(r"\bround\s+(\d+)\b", re.IGNORECASE)


@dataclass
class Message:
    body: str
    sender: Optional[str]
    runtime_type: str
    time: datetime
    round_number: Optional[int] = None


@dataclass
class Conversation:
    conversation_id: str
    name: str
    participants: list[str]
    messages: list[Message]
    created_at: Optional[datetime]
    last_active_at: Optional[datetime]
    player_message_count: int
    created_round: Optional[int]
    last_active_round: Optional[int]
    creator: Optional[str] = None
    reason: str = ""


def _parse_time(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _extract_round(body: str) -> Optional[int]:
    match = ROUND_PATTERN.search(body or "")
    if not match:
        return None
    return int(match.group(1))


def _latest_round_at(time: Optional[datetime], timeline: list[tuple[datetime, int]]) -> Optional[int]:
    if time is None:
        return None

    latest = None
    for event_time, round_number in timeline:
        if event_time <= time:
            latest = round_number
        else:
            break
    return latest


def _first_available(record: dict, keys: list[str], default=None):
    for key in keys:
        if key in record and record[key] is not None:
            return record[key]
    return default


def reasons_path_for(json_path: str | Path) -> Path:
    path = Path(json_path)
    return path.with_name(f"{path.stem}.reasons.json")


def load_reasons(reasons_path: str | Path) -> dict[str, str]:
    path = Path(reasons_path)
    if not path.exists():
        return {}

    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    reasons = data.get("reasons", data) if isinstance(data, dict) else None
    if not isinstance(reasons, dict):
        raise ValueError("The reasons file must contain a JSON object of conversation reasons.")
    return {str(conversation_id): str(reason) for conversation_id, reason in reasons.items()}


def save_reasons(reasons_path: str | Path, reasons: dict[str, str]) -> None:
    path = Path(reasons_path)
    with path.open("w", encoding="utf-8") as f:
        json.dump({"reasons": reasons}, f, indent=2, ensure_ascii=False)
        f.write("\n")


def load_common_reasons(common_reasons_path: str | Path) -> list[str]:
    path = Path(common_reasons_path)
    if not path.exists():
        return []

    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    reasons = data.get("reasons", data) if isinstance(data, dict) else data
    if not isinstance(reasons, list) or not all(isinstance(reason, str) for reason in reasons):
        raise ValueError("The common reasons file must contain a JSON list of strings.")
    return reasons


def save_common_reasons(common_reasons_path: str | Path, reasons: list[str]) -> None:
    path = Path(common_reasons_path)
    with path.open("w", encoding="utf-8") as f:
        json.dump({"reasons": reasons}, f, indent=2, ensure_ascii=False)
        f.write("\n")


def load_conversations(
    json_path: str | Path,
    reasons_path: str | Path | None = None,
) -> list[Conversation]:
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    reasons = load_reasons(reasons_path or reasons_path_for(json_path))
    raw_conversations = data.get("conversations") or data.get("chatGroups") or {}
    conversations: list[Conversation] = []

    for conversation_id, raw_conversation in raw_conversations.items():
        raw_messages = _first_available(raw_conversation, ["messages", "chatMessages"], {}) or {}
        messages: list[Message] = []
        for raw_message in raw_messages.values():
            message_time = _parse_time(_first_available(raw_message, ["time", "timestamp", "createdAt"]))
            if message_time is None:
                continue

            messages.append(
                Message(
                    body=str(_first_available(raw_message, ["body", "text", "message"], "")),
                    sender=_first_available(raw_message, ["from", "sender", "author"]),
                    runtime_type=str(_first_available(raw_message, ["runtimeType", "type"], "identified")),
                    time=message_time,
                )
            )

        messages.sort(key=lambda item: item.time)
        participants = [unquote(str(player)) for player in _first_available(raw_conversation, ["participants", "members"], [])]
        name = str(_first_available(raw_conversation, ["name", "title"], conversation_id))
        player_messages = [message for message in messages if message.runtime_type != "gameNotification"]

        conversations.append(
            Conversation(
                conversation_id=conversation_id,
                name=name,
                participants=participants,
                creator=participants[0] if participants else None,
                messages=messages,
                created_at=messages[0].time if messages else None,
                last_active_at=player_messages[-1].time if player_messages else None,
                player_message_count=len(player_messages),
                created_round=None,
                last_active_round=None,
                reason=reasons.get(conversation_id, ""),
            )
        )

    round_timeline: list[tuple[datetime, int]] = []
    for conversation in conversations:
        for message in conversation.messages:
            if message.runtime_type == "gameNotification":
                round_number = _extract_round(message.body)
                if round_number is not None:
                    round_timeline.append((message.time, round_number))

    round_timeline.sort(key=lambda item: item[0])

    for conversation in conversations:
        for message in conversation.messages:
            message.round_number = _latest_round_at(message.time, round_timeline)
        if conversation.created_at:
            conversation.created_round = _latest_round_at(conversation.created_at, round_timeline)
        if conversation.last_active_at:
            conversation.last_active_round = _latest_round_at(conversation.last_active_at, round_timeline)

    conversations.sort(key=lambda item: (item.created_at or datetime.min.replace(tzinfo=None), item.name.lower()))
    return conversations
