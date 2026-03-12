"""
社内コミュニケーションエンジン
LINEのようなシンプルチャット + 業務報告の自動連携。

チャットで「A案件5時間」→ 勤怠 → 工数 → 原価 → 利益 → 会計が全自動。

PC・SaaSを知らない人でも使える超シンプル設計。
全関数はpure Python、DB非依存。
"""
from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Sequence


# =====================================================================
# データ型
# =====================================================================

class MessageType(str, Enum):
    """メッセージ種別"""
    TEXT = "text"
    IMAGE = "image"
    FILE = "file"
    STAMP = "stamp"
    SYSTEM = "system"
    WORK_REPORT = "work_report"    # 業務報告 (自動検出)


class ChatType(str, Enum):
    """チャット種別"""
    DIRECT = "個人"
    GROUP = "グループ"


@dataclass
class ChatMessage:
    """チャットメッセージ"""
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    chat_id: str = ""
    sender_id: str = ""        # S001-C001
    sender_name: str = ""
    message_type: MessageType = MessageType.TEXT
    content: str = ""
    file_url: str = ""         # 画像/PDFのパス
    file_name: str = ""
    stamp_id: str = ""         # スタンプID
    timestamp: datetime = field(default_factory=datetime.now)
    read_by: list[str] = field(default_factory=list)   # 既読者のstaff_id
    # 業務報告自動検出
    detected_work: list[dict] = field(default_factory=list)  # [{project, hours}, ...]
    detected_expense: dict | None = None  # {category, amount}
    detected_attendance: str = ""  # "出勤" / "退勤" / ""


@dataclass
class ChatRoom:
    """チャットルーム"""
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    name: str = ""
    chat_type: ChatType = ChatType.GROUP
    members: list[str] = field(default_factory=list)   # staff_ids
    created_at: datetime = field(default_factory=datetime.now)
    messages: list[ChatMessage] = field(default_factory=list)


# =====================================================================
# スタンプ定義
# =====================================================================

STAMPS: dict[str, str] = {
    "ok": "了解",
    "thanks": "ありがとう",
    "good": "いいね",
    "sorry": "すみません",
    "thinking": "考え中",
    "done": "完了",
    "help": "助けて",
    "celebrate": "おめでとう",
    "fire": "がんばろう",
    "bow": "お疲れ様",
}


# =====================================================================
# 業務報告パーサー
# =====================================================================

@dataclass
class ParsedWorkReport:
    """パースされた業務報告"""
    project_entries: list[dict]   # [{project_name, hours, description}]
    attendance: str               # "出勤" / "退勤" / ""
    expense: dict | None          # {category, amount} or None
    is_work_report: bool


def parse_chat_message(text: str) -> ParsedWorkReport:
    """
    チャットメッセージを解析し、業務報告要素を自動検出。

    検出パターン:
      - 「出勤」「おはよう」→ 出勤
      - 「退勤」「お疲れ」「帰ります」→ 退勤
      - 「A案件5時間」「B 3h」→ 工数報告
      - 「タクシー 2000円」「交通費 500円」→ 経費
    """
    attendance = ""
    # 出勤検出
    if re.search(r'(出勤|おはよう|始めます|出社)', text):
        attendance = "出勤"
    elif re.search(r'(退勤|お疲れ|帰り|終わり|退社)', text):
        attendance = "退勤"

    # 工数検出
    project_entries: list[dict] = []
    # パターン1: 案件名 + 時間
    for m in re.finditer(r'([^\s\d,、。]+?)\s*(\d+(?:\.\d+)?)\s*[時h]間?', text):
        name = m.group(1).rstrip("案件の")
        project_entries.append({
            "project_name": name,
            "hours": float(m.group(2)),
            "description": "",
        })

    # パターン2: 「案件名 作業内容 N時間」
    for m in re.finditer(r'[「【](.+?)[」】]\s*(.+?)\s+(\d+(?:\.\d+)?)\s*[時h]間?', text):
        project_entries.append({
            "project_name": m.group(1),
            "hours": float(m.group(3)),
            "description": m.group(2),
        })

    # 経費検出
    expense = None
    expense_patterns = [
        (r'(タクシー|交通費|電車|バス)', "旅費交通費"),
        (r'(昼食|ランチ|夕食|飲食)', "会議費"),
        (r'(文房具|消耗品|コピー)', "消耗品費"),
        (r'(切手|郵便|宅配)', "通信費"),
    ]
    amount_match = re.search(r'(\d{1,3}(?:,\d{3})*|\d+)\s*円', text)
    if amount_match:
        amount = int(amount_match.group(1).replace(",", ""))
        for pattern, category in expense_patterns:
            if re.search(pattern, text):
                expense = {"category": category, "amount": amount}
                break

    is_work = bool(attendance or project_entries or expense)

    return ParsedWorkReport(
        project_entries=project_entries,
        attendance=attendance,
        expense=expense,
        is_work_report=is_work,
    )


# =====================================================================
# チャットエンジン
# =====================================================================

class ChatEngine:
    """
    社内チャットエンジン。
    送信するだけで業務報告が自動検出され、勤怠・工数・経費に連携。
    """

    # ----- チャットルーム管理 -----

    @staticmethod
    def create_room(
        name: str,
        members: list[str],
        chat_type: ChatType = ChatType.GROUP,
    ) -> ChatRoom:
        """チャットルームを作成"""
        return ChatRoom(
            name=name,
            chat_type=chat_type,
            members=members,
        )

    @staticmethod
    def create_direct(member1: str, member2: str) -> ChatRoom:
        """1:1チャットを作成"""
        return ChatRoom(
            name=f"{member1}_{member2}",
            chat_type=ChatType.DIRECT,
            members=[member1, member2],
        )

    # ----- メッセージ送信 -----

    @staticmethod
    def send_message(
        room: ChatRoom,
        sender_id: str,
        sender_name: str,
        content: str,
    ) -> ChatMessage:
        """テキストメッセージを送信（業務報告自動検出付き）"""
        # 業務報告をパース
        parsed = parse_chat_message(content)

        msg_type = MessageType.WORK_REPORT if parsed.is_work_report else MessageType.TEXT

        msg = ChatMessage(
            chat_id=room.id,
            sender_id=sender_id,
            sender_name=sender_name,
            message_type=msg_type,
            content=content,
            read_by=[sender_id],
            detected_work=parsed.project_entries,
            detected_expense=parsed.expense,
            detected_attendance=parsed.attendance,
        )
        room.messages.append(msg)
        return msg

    @staticmethod
    def send_image(
        room: ChatRoom,
        sender_id: str,
        sender_name: str,
        file_url: str,
        file_name: str = "",
        caption: str = "",
    ) -> ChatMessage:
        """画像を送信"""
        msg = ChatMessage(
            chat_id=room.id,
            sender_id=sender_id,
            sender_name=sender_name,
            message_type=MessageType.IMAGE,
            content=caption,
            file_url=file_url,
            file_name=file_name or file_url.split("/")[-1],
            read_by=[sender_id],
        )
        room.messages.append(msg)
        return msg

    @staticmethod
    def send_file(
        room: ChatRoom,
        sender_id: str,
        sender_name: str,
        file_url: str,
        file_name: str = "",
    ) -> ChatMessage:
        """ファイルを送信"""
        msg = ChatMessage(
            chat_id=room.id,
            sender_id=sender_id,
            sender_name=sender_name,
            message_type=MessageType.FILE,
            file_url=file_url,
            file_name=file_name or file_url.split("/")[-1],
            read_by=[sender_id],
        )
        room.messages.append(msg)
        return msg

    @staticmethod
    def send_stamp(
        room: ChatRoom,
        sender_id: str,
        sender_name: str,
        stamp_id: str,
    ) -> ChatMessage:
        """スタンプを送信"""
        msg = ChatMessage(
            chat_id=room.id,
            sender_id=sender_id,
            sender_name=sender_name,
            message_type=MessageType.STAMP,
            stamp_id=stamp_id,
            content=STAMPS.get(stamp_id, stamp_id),
            read_by=[sender_id],
        )
        room.messages.append(msg)
        return msg

    # ----- 既読管理 -----

    @staticmethod
    def mark_as_read(message: ChatMessage, reader_id: str) -> None:
        """既読にする"""
        if reader_id not in message.read_by:
            message.read_by.append(reader_id)

    @staticmethod
    def mark_room_as_read(room: ChatRoom, reader_id: str) -> int:
        """ルーム内の全メッセージを既読にする。既読にした件数を返す。"""
        count = 0
        for msg in room.messages:
            if reader_id not in msg.read_by:
                msg.read_by.append(reader_id)
                count += 1
        return count

    @staticmethod
    def unread_count(room: ChatRoom, user_id: str) -> int:
        """未読メッセージ数"""
        return sum(1 for msg in room.messages if user_id not in msg.read_by)

    # ----- メッセージ取得 -----

    @staticmethod
    def get_messages(
        room: ChatRoom,
        limit: int = 50,
        before: datetime | None = None,
    ) -> list[ChatMessage]:
        """メッセージ取得 (新しい順)"""
        msgs = room.messages
        if before:
            msgs = [m for m in msgs if m.timestamp < before]
        return sorted(msgs, key=lambda m: m.timestamp, reverse=True)[:limit]

    @staticmethod
    def search_messages(
        room: ChatRoom,
        keyword: str,
    ) -> list[ChatMessage]:
        """メッセージ検索"""
        return [m for m in room.messages if keyword in m.content]

    # ----- 業務報告の集約 -----

    @staticmethod
    def extract_work_reports(
        room: ChatRoom,
        sender_id: str | None = None,
    ) -> list[ChatMessage]:
        """業務報告メッセージだけを抽出"""
        msgs = room.messages
        if sender_id:
            msgs = [m for m in msgs if m.sender_id == sender_id]
        return [m for m in msgs if m.message_type == MessageType.WORK_REPORT]

    @staticmethod
    def aggregate_daily_hours(
        messages: Sequence[ChatMessage],
        target_date: str | None = None,
    ) -> list[dict]:
        """
        業務報告メッセージから日別工数を集約。
        勤怠エンジン / 工数管理への入力データとして使う。
        """
        entries: list[dict] = []
        for msg in messages:
            if msg.message_type != MessageType.WORK_REPORT:
                continue
            if target_date and msg.timestamp.date().isoformat() != target_date:
                continue
            for work in msg.detected_work:
                entries.append({
                    "sender_id": msg.sender_id,
                    "sender_name": msg.sender_name,
                    "date": msg.timestamp.date().isoformat(),
                    "project_name": work.get("project_name", ""),
                    "hours": work.get("hours", 0),
                    "description": work.get("description", ""),
                    "message_id": msg.id,
                })
        return entries

    @staticmethod
    def aggregate_expenses(
        messages: Sequence[ChatMessage],
    ) -> list[dict]:
        """業務報告メッセージから経費を集約"""
        expenses: list[dict] = []
        for msg in messages:
            if msg.detected_expense:
                expenses.append({
                    "sender_id": msg.sender_id,
                    "sender_name": msg.sender_name,
                    "date": msg.timestamp.date().isoformat(),
                    "category": msg.detected_expense["category"],
                    "amount": msg.detected_expense["amount"],
                    "message_id": msg.id,
                })
        return expenses
