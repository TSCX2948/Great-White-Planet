"""路径解析：唯一的“文件到底放在哪”的真相来源。

设计原则
--------
* 代码里**不出现任何绝对路径**；所有位置都由本模块按规则推导。
* 数据根目录（``D:\\Great White Planet\\data``）由 ``config.json`` 的 ``paths`` 段决定，
  可以整体迁移到别的磁盘，程序无需改动。
* ``user data``：用户自己上传/编辑的内容。
* ``else data``：非用户直接上传的内容（AI 缓存、聊天记录、日志、图片资源等）。
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

#: 软件根目录（= code 目录的上一级），可由环境变量 GWP_ROOT 覆盖，便于迁移/测试。
ENV_ROOT = "GWP_ROOT"

#: 默认目录名（与 core.constants 保持一致，这里复制为字面量以避免循环导入）
_DEFAULT_USER_DATA = "user data"
_DEFAULT_ELSE_DATA = "else data"
_DEFAULT_DATA_ROOT_NAME = "data"


def is_frozen() -> bool:
    """是否运行在打包后的可执行文件里（PyInstaller 等）。"""
    return bool(getattr(sys, "frozen", False))


def executable_dir() -> Path:
    """可执行文件所在目录（打包后就是安装目录）。"""
    return Path(sys.executable).resolve().parent


def project_root() -> Path:
    """返回 `Great White Planet` 根目录。

    三种情形，优先级从高到低：

    1. 环境变量 ``GWP_ROOT``（便于迁移与测试）；
    2. **打包运行**：可执行文件所在目录 —— 安装后 ``__file__`` 指向临时解包目录，
       不能再按源码目录层级推导，否则数据会被写到临时目录里，退出即丢失；
    3. 源码运行：``gwp/core/paths.py -> gwp/core -> gwp -> code -> <root>``。
    """
    override = os.environ.get(ENV_ROOT)
    if override:
        return Path(override).expanduser().resolve()
    if is_frozen():
        return executable_dir()
    # gwp/core/paths.py -> gwp/core -> gwp -> code -> <root>
    return Path(__file__).resolve().parents[3]


def code_dir() -> Path:
    """代码目录（``<root>/code``）。"""
    return project_root() / "code"


def app_dir() -> Path:
    """Python 包所在目录（``<root>/code/gwp``）。"""
    return Path(__file__).resolve().parents[1]


def bundle_dir() -> Path:
    """随程序打包的只读资源所在目录（**gwp 包目录**）。

    * 源码运行：``<root>/code/gwp``；
    * 打包运行：PyInstaller 解包目录下的 ``gwp`` 包 —— 图标等资源必须用
      ``sys._MEIPASS`` 定位，``__file__`` 在 onefile 模式下并不可靠。
    """
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        return Path(meipass) / "gwp"
    return app_dir()


def resources_dir() -> Path:
    """随软件分发的静态资源目录。"""
    return bundle_dir() / "resources"


def document_dir() -> Path:
    """设计文档目录（帮助菜单使用）。

    优先级：

    1. 环境变量 ``GWP_DOC_DIR``；
    2. ``<软件根>/Document``（存在就用它 —— 用户自己更新过的文档优先）；
    3. 打包时随程序分发的 ``Document``（在解包目录里，只读）。
    """
    override = os.environ.get("GWP_DOC_DIR")
    if override:
        return Path(override).expanduser().resolve()
    beside = project_root() / "Document"
    if beside.is_dir():
        return beside
    return bundle_dir() / "Document"


# --------------------------------------------------------------------------
# 数据目录
# --------------------------------------------------------------------------

class DataPaths:
    """按配置解析出的全部数据路径。配置变化后重新构造即可。"""

    def __init__(self, config) -> None:  # noqa: ANN001 - 避免循环导入，鸭子类型
        paths = config.section("paths")
        root: Path = self._resolve_data_root(paths.get("data_root"))
        self.data_root = root
        self.user_data: Path = root / str(paths.get("user_data_dir", _DEFAULT_USER_DATA))
        self.subjects_dir: Path = self.user_data / str(paths.get("subjects_dir", "subjects"))
        self.else_data: Path = root / str(paths.get("else_data_dir", _DEFAULT_ELSE_DATA))
        self.backup_dir: Path = self.else_data / str(paths.get("backup_dir", "summary_backup"))
        # 图片等资源不直接存入用户数据（需求文档第十节）
        self.assets_dir: Path = self.else_data / str(paths.get("assets_dir", "assets"))
        self.chat_dir: Path = self.else_data / str(paths.get("chat_dir", "chats"))
        self.cache_dir: Path = self.else_data / "cache"
        self.log_dir: Path = self.else_data / str(paths.get("log_dir", "logs"))
        self.config_file: Path = self.else_data / "config.json"
        self.secrets_file: Path = self.else_data / "secrets.json"
        # **单词书是所有科目共用的一个目录**（需求："所有科目公用一个文件夹"），
        # 放在 user data 下、**不在 subjects 里面** ——
        # 它不属于任何科目或书目，而是跨教材累积的生词本。
        self.wordbook_dir: Path = self.user_data / str(
            paths.get("wordbook_dir", "wordbook")
        )

    # -- 便捷方法 ---------------------------------------------------------

    @staticmethod
    def _resolve_data_root(configured) -> Path:
        """决定数据根目录。

        规则（让软件"换个地方装也能用"）：

        * 配置里空了 -> ``<软件根>/data``；
        * 配置是**相对路径** -> 相对软件根解析；
        * 配置是绝对路径 -> 就用它。

        **绝对路径即使还不存在也照用** —— 首次运行、全新安装时数据目录本来就
        还没建出来，不能因为"不存在"就判定配置失效。

        只有在**确定写不进去**时（目标是已存在的文件、或上层目录不可写）才回退到
        ``<软件根>/data``，避免把软件搬到新目录后还往旧路径写数据。
        """
        default = project_root() / _DEFAULT_DATA_ROOT_NAME
        raw = str(configured or "").strip()
        if not raw:
            return default
        candidate = Path(raw)
        if not candidate.is_absolute():
            return (project_root() / candidate).resolve()
        if candidate.is_dir():
            return candidate
        if candidate.exists():
            # 被一个同名文件占住了，没法当目录用
            return default
        # 还不存在：确认最近的存在祖先可写，否则回退
        ancestor = candidate.parent
        while not ancestor.exists() and ancestor != ancestor.parent:
            ancestor = ancestor.parent
        try:
            if ancestor.is_dir() and os.access(ancestor, os.W_OK):
                return candidate
        except OSError:
            pass
        return default

    def all_dirs(self) -> tuple[Path, ...]:
        return (
            self.data_root,
            self.user_data,
            self.subjects_dir,
            self.wordbook_dir,
            self.else_data,
            self.backup_dir,
            self.assets_dir,
            self.chat_dir,
            self.cache_dir,
            self.log_dir,
        )

    def ensure(self) -> None:
        """确保所有目录存在。"""
        for directory in self.all_dirs():
            directory.mkdir(parents=True, exist_ok=True)

    def subject_dir(self, subject_name: str) -> Path:
        return self.subjects_dir / subject_name

    def book_dir(self, subject_name: str, book_name: str) -> Path:
        return self.subject_dir(subject_name) / book_name

    def backup_book_dir(self, subject_name: str, book_name: str) -> Path:
        return self.backup_dir / subject_name / book_name

    def subject_asset_dir(self, subject_name: str) -> Path:
        return self.assets_dir / "subjects" / subject_name

    def __repr__(self) -> str:  # pragma: no cover - 调试用
        return f"<DataPaths data_root={self.data_root} subjects={self.subjects_dir}>"


#: 全局单例，由 bootstrap 注入。不要在导入期展开成路径常量，否则配置无法生效。
_current: DataPaths | None = None


def default_data_root() -> Path:
    """没有读取配置时的数据根目录（默认 ``<项目根>/data``）。"""
    return project_root() / _DEFAULT_DATA_ROOT_NAME


def default_config_file() -> Path:
    """没有读取配置时的配置文件位置（默认 ``<项目根>/data/else data/config.json``）。"""
    return default_data_root() / _DEFAULT_ELSE_DATA / "config.json"


def peek_data_root() -> str:
    """直接从配置文件里读 ``paths.data_root``，**不经过 Config 对象**。

    这样 :meth:`gwp.core.config.Config.load` 才能在路径单例尚未建立时定位配置文件，
    避免 Config 与 DataPaths 互相调用造成无限递归。
    """
    file = default_config_file()
    try:
        if file.is_file():
            import json

            data = json.loads(file.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                section = data.get("paths")
                if isinstance(section, dict):
                    return str(section.get("data_root") or "")
    except (OSError, ValueError):
        pass
    return ""


def set_current(paths: DataPaths) -> DataPaths:
    global _current
    _current = paths
    return paths


def current() -> DataPaths:
    """取当前路径配置；尚未初始化时按配置推导。

    ``DataPaths(config)`` 只需要一个普通的配置对象，因此这里用 ``DataPaths.__new__``
    的方式不成立——改为构造一个"轻量配置"：直接读取配置文件内容合并默认值，
    并且不写入 Config 单例，彻底避免 Config 与 DataPaths 互相调用。
    """
    global _current
    if _current is not None:
        return _current
    from gwp.core.config import Config

    if Config._instance is not None:
        config = Config._instance
    else:
        # 此时不能调用 Config.load()（它会来问我们配置文件在哪），
        # 所以直接读取默认位置的配置文件。
        config = Config.load(default_config_file())
    _current = DataPaths(config)
    return _current
