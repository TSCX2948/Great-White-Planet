"""启动引导：把配置、路径、日志、各个管理器装配成一个可用的运行时。

界面层通过 :class:`AppContext` 拿到所有依赖，不需要自己去 new 那些对象，
也就不会出现"到处 import 具体实现"的耦合。
"""

from __future__ import annotations

import logging
import sys
from dataclasses import dataclass, field
from pathlib import Path

from gwp import __app_name__, __version__
from gwp.ai.chat_session import ChatStore
from gwp.ai.manager import AIManager
from gwp.ai.summarizer import Summarizer
from gwp.core import constants as C
from gwp.core.config import Config
from gwp.core.eventbus import bus
from gwp.core.logging_setup import cleanup_old_logs, setup_logging
from gwp.core.paths import DataPaths, set_current
from gwp.core.write_guard import install_test_write_guard
from gwp.data_manager.cache import ScanCache
from gwp.data_manager.store import Library
from gwp.data_manager.summary_backup import BackupManager

log = logging.getLogger(__name__)

#: 已有实例在运行时的退出码（run.pyw 会原样返回，方便脚本判断）
EXIT_ALREADY_RUNNING = 2


@dataclass
class AppContext:
    """运行时的共享上下文。所有界面控件都持有它的引用。"""

    config: Config
    paths: DataPaths
    library: Library
    ai: AIManager
    summarizer: Summarizer
    backups: BackupManager
    chats: ChatStore
    cache: ScanCache
    root: Path
    argv: list[str] = field(default_factory=list)
    prewarm: bool = False
    services: dict = field(default_factory=dict)

    # -- 便捷访问 -------------------------------------------------------

    @property
    def clipboard(self):
        """文件剪贴板（复制/剪切/粘贴）。全局共享，切换书目时内容不丢。"""
        from gwp.services.file_clipboard import FileClipboard

        clipboard = self.services.get("clipboard")
        if clipboard is None:
            clipboard = FileClipboard()
            self.services["clipboard"] = clipboard
        return clipboard

    @property
    def backgrounds(self):
        """主界面背景图管理（图片放在 else data/background）。"""
        from gwp.services.background import BackgroundManager

        manager = self.services.get("backgrounds")
        if manager is None:
            manager = BackgroundManager(self.config, self.paths)
            self.services["backgrounds"] = manager
        return manager

    @property
    def schedule(self):
        """首页右侧日程栏用的"其它日程"存储（数据根目录下的 schedule.json）。"""
        from gwp.data_manager.schedule import ScheduleStore

        store = self.services.get("schedule")
        if store is None:
            store = ScheduleStore(self.paths.data_root)
            self.services["schedule"] = store
        return store

    @property
    def theme(self) -> str:
        return str(self.config.get("ui.theme", "light") or "light")

    @property
    def global_bus(self):
        return bus

    def save_config(self) -> None:
        self.config.save()
        bus.emit("config_changed")

    def reload_paths(self) -> None:
        """数据根目录被改动后重新解析路径。"""
        self.paths = set_current(DataPaths(self.config))
        self.paths.ensure()
        self.library = Library(self.config, self.paths)
        self.backups = BackupManager(self.config, self.paths)
        self.chats = ChatStore(self.config, self.paths)
        self.cache = ScanCache(self.paths)
        self.services.pop("backgrounds", None)      # 重建背景管理器指向新目录
        self.services.pop("schedule", None)         # 日程也指向新的数据根目录


def bootstrap(argv: list[str] | None = None) -> AppContext:
    """初始化软件运行时。可在创建 QApplication 之前调用。"""
    argv = list(argv if argv is not None else sys.argv[1:])

    # **最优先**装上"测试不许写真实数据"的硬保护。
    #
    # 放在所有磁盘操作之前是有意的：一旦开始读配置、建目录，
    # 就已经有写入可能了。见 gwp/core/write_guard.py 里的两次事故记录 ——
    # 这个保护不是"顺手加的检查"，而是唯一可靠的那一层。
    install_test_write_guard()

    config = Config.load()
    paths = set_current(DataPaths(config))

    log_level = str(config.get("logging.level", "INFO") or "INFO")
    keep_days = int(config.get("logging.keep_days", 14) or 14)
    setup_logging(paths.log_dir, log_level, keep_days)
    cleanup_old_logs(paths.log_dir, keep_days)

    try:
        paths.ensure()
    except OSError:
        log.exception("创建数据目录失败，请检查磁盘权限：%s", paths.data_root)

    # 配置文件不存在时写一份带默认值的，方便用户查看和修改
    if not paths.config_file.exists():
        try:
            config.save()
            log.info("已生成默认配置：%s", paths.config_file)
        except OSError:
            log.exception("写入默认配置失败")

    library = Library(config, paths)
    ai_manager = AIManager(config)

    # 旧版本的单词书是"每本书一个目录"，现在所有科目共用一个。
    # 在这里迁移一次：**绝不覆盖**、移动而不是复制、失败就留着。
    try:
        from gwp.data_manager import wordbook as _wordbook

        _wordbook.migrate_legacy_wordbooks(
            paths.wordbook_dir, paths.subjects_dir
        )
    except Exception:  # noqa: BLE001 - 迁移失败不该让软件起不来
        log.exception("迁移旧单词书失败（不影响启动）")

    context = AppContext(
        config=config,
        paths=paths,
        library=library,
        ai=ai_manager,
        summarizer=Summarizer(config, library, ai_manager),
        backups=BackupManager(config, paths),
        chats=ChatStore(config, paths),
        cache=ScanCache(paths),
        root=paths.data_root.parent,
        argv=argv,
        prewarm="--startup" in argv or "--prewarm" in argv,
    )
    log.info(
        "%s v%s 启动；数据目录=%s；当前 AI=%s",
        __app_name__,
        __version__,
        paths.user_data,
        context.ai.describe_active(),
    )
    return context


def check_single_instance(context: AppContext, hwnd: int = 0) -> int | None:
    """检查是否已有实例在运行。

    返回 None 表示可以继续启动；返回整数表示已有实例在跑，调用方应当用它作为退出码。
    拿到锁的实例会被记录在 ``context.services["instance_lock"]``，
    退出时由 :func:`release_single_instance` 释放。

    ``hwnd`` 是本进程主窗口的句柄；只有把它写进锁文件，下一个实例才能判断
    "已有实例的窗口在哪个虚拟桌面"（Win11 多桌面）。

    返回的退出码旁会附带信息，可用 :func:`last_instance_conflict` 取回。
    """
    from gwp.core import single_instance

    if "--allow-multiple" in (context.argv or []):
        log.warning("检测到 --allow-multiple，跳过单实例检查")
        return None

    lock = single_instance.acquire(context.paths.else_data, hwnd=hwnd)
    if lock.acquired:
        context.services["instance_lock"] = lock
        # 进程被强杀时也尽量删掉锁文件
        try:
            import atexit

            atexit.register(lock.release)
        except Exception:  # noqa: BLE001
            pass
        return None

    context.services["instance_conflict"] = lock
    if lock.on_other_desktop:
        log.warning(
            "已有实例在**另一个虚拟桌面**上运行（PID %s），本次启动退出。数据目录=%s",
            lock.pid,
            context.paths.else_data,
        )
    else:
        log.warning(
            "已有实例在运行（PID %s），本次启动退出。数据目录=%s",
            lock.pid,
            context.paths.else_data,
        )
    return EXIT_ALREADY_RUNNING


def last_instance_conflict(context: AppContext):
    """取回上次 :func:`check_single_instance` 记录的冲突信息（可能为 None）。"""
    return context.services.get("instance_conflict")


def publish_instance_window(context: AppContext, hwnd: int) -> None:
    """把主窗口句柄写进实例锁，供下一个实例判断虚拟桌面。"""
    lock = context.services.get("instance_lock")
    if lock is not None:
        lock.publish_window(hwnd)


def release_single_instance(context: AppContext) -> None:
    lock = context.services.pop("instance_lock", None)
    if lock is not None:
        lock.release()


def prewarm_scan(context: AppContext) -> None:
    """后台预扫描：把科目/书目结构提前读进内存与缓存（需求文档第十三节）。"""
    try:
        subjects = context.library.subjects(refresh=True)
        for subject in subjects:
            context.cache.record(subject.path, subject.book_count, subject.file_count, subject.total_size)
        context.cache.save()
        log.info("预扫描完成：%s 个科目", len(subjects))
    except Exception:  # noqa: BLE001 - 预扫描失败不影响正常使用
        log.exception("预扫描失败")


def cleanup_on_exit(context: AppContext) -> None:
    """退出时的收尾：按配置清除聊天记录（需求文档第七节）。"""
    try:
        if context.config.get("ai.clear_chat_on_exit", True):
            if context.config.get("ai.persist_chat_on_close", True):
                days = int(context.config.get("ai.clear_chat_days", 0) or 0)
                context.chats.clear_all(keep_days=days)
            else:
                context.chats.clear_all()
    except Exception:  # noqa: BLE001
        log.exception("退出清理失败")


def default_theme_qss(context: AppContext) -> str:
    from gwp.services import themes

    return themes.app_qss(
        theme=context.theme,
        accent=str(context.config.get("ui.accent", "") or ""),
        font_family=str(context.config.get("ui.font_family", "") or ""),
        font_size=int(context.config.get("ui.font_size", 10) or 10),
    )


__all__ = [
    "EXIT_ALREADY_RUNNING",
    "AppContext",
    "bootstrap",
    "check_single_instance",
    "cleanup_on_exit",
    "default_theme_qss",
    "last_instance_conflict",
    "prewarm_scan",
    "publish_instance_window",
    "release_single_instance",
]
