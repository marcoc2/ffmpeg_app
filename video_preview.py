"""
Video Preview Widget – right-side panel for visually selecting cut points.

Shows a video player with a frame-accurate slider and buttons to set
the frame value into the main GUI's SpinBox.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QSlider,
    QSizePolicy, QStyle
)
from PyQt6.QtCore import Qt, QUrl, pyqtSignal
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtMultimediaWidgets import QVideoWidget


class VideoPreviewWidget(QWidget):
    """
    Right-side panel that shows a video preview with a scrub slider.
    Emits `frame_selected(int)` when the user clicks 'Usar este frame'.
    """

    frame_selected = pyqtSignal(int)

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

    def load_video(self, path, fps=30.0, total_frames=0):
        """Load a video file into the preview."""
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

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _ms_to_frame(self, ms):
        return int(round(ms / 1000.0 * self._fps))

    def _frame_to_ms(self, frame):
        return int(round(frame / self._fps * 1000.0))

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
        target_ms = self._frame_to_ms(target_frame)
        self._player.setPosition(target_ms)

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
        self._info_label.setText(f"Frame: {frame} / {total}  —  {t_sec:.3f}s")

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
