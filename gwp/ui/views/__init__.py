"""gwp.ui.views：页面级视图。"""

from gwp.ui.views.base_view import BaseView
from gwp.ui.views.book_view import BookView
from gwp.ui.views.document_view import DocumentView
from gwp.ui.views.home_view import HomeView
from gwp.ui.views.subject_view import SubjectView

__all__ = ["BaseView", "BookView", "DocumentView", "HomeView", "SubjectView"]
