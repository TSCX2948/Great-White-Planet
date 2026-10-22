"""配置系统。

配置全部来自 JSON，代码只提供**默认值**；用户改动 ``else data/config.json``
即可调整行为，无需修改任何 Python 代码。

    config.json   可读可改：路径、界面、AI 提供方与模型、提示词、总结参数……
    secrets.json  只存密钥：API Key 等敏感信息，与 config.json 分离

取值方式::

    cfg = Config.load()
    cfg.get("ui.theme")             # 点号路径，缺失返回 None
    cfg.get("summary.chunk_chars", 20000)
    cfg.section("ai")               # 取整个 dict（副本）
"""

from __future__ import annotations

import copy
import json
import logging
import os
import threading
from pathlib import Path
from typing import Any

from gwp.core import constants as C

log = logging.getLogger(__name__)

CONFIG_VERSION = 1

# --------------------------------------------------------------------------
# 默认配置（唯一来源；新增配置项只需加在这里）
# --------------------------------------------------------------------------

DEFAULT_CONFIG: dict[str, Any] = {
    "config_version": CONFIG_VERSION,
    "app": {
        "name": "Great White Planet",
        "language": "zh_CN",
        "check_updates_on_start": False,
    },
    # 路径：留空表示按 paths.py 的规则推导
    "paths": {
        "data_root": "",              # 例如 "D:/Great White Planet/data"
        "user_data_dir": "user data",
        "else_data_dir": "else data",
        "subjects_dir": "subjects",
        "backup_dir": "summary_backup",
        "assets_dir": "assets",
        "chat_dir": "chats",
        "log_dir": "logs",
    },
    "ui": {
        "theme": "light",              # light | dark
        "accent": "#4F7CFF",
        # 程序图标：留空表示用 gwp/resources/icons/planet.ico（内置"太白金星"）。
        # 想换成自己的图片，填绝对路径即可（推荐 .ico 或 512x512 的 png）。
        "app_icon": "",
        "font_family": "Microsoft YaHei UI",
        "font_size": 10,
        # 后台监听 user data 的变化（需求："软件后台要不断扫描 user data
        # 文件夹，更新文件变动，但不要耗费 cpu 太多性能"）。
        # 间隔单位毫秒：5000 时单核占用约 0.2%（5000 文件规模），
        # 想更省就调大（如 15000），想更灵就调小（最小 1000）。
        # 窗口隐藏或最小化时会**完全停掉**，所以后台待机不耗 CPU。
        "data_scan_interval_ms": 2000,
        "auto_refresh_on_change": True,
        "card": {
            "width": 190,
            "height": 118,
            "radius": 14,
            "show_cover_image": True,
        },
        # 书目页右侧「资料概览」面板：默认折起，需要时点顶部 ▤ 按钮展开
        "book_side_collapsed": True,
        "book_side_width": 0,          # 展开宽度；0 = 按窗口宽度自动
        # 主界面背景图：图片放在 else data/background，这里记录当前用哪一张
        "background_image": "",        # 相对 else data/background 的路径
        "background_enabled": True,    # 临时关掉背景而不清空设置
        "background_overlay": 0.0,     # 蒙层不透明度 0~0.9（默认不压暗背景）
        "background_margin": 0,        # 0=背景铺满工作区；>0 则四周留边当外框
        "background_fit": "cover",     # cover | contain | stretch | center
        "start_view": "home",          # home | last
        "confirm_on_delete": True,
        "open_files_in_new_window": True,
        # 首页右侧的日期/时间/天气条
        "show_clock_bar": True,        # 关掉后整条不显示（连日期时间也不显示）
        "weather_enabled": True,       # 关掉后不联网取天气（只显示日期与时间）
        # 首页右侧日程栏：单个任务行的高度（像素）。
        # 每行内容：标题 / 来源 / **DDL（单独一行、加粗）** / 备注（可选）。
        # 四行文字需要约 88px，给太小会挤在一起（内容多时行会自动更高）。
        "schedule_row_height": 88,
        # 日程栏是否隐藏「已完成」的条目（需求："日程默认 隐藏已完成"）。
        #
        # 这是**默认值**：用户自己取消勾选后会被写回这里，下次启动按他选的来
        # —— "默认隐藏"和"每次启动都掰回去"是两件事。
        "schedule_hide_done": True,
        #: 关闭主窗口时：True = 隐藏到系统托盘继续在后台运行（下次唤回是**瞬间**的，
        #: 不用再等一次冷启动）；False = 真正退出进程。
        #: 默认 True 是因为启动一次要重建界面并预热扫描，留在后台明显更省事。
        #: 托盘右键菜单里永远有「完全退出」，所以不会"关不掉"。
        "close_to_background": True,
        #: 第一次隐藏到后台时是否弹气泡提示（只弹一次，避免每次烦人）
        "close_to_background_notified": False,
    },
    "editor": {
        "autosave_seconds": 20,        # 0 表示关闭自动保存
        "font_family": "Consolas",
        "font_size": 11,
        "tab_width": 4,
        "preview_live": True,
    },
    "startup": {
        "autostart": False,            # 开机自动启动（写入注册表 Run 项）
        "prewarm_scan": True,          # 启动时后台预扫描，减少等待
        "scan_workers": 4,
    },
    # 论坛：菜单里「论坛 → 牢大CS」点一下用**系统默认浏览器**打开
    "forum": {
        "laoda_cs_url": "https://cs9.x-way.work/",
    },
    "ai": {
        "active_provider": "deepseek_api",
        "auto_send_current_file": True,   # 首次在文件中打开 AI 时自动发送当前文件
        "persist_chat_on_close": True,    # 关闭 AI 面板时保存聊天记录
        "clear_chat_on_exit": True,       # 关闭软件时清除全部聊天记录（需求文档）
        "clear_chat_days": 0,             # >0 时只保留最近 N 天
        "request_timeout": 180,
        "max_retries": 2,
        "temperature": 0.3,
        "max_tokens": 8192,
        "stream": True,
        #: 是否允许把图片发给 AI（"图片提取为 Markdown"用）。
        #: 默认 **False** 是刻意的：图片可能是作业照片、证件、手写笔记，
        #: 发出去有隐私含义，必须用户明确同意。关闭时该功能走网页版桥接
        #: （图片只进用户自己的剪贴板，由用户决定粘给谁）。
        "send_images": False,
        #: AI 对话的附件：单个文件最多送进对话的字符数 / 所有附件合计上限。
        #: 一份 20 页讲义正文大约 20000 字；再长的部分对问答帮助有限，
        #: 却会把上下文挤满、让回答变差。
        "attach_chars_per_file": 20000,
        "attach_chars_total": 60000,
        "fallback_chain": ["deepseek_api", "gpt_api", "tianxi_local"],
        "notify_on_fallback": True,       # 切换 AI 时弹窗提示
        "providers": {
            "deepseek_api": {
                "label": "DeepSeek API",
                "type": "openai_compatible",
                "enabled": True,
                "base_url": "https://api.deepseek.com",
                "path": "/chat/completions",
                "model": "deepseek-chat",
                "api_key_env": "DEEPSEEK_API_KEY",
                "api_key": "",
                "supports_vision": False,
                "extra_headers": {},
            },
            "gpt_api": {
                "label": "GPT API",
                "type": "openai_compatible",
                "enabled": True,
                "base_url": "https://api.openai.com",
                "path": "/v1/chat/completions",
                "model": "gpt-4o-mini",
                "api_key_env": "OPENAI_API_KEY",
                "api_key": "",
                "supports_vision": True,
                "extra_headers": {},
            },
            "deepseek_web": {
                "label": "DeepSeek 网页版",
                "type": "web_bridge",
                "enabled": True,
                "url": "https://chat.deepseek.com/",
                "auto_paste": True,       # 尝试自动把文件内容写入剪贴板
            },
            "gpt_web": {
                "label": "GPT 网页版",
                "type": "web_bridge",
                "enabled": True,
                "url": "https://chatgpt.com/",
                "auto_paste": True,
            },
            "tianxi_local": {
                "label": "本地天禧 AI",
                "type": "local_command",
                "enabled": True,
                "command": "",            # 例如 "tianxi-cli --chat"
                "workdir": "",
                "timeout": 180,
            },
            "custom_api": {
                "label": "自定义 API",
                "type": "openai_compatible",
                "enabled": False,
                "base_url": "",
                "path": "/v1/chat/completions",
                "model": "",
                "api_key_env": "",
                "api_key": "",
                "supports_vision": False,
                "extra_headers": {},
            },
        },
    },
    "summary": {
        # 留空 = 按科目类型自动决定（日记用 my diary/else diary，
        # 其它类型用 notebook/error-prone）。用户填了就以用户为准。
        "sources": [],
        "exclude_dirs": ["book"],
        "chunk_chars": 18000,          # 单次请求送入的字符数上限
        "chunk_overlap": 400,
        "max_input_chars": 400000,     # 超过则最多保留这么多字符并给出提示
        "backup_keep": 1,              # 只保留一个上一版本（需求文档）
        "include_images": True,        # notebook 中识别不可靠的 PDF 以图片插入
        "image_max_width": 1600,       # 转图片时的最大宽度（像素）
        "image_max_pages": 60,         # 单个 PDF 最多转多少页
        "min_text_chars_per_page": 80, # 每页文字少于该值则判定为“识别不可靠”
        "auto_open_after_generate": True,
    },
    "import": {
        "copy_files": True,            # 复制而不是移动（need.md 要求实际为复制）
        "ask_before_overwrite": True,
        "suffix_on_conflict": "_1",
        "extract_images_to_assets": True,
    },
    "export": {
        "pdf_page_size": "A4",
        "pdf_margin_mm": 18,
        "pdf_font_family": "Microsoft YaHei",
        "pdf_code_font": "Consolas",
        "pdf_embed_images": True,
        "pdf_page_numbers": True,       # 页脚居中插入 "- 页码 / 总页数 -"
        "ask_page_range": True,         # 排版完成后弹窗询问页码与导出范围
        "remember_last_dir": True,
    },
    "logging": {
        "level": "INFO",
        "keep_days": 14,
    },
    "prompts": {
        #: 提示词版本号。落后于 constants.PROMPT_REVISION 时，
        #: 下面这些"系统提示词"会被新版默认值整段替换（见 _migrate_prompts）。
        "revision": C.PROMPT_REVISION,
        "summary_system": C.SUMMARY_SYSTEM_PROMPT,
        "summary_chunk_system": C.SUMMARY_CHUNK_SYSTEM_PROMPT,
        "summary_merge_system": C.SUMMARY_MERGE_SYSTEM_PROMPT,
        "chat_system": C.CHAT_SYSTEM_PROMPT,
        "daily_chat_system": C.DAILY_CHAT_SYSTEM_PROMPT,
        "uncertainty_rules": "\n".join(C.DEFAULT_UNCERTAINTY_RULES),
        "summary_user_template": (
            "书目名称：{book}\n所属科目：{subject}\n\n"
            "以下是需要整合的全部资料（已按来源标注）：\n\n{materials}\n\n"
            "请按系统提示词的要求，输出完整的学习文档。"
        ),
        "chunk_user_template": (
            "书目名称：{book}\n这是第 {index}/{total} 部分资料。\n\n{materials}"
        ),
        "merge_user_template": (
            "书目名称：{book}\n所属科目：{subject}\n\n"
            "以下是各部分资料的提炼结果：\n\n{materials}\n\n"
            "请整合为一份完整的学习文档。"
        ),
    },
}


# --------------------------------------------------------------------------

def _deep_merge(base: dict, override: dict) -> dict:
    """递归合并：override 覆盖 base，dict 逐层合并，其它类型直接替换。"""
    result = copy.deepcopy(base)
    for key, value in (override or {}).items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = copy.deepcopy(value)
    return result


class Config:
    """线程安全的配置对象。"""

    _lock = threading.RLock()
    _instance: "Config | None" = None

    def __init__(self, data: dict[str, Any], path: Path | None = None) -> None:
        self._data = data
        self.path = path

    # -- 加载 / 保存 -------------------------------------------------------

    @classmethod
    def load(cls, path: Path | None = None, force: bool = False) -> "Config":
        """加载配置。第一次调用会创建带默认值的 config.json。

        注意：定位配置文件时**不能**调用 ``paths.current()``——那会反过来触发
        ``Config.load()``，形成无限递归。因此这里用 ``paths.peek_data_root()``
        直接读配置文件里的路径设置（不构造 Config 对象）。
        """
        with cls._lock:
            if cls._instance is not None and not force and path is None:
                return cls._instance

            if path is None:
                from gwp.core import constants as settings_defaults
                from gwp.core.paths import default_data_root, peek_data_root, project_root

                override = peek_data_root()
                if override:
                    candidate = Path(override)
                    if not candidate.is_absolute():
                        candidate = (project_root() / candidate).resolve()
                else:
                    candidate = default_data_root()
                # 与 DataPaths 使用同一套目录名规则
                path = candidate / settings_defaults.DEFAULT_ELSE_DATA_DIR / "config.json"

            user_data: dict[str, Any] = {}
            if path.exists():
                try:
                    user_data = json.loads(path.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError):
                    user_data = {}
            merged = _deep_merge(DEFAULT_CONFIG, user_data)
            config = cls(merged, path)
            # 提示词版本升级：把过期的默认提示词换成新版
            migrated = config._migrate_prompts(user_data)
            if path is not None:
                cls._instance = config
                if migrated:
                    try:
                        config.save()
                        log.info("提示词已升级到第 %s 版", C.PROMPT_REVISION)
                    except OSError:
                        log.warning("提示词升级后保存配置失败", exc_info=True)
            return config

    def _migrate_prompts(self, user_data: dict) -> bool:
        """把 config.json 里**过期的默认提示词**升级到当前版本。

        背景：配置是深合并的，用户已经落盘的 ``prompts`` 不会被新默认值覆盖
        （这是刻意的 —— 用户手改过的提示词必须保住）。
        但如果那份 prompts 只是**旧版本的默认值**，它就该跟着升级，
        否则改了默认提示词对老用户永远不生效（"长庚"这件事就卡在这里）。

        判定方式：``prompts.revision`` 落后于 :data:`C.PROMPT_REVISION`
        就整段换成新默认值。用户想自己改提示词时，
        **把 ``revision`` 手动改成当前版本号即可锁定**（不再被自动升级）。

        返回是否发生了改动（调用方据此决定要不要落盘）。
        """
        stored = user_data.get("prompts")
        if not isinstance(stored, dict):
            return False                     # 用户没写过 prompts，走默认值即可
        try:
            revision = int(stored.get("revision", 0) or 0)
        except (TypeError, ValueError):
            revision = 0
        if revision >= C.PROMPT_REVISION:
            return False                     # 已经是最新（或用户自己锁定过）
        defaults = DEFAULT_CONFIG["prompts"]
        for key, value in defaults.items():
            if key == "revision":
                continue
            # 只覆盖"存在且是字符串"的键，不硬塞用户没有的键
            if key in self._data.get("prompts", {}):
                self._data["prompts"][key] = value
        self._data["prompts"]["revision"] = C.PROMPT_REVISION
        log.info("检测到旧版提示词（第 %s 版），已升级到第 %s 版",
                 revision, C.PROMPT_REVISION)
        return True

    def save(self) -> None:
        """把当前配置写回磁盘（原子写，避免中途崩溃损坏文件）。"""
        if self.path is None:
            return
        with self._lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            payload = json.dumps(self._data, ensure_ascii=False, indent=2)
            self._atomic_write(self.path, payload)

    @staticmethod
    def _atomic_write(target: Path, payload: str) -> None:
        tmp = target.with_suffix(target.suffix + ".tmp")
        tmp.write_text(payload, encoding="utf-8")
        os.replace(tmp, target)

    # -- 读取 --------------------------------------------------------------

    def get(self, dotted: str, default: Any = None) -> Any:
        """按点号路径读取，例如 ``ai.providers.deepseek_api.model``。"""
        node: Any = self._data
        for part in dotted.split("."):
            if isinstance(node, dict) and part in node:
                node = node[part]
            else:
                return default
        return node

    def section(self, name: str) -> dict[str, Any]:
        """返回某个配置段的副本，避免调用方误改内部状态。"""
        value = self._data.get(name, {})
        return copy.deepcopy(value) if isinstance(value, dict) else {}

    def as_dict(self) -> dict[str, Any]:
        return copy.deepcopy(self._data)

    # -- 写入 --------------------------------------------------------------

    def set(self, dotted: str, value: Any) -> None:
        with self._lock:
            parts = dotted.split(".")
            node = self._data
            for part in parts[:-1]:
                nxt = node.get(part)
                if not isinstance(nxt, dict):
                    nxt = {}
                    node[part] = nxt
                node = nxt
            node[parts[-1]] = value

    def update(self, patch: dict[str, Any]) -> None:
        """深度合并一个补丁。"""
        with self._lock:
            self._data = _deep_merge(self._data, patch)

    def reset_section(self, name: str) -> None:
        with self._lock:
            if name in DEFAULT_CONFIG:
                self._data[name] = copy.deepcopy(DEFAULT_CONFIG[name])

    def reload(self) -> "Config":
        return Config.load(self.path, force=True)

    # -- 密钥（独立文件） --------------------------------------------------

    def load_secrets(self) -> dict[str, str]:
        from gwp.core.paths import current as current_paths

        path = current_paths().secrets_file
        if not path.exists():
            return {}
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}

    def save_secrets(self, secrets: dict[str, str]) -> None:
        from gwp.core.paths import current as current_paths

        path = current_paths().secrets_file
        path.parent.mkdir(parents=True, exist_ok=True)
        self._atomic_write(path, json.dumps(secrets, ensure_ascii=False, indent=2))

    def api_key_for(self, provider_id: str) -> str:
        """解析某个 provider 的 API Key：环境变量优先，其次 secrets.json，最后 config。"""
        providers = self.get("ai.providers", {}) or {}
        node = providers.get(provider_id, {}) or {}
        env_name = node.get("api_key_env") or ""
        if env_name:
            value = os.environ.get(env_name, "")
            if value:
                return value.strip()
        secrets = self.load_secrets()
        value = (secrets.get(provider_id) or "").strip()
        if value:
            return value
        return (node.get("api_key") or "").strip()

    def set_api_key(self, provider_id: str, api_key: str) -> None:
        secrets = self.load_secrets()
        if api_key:
            secrets[provider_id] = api_key
        else:
            secrets.pop(provider_id, None)
        self.save_secrets(secrets)
