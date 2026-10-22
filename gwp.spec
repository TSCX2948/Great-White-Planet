# -*- mode: python ; coding: utf-8 -*-
"""Great White Planet 打包配置（PyInstaller）。

要点：

* **不打包任何 data 目录** —— 用户数据由程序首次运行时自己创建，安装包必须干净；
* 随包带上 `Document` 里的三份说明文档，帮助菜单离线可用；
* 可选依赖（docx/pptx/xlsx 解析）用 hiddenimports 显式带上，
  它们是在函数内部按需导入的，PyInstaller 静态分析扫不到；
* AI 提供方是 `pkgutil` 动态发现的，同样需要显式声明。
"""

from pathlib import Path

# SPECPATH 是 spec 文件所在目录，也就是 code 目录
CODE = Path(SPECPATH).resolve()
PROJECT = CODE.parent                    # <软件根>

# --------------------------------------------------------------------------
# 可选依赖：按需导入，必须显式声明
# --------------------------------------------------------------------------
HIDDEN = [
    # 文档解析（gwp/services/document_reader.py 内部导入）
    "docx",
    "pptx",
    "openpyxl",
    "pymupdf",
    "fitz",
    "PIL",
    "PIL.Image",
    # Markdown 渲染与 PDF 导出
    "markdown",
    "markdown.extensions.extra",
    "markdown.extensions.tables",
    "markdown.extensions.fenced_code",
    "markdown.extensions.codehilite",
    "pygments",
    "pygments.formatters.html",
    "pygments.lexers.python",
    # AI 提供方（pkgutil 动态发现）
    "gwp.ai.providers",
    "gwp.ai.providers.openai_compatible",
    "gwp.ai.providers.local_command",
    "gwp.ai.providers.web_bridge",
    # 服务层是通过 PEP 562 __getattr__ 惰性导入的，静态分析看不到
    "gwp.services.background",
    "gwp.services.dependencies",
    "gwp.services.document_reader",
    "gwp.services.file_clipboard",
    "gwp.services.file_ops",
    "gwp.services.markdown_renderer",
    "gwp.services.page_range",
    "gwp.services.pdf_exporter",
    "gwp.services.shell_ops",
    "gwp.services.themes",
    "gwp.ui.views.book_view",
    "gwp.ui.views.document_view",
    "gwp.ui.views.home_view",
    "gwp.ui.views.subject_view",
    "gwp.ui.windows.document_window",
    "gwp.ui.windows.global_chat_window",
]

# 明确排除：体积大且用不到
EXCLUDES = [
    "tkinter",
    "unittest",
    "pydoc",
    "doctest",
    "test",
    # 论坛是用**系统浏览器**打开的（菜单「论坛」里用户自己维护的网址列表），
    # 不需要内嵌 Chromium，所以可以排除掉这一大坨（省约 130MB）
    "PyQt6.QtWebEngineCore",
    "PyQt6.QtWebEngineWidgets",
    "PyQt6.QtWebEngineQuick",
    "PyQt6.QtQml",
    "PyQt6.QtQuick",
    "PyQt6.QtQuick3D",
    "PyQt6.QtQuickWidgets",
    "PyQt6.Qt3DCore",
    "PyQt6.QtBluetooth",
    "PyQt6.QtMultimedia",
    "PyQt6.QtMultimediaWidgets",
    "PyQt6.QtNetworkAuth",
    "PyQt6.QtPositioning",
    "PyQt6.QtSerialPort",
    "PyQt6.QtSql",
    "PyQt6.QtTest",
    "PyQt6.QtDesigner",
    "PyQt6.QtHelp",
    "PyQt6.QtOpenGL",
    "PyQt6.QtOpenGLWidgets",
    # numpy 只在"现场绘制图标"（CLI 的 icon 子命令）时才需要；
    # 随包已经带了 icons/planet.ico，正常启动用不到，排除可省约 40MB
    "numpy",
    "matplotlib",
    "pandas",
    "scipy",
    "pyinstaller",
]

# --------------------------------------------------------------------------
# 随包资源（先建好 list，下面 QtWebEngine 的 collect_all 会往里追加）
# --------------------------------------------------------------------------
datas = []
binaries = []

# 图标与图片
resources = CODE / "gwp" / "resources"
if resources.is_dir():
    datas.append((str(resources), "gwp/resources"))

# 说明文档（帮助菜单离线可读）
document = PROJECT / "Document"
DOC_FILES = (
    "Great_White_Planet_功能说明.md",
    "Great_White_Planet_设计思想.md",
    "Great_White_Planet_使用说明.md",
    "Great White Planet 简要说明书.pdf",
    "Great White Planet 安装步骤说明.pdf",
    # 教学书（用本项目讲软件工程全流程）。
    # 用户已明确不要这本书的 PDF，所以随包带 **Markdown** 版本。
    "开发实践——Great White Planet.md",
)
for name in DOC_FILES:
    source = document / name
    if source.is_file():
        datas.append((str(source), "Document"))
    else:
        print(f"[警告] 缺少文档：{source}")

# 从产物里剔除的文件（二进制/资源，Excludes 管不到）
EXCLUDE_BINARIES = ("opengl32sw.dll",)

# 版本资源（exe 的「属性 -> 详细信息」里显示的版本号）
#
# **从 gwp/__init__.py 读出版本号再生成**，而不是在这里写死 ——
# 版本号只能有一个来源（见 installer/build_version_info.py 的说明）。
_VERSRC = out = None
try:
    import sys as _sys

    _sys.path.insert(0, str(CODE / "installer"))
    from build_version_info import write_version_file as _write_ver

    _VERSRC = str(_write_ver(CODE, Path(SPECPATH) / ".version_tmp"))
    print(f"[版本信息] {_VERSRC}")
except Exception as _exc:  # noqa: BLE001 - 生成失败不该让打包挂掉
    print(f"[警告] 生成版本信息失败，exe 将没有版本号：{_exc}")

icon = resources / "icons" / "planet.ico"

a = Analysis(
    [str(CODE / "gwp_main.py")],
    pathex=[str(CODE)],
    binaries=[],
    datas=datas,
    hiddenimports=HIDDEN,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=EXCLUDES,
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

# 剔除不需要的二进制
a.binaries = TOC(
    [entry for entry in a.binaries if Path(entry[0]).name not in EXCLUDE_BINARIES]
)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Great White Planet",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,                       # 无控制台窗口
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(icon) if icon.is_file() else None,
    version=_VERSRC,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="Great White Planet",
)
