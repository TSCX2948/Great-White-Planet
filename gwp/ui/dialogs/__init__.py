"""gwp.ui.dialogs：所有对话框。"""

from gwp.ui.dialogs.backup_dialog import BackupDialog, DiffDialog
from gwp.ui.dialogs.background_dialog import BackgroundDialog
from gwp.ui.dialogs.book_dialog import BookDialog
from gwp.ui.dialogs.chat_manager_dialog import ChatManagerDialog
from gwp.ui.dialogs.export_dialog import ExportPdfDialog
from gwp.ui.dialogs.help_dialog import HelpDialog
from gwp.ui.dialogs.image_digest_dialog import ImageDigestDialog
from gwp.ui.dialogs.materials_dialog import SummarySourcesDialog
from gwp.ui.dialogs.progress_dialog import SummaryProgressDialog
from gwp.ui.dialogs.question_dialog import AiQuestionDialog
from gwp.ui.dialogs.settings_dialog import SettingsDialog
from gwp.ui.dialogs.subject_dialog import SubjectDialog

__all__ = [
    "AiQuestionDialog",
    "BackupDialog",
    "BackgroundDialog",
    "BookDialog",
    "ChatManagerDialog",
    "DiffDialog",
    "ExportPdfDialog",
    "HelpDialog",
    "ImageDigestDialog",
    "SummarySourcesDialog",
    "SettingsDialog",
    "SubjectDialog",
    "SummaryProgressDialog",
]
