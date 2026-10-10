"""单词卡：一个英文词/短语 → 自动补齐中文解释、例句等。

需求原话：

> 在英语科目中新增单词书栏目 书内部可以添加单词卡 单词卡可折叠
> 我只需要添加英文单词/短语 就可以自动补齐中文解释/例句等等
> 单词卡折叠后只显示英语 单击后展开

三件事：

1. **一张卡一个 json**（``wordbook/<英文>.json``）—— 方便单独改、
   单独拷给同学、直接进版本管理。与"磁盘即数据库"一致。
2. **用户只填英文**，其余字段由 AI 补齐（见 :func:`parse_completion`）。
3. 折叠/展开是界面的事，但**"折叠时显示什么"是数据的决定**：
   所以模型里显式提供 :attr:`WordCard.english` 作为唯一折叠标题。

这个模块**不依赖 Qt**，可以单独测试。
"""

from __future__ import annotations

import json
import logging
import re
import shutil
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

from gwp.core import constants as C
from gwp.data_manager import metadata as meta_io

log = logging.getLogger(__name__)

#: 文件名里不能出现的字符（与其它地方的 sanitize 保持一致：替换成下划线）
_ILLEGAL = r'[\\/:*?"<>|\r\n\t]'


def sanitize_english(text: str) -> str:
    """把用户输入的英文变成安全的文件名主干。

    只去掉**文件名非法字符**和首尾空白，**不改大小写、不删标点**：
    ``don't`` / ``give up`` / ``a.m.`` / ``well-known`` 都要原样保留 ——
    它们是词条本身，不是标识符。**不要在这里做"美化"**，
    否则 ``a.m.`` 会变成 ``a.m``，和词条就对不上了。
    """
    cleaned = re.sub(_ILLEGAL, "_", (text or "").strip())
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.strip()


def card_path(folder: Path, english: str) -> Path:
    """给定单词书目录与英文，算出卡片的 json 路径。"""
    return Path(folder) / f"{sanitize_english(english)}{C.WORD_CARD_SUFFIX}"


# --------------------------------------------------------------------------
# 卡片模型
# --------------------------------------------------------------------------

@dataclass
class WordCard:
    """一张单词卡。

    ``english`` 是**唯一必填字段**，也是折叠状态下显示的内容；
    其余都由 AI 补齐，但用户可以随时手改（手改过的字段不会被 AI 覆盖成空）。
    """

    english: str
    #: 音标，例如 /əˈbændən/
    phonetic: str = ""
    #: 词性，例如 n. / v. / adj.
    part_of_speech: str = ""
    #: 中文释义（可多行；一个词性一行）
    meaning: str = ""
    #: 例句（正文，每行一句，可含加粗的中文翻译）
    examples: str = ""
    #: 常见搭配 / 短语
    phrases: str = ""
    #: 记忆提示（词根词缀、联想）
    tip: str = ""
    #: 用户自己的笔记
    note: str = ""
    #: 元信息
    created_at: str = ""
    updated_at: str = ""
    #: 这一张是否已经由 AI 补齐过（用来在界面上区分"待补齐"）
    completed: bool = False
    #: 用户手动标记"这个词 AI 补得不对，别再自动覆盖"
    locked: bool = False

    @property
    def path(self) -> Path | None:
        return getattr(self, "_path", None)

    @property
    def has_details(self) -> bool:
        """除了英文之外有没有内容（决定展开后是不是一片空白）。"""
        return any((
            self.phonetic, self.part_of_speech, self.meaning,
            self.examples, self.phrases, self.tip, self.note,
        ))

    def to_dict(self) -> dict:
        data = asdict(self)
        data.pop("_path", None)
        return data

    @classmethod
    def from_dict(cls, data: dict, path: Path | None = None) -> "WordCard":
        """从 json 数据建卡片。**缺字段一律用默认值**（用户会手改文件）。"""
        english = str(data.get("english") or "").strip()
        if not english and path is not None:
            english = path.stem                 # 兜底：拿文件名当词条
        card = cls(
            english=english,
            phonetic=str(data.get("phonetic") or ""),
            part_of_speech=str(data.get("part_of_speech") or ""),
            meaning=str(data.get("meaning") or ""),
            examples=str(data.get("examples") or ""),
            phrases=str(data.get("phrases") or ""),
            tip=str(data.get("tip") or ""),
            note=str(data.get("note") or ""),
            created_at=str(data.get("created_at") or ""),
            updated_at=str(data.get("updated_at") or ""),
            completed=bool(data.get("completed")),
            locked=bool(data.get("locked")),
        )
        if path is not None:
            card._path = Path(path)             # type: ignore[attr-defined]
        return card


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%S")


# --------------------------------------------------------------------------
# 读写
# --------------------------------------------------------------------------

def load_card(path: Path) -> WordCard | None:
    """读一张卡。**读取永不抛异常**（与项目其它元数据读取一致）。

    这里**不用** ``meta_io.read_json``：它对损坏文件会返回一个空 dict，
    和"合法但内容为空的 json"就区分不开了 —— 那样一张读坏的卡会被
    当成"英文为空的卡"，然后在列表里冒出一个用文件名当词条的怪东西。
    所以这里自己读，解析失败就明确返回 ``None``。
    """
    target = Path(path)
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeDecodeError) as exc:
        log.warning("单词卡读不出来：%s (%s)", target, exc)
        return None
    if not isinstance(data, dict):
        return None
    return WordCard.from_dict(data, target)


def save_card(card: WordCard, folder: Path) -> Path:
    """把卡片写入单词书目录（原子写），返回落盘路径。"""
    directory = Path(folder)
    directory.mkdir(parents=True, exist_ok=True)
    target = card.path
    if target is None:
        target = card_path(directory, card.english)
    if not card.created_at:
        card.created_at = _now()
    card.updated_at = _now()
    if card.has_details:
        card.completed = True
    meta_io.write_json(target, card.to_dict())
    card._path = target                          # type: ignore[attr-defined]
    return target


def delete_card(path: Path) -> bool:
    """删除一张卡片。返回是否删掉了。"""
    try:
        Path(path).unlink()
        return True
    except OSError:
        log.warning("删除单词卡失败：%s", path, exc_info=True)
        return False


def list_cards(folder: Path, *, english_first: bool = True) -> list[WordCard]:
    """列出单词书目录里的全部卡片，按英文字母序（不区分大小写）。

    读不出来的文件会被跳过并记日志 —— 一个坏文件不该让整个单词书打不开。
    """
    directory = Path(folder)
    if not directory.is_dir():
        return []
    cards: list[WordCard] = []
    try:
        entries = sorted(
            directory.glob(f"*{C.WORD_CARD_SUFFIX}"), key=lambda p: p.name.lower()
        )
    except OSError:
        return []
    for entry in entries:
        if entry.name.startswith("."):
            continue
        card = load_card(entry)
        if card is None:
            log.warning("跳过读不出来的单词卡：%s", entry)
            continue
        # **校验它真的像一张单词卡**：json 合法但内容不是卡片
        # （例如用户手工丢进来的普通 json）时，不能把文件名当成词条 ——
        # 那会凭空多出一张没有释义的怪卡。
        if not str(card.english or "").strip():
            log.warning("跳过不像单词卡的 json：%s", entry)
            continue
        cards.append(card)
    if english_first:
        cards.sort(key=lambda c: c.english.lower())
    return cards


def find_card(folder: Path, english: str) -> WordCard | None:
    """按英文查一张卡（忽略大小写与首尾空白）。"""
    target = sanitize_english(english).lower()
    if not target:
        return None
    for card in list_cards(folder, english_first=False):
        if card.english.strip().lower() == target:
            return card
    return None


# --------------------------------------------------------------------------
# AI 补齐
# --------------------------------------------------------------------------

#: 让 AI 返回**严格 JSON** 的提示词。
#:
#: 为什么要 JSON 而不是 Markdown：这些字段要分别显示在卡片的不同位置
#: （音标、释义、例句…），结构化数据比分段文本好用得多，
#: 也让用户能单独改某一栏而不影响其它栏。
WORD_COMPLETE_PROMPT = """你是一位英语词典编辑。请为下面这个词/短语给出学习卡片所需的信息。

词/短语：{word}

请**只输出一个 JSON 对象**，不要输出任何解释文字，不要用 ``` 包裹。字段如下：

{{
  "english": "词/短语本身（保持原样）",
  "phonetic": "英式或美式音标，用 /.../ 包裹；短语没有音标就留空字符串",
  "part_of_speech": "词性，如 n. / v. / adj. / phr.，多个用 / 分隔",
  "meaning": "中文释义。有多个词性时每个词性单独一行，行首写词性。要准确、简洁",
  "examples": "2~3 个例句。每行一句，格式：英文句子 —— 中文翻译",
  "phrases": "2~4 个常用搭配或短语，每行一个，格式：短语 —— 中文",
  "tip": "一句话记忆提示（词根词缀或联想）；没有就留空字符串"
}}

要求：
1. 释义必须准确，**不确定时宁可少写也不要猜**；确实是生僻/不存在的词，
   在 meaning 里写「未查到该词，请确认拼写」。
2. 例句要地道、简单，适合学习者。
3. 全部用中文写解释部分，英文部分保持英文。
"""


def build_prompt(english: str) -> str:
    return WORD_COMPLETE_PROMPT.format(word=english.strip())


def extract_json(text: str) -> dict | None:
    """从 AI 的回答里**尽量**抠出一个 JSON 对象。

    模型经常会这样回：`````json {...} ``` ``、或者前面加一句"好的，这是结果："。
    这些都不该让功能失败，所以按优先级尝试三种方式：

    1. 去掉 ``` 围栏后整体解析；
    2. 正则找第一个 ``{...}`` 片段解析；
    3. 逐行扫描累积括号配对（对付多层嵌套 + 前后有杂文字的情况）。

    全部失败返回 ``None``，由调用方提示用户手动填写 ——
    **绝不猜内容**。
    """
    raw = (text or "").strip()
    if not raw:
        return None

    # 1) 去掉代码围栏
    fenced = re.sub(r"^\s*```[a-zA-Z]*\s*", "", raw)
    fenced = re.sub(r"\s*```\s*$", "", fenced).strip()
    for candidate in (fenced, raw):
        try:
            data = json.loads(candidate)
            if isinstance(data, dict):
                return data
        except (ValueError, TypeError):
            pass

    # 2) 第一个 { ... } 片段
    match = re.search(r"\{.*\}", fenced if fenced else raw, re.DOTALL)
    if match:
        try:
            data = json.loads(match.group(0))
            if isinstance(data, dict):
                return data
        except (ValueError, TypeError):
            pass

    # 3) 括号配对扫描（容忍前面有"好的，这是结果："之类的杂文字）
    start = raw.find("{")
    if start >= 0:
        depth = 0
        in_string = False
        escaped = False
        for index in range(start, len(raw)):
            char = raw[index]
            if in_string:
                if escaped:
                    escaped = False
                elif char == "\\":
                    escaped = True
                elif char == '"':
                    in_string = False
                continue
            if char == '"':
                in_string = True
            elif char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    try:
                        data = json.loads(raw[start:index + 1])
                        if isinstance(data, dict):
                            return data
                    except (ValueError, TypeError):
                        break
    return None


#: AI 明说查不到词时的标志（这种情况下不该把卡片标成"已补齐"）
_NOT_FOUND_MARKERS = ("未查到该词", "请确认拼写", "无法确认", "not found")


def parse_completion(text: str, english: str) -> tuple[WordCard | None, str]:
    """把 AI 的回答解析成卡片。返回 ``(卡片, 错误说明)``。

    成功时错误说明为空串。失败时**不编内容**，只给出可操作的原因。
    """
    data = extract_json(text)
    if data is None:
        return None, "没能从 AI 的回答里解析出内容（可能它没有按 JSON 格式回答）"

    card = WordCard.from_dict(data)
    if not card.english.strip():
        card.english = english.strip()
    meaning = card.meaning.strip()
    if any(marker in meaning for marker in _NOT_FOUND_MARKERS):
        return card, "AI 说查不到这个词，请确认拼写后再试"
    if not meaning:
        return card, "AI 没有给出中文释义"
    card.completed = True
    return card, ""


def merge_into(existing: WordCard, fresh: WordCard, *, force: bool = False) -> WordCard:
    """把 AI 的新结果合并进已有卡片。

    **默认只填空白字段**（``force=False``）：用户手改过的内容不能被
    重新补齐悄悄冲掉。要看新结果得显式 ``force=True``。
    ``english`` / ``note`` / ``locked`` 永远保留用户这边的值。
    """
    if existing.locked and not force:
        return existing
    for name in ("phonetic", "part_of_speech", "meaning", "examples",
                 "phrases", "tip"):
        current = getattr(existing, name, "")
        incoming = getattr(fresh, name, "")
        if force or not str(current or "").strip():
            setattr(existing, name, incoming)
    existing.completed = True
    return existing


def summarize(cards: list[WordCard]) -> str:
    """给状态栏用的一句话统计。"""
    if not cards:
        return "单词书是空的，点「添加单词」开始"
    pending = sum(1 for c in cards if not c.completed)
    text = f"共 {len(cards)} 张单词卡"
    if pending:
        text += f"，{pending} 张待补齐解释"
    return text


# --------------------------------------------------------------------------
# 旧布局迁移
# --------------------------------------------------------------------------

def find_legacy_wordbooks(subjects_dir: Path) -> list[Path]:
    """找出旧布局留下的"每本书一个"单词书目录。

    旧布局是 ``<科目>/<书目>/wordbook/``；新布局是全局一个
    ``<user data>/wordbook/``。为了不丢用户的卡片，启动时会把旧目录里的
    json **移动**过来（见 :func:`migrate_legacy_wordbooks`）。
    """
    root = Path(subjects_dir)
    if not root.is_dir():
        return []
    found: list[Path] = []
    try:
        for subject in root.iterdir():
            if not subject.is_dir():
                continue
            for book in subject.iterdir():
                if not book.is_dir():
                    continue
                candidate = book / C.WORDBOOK_LEGACY_FOLDER
                if candidate.is_dir() and any(
                    candidate.glob(f"*{C.WORD_CARD_SUFFIX}")
                ):
                    found.append(candidate)
    except OSError:
        log.debug("扫描旧单词书目录失败：%s", root, exc_info=True)
    return sorted(found)


def migrate_legacy_wordbooks(target_dir: Path, subjects_dir: Path) -> dict:
    """把旧布局的单词卡**移动**到全局单词书。返回一份迁移报告。

    报告形如 ``{"moved": [...], "kept": [...], "removed_dirs": [...], "failed": [...]}``。

    三条原则：

    1. **绝不覆盖**：目标已存在同名卡时，把新来的改名为
       ``<名字> (来自<科目>-<书目>).json`` 保留下来 ——
       两张卡都有价值，"谁赢"不该由我们决定。
    2. **移动而不是复制**：成功后删掉旧目录，避免留下两份让人困惑
       （"我改了这张卡怎么没生效"通常是改到了另一份上）。
    3. **失败就留着**：移动不了的（占用、权限）原样留在旧目录，只记日志。
       宁可留着旧数据，也不要"为了干净"把它删掉。
    """
    target = Path(target_dir)
    report: dict = {"moved": [], "kept": [], "removed_dirs": [], "failed": []}
    legacy_dirs = find_legacy_wordbooks(subjects_dir)
    if not legacy_dirs:
        return report

    try:
        target.mkdir(parents=True, exist_ok=True)
    except OSError:
        log.warning("无法创建单词书目录，跳过迁移：%s", target, exc_info=True)
        report["failed"] = [str(p) for p in legacy_dirs]
        return report

    for legacy in legacy_dirs:
        # 用"科目-书目"给冲突的卡起个能认出来的名字
        origin = f"{legacy.parent.parent.name}-{legacy.parent.name}"
        for source in sorted(legacy.glob(f"*{C.WORD_CARD_SUFFIX}")):
            destination = target / source.name
            if destination.exists():
                stem = source.stem
                destination = target / f"{stem} (来自{origin}){source.suffix}"
                suffix_index = 2
                while destination.exists():
                    destination = target / (
                        f"{stem} (来自{origin} {suffix_index}){source.suffix}"
                    )
                    suffix_index += 1
                report["kept"].append(str(destination))
            try:
                shutil.move(str(source), str(destination))
                report["moved"].append(str(destination))
            except (OSError, shutil.Error):
                log.warning("迁移单词卡失败：%s", source, exc_info=True)
                report["failed"].append(str(source))
        # 卡片都搬走了、目录空了，才把旧目录删掉
        try:
            if legacy.is_dir() and not any(legacy.iterdir()):
                legacy.rmdir()
                report["removed_dirs"].append(str(legacy))
        except OSError:
            log.debug("删除空的旧单词书目录失败：%s", legacy, exc_info=True)
    if report["moved"]:
        log.info("已把 %s 张旧单词卡迁移到共用单词书：%s",
                 len(report["moved"]), target)
    return report


__all__ = [
    "WORD_COMPLETE_PROMPT",
    "WordCard",
    "build_prompt",
    "card_path",
    "delete_card",
    "extract_json",
    "find_card",
    "find_legacy_wordbooks",
    "list_cards",
    "load_card",
    "merge_into",
    "migrate_legacy_wordbooks",
    "parse_completion",
    "sanitize_english",
    "save_card",
    "summarize",
]
