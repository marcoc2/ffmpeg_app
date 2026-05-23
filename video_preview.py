"""
Video Preview Widget – right-side panel for visually selecting cut points.

Shows a video player with a frame-accurate slider and buttons to set
the frame value into the main GUI's SpinBox.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QSlider,
    QSizePolicy, QStyle
)
from PyQt6.QtCore import Qt, QUrl, pyqtSignal, QRectF, QPointF
from PyQt6.QtGui import QPainter, QColor, QPen, QPainterPath
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtMultimediaWidgets import QVideoWidget


class CropOverlayWidget(QWidget):
    crop_changed = pyqtSignal(int, int, int, int, bool) # x, y, w, h, center

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setMouseTracking(True)
        
        self.video_width = 1920
        self.video_height = 1080
        self.crop_x = 0
        self.crop_y = 0
        self.crop_w = 480
        self.crop_h = 480
        self.crop_center = True
        self._active = False
        
        self._is_dragging = False
        self._drag_start_vx = 0
        self._drag_start_vy = 0

    def set_active(self, active):
        self._active = active
        self.setVisible(active)
        self.update()

    def set_video_dimensions(self, width, height):
        self.video_width = width if width > 0 else 1920
        self.video_height = height if height > 0 else 1080
        self.update()

    def set_crop_rect(self, x, y, w, h, center):
        self.crop_x = x
        self.crop_y = y
        self.crop_w = w
        self.crop_h = h
        self.crop_center = center
        self.update()

    def _get_video_render_rect(self):
        widget_rect = self.rect()
        if not self.video_width or not self.video_height:
            return QRectF(widget_rect)
            
        ar_vid = self.video_width / self.video_height
        ar_widget = widget_rect.width() / widget_rect.height()

        if ar_vid > ar_widget:
            w_render = widget_rect.width()
            h_render = widget_rect.width() / ar_vid
            x_offset = 0
            y_offset = (widget_rect.height() - h_render) / 2
        else:
            w_render = widget_rect.height() * ar_vid
            h_render = widget_rect.height()
            x_offset = (widget_rect.width() - w_render) / 2
            y_offset = 0

        return QRectF(x_offset, y_offset, w_render, h_render)

    def paintEvent(self, event):
        if not self._active or not self.video_width or not self.video_height:
            return
            
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        video_rect = self._get_video_render_rect()

        if self.crop_center:
            cx = (self.video_width - self.crop_w) / 2
            cy = (self.video_height - self.crop_h) / 2
        else:
            cx = self.crop_x
            cy = self.crop_y

        rx = video_rect.x() + (cx / self.video_width) * video_rect.width()
        ry = video_rect.y() + (cy / self.video_height) * video_rect.height()
        rw = (self.crop_w / self.video_width) * video_rect.width()
        rh = (self.crop_h / self.video_height) * video_rect.height()

        crop_rect = QRectF(rx, ry, rw, rh)
        intersected_crop = crop_rect.intersected(video_rect)

        path = QPainterPath()
        path.setFillRule(Qt.FillRule.OddEvenFill)
        path.addRect(QRectF(self.rect()))
        
        if intersected_crop.isValid():
            path.addRect(intersected_crop)
            
        painter.fillPath(path, QColor(0, 0, 0, 160))

        if intersected_crop.isValid():
            pen = QPen(QColor("#00E5FF"), 2, Qt.PenStyle.SolidLine)
            painter.setPen(pen)
            painter.drawRect(intersected_crop)
            
            # Corner accents
            pen_corner = QPen(QColor("#00E5FF"), 4, Qt.PenStyle.SolidLine)
            painter.setPen(pen_corner)
            c_len = 12
            # TL
            painter.drawLine(int(intersected_crop.left()), int(intersected_crop.top()), int(intersected_crop.left() + c_len), int(intersected_crop.top()))
            painter.drawLine(int(intersected_crop.left()), int(intersected_crop.top()), int(intersected_crop.left()), int(intersected_crop.top() + c_len))
            # TR
            painter.drawLine(int(intersected_crop.right()), int(intersected_crop.top()), int(intersected_crop.right() - c_len), int(intersected_crop.top()))
            painter.drawLine(int(intersected_crop.right()), int(intersected_crop.top()), int(intersected_crop.right()), int(intersected_crop.top() + c_len))
            # BL
            painter.drawLine(int(intersected_crop.left()), int(intersected_crop.bottom()), int(intersected_crop.left() + c_len), int(intersected_crop.bottom()))
            painter.drawLine(int(intersected_crop.left()), int(intersected_crop.bottom()), int(intersected_crop.left()), int(intersected_crop.bottom() - c_len))
            # BR
            painter.drawLine(int(intersected_crop.right()), int(intersected_crop.bottom()), int(intersected_crop.right() - c_len), int(intersected_crop.bottom()))
            painter.drawLine(int(intersected_crop.right()), int(intersected_crop.bottom()), int(intersected_crop.right()), int(intersected_crop.bottom() - c_len))

    def mousePressEvent(self, event):
        if not self._active or not self.video_width or not self.video_height:
            return
            
        video_rect = self._get_video_render_rect()
        pos = event.position()
        
        if video_rect.contains(pos):
            self._is_dragging = True
            self.crop_center = False
            
            self._drag_start_vx = int((pos.x() - video_rect.x()) / video_rect.width() * self.video_width)
            self._drag_start_vy = int((pos.y() - video_rect.y()) / video_rect.height() * self.video_height)
            self._drag_start_vx = max(0, min(self._drag_start_vx, self.video_width))
            self._drag_start_vy = max(0, min(self._drag_start_vy, self.video_height))
            
            self.crop_x = self._drag_start_vx
            self.crop_y = self._drag_start_vy
            self.crop_w = 2
            self.crop_h = 2
            self.update()
            
            self.crop_changed.emit(self.crop_x, self.crop_y, self.crop_w, self.crop_h, self.crop_center)

    def mouseMoveEvent(self, event):
        if self._is_dragging:
            video_rect = self._get_video_render_rect()
            pos = event.position()
            
            curr_vx = int((pos.x() - video_rect.x()) / video_rect.width() * self.video_width)
            curr_vy = int((pos.y() - video_rect.y()) / video_rect.height() * self.video_height)
            curr_vx = max(0, min(curr_vx, self.video_width))
            curr_vy = max(0, min(curr_vy, self.video_height))
            
            x1, x2 = min(self._drag_start_vx, curr_vx), max(self._drag_start_vx, curr_vx)
            y1, y2 = min(self._drag_start_vy, curr_vy), max(self._drag_start_vy, curr_vy)
            
            cw = x2 - x1
            ch = y2 - y1
            if cw % 2 != 0:
                cw += 1
            if ch % 2 != 0:
                ch += 1
            
            self.crop_x = x1
            self.crop_y = y1
            self.crop_w = max(2, cw)
            self.crop_h = max(2, ch)
            
            if self.crop_x + self.crop_w > self.video_width:
                self.crop_w = self.video_width - self.crop_x
                if self.crop_w % 2 != 0:
                    self.crop_w -= 1
            if self.crop_y + self.crop_h > self.video_height:
                self.crop_h = self.video_height - self.crop_y
                if self.crop_h % 2 != 0:
                    self.crop_h -= 1
                    
            self.update()
            self.crop_changed.emit(self.crop_x, self.crop_y, self.crop_w, self.crop_h, self.crop_center)

    def mouseReleaseEvent(self, event):
        if self._is_dragging:
            self._is_dragging = False


class VideoPreviewWidget(QWidget):
    """
    Right-side panel that shows a video preview with a scrub slider.
    Emits `frame_selected(int)` when the user clicks 'Usar este frame'.
    """

    frame_selected = pyqtSignal(int)
    frame_editor_requested = pyqtSignal(int)
    crop_changed = pyqtSignal(int, int, int, int, bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._fps = 30.0
        self._total_frames = 0
        self._duration_ms = 0
        self._loaded_path = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 6, 6, 6)
        layout.setSpacing(6)

        # Title
        title = QLabel("Preview de Vídeo")
        title.setStyleSheet("font-weight: bold; font-size: 13px;")
        layout.addWidget(title)

        # Video display
        self._video_widget = QVideoWidget()
        self._video_widget.setMinimumSize(320, 180)
        self._video_widget.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        layout.addWidget(self._video_widget, 1)

        # Crop overlay
        self.crop_overlay = CropOverlayWidget(self._video_widget)
        self.crop_overlay.setVisible(False)
        self.crop_overlay.crop_changed.connect(self.crop_changed.emit)
        self._video_widget.installEventFilter(self)

        # Player
        self._player = QMediaPlayer()
        self._audio = QAudioOutput()
        self._audio.setVolume(0.3)
        self._player.setAudioOutput(self._audio)
        self._player.setVideoOutput(self._video_widget)

        # Slider
        slider_row = QHBoxLayout()
        self._slider = QSlider(Qt.Orientation.Horizontal)
        self._slider.setRange(0, 0)
        self._slider.setTracking(True)
        slider_row.addWidget(self._slider, 1)
        layout.addLayout(slider_row)

        # Info label + controls
        ctrl_row = QHBoxLayout()

        self._btn_play = QPushButton("▶")
        self._btn_play.setFixedWidth(32)
        self._btn_play.setToolTip("Play/Pause")
        self._btn_play.clicked.connect(self._toggle_play)
        ctrl_row.addWidget(self._btn_play)

        self._btn_step_back = QPushButton("◀◀")
        self._btn_step_back.setFixedWidth(40)
        self._btn_step_back.setToolTip("-1 frame")
        self._btn_step_back.clicked.connect(lambda: self._step_frames(-1))
        ctrl_row.addWidget(self._btn_step_back)

        self._btn_step_fwd = QPushButton("▶▶")
        self._btn_step_fwd.setFixedWidth(40)
        self._btn_step_fwd.setToolTip("+1 frame")
        self._btn_step_fwd.clicked.connect(lambda: self._step_frames(1))
        ctrl_row.addWidget(self._btn_step_fwd)

        self._info_label = QLabel("Frame: 0 / 0  —  0.000s")
        self._info_label.setStyleSheet("color: #aaa; font-size: 11px; font-family: monospace;")
        ctrl_row.addWidget(self._info_label, 1)

        self._btn_use = QPushButton("✂ Usar este frame")
        self._btn_use.setStyleSheet(
            "font-weight: bold; background-color: #1976D2; color: white; "
            "padding: 4px 12px; border-radius: 3px;"
        )
        self._btn_use.setToolTip("Envia o frame atual para o campo 'Frames' da operação")
        self._btn_use.clicked.connect(self._emit_frame)
        ctrl_row.addWidget(self._btn_use)

        self._btn_edit = QPushButton("Editar Frames")
        self._btn_edit.setStyleSheet(
            "font-weight: bold; background-color: #7B1FA2; color: white; "
            "padding: 4px 12px; border-radius: 3px;"
        )
        self._btn_edit.setToolTip("Abrir editor de frames para edição pixel a pixel")
        self._btn_edit.clicked.connect(self._emit_edit_request)
        ctrl_row.addWidget(self._btn_edit)

        layout.addLayout(ctrl_row)

        self.setMinimumWidth(400)

        # Connections
        self._slider.valueChanged.connect(self._on_slider_moved)
        self._player.positionChanged.connect(self._on_position_changed)
        self._player.durationChanged.connect(self._on_duration_changed)

        # Start paused
        self._is_playing = False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def load_video(self, path, fps=30.0, total_frames=0, width=1920, height=1080):
        """Load a video file into the preview."""
        if hasattr(self, "crop_overlay"):
            self.crop_overlay.set_video_dimensions(width, height)

        if self._loaded_path == path:
            return
        self._loaded_path = path
        self._fps = fps if fps > 0 else 30.0
        self._total_frames = total_frames
        self._player.setSource(QUrl.fromLocalFile(path))
        self._player.pause()
        self._is_playing = False
        self._btn_play.setText("▶")

    def clear(self):
        """Unload and reset the preview."""
        self._player.stop()
        self._player.setSource(QUrl())
        self._loaded_path = None
        self._total_frames = 0
        self._duration_ms = 0
        self._slider.setRange(0, 0)
        self._info_label.setText("Frame: 0 / 0  —  0.000s")
        self._is_playing = False
        self._btn_play.setText("▶")
        if hasattr(self, "crop_overlay"):
            self.crop_overlay.set_active(False)
            self.crop_overlay.set_video_dimensions(0, 0)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _ms_to_frame(self, ms):
        # floor: which frame window does this timestamp fall in?
        return int(ms * self._fps / 1000.0)

    def _frame_to_ms(self, frame):
        # midpoint of the frame window — never lands on a boundary
        return int((frame + 0.5) * 1000.0 / self._fps)

    def _toggle_play(self):
        if self._is_playing:
            self._player.pause()
            self._is_playing = False
            self._btn_play.setText("▶")
        else:
            self._player.play()
            self._is_playing = True
            self._btn_play.setText("⏸")

    def _step_frames(self, delta):
        """Step forward or backward by delta frames."""
        if self._is_playing:
            self._player.pause()
            self._is_playing = False
            self._btn_play.setText("▶")

        current_frame = self._ms_to_frame(self._player.position())
        target_frame = max(0, current_frame + delta)
        if self._total_frames > 0:
            target_frame = min(target_frame, self._total_frames - 1)
        self._player.setPosition(self._frame_to_ms(target_frame))

    def _on_slider_moved(self, value):
        """User dragged the slider — seek the player."""
        # Only seek if this was a user action (not programmatic from _on_position_changed)
        if not self._slider.isSliderDown():
            return
        target_ms = self._frame_to_ms(value)
        if self._is_playing:
            self._player.pause()
            self._is_playing = False
            self._btn_play.setText("▶")
        self._player.setPosition(target_ms)

    def _on_position_changed(self, position_ms):
        """Player position updated — sync slider and info label."""
        frame = self._ms_to_frame(position_ms)
        t_sec = position_ms / 1000.0

        # Update slider without triggering another seek
        if not self._slider.isSliderDown():
            self._slider.blockSignals(True)
            self._slider.setValue(frame)
            self._slider.blockSignals(False)

        total = self._total_frames if self._total_frames > 0 else "?"
        self._info_label.setText(f"~Frame {frame} / {total}  —  {t_sec:.3f}s")

    def _on_duration_changed(self, duration_ms):
        """Player reported total duration — update slider range."""
        self._duration_ms = duration_ms
        if self._total_frames <= 0 and self._fps > 0:
            self._total_frames = self._ms_to_frame(duration_ms)
        self._slider.setRange(0, max(1, self._total_frames))

    def _emit_frame(self):
        """Send the current frame number to the main GUI."""
        frame = self._ms_to_frame(self._player.position())
        self.frame_selected.emit(frame)

    def _emit_edit_request(self):
        """Open the frame editor centered on the current frame."""
        frame = self._ms_to_frame(self._player.position())
        self.frame_editor_requested.emit(frame)

    def set_crop_mode(self, active, x=0, y=0, w=100, h=100, center=True):
        if hasattr(self, "crop_overlay"):
            self.crop_overlay.set_active(active)
            self.crop_overlay.set_crop_rect(x, y, w, h, center)

    def set_crop_rect(self, x, y, w, h, center):
        if hasattr(self, "crop_overlay"):
            self.crop_overlay.set_crop_rect(x, y, w, h, center)

    def eventFilter(self, watched, event):
        if watched == self._video_widget and event.type() == event.Type.Resize:
            if hasattr(self, "crop_overlay"):
                self.crop_overlay.setGeometry(self._video_widget.rect())
        return super().eventFilter(watched, event)
