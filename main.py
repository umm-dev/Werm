import os
import sys
import json
import time
from dataclasses import dataclass, asdict
from typing import Callable, List, Dict, Optional
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode

from PySide6.QtCore import (
    QUrl,
    Qt,
    QStandardPaths,
    QTimer,
    QEvent,
    QModelIndex,
    QObject,
    Signal,
    QEasingCurve,
    QPropertyAnimation,
    QRect,
    QSize,
)
from PySide6.QtGui import (
    QAction,
    QKeySequence,
    QFontDatabase,
    QDesktopServices,
    QStandardItemModel,
    QStandardItem,
    QPixmap,
    QIcon,
    QColor,
    QPainter,
    QPen,
    QBrush,
)
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QToolBar,
    QLineEdit,
    QTabWidget,
    QMessageBox,
    QDialog,
    QVBoxLayout,
    QListWidget,
    QListWidgetItem,
    QLabel,
    QPushButton,
    QHBoxLayout,
    QTableWidget,
    QTableWidgetItem,
    QAbstractItemView,
    QStackedWidget,
    QProgressBar,
    QWidget,
    QCompleter,
    QCheckBox,
    QStyle,
    QHeaderView,
    QGridLayout,
    QFrame,
    QScrollArea,
    QSizePolicy,
    QGraphicsOpacityEffect,
)
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebEngineCore import (
    QWebEngineProfile,
    QWebEngineScript,
    QWebEnginePage,
    QWebEngineUrlRequestInterceptor,
    QWebEngineSettings,
)
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply

APP_NAME = "Werm"
HOME_URL = "https://google.com/aimode"
SHOW_PAGE_JS_CONSOLE = False
SEARCH_ENGINE_URL = "https://www.google.com/search"
SEARCH_QUERY_PARAM = "q"
SERVICE_ID = f"{APP_NAME}:passwords"
REQUIRE_HTTPS_FOR_PASSWORDS = True

PROFILE_NAMES = ["default", "work", "private"]
PRIVATE_PROFILE_NAME = "private"
DEFAULT_PROFILE_NAME = "default"

ZOOM_DEFAULT = 1.0
ZOOM_MIN = 0.25
ZOOM_MAX = 5.0
ZOOM_STEP = 0.1

OMNIBAR_SUGGEST_DEBOUNCE_MS = 100
HISTORY_SUGGEST_LIMIT = 8
HISTORY_MAX_ENTRIES = 5000
STORE_SAVE_DEBOUNCE_MS = 700

EPHEMERAL_IDLE_MS = 10 * 60 * 1000

FIRST_RUN_FADE_MS = 220
FIRST_RUN_STAGGER_MS = 45
CONFIG_FILENAME = "config.json"
DEFAULT_SEARCH_ENGINE_NAME = "Built-in Default"

DEFAULT_TRACKER_BLOCKLIST = [
    "doubleclick.net",
    "googlesyndication.com",
    "google-analytics.com",
    "facebook.net",
    "connect.facebook.net",
    "stats.g.doubleclick.net",
]

POPUP_FEATURE_KEY = "popups"


@dataclass
class SearchEngineOption:
    key: str
    label: str
    home_url: str
    search_url: str
    query_param: str
    favicon_url: str
    category: str
    description: str = ""


SEARCH_ENGINE_OPTIONS: List[SearchEngineOption] = [
    SearchEngineOption(
        key="built_in_default",
        label="Built-in Default",
        home_url=HOME_URL,
        search_url=SEARCH_ENGINE_URL,
        query_param=SEARCH_QUERY_PARAM,
        favicon_url="https://www.google.com/favicon.ico",
        category="AI-focused",
        description="Ships with Google AI Mode as home and plain Google search in the omnibar.",
    ),
    SearchEngineOption(
        key="google_utm14",
        label="Google (utm=14)",
        home_url="https://www.google.com/",
        search_url="https://www.google.com/search?utm=14",
        query_param="q",
        favicon_url="https://www.google.com/favicon.ico",
        category="Normal",
        description="Classic Google search with utm=14 attached.",
    ),
    SearchEngineOption(
        key="google_plain",
        label="Google",
        home_url="https://www.google.com/",
        search_url="https://www.google.com/search",
        query_param="q",
        favicon_url="https://www.google.com/favicon.ico",
        category="Normal",
        description="Plain Google home and search.",
    ),
    SearchEngineOption(
        key="bing",
        label="Bing",
        home_url="https://www.bing.com/",
        search_url="https://www.bing.com/search",
        query_param="q",
        favicon_url="https://www.bing.com/favicon.ico",
        category="Normal",
        description="Microsoft Bing as home and search.",
    ),
    SearchEngineOption(
        key="duckduckgo",
        label="DuckDuckGo",
        home_url="https://duckduckgo.com/",
        search_url="https://duckduckgo.com/",
        query_param="q",
        favicon_url="https://duckduckgo.com/favicon.ico",
        category="Normal",
        description="DuckDuckGo with a privacy-first feel.",
    ),
    SearchEngineOption(
        key="google_ai_mode",
        label="Google AI Mode",
        home_url="https://google.com/aimode",
        search_url="https://www.google.com/search",
        query_param="q",
        favicon_url="https://www.google.com/favicon.ico",
        category="AI-focused",
        description="AI Mode as home, plain Google in the omnibar.",
    ),
    SearchEngineOption(
        key="chatgpt_search",
        label="ChatGPT Search",
        home_url="https://chatgpt.com/?hints=search",
        search_url="https://chatgpt.com/?hints=search",
        query_param="prompt",
        favicon_url="https://qph.cf2.poecdn.net/main-thumb-pb-3062-200-xkeutmibkvqgfuvcprpuivgjohdgesee.jpeg",
        category="AI-focused",
        description="ChatGPT search-style landing page.",
    ),
]

try:
    import keyring
    HAVE_KEYRING = True
except Exception:
    keyring = None
    HAVE_KEYRING = False


def app_data_dir() -> str:
    base = QStandardPaths.writableLocation(QStandardPaths.AppDataLocation)
    path = os.path.join(base, APP_NAME)
    os.makedirs(path, exist_ok=True)
    return path


def profile_root_dir(profile_name: str) -> Optional[str]:
    if profile_name == PRIVATE_PROFILE_NAME:
        return None
    base = app_data_dir()
    path = os.path.join(base, "profiles", profile_name)
    os.makedirs(path, exist_ok=True)
    return path


def profile_download_dir(profile_name: str) -> str:
    root = profile_root_dir(profile_name)
    if root:
        path = os.path.join(root, "downloads")
    else:
        temp = QStandardPaths.writableLocation(QStandardPaths.TempLocation)
        path = os.path.join(temp, APP_NAME, "downloads", profile_name)
    os.makedirs(path, exist_ok=True)
    return path


def config_path() -> str:
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), CONFIG_FILENAME)


def favicon_cache_dir() -> str:
    path = os.path.join(app_data_dir(), "favicons")
    os.makedirs(path, exist_ok=True)
    return path


@dataclass
class AppConfig:
    home_url: str
    search_engine_url: str
    search_query_param: str
    search_engine_name: str = DEFAULT_SEARCH_ENGINE_NAME
    search_engine_key: str = "built_in_default"
    first_run_completed: bool = True


DEFAULT_APP_CONFIG = AppConfig(
    home_url=HOME_URL,
    search_engine_url=SEARCH_ENGINE_URL,
    search_query_param=SEARCH_QUERY_PARAM,
    search_engine_name=DEFAULT_SEARCH_ENGINE_NAME,
    search_engine_key="built_in_default",
    first_run_completed=True,
)


def normalize_url_value(value: str) -> str:
    return (value or "").strip().rstrip("/")


def default_app_config() -> AppConfig:
    return AppConfig(**asdict(DEFAULT_APP_CONFIG))


def option_to_config(option: SearchEngineOption) -> AppConfig:
    return AppConfig(
        home_url=option.home_url,
        search_engine_url=option.search_url,
        search_query_param=option.query_param,
        search_engine_name=option.label,
        search_engine_key=option.key,
        first_run_completed=True,
    )


def find_option_by_key(key: str) -> Optional[SearchEngineOption]:
    for option in SEARCH_ENGINE_OPTIONS:
        if option.key == key:
            return option
    return None


def save_app_config(config: AppConfig):
    path = config_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(asdict(config), f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def load_app_config() -> AppConfig:
    path = config_path()
    if not os.path.exists(path):
        return default_app_config()
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return AppConfig(
            home_url=str(data.get("home_url") or HOME_URL),
            search_engine_url=str(data.get("search_engine_url") or SEARCH_ENGINE_URL),
            search_query_param=str(data.get("search_query_param") or SEARCH_QUERY_PARAM),
            search_engine_name=str(data.get("search_engine_name") or DEFAULT_SEARCH_ENGINE_NAME),
            search_engine_key=str(data.get("search_engine_key") or "built_in_default"),
            first_run_completed=bool(data.get("first_run_completed", True)),
        )
    except Exception:
        return default_app_config()


def host_from_qurl(qurl: QUrl) -> str:
    return (qurl.host() or "").lower().strip(".")


def origin_from_qurl(qurl: QUrl) -> str:
    scheme = (qurl.scheme() or "").lower()
    host = (qurl.host() or "").lower().strip(".")
    port = qurl.port()
    if not scheme or not host:
        return ""
    if port > 0 and not ((scheme == "http" and port == 80) or (scheme == "https" and port == 443)):
        return f"{scheme}://{host}:{port}"
    return f"{scheme}://{host}"


def looks_like_url(text: str) -> bool:
    t = text.strip()
    if not t:
        return False
    if "://" in t:
        return True
    if t.startswith("localhost"):
        return True
    if t.replace(".", "").isdigit():
        return True
    return "." in t and " " not in t


def build_search_url(query: str, config: Optional[AppConfig] = None) -> str:
    cfg = config or DEFAULT_APP_CONFIG
    base = (cfg.search_engine_url or cfg.home_url).strip() or HOME_URL
    parts = urlsplit(base)
    params = dict(parse_qsl(parts.query, keep_blank_values=True))
    params[cfg.search_query_param] = query
    new_query = urlencode(params, doseq=True)
    return urlunsplit((parts.scheme, parts.netloc, parts.path or "/", new_query, parts.fragment))


def normalize_url_or_search(text: str, config: Optional[AppConfig] = None) -> QUrl:
    t = (text or "").strip()
    if looks_like_url(t):
        if "://" not in t:
            t = "https://" + t
        return QUrl(t)
    return QUrl(build_search_url(t, config=config))


def make_placeholder_icon(size: int = 22) -> QIcon:
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing, True)
    painter.setPen(QPen(QColor("#32405f"), 1.4))
    painter.setBrush(QBrush(QColor("#182031")))
    painter.drawEllipse(1, 1, size - 2, size - 2)
    painter.end()
    return QIcon(pixmap)


def animate_fade(widget: QWidget, duration: int = FIRST_RUN_FADE_MS, start: float = 0.0, end: float = 1.0):
    effect = widget.graphicsEffect()
    if not isinstance(effect, QGraphicsOpacityEffect):
        effect = QGraphicsOpacityEffect(widget)
        widget.setGraphicsEffect(effect)
    effect.setOpacity(start)
    anim = QPropertyAnimation(effect, b"opacity", widget)
    anim.setDuration(duration)
    anim.setStartValue(start)
    anim.setEndValue(end)
    anim.setEasingCurve(QEasingCurve.OutCubic)
    widget._fade_anim = anim
    anim.start()


def animate_slide(widget: QWidget, start_rect: QRect, end_rect: QRect, duration: int = FIRST_RUN_FADE_MS):
    anim = QPropertyAnimation(widget, b"geometry", widget)
    anim.setDuration(duration)
    anim.setStartValue(start_rect)
    anim.setEndValue(end_rect)
    anim.setEasingCurve(QEasingCurve.OutCubic)
    widget._slide_anim = anim
    anim.start()


def _set_request_redirects(req: QNetworkRequest):
    attr = getattr(QNetworkRequest, "FollowRedirectsAttribute", None)
    if attr is not None:
        try:
            req.setAttribute(attr, True)
        except Exception:
            pass


class FaviconLoader(QObject):
    icon_loaded = Signal(str, QIcon)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.nam = QNetworkAccessManager(self)
        self._pending: Dict[QNetworkReply, str] = {}

    def _cache_path(self, key: str) -> str:
        return os.path.join(favicon_cache_dir(), f"{key}.bin")

    def load(self, option: SearchEngineOption):
        key = option.key
        cache = self._cache_path(key)
        if os.path.exists(cache):
            try:
                with open(cache, "rb") as f:
                    cached_data = f.read()
                pixmap = QPixmap()
                pixmap.loadFromData(cached_data)
                if not pixmap.isNull():
                    self.icon_loaded.emit(key, QIcon(pixmap))
                    return
            except Exception:
                pass
        req = QNetworkRequest(QUrl(option.favicon_url))
        _set_request_redirects(req)
        reply = self.nam.get(req)
        self._pending[reply] = key
        reply.finished.connect(lambda r=reply: self._on_finished(r))

    def _on_finished(self, reply: QNetworkReply):
        key = self._pending.pop(reply, "")
        if reply.error() != QNetworkReply.NoError:
            reply.deleteLater()
            return
        data = bytes(reply.readAll())
        if data:
            pixmap = QPixmap()
            pixmap.loadFromData(data)
            if not pixmap.isNull():
                cache = self._cache_path(key)
                try:
                    with open(cache, "wb") as f:
                        f.write(data)
                except Exception:
                    pass
                self.icon_loaded.emit(key, QIcon(pixmap))
        reply.deleteLater()


class SearchEngineCard(QFrame):
    clicked = Signal(str)

    def __init__(self, option: SearchEngineOption, is_default_card: bool = False, parent=None):
        super().__init__(parent)
        self.option = option
        self.is_selected = False
        self.is_default_card = is_default_card
        self.setObjectName("searchEngineCard")
        self.setCursor(Qt.PointingHandCursor)
        self.setFrameShape(QFrame.NoFrame)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setMinimumHeight(86)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(12)

        self.icon_label = QLabel()
        self.icon_label.setFixedSize(28, 28)
        self._set_icon(make_placeholder_icon())
        layout.addWidget(self.icon_label, 0, Qt.AlignTop)

        text_col = QVBoxLayout()
        text_col.setSpacing(4)
        self.title_label = QLabel(option.label)
        self.title_label.setObjectName("engineCardTitle")
        self.title_label.setWordWrap(True)
        text_col.addWidget(self.title_label)

        subtitle = option.description or option.home_url
        if self.is_default_card:
            subtitle = f"Uses shipped defaults: {HOME_URL} + {SEARCH_ENGINE_URL}"
        self.desc_label = QLabel(subtitle)
        self.desc_label.setObjectName("engineCardDescription")
        self.desc_label.setWordWrap(True)
        text_col.addWidget(self.desc_label)
        layout.addLayout(text_col, 1)

        self.badge = QLabel("DEFAULT" if is_default_card else option.category.upper())
        self.badge.setObjectName("engineCardBadge")
        self.badge.setAlignment(Qt.AlignCenter)
        self.badge.setFixedHeight(24)
        layout.addWidget(self.badge, 0, Qt.AlignTop)

        self.refresh_style()

    def _set_icon(self, icon: QIcon):
        self.icon_label.setPixmap(icon.pixmap(QSize(24, 24)))

    def set_icon(self, icon: QIcon):
        self._set_icon(icon)

    def set_selected(self, value: bool):
        self.is_selected = value
        self.refresh_style()

    def refresh_style(self):
        self.setProperty("selected", self.is_selected)
        self.style().unpolish(self)
        self.style().polish(self)
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.option.key)
        super().mousePressEvent(event)


class FirstRunDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Welcome to {APP_NAME}")
        self.setModal(True)
        self.setObjectName("firstRunDialog")
        self.resize(820, 640)
        self.setMinimumSize(720, 560)

        self.selected_key: str = DEFAULT_APP_CONFIG.search_engine_key
        self.selected_config: AppConfig = default_app_config()
        self.cards: Dict[str, SearchEngineCard] = {}
        self.loader = FaviconLoader(self)
        self.loader.icon_loaded.connect(self._on_icon_loaded)

        root = QVBoxLayout(self)
        root.setContentsMargins(26, 24, 26, 20)
        root.setSpacing(14)

        self.title_label = QLabel(f"Welcome to {APP_NAME}")
        self.title_label.setObjectName("firstRunTitle")
        root.addWidget(self.title_label)

        self.subtitle_label = QLabel(
            "Choose how Werm should search. You can keep the shipped defaults or pick a custom start experience."
        )
        self.subtitle_label.setObjectName("firstRunSubtitle")
        self.subtitle_label.setWordWrap(True)
        root.addWidget(self.subtitle_label)

        self.preview_label = QLabel()
        self.preview_label.setObjectName("firstRunPreview")
        self.preview_label.setWordWrap(True)
        root.addWidget(self.preview_label)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        root.addWidget(scroll, 1)

        content = QWidget()
        self.content_layout = QVBoxLayout(content)
        self.content_layout.setContentsMargins(0, 4, 0, 4)
        self.content_layout.setSpacing(18)
        scroll.setWidget(content)

        self._build_sections()

        btn_row = QHBoxLayout()
        btn_row.addWidget(QLabel("You can change this later in Settings once you add one."), 1)

        self.use_defaults_btn = QPushButton("Use Defaults")
        self.use_defaults_btn.clicked.connect(self._use_defaults)
        btn_row.addWidget(self.use_defaults_btn)

        self.continue_btn = QPushButton("Continue")
        self.continue_btn.setDefault(True)
        self.continue_btn.clicked.connect(self.accept)
        btn_row.addWidget(self.continue_btn)

        root.addLayout(btn_row)

        self._select_key(DEFAULT_APP_CONFIG.search_engine_key)
        self._kickoff_favicons()
        QTimer.singleShot(0, self._play_intro_animations)

    def _build_sections(self):
        for category in ("Normal", "AI-focused"):
            title = QLabel(category)
            title.setObjectName("firstRunSectionTitle")
            self.content_layout.addWidget(title)

            grid_wrap = QWidget()
            grid = QGridLayout(grid_wrap)
            grid.setContentsMargins(0, 0, 0, 0)
            grid.setHorizontalSpacing(12)
            grid.setVerticalSpacing(12)

            row = 0
            col = 0
            options = [o for o in SEARCH_ENGINE_OPTIONS if o.category == category and o.key != "built_in_default"]
            if category == "AI-focused":
                options = [SEARCH_ENGINE_OPTIONS[0]] + options

            for option in options:
                is_default_card = option.key == "built_in_default"
                card = SearchEngineCard(option, is_default_card=is_default_card)
                card.clicked.connect(self._select_key)
                self.cards[option.key] = card
                grid.addWidget(card, row, col)
                col += 1
                if col >= 2:
                    col = 0
                    row += 1

            self.content_layout.addWidget(grid_wrap)

    def _kickoff_favicons(self):
        for option in SEARCH_ENGINE_OPTIONS:
            self.loader.load(option)

    def _on_icon_loaded(self, key: str, icon: QIcon):
        card = self.cards.get(key)
        if card:
            card.set_icon(icon)

    def _select_key(self, key: str):
        option = find_option_by_key(key) or find_option_by_key("built_in_default")
        if option is None:
            return
        self.selected_key = option.key
        self.selected_config = option_to_config(option)
        for current_key, card in self.cards.items():
            card.set_selected(current_key == option.key)
        self.preview_label.setText(
            f"Home: {self.selected_config.home_url}\n"
            f"Search: {self.selected_config.search_engine_url}   ({self.selected_config.search_query_param}=...)"
        )

    def _use_defaults(self):
        self.selected_config = default_app_config()
        save_app_config(self.selected_config)
        self.done(QDialog.Accepted)

    def accept(self):
        save_app_config(self.selected_config)
        super().accept()

    def _play_intro_animations(self):
        widgets = [self.title_label, self.subtitle_label, self.preview_label]
        widgets.extend(list(self.cards.values()))
        widgets.extend([self.use_defaults_btn, self.continue_btn])

        for widget in widgets:
            effect = QGraphicsOpacityEffect(widget)
            effect.setOpacity(0.0)
            widget.setGraphicsEffect(effect)

        for i, widget in enumerate(widgets):
            end_rect = widget.geometry()
            start_rect = QRect(end_rect.x(), end_rect.y() + 10, end_rect.width(), end_rect.height())
            widget.setGeometry(start_rect)
            delay = i * FIRST_RUN_STAGGER_MS
            QTimer.singleShot(delay, lambda w=widget, s=start_rect, e=end_rect: self._animate_widget_in(w, s, e))

    def _animate_widget_in(self, widget: QWidget, start_rect: QRect, end_rect: QRect):
        animate_fade(widget, duration=FIRST_RUN_FADE_MS, start=0.0, end=1.0)
        animate_slide(widget, start_rect, end_rect, duration=FIRST_RUN_FADE_MS)


class JsonStore(QObject):
    changed = Signal()

    def __init__(self, path: Optional[str], parent=None):
        super().__init__(parent)
        self.path = path
        self._save_timer = QTimer(self)
        self._save_timer.setSingleShot(True)
        self._save_timer.setInterval(STORE_SAVE_DEBOUNCE_MS)
        self._save_timer.timeout.connect(self._flush)

    def schedule_save(self):
        if self.path:
            self._save_timer.start()
        self.changed.emit()

    def _atomic_write_json(self, data: dict):
        if not self.path:
            return
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, separators=(",", ":"))
        os.replace(tmp, self.path)

    def _flush(self):
        raise NotImplementedError


class CredentialStore(JsonStore):
    def __init__(self, service_id: str, index_path: Optional[str], use_keyring: bool, parent=None):
        super().__init__(index_path, parent)
        self.service_id = service_id
        self.use_keyring = use_keyring and HAVE_KEYRING
        self._index: Dict[str, List[str]] = {}
        self._load_index()

    def can_store(self) -> bool:
        return self.use_keyring

    def _load_index(self):
        if self.path and os.path.exists(self.path):
            try:
                with open(self.path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    self._index = {
                        str(origin): sorted({str(user) for user in users if isinstance(user, str)})
                        for origin, users in data.items()
                        if isinstance(users, list)
                    }
            except Exception:
                self._index = {}

    def _flush(self):
        self._atomic_write_json(self._index)

    def save_credentials(self, origin: str, username: str, password: str) -> bool:
        if not self.use_keyring or not origin or not password:
            return False
        username = username or ""
        users = set(self._index.get(origin, []))
        users.add(username)
        self._index[origin] = sorted(users)
        self.schedule_save()
        key = f"{origin}|{username}"
        try:
            keyring.set_password(self.service_id, key, password)
            return True
        except Exception:
            return False

    def get_credentials_for_origin(self, origin: str):
        if not self.use_keyring or not origin:
            return []
        out = []
        for user in self._index.get(origin, []):
            key = f"{origin}|{user}"
            try:
                pw = keyring.get_password(self.service_id, key)
            except Exception:
                pw = None
            if pw:
                out.append((user, pw))
        return out


class HistoryManager(JsonStore):
    def __init__(self, path: Optional[str], parent=None):
        super().__init__(path, parent)
        self.entries: List[dict] = []
        self.by_url: Dict[str, dict] = {}
        self._load()

    def _load(self):
        if not self.path or not os.path.exists(self.path):
            return
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                data = json.load(f)
            for item in data.get("entries", []):
                if not isinstance(item, dict):
                    continue
                url = item.get("url")
                if url:
                    self.entries.append(item)
                    self.by_url[url] = item
        except Exception:
            self.entries = []
            self.by_url = {}

    def _flush(self):
        self._atomic_write_json({"entries": self.entries[-HISTORY_MAX_ENTRIES:]})

    def record_visit(self, url: str, title: str):
        if not url or url.startswith("about:"):
            return
        now = time.time()
        entry = self.by_url.get(url)
        if entry:
            entry["title"] = title or entry.get("title") or ""
            entry["visit_count"] = int(entry.get("visit_count", 0)) + 1
            entry["last_visit"] = now
        else:
            entry = {"url": url, "title": title or "", "visit_count": 1, "last_visit": now}
            self.entries.append(entry)
            self.by_url[url] = entry

        if len(self.entries) > HISTORY_MAX_ENTRIES:
            self.entries = self.entries[-HISTORY_MAX_ENTRIES:]
            self.by_url = {e["url"]: e for e in self.entries if e.get("url")}
        self.schedule_save()

    def update_title(self, url: str, title: str):
        entry = self.by_url.get(url)
        if not entry:
            return
        new_title = title or entry.get("title") or ""
        if entry.get("title") != new_title:
            entry["title"] = new_title
            self.schedule_save()

    def suggestions(self, query: str, limit: int = HISTORY_SUGGEST_LIMIT) -> List[dict]:
        q = (query or "").strip().lower()
        now = time.time()
        results = []
        for entry in self.entries:
            title = (entry.get("title") or "").lower()
            url = (entry.get("url") or "").lower()
            if q and q not in title and q not in url:
                continue
            age_hours = max((now - float(entry.get("last_visit", now))) / 3600.0, 0.0)
            recency = 1.0 / (1.0 + age_hours)
            freq = min(int(entry.get("visit_count", 1)), 50) / 10.0
            results.append((recency * 2.5 + freq, entry))
        results.sort(key=lambda x: x[0], reverse=True)
        return [entry for _, entry in results[:limit]]


class BookmarkManager(JsonStore):
    def __init__(self, path: Optional[str], parent=None):
        super().__init__(path, parent)
        self.bookmarks: List[dict] = []
        self.by_keyword: Dict[str, dict] = {}
        self._load()

    def _load(self):
        if not self.path or not os.path.exists(self.path):
            return
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                data = json.load(f)
            for item in data.get("bookmarks", []):
                if not isinstance(item, dict):
                    continue
                keyword = (item.get("keyword") or "").lower()
                if keyword and item.get("url"):
                    self.bookmarks.append(item)
                    self.by_keyword[keyword] = item
        except Exception:
            self.bookmarks = []
            self.by_keyword = {}

    def _flush(self):
        self._atomic_write_json({"bookmarks": self.bookmarks})

    def add_bookmark(self, keyword: str, url: str, title: str = "", folder: str = "") -> bool:
        keyword = (keyword or "").strip().lower()
        if not keyword or not url:
            return False
        item = {"keyword": keyword, "url": url, "title": title or "", "folder": folder or ""}
        existing = self.by_keyword.get(keyword)
        if existing:
            existing.update(item)
        else:
            self.bookmarks.append(item)
            self.by_keyword[keyword] = item
        self.schedule_save()
        return True

    def resolve_keyword(self, text: str) -> Optional[str]:
        item = self.by_keyword.get((text or "").strip().lower())
        return item.get("url") if item else None

    def list_bookmarks(self) -> List[dict]:
        return list(self.bookmarks)


class RequestRuleStore(JsonStore):
    def __init__(self, path: Optional[str], parent=None):
        super().__init__(path, parent)
        self.rules = {"blocked_domains": list(DEFAULT_TRACKER_BLOCKLIST), "user_agent_overrides": {}}
        self._load()

    def _load(self):
        if not self.path or not os.path.exists(self.path):
            return
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                blocked_domains = data.get("blocked_domains")
                if isinstance(blocked_domains, list):
                    self.rules["blocked_domains"] = [
                        str(x).lower().strip(".") for x in blocked_domains if str(x).strip()
                    ]
                overrides = data.get("user_agent_overrides")
                if isinstance(overrides, dict):
                    self.rules["user_agent_overrides"] = {
                        str(k).lower().strip("."): str(v)
                        for k, v in overrides.items()
                        if str(k).strip() and str(v).strip()
                    }
        except Exception:
            pass

    def _flush(self):
        self._atomic_write_json(self.rules)

    def is_blocked(self, host: str) -> bool:
        host = (host or "").lower().strip(".")
        for rule in self.rules.get("blocked_domains", []):
            rule = (rule or "").lower().strip(".")
            if rule and (host == rule or host.endswith("." + rule)):
                return True
        return False

    def user_agent_for(self, host: str) -> Optional[str]:
        host = (host or "").lower().strip(".")
        overrides = self.rules.get("user_agent_overrides", {})
        if not isinstance(overrides, dict):
            return None
        for pattern, ua in overrides.items():
            pattern = (pattern or "").lower().strip(".")
            if pattern and ua and (host == pattern or host.endswith("." + pattern)):
                return ua
        return None


class RequestInterceptor(QWebEngineUrlRequestInterceptor):
    def __init__(self, rules: RequestRuleStore):
        super().__init__()
        self.rules = rules

    def interceptRequest(self, info):
        host = info.requestUrl().host()
        if self.rules.is_blocked(host):
            info.block(True)
            return
        ua = self.rules.user_agent_for(host)
        if ua:
            info.setHttpHeader(b"User-Agent", ua.encode("utf-8", errors="ignore"))


class PermissionsManager(JsonStore):
    def __init__(self, path: Optional[str], parent=None):
        super().__init__(path, parent)
        self.data: Dict[str, Dict[str, str]] = {}
        self._load()

    def _load(self):
        if not self.path or not os.path.exists(self.path):
            return
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                self.data = data
        except Exception:
            self.data = {}

    def _flush(self):
        self._atomic_write_json(self.data)

    def get(self, origin: str, feature_key: str) -> Optional[bool]:
        val = self.data.get(origin or "", {}).get(feature_key or "")
        if val == "allow":
            return True
        if val == "deny":
            return False
        return None

    def set(self, origin: str, feature_key: str, allow: bool):
        origin = origin or ""
        feature_key = feature_key or ""
        self.data.setdefault(origin, {})[feature_key] = "allow" if allow else "deny"
        self.schedule_save()

    def list_entries(self) -> List[tuple]:
        out = []
        for origin, feats in self.data.items():
            for feature_key, val in feats.items():
                out.append((origin, feature_key, val == "allow"))
        return out

    def feature_label(self, feature_key: str) -> str:
        mapping = {
            "MediaAudioCapture": "Microphone",
            "MediaVideoCapture": "Camera",
            "MediaAudioVideoCapture": "Camera + Microphone",
            "ClipboardRead": "Clipboard",
            "ClipboardReadWrite": "Clipboard",
            POPUP_FEATURE_KEY: "Pop-ups",
        }
        return mapping.get(feature_key, feature_key)


class DownloadItemWidget(QWidget):
    def __init__(self, request):
        super().__init__()
        self.request = request
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(10)

        self.label = QLabel(request.downloadFileName() or "download")
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setTextVisible(False)
        self.open_btn = QPushButton("Show Folder")
        self.cancel_btn = QPushButton("Cancel")

        self.open_btn.clicked.connect(self.open_folder)
        self.cancel_btn.clicked.connect(self.cancel)

        layout.addWidget(self.label, 2)
        layout.addWidget(self.progress, 3)
        layout.addWidget(self.open_btn, 1)
        layout.addWidget(self.cancel_btn, 1)

        request.downloadProgress.connect(self.on_progress)
        request.finished.connect(self.on_finished)

    def on_progress(self, received, total):
        if total > 0:
            self.progress.setValue(max(0, min(100, int((received / total) * 100))))

    def on_finished(self):
        self.progress.setValue(100)
        self.cancel_btn.setEnabled(False)

    def open_folder(self):
        folder = self.request.downloadDirectory()
        if folder:
            QDesktopServices.openUrl(QUrl.fromLocalFile(folder))

    def cancel(self):
        self.request.cancel()


class DownloadManager(QDialog):
    def __init__(self, download_dir: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Downloads")
        self.setModal(False)
        self.download_dir = download_dir
        self.setMinimumWidth(620)

        layout = QVBoxLayout(self)
        self.list = QListWidget()
        layout.addWidget(self.list)

    def handle_download(self, request):
        try:
            request.setDownloadDirectory(self.download_dir)
        except Exception:
            pass
        try:
            request.accept()
        except Exception:
            pass

        widget = DownloadItemWidget(request)
        item = QListWidgetItem(self.list)
        item.setSizeHint(widget.sizeHint())
        self.list.addItem(item)
        self.list.setItemWidget(item, widget)
        self.show()
        self.raise_()
        self.activateWindow()


@dataclass
class CommandAction:
    title: str
    subtitle: str
    handler: Callable[[], None]


class CommandRegistry:
    def __init__(self, browser):
        self.browser = browser
        self.providers: List[Callable[[str], List[CommandAction]]] = []

    def register(self, provider: Callable[[str], List[CommandAction]]):
        self.providers.append(provider)

    def actions(self, query: str) -> List[CommandAction]:
        out: List[CommandAction] = []
        for provider in self.providers:
            try:
                out.extend(provider(query))
            except Exception:
                continue
        return out


class CommandPalette(QDialog):
    def __init__(self, browser):
        super().__init__(browser)
        self.browser = browser
        self.setWindowTitle("Command Palette")
        self.setModal(False)
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setObjectName("commandPalette")
        self.setMinimumWidth(560)

        layout = QVBoxLayout(self)
        self.input = QLineEdit()
        self.input.setPlaceholderText("Type a command or query")
        self.list = QListWidget()
        self.list.setSelectionMode(QAbstractItemView.SingleSelection)
        layout.addWidget(self.input)
        layout.addWidget(self.list)

        self._actions: List[CommandAction] = []
        self.input.textChanged.connect(self.refresh)
        self.input.returnPressed.connect(self.run_selected)
        self.list.itemActivated.connect(self._on_item_activated)

    def open(self):
        self.input.clear()
        self.refresh()
        self.show()
        self.raise_()
        self.activateWindow()
        self.input.setFocus()

    def refresh(self):
        self._actions = self.browser.command_registry.actions(self.input.text())
        self.list.clear()
        for action in self._actions:
            item = QListWidgetItem(action.title)
            item.setToolTip(action.subtitle)
            self.list.addItem(item)
        if self.list.count() > 0:
            self.list.setCurrentRow(0)

    def run_selected(self):
        row = self.list.currentRow()
        if row < 0 and self._actions:
            row = 0
        if 0 <= row < len(self._actions):
            self._actions[row].handler()
        self.close()

    def _on_item_activated(self, _item):
        self.run_selected()


PW_CAPTURE_JS = r"""
(function(){
  if (window.__pwcap_installed) return;
  window.__pwcap_installed = true;

  function likelyUserField(form, pw){
    const byAttr = form.querySelector('input[name*=user i], input[name*=email i], input[id*=user i], input[id*=email i]');
    if (byAttr) return byAttr;
    const txt = form.querySelector('input[type="text"], input[type="email"]');
    if (txt) return txt;
    const inputs = Array.from(form.querySelectorAll('input'));
    const idx = inputs.indexOf(pw);
    for (let i = idx - 1; i >= 0; i--){
      if (inputs[i].type === 'text' || inputs[i].type === 'email') return inputs[i];
    }
    return null;
  }

  function handleForm(form){
    if (form.__pwcap_bound) return;
    form.__pwcap_bound = true;

    form.addEventListener('submit', function(){
      try {
        const pw = form.querySelector('input[type="password"]');
        if (!pw || !pw.value) return;
        const user = likelyUserField(form, pw);
        const payload = {
          origin: location.origin,
          host: location.host,
          href: location.href,
          username: user ? (user.value || '') : '',
          password: pw.value || ''
        };
        console.log('__PW_CAPTURE__' + JSON.stringify(payload));
      } catch (e) {}
    }, true);
  }

  Array.from(document.forms).forEach(handleForm);

  const mo = new MutationObserver(function(muts){
    muts.forEach(m => {
      m.addedNodes && m.addedNodes.forEach(n => {
        if (n.nodeType === 1) {
          if (n.tagName === 'FORM') handleForm(n);
          n.querySelectorAll && n.querySelectorAll('form').forEach(handleForm);
        }
      });
    });
  });
  mo.observe(document.documentElement, {childList: true, subtree: true});
})();
"""


class CapturingPage(QWebEnginePage):
    def __init__(self, profile: QWebEngineProfile, parent=None, main_window=None, profile_name=None, is_ephemeral=False):
        super().__init__(profile, parent)
        self.main_window = main_window
        self.profile_name = profile_name
        self.is_ephemeral = is_ephemeral

    def javaScriptConsoleMessage(self, level, message, line, source):
        if isinstance(message, str) and message.startswith("__PW_CAPTURE__"):
            try:
                payload = json.loads(message[len("__PW_CAPTURE__"):])
            except Exception:
                payload = None
            if payload and self.main_window:
                self.main_window.handle_pw_capture(self.profile_name, payload, self.is_ephemeral)
            return
        if SHOW_PAGE_JS_CONSOLE:
            super().javaScriptConsoleMessage(level, message, line, source)

    def featurePermissionRequested(self, security_origin, feature):
        if self.main_window:
            self.main_window.handle_feature_permission_request(self.profile_name, self, security_origin, feature)

    def createWindow(self, _type):
        if self.main_window:
            return self.main_window.handle_popup_request(self.profile_name, self)
        return None


class BrowserTab(QWebEngineView):
    def __init__(self, profile: QWebEngineProfile, url: Optional[str] = None, main_window=None, profile_name=None, is_ephemeral=False):
        super().__init__(parent=main_window)
        self.main_window = main_window
        self.profile_name = profile_name
        self.is_ephemeral = is_ephemeral
        self.zoom_factor = ZOOM_DEFAULT

        page = CapturingPage(profile, self, main_window=main_window, profile_name=profile_name, is_ephemeral=is_ephemeral)
        self.setPage(page)
        self.setZoomFactor(self.zoom_factor)
        self.setUrl(QUrl(url or (main_window.config.home_url if main_window else HOME_URL)))

        if self.is_ephemeral:
            self._idle_timer = QTimer(self)
            self._idle_timer.setInterval(EPHEMERAL_IDLE_MS)
            self._idle_timer.setSingleShot(True)
            self._idle_timer.timeout.connect(self._on_idle_timeout)
            self._idle_timer.start()
            self.installEventFilter(self)
            self.loadStarted.connect(self.reset_idle_timer)
            self.loadFinished.connect(lambda _ok: self.reset_idle_timer())
            self.urlChanged.connect(lambda _u: self.reset_idle_timer())

    def reset_idle_timer(self):
        if self.is_ephemeral:
            self._idle_timer.start()

    def _on_idle_timeout(self):
        if self.main_window:
            self.main_window.close_ephemeral_tab(self)

    def eventFilter(self, _obj, event):
        if self.is_ephemeral and event.type() in (QEvent.MouseButtonPress, QEvent.KeyPress, QEvent.Wheel, QEvent.FocusIn):
            self.reset_idle_timer()
        return super().eventFilter(_obj, event)


@dataclass
class ProfileContext:
    name: str
    profile: QWebEngineProfile
    tabs: QTabWidget
    history: HistoryManager
    bookmarks: BookmarkManager
    permissions: PermissionsManager
    interceptor: RequestInterceptor
    rules: RequestRuleStore
    creds: CredentialStore
    persistent: bool
    downloads: Optional[DownloadManager] = None


def _web_attr(name: str):
    direct = getattr(QWebEngineSettings, name, None)
    if direct is not None:
        return direct
    enum_cls = getattr(QWebEngineSettings, "WebAttribute", None)
    if enum_cls is not None:
        return getattr(enum_cls, name, None)
    return None


def _set_web_attribute(settings, name: str, value: bool):
    attr = _web_attr(name)
    if attr is not None:
        try:
            settings.setAttribute(attr, value)
        except Exception:
            pass


def _set_unknown_scheme_policy(settings):
    policy = getattr(QWebEngineSettings, "AllowUnknownUrlSchemesFromUserInteraction", None)
    if policy is None:
        policy_cls = getattr(QWebEngineSettings, "UnknownUrlSchemePolicy", None)
        if policy_cls is not None:
            policy = getattr(policy_cls, "AllowUnknownUrlSchemesFromUserInteraction", None)
    if policy is not None:
        try:
            settings.setUnknownUrlSchemePolicy(policy)
        except Exception:
            pass


class Browser(QMainWindow):
    def __init__(self, config: AppConfig):
        super().__init__()
        self.config = config
        self.setWindowTitle(APP_NAME)
        self.setWindowIcon(QIcon("./Werm_Icon.jpg"))
        self.resize(1280, 840)

        self.profile_contexts: Dict[str, Optional[ProfileContext]] = {}
        self.current_profile_name: Optional[str] = DEFAULT_PROFILE_NAME

        self.tab_stack = QStackedWidget()
        self.setCentralWidget(self.tab_stack)

        nav = QToolBar()
        nav.setMovable(False)
        nav.setObjectName("navBar")
        self.addToolBar(nav)

        style = self.style()

        self.back_act = QAction(style.standardIcon(QStyle.SP_ArrowBack), "Back", self)
        self.back_act.setToolTip("Back (Alt+Left)")
        self.back_act.triggered.connect(lambda: self.current_tab().back() if self.current_tab() else None)
        nav.addAction(self.back_act)

        self.fwd_act = QAction(style.standardIcon(QStyle.SP_ArrowForward), "Forward", self)
        self.fwd_act.setToolTip("Forward (Alt+Right)")
        self.fwd_act.triggered.connect(lambda: self.current_tab().forward() if self.current_tab() else None)
        nav.addAction(self.fwd_act)

        self.reload_act = QAction(style.standardIcon(QStyle.SP_BrowserReload), "Reload", self)
        self.reload_act.setToolTip("Reload (Ctrl+R)")
        self.reload_act.triggered.connect(lambda: self.current_tab().reload() if self.current_tab() else None)
        nav.addAction(self.reload_act)

        self.newtab_act = QAction("New", self)
        self.newtab_act.setToolTip("New Tab (Ctrl+T)")
        self.newtab_act.triggered.connect(self.add_tab)
        nav.addAction(self.newtab_act)

        self.autofill_act = QAction("Fill", self)
        self.autofill_act.setToolTip("Fill saved login for this site")
        self.autofill_act.triggered.connect(self.autofill_current)
        nav.addAction(self.autofill_act)

        self.downloads_act = QAction("Downloads", self)
        self.downloads_act.triggered.connect(lambda: self.get_download_manager(self.current_context()).show())
        nav.addAction(self.downloads_act)

        self.urlbar = QLineEdit()
        self.urlbar.setPlaceholderText("Search or type a URL")
        self.urlbar.setClearButtonEnabled(True)
        self.urlbar.returnPressed.connect(self.navigate_from_omnibar)
        self.urlbar.textChanged.connect(self._schedule_omnibar_suggestions)
        self.urlbar.setMinimumWidth(560)
        nav.addWidget(self.urlbar)

        self.omni_model = QStandardItemModel(self)
        self.omni_completer = QCompleter(self.omni_model, self)
        self.omni_completer.setCaseSensitivity(Qt.CaseInsensitive)
        self.omni_completer.setCompletionMode(QCompleter.PopupCompletion)
        self.omni_completer.activated.connect(self._on_omnibar_suggestion)
        self.urlbar.setCompleter(self.omni_completer)

        self.omnibar_timer = QTimer(self)
        self.omnibar_timer.setSingleShot(True)
        self.omnibar_timer.setInterval(OMNIBAR_SUGGEST_DEBOUNCE_MS)
        self.omnibar_timer.timeout.connect(self._update_omnibar_suggestions)

        self.command_registry = CommandRegistry(self)
        self._register_commands()
        self.command_palette = CommandPalette(self)

        self._add_shortcuts()
        self._init_profiles()
        self.switch_profile(DEFAULT_PROFILE_NAME)
        self.update_nav_buttons()

    def search_label(self) -> str:
        return self.config.search_engine_name or self.config.search_engine_url

    def _init_profiles(self):
        for name in PROFILE_NAMES:
            self.profile_contexts[name] = None
        self.ensure_profile(DEFAULT_PROFILE_NAME)

    def ensure_profile(self, profile_name: str):
        if profile_name not in self.profile_contexts or self.profile_contexts[profile_name] is not None:
            return
        ctx = self._create_profile_context(profile_name)
        self.profile_contexts[profile_name] = ctx
        self.tab_stack.addWidget(ctx.tabs)
        self.add_tab(self.config.home_url, profile_name=profile_name, make_active=False)

    def _configure_profile_security(self, profile: QWebEngineProfile):
        settings = profile.settings()
        _set_web_attribute(settings, "JavascriptCanAccessClipboard", False)
        _set_web_attribute(settings, "JavascriptCanPaste", False)
        _set_web_attribute(settings, "AllowRunningInsecureContent", False)
        _set_web_attribute(settings, "AllowGeolocationOnInsecureOrigins", False)
        _set_web_attribute(settings, "ScreenCaptureEnabled", False)
        _set_web_attribute(settings, "HyperlinkAuditingEnabled", False)
        _set_web_attribute(settings, "ReadingFromCanvasEnabled", False)
        _set_web_attribute(settings, "PlaybackRequiresUserGesture", True)
        _set_web_attribute(settings, "AutoLoadIconsForPage", True)
        _set_unknown_scheme_policy(settings)

    def _create_profile_context(self, profile_name: str) -> ProfileContext:
        persistent = profile_name != PRIVATE_PROFILE_NAME
        profile = self._make_persistent_profile(profile_name) if persistent else self._make_private_profile()
        self._configure_profile_security(profile)
        self._install_pw_capture_script(profile)

        root = profile_root_dir(profile_name)
        rules_path = os.path.join(root, "request_rules.json") if root else None
        hist_path = os.path.join(root, "history.json") if root else None
        bookmarks_path = os.path.join(root, "bookmarks.json") if root else None
        permissions_path = os.path.join(root, "permissions.json") if root else None
        creds_path = os.path.join(root, "creds_index.json") if root else None

        rules = RequestRuleStore(rules_path, self)
        interceptor = RequestInterceptor(rules)
        profile.setUrlRequestInterceptor(interceptor)

        history = HistoryManager(hist_path, self)
        bookmarks = BookmarkManager(bookmarks_path, self)
        permissions = PermissionsManager(permissions_path, self)
        creds = CredentialStore(f"{SERVICE_ID}:{profile_name}", creds_path, use_keyring=persistent, parent=self)

        tabs = QTabWidget()
        tabs.setDocumentMode(True)
        tabs.setMovable(True)
        tabs.setTabsClosable(True)
        tabs.tabCloseRequested.connect(lambda idx, name=profile_name: self.close_tab(idx, name))
        tabs.currentChanged.connect(lambda idx, name=profile_name: self.on_tab_changed(name, idx))

        return ProfileContext(
            name=profile_name,
            profile=profile,
            tabs=tabs,
            history=history,
            bookmarks=bookmarks,
            permissions=permissions,
            interceptor=interceptor,
            rules=rules,
            creds=creds,
            persistent=persistent,
        )

    def _make_persistent_profile(self, name: str) -> QWebEngineProfile:
        root = profile_root_dir(name) or app_data_dir()
        cache = os.path.join(root, "cache")
        storage = os.path.join(root, "storage")
        os.makedirs(cache, exist_ok=True)
        os.makedirs(storage, exist_ok=True)

        profile = QWebEngineProfile(name, self)
        profile.setCachePath(cache)
        profile.setPersistentStoragePath(storage)
        try:
            profile.setHttpCacheMaximumSize(64 * 1024 * 1024)
        except Exception:
            pass
        try:
            profile.setPersistentCookiesPolicy(QWebEngineProfile.ForcePersistentCookies)
        except Exception:
            try:
                profile.setPersistentCookiesPolicy(QWebEngineProfile.PersistentCookiesPolicy.ForcePersistentCookies)
            except Exception:
                pass
        return profile

    def _make_private_profile(self) -> QWebEngineProfile:
        return QWebEngineProfile(self)

    def _make_ephemeral_profile(self, base_ctx: ProfileContext) -> QWebEngineProfile:
        profile = QWebEngineProfile(self)
        self._configure_profile_security(profile)
        profile.setUrlRequestInterceptor(base_ctx.interceptor)
        self._install_pw_capture_script(profile)
        return profile

    def _install_pw_capture_script(self, profile: QWebEngineProfile):
        scripts = profile.scripts()
        try:
            for existing in scripts.toList():
                if existing.name() == "pw-capture":
                    return
        except Exception:
            pass
        script = QWebEngineScript()
        script.setName("pw-capture")
        script.setInjectionPoint(QWebEngineScript.DocumentReady)
        script.setRunsOnSubFrames(True)
        script.setWorldId(QWebEngineScript.MainWorld)
        script.setSourceCode(PW_CAPTURE_JS)
        scripts.insert(script)

    def get_download_manager(self, ctx: ProfileContext) -> DownloadManager:
        if ctx.downloads is None:
            ctx.downloads = DownloadManager(profile_download_dir(ctx.name), parent=self)
            ctx.profile.downloadRequested.connect(ctx.downloads.handle_download)
        return ctx.downloads

    def switch_profile(self, profile_name: str):
        if profile_name not in self.profile_contexts:
            return
        self.ensure_profile(profile_name)
        self.current_profile_name = profile_name
        ctx = self.profile_contexts[profile_name]
        self.tab_stack.setCurrentWidget(ctx.tabs)
        if ctx.tabs.count() == 0:
            self.add_tab(self.config.home_url, profile_name=profile_name)
        self.on_tab_changed(profile_name, ctx.tabs.currentIndex())
        self._update_omnibar_suggestions()

    def current_context(self) -> ProfileContext:
        self.ensure_profile(self.current_profile_name)
        return self.profile_contexts[self.current_profile_name]

    def add_tab(self, url: Optional[str] = None, profile_name: Optional[str] = None, make_active: bool = True, ephemeral: bool = False):
        profile_name = profile_name or self.current_profile_name
        self.ensure_profile(profile_name)
        ctx = self.profile_contexts[profile_name]
        profile = ctx.profile if not ephemeral else self._make_ephemeral_profile(ctx)

        tab = BrowserTab(profile, url or self.config.home_url, main_window=self, profile_name=profile_name, is_ephemeral=ephemeral)
        if ephemeral:
            tab._ephemeral_profile = profile

        index = ctx.tabs.addTab(tab, "New Tab")
        if make_active:
            ctx.tabs.setCurrentIndex(index)

        tab.urlChanged.connect(lambda qurl, t=tab, n=profile_name: self.on_url_changed(n, t, qurl))
        tab.titleChanged.connect(lambda title, t=tab, n=profile_name: self.on_title_changed(n, t, title))
        tab.iconChanged.connect(lambda icon, t=tab, n=profile_name: self.on_icon_changed(n, t, icon))
        tab.loadFinished.connect(lambda _ok, t=tab, n=profile_name: self._post_load_actions(n, t))

        if make_active and profile_name == self.current_profile_name:
            self.on_tab_changed(profile_name, index)
        return tab

    def close_tab(self, index: int, profile_name: Optional[str] = None):
        profile_name = profile_name or self.current_profile_name
        self.ensure_profile(profile_name)
        ctx = self.profile_contexts[profile_name]
        if ctx.tabs.count() <= 1:
            tab = ctx.tabs.widget(0)
            if tab and getattr(tab, "is_ephemeral", False):
                ctx.tabs.removeTab(0)
                self.add_tab(self.config.home_url, profile_name=profile_name)
            elif tab:
                tab.setUrl(QUrl(self.config.home_url))
            return

        widget = ctx.tabs.widget(index)
        ctx.tabs.removeTab(index)
        if widget:
            widget.deleteLater()
        if profile_name == self.current_profile_name:
            self.update_nav_buttons()

    def close_ephemeral_tab(self, tab: BrowserTab):
        ctx = self.profile_contexts.get(tab.profile_name)
        if not ctx:
            return
        idx = ctx.tabs.indexOf(tab)
        if idx != -1:
            self.close_tab(idx, tab.profile_name)

    def current_tab(self) -> Optional[BrowserTab]:
        return self.current_context().tabs.currentWidget()

    def _set_urlbar_text(self, text: str):
        if getattr(self, "urlbar", None) is None:
            return
        self.urlbar.blockSignals(True)
        self.urlbar.setText(text)
        self.urlbar.blockSignals(False)

    def on_tab_changed(self, profile_name: str, index: int):
        if profile_name != self.current_profile_name:
            return
        tab = self.current_tab()
        if tab:
            self._set_urlbar_text(tab.url().toString())
        self.update_nav_buttons()

    def on_url_changed(self, profile_name: str, tab: BrowserTab, qurl: QUrl):
        if profile_name == self.current_profile_name and tab == self.current_tab():
            self._set_urlbar_text(qurl.toString())
            self.update_nav_buttons()

    def on_title_changed(self, profile_name: str, tab: BrowserTab, title: str):
        ctx = self.profile_contexts[profile_name]
        idx = ctx.tabs.indexOf(tab)
        if idx != -1:
            clean = title.strip() if title else tab.url().host() or "New Tab"
            ctx.tabs.setTabText(idx, clean[:30] + ("…" if len(clean) > 30 else ""))
        if not tab.is_ephemeral:
            ctx.history.update_title(tab.url().toString(), title)

    def on_icon_changed(self, profile_name: str, tab: BrowserTab, icon):
        ctx = self.profile_contexts[profile_name]
        idx = ctx.tabs.indexOf(tab)
        if idx != -1:
            ctx.tabs.setTabIcon(idx, icon)

    def update_nav_buttons(self):
        tab = self.current_tab()
        if not tab:
            self.back_act.setEnabled(False)
            self.fwd_act.setEnabled(False)
            self.reload_act.setEnabled(False)
            self.autofill_act.setEnabled(False)
            return
        history = tab.history()
        self.back_act.setEnabled(history.canGoBack())
        self.fwd_act.setEnabled(history.canGoForward())
        self.reload_act.setEnabled(True)
        self.autofill_act.setEnabled(not tab.is_ephemeral)

    def navigate_from_omnibar(self):
        tab = self.current_tab()
        if tab:
            tab.setUrl(self._resolve_omnibox(self.urlbar.text()))

    def _resolve_omnibox(self, text: str) -> QUrl:
        bookmark_url = self.current_context().bookmarks.resolve_keyword(text)
        if bookmark_url:
            return QUrl(bookmark_url)
        return normalize_url_or_search(text, config=self.config)

    def _post_load_actions(self, profile_name: str, tab: BrowserTab):
        if not tab.is_ephemeral:
            self.profile_contexts[profile_name].history.record_visit(tab.url().toString(), tab.title() or "")

    def handle_pw_capture(self, profile_name: str, payload: dict, is_ephemeral: bool):
        if is_ephemeral:
            return
        origin = (payload.get("origin") or "").strip().lower()
        username = payload.get("username") or ""
        password = payload.get("password") or ""
        if not origin or not password:
            return
        if REQUIRE_HTTPS_FOR_PASSWORDS and not origin.startswith("https://"):
            return

        ctx = self.profile_contexts[profile_name]
        if not ctx.creds.can_store():
            return

        res = QMessageBox.question(
            self,
            "Save password?",
            f"Save password for:\n{origin}\n\nUser: {username or '(blank)'}",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if res == QMessageBox.Yes and not ctx.creds.save_credentials(origin, username, password):
            QMessageBox.warning(self, "Password not saved", "The OS keychain could not store this password.")

    def try_autofill(self, profile_name: str, tab: BrowserTab):
        if tab.is_ephemeral:
            return
        origin = origin_from_qurl(tab.url())
        if not origin:
            return
        ctx = self.profile_contexts[profile_name]
        creds = ctx.creds.get_credentials_for_origin(origin)
        if not creds:
            QMessageBox.information(self, "No saved login", f"No saved credentials for:\n{origin}")
            return

        username, password = creds[0]
        js = f"""
        (() => {{
          const pw = document.querySelector('input[type="password"]');
          if (!pw) return false;
          const form = pw.form || document;
          const usr = form.querySelector(
            'input[name*=user i], input[name*=email i], input[id*=user i], input[id*=email i], input[type="text"], input[type="email"]'
          );
          if (usr) {{
            usr.value = {json.dumps(username)};
            usr.dispatchEvent(new Event('input', {{ bubbles: true }}));
            usr.dispatchEvent(new Event('change', {{ bubbles: true }}));
          }}
          pw.value = {json.dumps(password)};
          pw.dispatchEvent(new Event('input', {{ bubbles: true }}));
          pw.dispatchEvent(new Event('change', {{ bubbles: true }}));
          return true;
        }})();
        """

        def after_fill(ok):
            if ok is not True:
                QMessageBox.information(self, "Autofill", "No compatible password field was found on this page.")

        tab.page().runJavaScript(js, after_fill)

    def autofill_current(self):
        tab = self.current_tab()
        if tab:
            self.try_autofill(self.current_profile_name, tab)

    def handle_feature_permission_request(self, profile_name: str, page: QWebEnginePage, security_origin, feature):
        ctx = self.profile_contexts[profile_name]
        origin = security_origin.toString()
        feature_key = getattr(feature, "name", str(int(feature)))
        decision = ctx.permissions.get(origin, feature_key)
        if decision is None:
            label = ctx.permissions.feature_label(feature_key)
            decision = self._ask_permission(origin, label)
            ctx.permissions.set(origin, feature_key, decision)
        perm = QWebEnginePage.PermissionGrantedByUser if decision else QWebEnginePage.PermissionDeniedByUser
        page.setFeaturePermission(security_origin, feature, perm)

    def handle_popup_request(self, profile_name: str, opener_page: QWebEnginePage):
        ctx = self.profile_contexts[profile_name]
        origin = origin_from_qurl(opener_page.url()) or opener_page.url().toString()
        decision = ctx.permissions.get(origin, POPUP_FEATURE_KEY)
        if decision is None:
            decision = self._ask_permission(origin, "Pop-ups")
            ctx.permissions.set(origin, POPUP_FEATURE_KEY, decision)
        if not decision:
            return None
        tab = self.add_tab(profile_name=profile_name)
        return tab.page()

    def _ask_permission(self, origin: str, label: str) -> bool:
        res = QMessageBox.question(
            self,
            "Permission request",
            f"Allow {label} for\n{origin}?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        return res == QMessageBox.Yes

    def open_permissions_dialog(self):
        ctx = self.current_context()
        dlg = QDialog(self)
        dlg.setWindowTitle("Permissions")
        dlg.setModal(False)
        layout = QVBoxLayout(dlg)
        table = QTableWidget(0, 3)
        table.setHorizontalHeaderLabels(["Site", "Feature", "Allow"])
        table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        table.setSelectionBehavior(QAbstractItemView.SelectRows)
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        layout.addWidget(table)

        entries = ctx.permissions.list_entries()
        table.setRowCount(len(entries))
        for row, (origin, feature_key, allow) in enumerate(entries):
            table.setItem(row, 0, QTableWidgetItem(origin))
            table.setItem(row, 1, QTableWidgetItem(ctx.permissions.feature_label(feature_key)))
            box = QCheckBox()
            box.setChecked(allow)
            box.toggled.connect(lambda checked, o=origin, f=feature_key: ctx.permissions.set(o, f, checked))
            table.setCellWidget(row, 2, box)

        dlg.setMinimumWidth(620)
        dlg.show()
        dlg.raise_()
        dlg.activateWindow()

    def _schedule_omnibar_suggestions(self):
        self.omnibar_timer.start()

    def _update_omnibar_suggestions(self):
        suggestions = self.current_context().history.suggestions(self.urlbar.text())
        self.omni_model.clear()
        for entry in suggestions:
            title = entry.get("title") or ""
            url = entry.get("url") or ""
            display = f"{title} — {url}" if title else url
            item = QStandardItem(display)
            item.setData(url, Qt.UserRole)
            self.omni_model.appendRow(item)

    def _on_omnibar_suggestion(self, value):
        url = value.data(Qt.UserRole) if isinstance(value, QModelIndex) else value if isinstance(value, str) else None
        if url and self.current_tab():
            self.current_tab().setUrl(QUrl(url))

    def _apply_zoom(self, delta: float, absolute: bool = False):
        tab = self.current_tab()
        if not tab:
            return
        new_zoom = delta if absolute else tab.zoom_factor + delta
        tab.zoom_factor = max(ZOOM_MIN, min(ZOOM_MAX, new_zoom))
        tab.setZoomFactor(tab.zoom_factor)

    def zoom_in(self):
        self._apply_zoom(ZOOM_STEP)

    def zoom_out(self):
        self._apply_zoom(-ZOOM_STEP)

    def zoom_reset(self):
        self._apply_zoom(ZOOM_DEFAULT, absolute=True)

    def _register_commands(self):
        def open_or_search_provider(query: str) -> List[CommandAction]:
            q = (query or "").strip()
            if not q:
                return []
            if looks_like_url(q):
                url = q if "://" in q else f"https://{q}"
                return [CommandAction(f"Open URL: {url}", "Open in current tab", lambda u=url: self.current_tab().setUrl(QUrl(u)) if self.current_tab() else None)]
            return [CommandAction(
                f"Search: {q}",
                f"Search with {self.search_label()}",
                lambda text=q: self.current_tab().setUrl(QUrl(build_search_url(text, config=self.config))) if self.current_tab() else None,
            )]

        def switch_tab_provider(query: str) -> List[CommandAction]:
            q = (query or "").strip().lower()
            if not q:
                return []
            ctx = self.current_context()
            actions = []
            for i in range(ctx.tabs.count()):
                title = (ctx.tabs.tabText(i) or "").strip()
                if q in title.lower():
                    actions.append(CommandAction(f"Switch tab: {title}", "Activate tab", lambda idx=i: ctx.tabs.setCurrentIndex(idx)))
            return actions

        def switch_profile_provider(query: str) -> List[CommandAction]:
            q = (query or "").strip().lower()
            if not q or (not q.startswith("profile") and not q.startswith("switch")):
                return []
            return [CommandAction(f"Switch profile: {name}", "Switch active profile", lambda n=name: self.switch_profile(n)) for name in PROFILE_NAMES]

        def quick_actions_provider(query: str) -> List[CommandAction]:
            q = (query or "").strip().lower()
            actions = []
            if q.startswith("reload"):
                actions.append(CommandAction("Reload tab", "Reload current tab", lambda: self.current_tab().reload() if self.current_tab() else None))
            if q.startswith("close"):
                actions.append(CommandAction("Close tab", "Close current tab", lambda: self.close_tab(self.current_context().tabs.currentIndex())))
            if q.startswith("ephemeral") or q.startswith("new ephemeral"):
                actions.append(CommandAction("New ephemeral tab", "No history, no persistent cookies, auto-closes on idle", lambda: self.add_tab(ephemeral=True)))
            if q.startswith("downloads"):
                actions.append(CommandAction("Show downloads", "Open download manager", lambda: self.get_download_manager(self.current_context()).show()))
            if q.startswith("permissions"):
                actions.append(CommandAction("Permissions", "Open site permissions", self.open_permissions_dialog))
            if q.startswith("profile"):
                actions.extend(switch_profile_provider("switch"))
            return actions

        def bookmarks_provider(query: str) -> List[CommandAction]:
            q = (query or "").strip()
            lower = q.lower()
            ctx = self.current_context()
            actions = []
            if lower.startswith("bm add ") or lower.startswith("bookmark add "):
                parts = q.split()
                if len(parts) >= 4:
                    keyword = parts[2]
                    url = parts[3]
                    folder = " ".join(parts[4:]) if len(parts) > 4 else ""
                    actions.append(CommandAction(f"Add bookmark: {keyword} → {url}", f"Folder: {folder or 'root'}", lambda k=keyword, u=url, f=folder: ctx.bookmarks.add_bookmark(k, u, folder=f)))
                return actions
            for bm in ctx.bookmarks.list_bookmarks():
                keyword = bm.get("keyword", "")
                title = bm.get("title") or keyword
                url = bm.get("url")
                if lower and lower not in keyword and lower not in title.lower():
                    continue
                actions.append(CommandAction(f"Open bookmark: {title}", url, lambda u=url: self.current_tab().setUrl(QUrl(u)) if self.current_tab() else None))
            return actions

        self.command_registry.register(open_or_search_provider)
        self.command_registry.register(switch_tab_provider)
        self.command_registry.register(switch_profile_provider)
        self.command_registry.register(bookmarks_provider)
        self.command_registry.register(quick_actions_provider)

    def _add_shortcuts(self):
        def add(seq, fn):
            act = QAction(self)
            act.setShortcut(QKeySequence(seq) if isinstance(seq, str) else seq)
            act.triggered.connect(fn)
            self.addAction(act)

        add("Ctrl+L", self._focus_omnibar)
        add("Ctrl+T", self.add_tab)
        add("Ctrl+W", lambda: self.close_tab(self.current_context().tabs.currentIndex()))
        add("Ctrl+R", lambda: self.current_tab().reload() if self.current_tab() else None)
        add("Ctrl+K", self.command_palette.open)
        add("Ctrl++", self.zoom_in)
        add("Ctrl+=", self.zoom_in)
        add("Ctrl+-", self.zoom_out)
        add("Ctrl+0", self.zoom_reset)
        add(QKeySequence(Qt.ALT | Qt.Key_Left), lambda: self.current_tab().back() if self.current_tab() else None)
        add(QKeySequence(Qt.ALT | Qt.Key_Right), lambda: self.current_tab().forward() if self.current_tab() else None)

    def _focus_omnibar(self):
        self.urlbar.setFocus()
        self.urlbar.selectAll()


def apply_dark_style(app: QApplication):
    base = QFontDatabase.systemFont(QFontDatabase.GeneralFont)
    base.setPointSize(11 if base.pointSize() <= 0 else max(10, base.pointSize()))
    app.setFont(base)

    app.setStyleSheet("""
    QMainWindow {
        background-color: #0f1115;
    }

    QToolBar#navBar {
        background: #151922;
        border: none;
        padding: 10px;
        spacing: 8px;
    }

    QToolButton {
        color: #eef2ff;
        background: transparent;
        border: 1px solid transparent;
        padding: 7px 12px;
        border-radius: 11px;
    }

    QToolButton:hover {
        background: #202635;
        border: 1px solid #2a3348;
    }

    QToolButton:pressed {
        background: #273147;
    }

    QLineEdit {
        background: #161b26;
        color: #eef2ff;
        border: 1px solid #2b3447;
        border-radius: 16px;
        padding: 11px 14px;
        selection-background-color: #3b4d73;
    }

    QLineEdit:focus {
        border: 1px solid #4d6799;
        background: #1a2030;
    }

    QTabWidget::pane {
        border: none;
    }

    QTabBar {
        background: #0f1115;
    }

    QTabBar::tab {
        background: #151922;
        color: #9aa7c2;
        padding: 10px 16px;
        border: 1px solid #20283a;
        border-radius: 12px;
        margin-right: 6px;
        min-width: 120px;
    }

    QTabBar::tab:selected {
        background: #1a2030;
        color: #eef2ff;
        border: 1px solid #32405f;
    }

    QTabBar::tab:hover {
        background: #1d2434;
        color: #eef2ff;
    }

    QDialog, QListWidget, QTableWidget {
        background: #131823;
        color: #eef2ff;
        border: 1px solid #232c3f;
        border-radius: 12px;
    }

    QDialog#commandPalette, QDialog#firstRunDialog {
        background: #131823;
        border: 1px solid #2a344b;
        border-radius: 14px;
    }

    QLabel#firstRunTitle {
        font-size: 28px;
        font-weight: 700;
        color: #f5f8ff;
    }

    QLabel#firstRunSubtitle {
        font-size: 14px;
        color: #bac5dd;
    }

    QLabel#firstRunPreview {
        background: #101521;
        border: 1px solid #25304a;
        border-radius: 12px;
        padding: 12px 14px;
        color: #dce7ff;
    }

    QLabel#firstRunSectionTitle {
        font-size: 16px;
        font-weight: 700;
        color: #edf2ff;
        margin-top: 6px;
    }

    QFrame#searchEngineCard {
        background: #151922;
        border: 1px solid #20283a;
        border-radius: 14px;
    }

    QFrame#searchEngineCard:hover {
        background: #1b2231;
        border: 1px solid #33415f;
    }

    QFrame#searchEngineCard[selected="true"] {
        background: #1b2437;
        border: 2px solid #5d79b7;
    }

    QLabel#engineCardTitle {
        font-size: 15px;
        font-weight: 700;
        color: #eef2ff;
    }

    QLabel#engineCardDescription {
        font-size: 12px;
        color: #a8b4cf;
    }

    QLabel#engineCardBadge {
        min-width: 84px;
        padding: 3px 8px;
        border-radius: 12px;
        background: #20293d;
        border: 1px solid #31415e;
        color: #d8e3ff;
        font-size: 11px;
        font-weight: 700;
    }

    QListWidget::item, QTableWidget::item {
        padding: 6px;
    }

    QListWidget::item:selected {
        background: #26314a;
        border-radius: 8px;
    }

    QPushButton {
        background: #1a2030;
        color: #eef2ff;
        border: 1px solid #2f3a52;
        border-radius: 10px;
        padding: 8px 12px;
    }

    QPushButton:hover {
        background: #20283b;
    }

    QPushButton:default {
        border: 1px solid #5d79b7;
        background: #22314e;
    }

    QProgressBar {
        background: #101521;
        border: 1px solid #273149;
        border-radius: 8px;
    }

    QProgressBar::chunk {
        background: #5d79b7;
        border-radius: 7px;
    }

    QHeaderView::section {
        background: #182031;
        color: #dbe6ff;
        border: none;
        padding: 8px;
    }
    """)


def load_or_create_runtime_config() -> AppConfig:
    cfg_path = config_path()
    if os.path.exists(cfg_path):
        return load_app_config()
    dialog = FirstRunDialog()
    if dialog.exec() == QDialog.Accepted:
        return dialog.selected_config
    cfg = default_app_config()
    save_app_config(cfg)
    return cfg


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon("./Werm_Icon.jpg"))
    apply_dark_style(app)
    runtime_config = load_or_create_runtime_config()
    w = Browser(runtime_config)
    w.show()
    sys.exit(app.exec())
