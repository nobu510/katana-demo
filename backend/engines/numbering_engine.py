"""
採番ルールエンジン
全エンティティをIDで紐づけ、どこからでも横断追跡可能にする。

採番体系:
  企業:     C001, C002, ...
  案件:     P001-C001 (案件-企業)
  社員:     S001-C001 (社員-企業)
  取引:     T001-P001-C001 (取引-案件)
  仕訳:     J001-C001 (仕訳-企業)
  経費:     E001-C001 (経費-企業)
  売上:     SL001-C001 (売上-企業)
  見積:     Q001-C001 (見積-企業)
  請求:     IV001-C001 (請求-企業)
  勤怠:     AT001-S001-C001 (勤怠-社員)

pure function設計: カウンタ状態を受け取り、新IDとカウンタを返す。
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Sequence


# =====================================================================
# 採番プレフィックス定義
# =====================================================================

PREFIX_COMPANY = "C"
PREFIX_PROJECT = "P"
PREFIX_STAFF = "S"
PREFIX_TRANSACTION = "T"
PREFIX_JOURNAL = "J"
PREFIX_EXPENSE = "E"
PREFIX_SALES = "SL"
PREFIX_ESTIMATE = "Q"
PREFIX_INVOICE = "IV"
PREFIX_ATTENDANCE = "AT"

# 有効なプレフィックス一覧 (バリデーション用)
ALL_PREFIXES = frozenset({
    PREFIX_COMPANY, PREFIX_PROJECT, PREFIX_STAFF, PREFIX_TRANSACTION,
    PREFIX_JOURNAL, PREFIX_EXPENSE, PREFIX_SALES, PREFIX_ESTIMATE,
    PREFIX_INVOICE, PREFIX_ATTENDANCE,
})

# プレフィックス → 親のプレフィックス (バリデーション用)
PARENT_PREFIX_MAP: dict[str, str | None] = {
    PREFIX_COMPANY: None,          # ルート
    PREFIX_PROJECT: PREFIX_COMPANY,
    PREFIX_STAFF: PREFIX_COMPANY,
    PREFIX_TRANSACTION: PREFIX_PROJECT,
    PREFIX_JOURNAL: PREFIX_COMPANY,
    PREFIX_EXPENSE: PREFIX_COMPANY,
    PREFIX_SALES: PREFIX_COMPANY,
    PREFIX_ESTIMATE: PREFIX_COMPANY,
    PREFIX_INVOICE: PREFIX_COMPANY,
    PREFIX_ATTENDANCE: PREFIX_STAFF,
}

# 連番の上限桁数
SEQ_DIGITS = 3
SEQ_MAX = 10 ** SEQ_DIGITS - 1  # 999


# =====================================================================
# エラー型
# =====================================================================

class NumberingError(Exception):
    """採番エラー"""
    pass


# =====================================================================
# データ型
# =====================================================================

@dataclass
class NumberingState:
    """
    採番カウンタの状態。
    各キーは (prefix, parent_id) のタプルで、値は最後に発番した連番。
    """
    counters: dict[tuple[str, str], int] = field(default_factory=dict)


@dataclass
class NumberedId:
    """採番結果"""
    id: str            # 例: "P003-C001"
    prefix: str        # 例: "P"
    seq: int           # 例: 3
    parent_id: str     # 例: "C001" (なければ "")


# =====================================================================
# パースされたID
# =====================================================================

@dataclass
class ParsedId:
    """パースされたID"""
    raw: str
    prefix: str
    seq: int
    parent_id: str
    parent_prefix: str
    parent_seq: int


# IDパースの正規表現 (コンパイル済み)
_ID_RE = re.compile(r'^([A-Z]+)(\d{3,})(?:-(.+))?$')
_PREFIX_SEQ_RE = re.compile(r'^([A-Z]+)(\d{3,})')


def parse_id(id_str: str) -> ParsedId | None:
    """
    IDを解析して構造を返す。マルチキャラクタプレフィックス対応。

    >>> parse_id("AT003-S001-C002")
    ParsedId(raw='AT003-S001-C002', prefix='AT', seq=3, parent_id='S001-C002', ...)
    >>> parse_id("C001")
    ParsedId(raw='C001', prefix='C', seq=1, parent_id='', ...)
    """
    m = _ID_RE.match(id_str)
    if not m:
        return None

    prefix = m.group(1)
    seq = int(m.group(2))
    parent_id = m.group(3) or ""

    parent_prefix = ""
    parent_seq = 0
    if parent_id:
        pm = _PREFIX_SEQ_RE.match(parent_id)
        if pm:
            parent_prefix = pm.group(1)
            parent_seq = int(pm.group(2))

    return ParsedId(
        raw=id_str,
        prefix=prefix,
        seq=seq,
        parent_id=parent_id,
        parent_prefix=parent_prefix,
        parent_seq=parent_seq,
    )


# =====================================================================
# 内部ヘルパー
# =====================================================================

def _validate_parent(prefix: str, parent_id: str) -> None:
    """親IDのバリデーション"""
    expected_parent_prefix = PARENT_PREFIX_MAP.get(prefix)

    if expected_parent_prefix is None:
        # ルートエンティティ (C) は親IDなし
        if parent_id:
            raise NumberingError(f"{prefix}はルートエンティティです。parent_id は不要です")
        return

    if not parent_id:
        raise NumberingError(f"{prefix}には親ID (prefix={expected_parent_prefix}) が必要です")

    parsed = parse_id(parent_id)
    if not parsed:
        raise NumberingError(f"親ID '{parent_id}' のフォーマットが不正です")

    # 親IDの先頭プレフィックスが期待通りか
    if parsed.prefix != expected_parent_prefix:
        raise NumberingError(
            f"{prefix}の親は{expected_parent_prefix}ですが、{parsed.prefix}が渡されました"
        )


def _next_seq(state: NumberingState, prefix: str, parent_id: str) -> tuple[int, NumberingState]:
    """カウンタをインクリメントして新しいstateを返す"""
    key = (prefix, parent_id)
    current = state.counters.get(key, 0)
    next_val = current + 1
    if next_val > SEQ_MAX:
        raise NumberingError(
            f"{prefix}-{parent_id} の採番が上限 {SEQ_MAX} に達しました"
        )
    new_counters = {**state.counters, key: next_val}
    return next_val, NumberingState(counters=new_counters)


def _format_id(prefix: str, seq: int, parent_id: str = "") -> str:
    """IDフォーマット: P003-C001"""
    own = f"{prefix}{seq:0{SEQ_DIGITS}d}"
    if parent_id:
        return f"{own}-{parent_id}"
    return own


def _generate(
    state: NumberingState,
    prefix: str,
    parent_id: str,
) -> tuple[NumberedId, NumberingState]:
    """汎用採番関数 (バリデーション付き)"""
    _validate_parent(prefix, parent_id)
    seq, new_state = _next_seq(state, prefix, parent_id)
    id_str = _format_id(prefix, seq, parent_id)
    return NumberedId(id=id_str, prefix=prefix, seq=seq, parent_id=parent_id), new_state


# =====================================================================
# 採番関数 (公開API)
# =====================================================================

def generate_company_id(state: NumberingState) -> tuple[NumberedId, NumberingState]:
    """企業ID: C001, C002, ..."""
    return _generate(state, PREFIX_COMPANY, "")


def generate_project_id(state: NumberingState, company_id: str) -> tuple[NumberedId, NumberingState]:
    """案件/商品ID: P001-C001"""
    return _generate(state, PREFIX_PROJECT, company_id)


def generate_staff_id(state: NumberingState, company_id: str) -> tuple[NumberedId, NumberingState]:
    """社員ID: S001-C001"""
    return _generate(state, PREFIX_STAFF, company_id)


def generate_transaction_id(state: NumberingState, project_id: str) -> tuple[NumberedId, NumberingState]:
    """取引ID: T001-P001-C001 (取引-案件紐づけ)"""
    return _generate(state, PREFIX_TRANSACTION, project_id)


def generate_journal_id(state: NumberingState, company_id: str) -> tuple[NumberedId, NumberingState]:
    """仕訳ID: J001-C001"""
    return _generate(state, PREFIX_JOURNAL, company_id)


def generate_expense_id(state: NumberingState, company_id: str) -> tuple[NumberedId, NumberingState]:
    """経費ID: E001-C001"""
    return _generate(state, PREFIX_EXPENSE, company_id)


def generate_sales_id(state: NumberingState, company_id: str) -> tuple[NumberedId, NumberingState]:
    """売上ID: SL001-C001"""
    return _generate(state, PREFIX_SALES, company_id)


def generate_estimate_id(state: NumberingState, company_id: str) -> tuple[NumberedId, NumberingState]:
    """見積ID: Q001-C001"""
    return _generate(state, PREFIX_ESTIMATE, company_id)


def generate_invoice_id(state: NumberingState, company_id: str) -> tuple[NumberedId, NumberingState]:
    """請求ID: IV001-C001"""
    return _generate(state, PREFIX_INVOICE, company_id)


def generate_attendance_id(state: NumberingState, staff_id: str) -> tuple[NumberedId, NumberingState]:
    """勤怠ID: AT001-S001-C001 (勤怠-社員紐づけ)"""
    return _generate(state, PREFIX_ATTENDANCE, staff_id)


# =====================================================================
# 状態復元 (既存IDからカウンタを復元)
# =====================================================================

def rebuild_state(existing_ids: Sequence[str]) -> NumberingState:
    """
    既存のID一覧からNumberingStateを復元する。
    再起動後や永続化からの復帰時に使う。

    >>> ids = ["C001", "C002", "P001-C001", "P003-C001", "J001-C001"]
    >>> state = rebuild_state(ids)
    >>> # C: 2, P-C001: 3, J-C001: 1  ← 最大値がセットされる
    """
    counters: dict[tuple[str, str], int] = {}
    for id_str in existing_ids:
        parsed = parse_id(id_str)
        if not parsed:
            continue
        key = (parsed.prefix, parsed.parent_id)
        if parsed.seq > counters.get(key, 0):
            counters[key] = parsed.seq
    return NumberingState(counters=counters)


# =====================================================================
# バッチ採番
# =====================================================================

def generate_batch(
    state: NumberingState,
    generator_fn,
    parent_id: str,
    count: int,
) -> tuple[list[NumberedId], NumberingState]:
    """複数IDを一括採番"""
    ids: list[NumberedId] = []
    current_state = state
    for _ in range(count):
        nid, current_state = generator_fn(current_state, parent_id)
        ids.append(nid)
    return ids, current_state


# =====================================================================
# ID抽出 (任意の文字列から特定プレフィックスのIDを取り出す)
# =====================================================================

def extract_company_id(id_str: str) -> str | None:
    """任意のIDから企業IDを抽出"""
    m = re.search(r'(C\d{3})', id_str)
    return m.group(1) if m else None


def extract_project_id(id_str: str) -> str | None:
    """任意のIDから案件IDを抽出 (P001-C001形式)"""
    m = re.search(r'(P\d{3}-C\d{3})', id_str)
    return m.group(1) if m else None


def extract_staff_id(id_str: str) -> str | None:
    """任意のIDから社員IDを抽出 (S001-C001形式)"""
    m = re.search(r'(S\d{3}-C\d{3})', id_str)
    return m.group(1) if m else None


def extract_by_prefix(id_str: str, prefix: str) -> str | None:
    """任意のIDから指定プレフィックスの部分を抽出"""
    pattern = rf'({re.escape(prefix)}\d{{{SEQ_DIGITS}}}(?:-[A-Z]+\d{{{SEQ_DIGITS}}})*)'
    m = re.search(pattern, id_str)
    return m.group(1) if m else None


# =====================================================================
# 横断検索ヘルパー
# =====================================================================

def filter_by_company(ids: Sequence[str], company_id: str) -> list[str]:
    """企業IDでフィルタ"""
    return [i for i in ids if company_id in i]


def filter_by_project(ids: Sequence[str], project_id: str) -> list[str]:
    """案件IDでフィルタ"""
    return [i for i in ids if project_id in i]


def group_by_parent(ids: Sequence[str]) -> dict[str, list[str]]:
    """親IDでグルーピング"""
    groups: dict[str, list[str]] = {}
    for id_str in ids:
        parsed = parse_id(id_str)
        if parsed:
            parent = parsed.parent_id or "__root__"
            groups.setdefault(parent, []).append(id_str)
    return groups


def build_hierarchy(ids: Sequence[str]) -> dict[str, list[str]]:
    """
    全IDから親子関係ツリーを構築する。

    Returns: { parent_id: [child_id, ...] }
    企業C001 → 案件P001-C001, 社員S001-C001, ...
    案件P001-C001 → 取引T001-P001-C001, ...
    """
    tree: dict[str, list[str]] = {}
    for id_str in ids:
        parsed = parse_id(id_str)
        if not parsed:
            continue
        parent = parsed.parent_id or "__root__"
        tree.setdefault(parent, []).append(id_str)
    return tree


def trace_to_root(id_str: str) -> list[str]:
    """
    IDから企業ルートまでの経路を返す。
    "T001-P001-C001" → ["T001-P001-C001", "P001-C001", "C001"]
    """
    path = [id_str]
    parsed = parse_id(id_str)
    while parsed and parsed.parent_id:
        path.append(parsed.parent_id)
        parsed = parse_id(parsed.parent_id)
    return path
