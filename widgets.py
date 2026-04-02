from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QSpinBox, QCheckBox,
    QPushButton, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPainter, QPen, QColor, QFont, QBrush

class ConcatOptionsWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        row1 = QHBoxLayout()
        row1.addWidget(QLabel("Resolução:"))
        self.res_heuristic_combo = QComboBox()
        self.res_heuristic_combo.addItems([
            "Maior Duração Total",
            "Maior Resolução",
            "Maioria (Contagem)",
            "Primeiro Arquivo",
            "Manual",
        ])
        self.res_heuristic_combo.setMinimumWidth(180)
        row1.addWidget(self.res_heuristic_combo)

        row1.addSpacing(15)
        row1.addWidget(QLabel("Ajuste:"))
        self.crop_combo = QComboBox()
        self.crop_combo.addItems([
            "Letterbox (Barras Pretas)",
            "Crop Centro",
            "Crop Cima",
            "Crop Baixo",
            "Crop Esquerda",
            "Crop Direita",
        ])
        self.crop_combo.setMinimumWidth(180)
        row1.addWidget(self.crop_combo)
        row1.addStretch()
        layout.addLayout(row1)

        row2 = QHBoxLayout()
        self.manual_lbl = QLabel("Largura:")
        row2.addWidget(self.manual_lbl)
        self.manual_w_spin = QSpinBox()
        self.manual_w_spin.setRange(2, 7680)
        self.manual_w_spin.setValue(1920)
        self.manual_w_spin.setSingleStep(2)
        self.manual_w_spin.setFixedWidth(80)
        row2.addWidget(self.manual_w_spin)
        self.manual_h_lbl = QLabel("Altura:")
        row2.addWidget(self.manual_h_lbl)
        self.manual_h_spin = QSpinBox()
        self.manual_h_spin.setRange(2, 4320)
        self.manual_h_spin.setValue(1080)
        self.manual_h_spin.setSingleStep(2)
        self.manual_h_spin.setFixedWidth(80)
        row2.addWidget(self.manual_h_spin)
        row2.addStretch()
        layout.addLayout(row2)

        self.res_heuristic_combo.currentTextChanged.connect(self._on_heuristic_changed)
        self._on_heuristic_changed(self.res_heuristic_combo.currentText())

    def _on_heuristic_changed(self, text):
        is_manual = text == "Manual"
        self.manual_lbl.setVisible(is_manual)
        self.manual_w_spin.setVisible(is_manual)
        self.manual_h_lbl.setVisible(is_manual)
        self.manual_h_spin.setVisible(is_manual)

class SpatialCropWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        layout.addWidget(QLabel("W:"))
        self.sc_w_spin = QSpinBox()
        self.sc_w_spin.setRange(2, 7680)
        self.sc_w_spin.setValue(480)
        self.sc_w_spin.setSingleStep(2)
        self.sc_w_spin.setFixedWidth(70)
        layout.addWidget(self.sc_w_spin)

        layout.addWidget(QLabel("H:"))
        self.sc_h_spin = QSpinBox()
        self.sc_h_spin.setRange(2, 4320)
        self.sc_h_spin.setValue(480)
        self.sc_h_spin.setSingleStep(2)
        self.sc_h_spin.setFixedWidth(70)
        layout.addWidget(self.sc_h_spin)

        layout.addSpacing(10)

        self.sc_center_cb = QCheckBox("Centro")
        self.sc_center_cb.setChecked(True)
        self.sc_center_cb.toggled.connect(self._on_sc_center_toggled)
        layout.addWidget(self.sc_center_cb)

        layout.addSpacing(10)

        self.sc_x_lbl = QLabel("X:")
        layout.addWidget(self.sc_x_lbl)
        self.sc_x_spin = QSpinBox()
        self.sc_x_spin.setRange(0, 7680)
        self.sc_x_spin.setValue(0)
        self.sc_x_spin.setFixedWidth(70)
        self.sc_x_spin.setEnabled(False)
        layout.addWidget(self.sc_x_spin)

        self.sc_y_lbl = QLabel("Y:")
        layout.addWidget(self.sc_y_lbl)
        self.sc_y_spin = QSpinBox()
        self.sc_y_spin.setRange(0, 4320)
        self.sc_y_spin.setValue(0)
        self.sc_y_spin.setFixedWidth(70)
        self.sc_y_spin.setEnabled(False)
        layout.addWidget(self.sc_y_spin)

        layout.addStretch()

    def _on_sc_center_toggled(self, checked):
        self.sc_x_spin.setEnabled(not checked)
        self.sc_y_spin.setEnabled(not checked)

class MemoryFlashOptionsWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        row1 = QHBoxLayout()
        row1.addWidget(QLabel("Fragmentos:"))
        self.flash_count_spin = QSpinBox()
        self.flash_count_spin.setRange(1, 50)
        self.flash_count_spin.setValue(4)
        self.flash_count_spin.setFixedWidth(50)
        row1.addWidget(self.flash_count_spin)

        row1.addSpacing(10)
        row1.addWidget(QLabel("Subfragmentos:"))
        self.flash_sub_spin = QSpinBox()
        self.flash_sub_spin.setRange(1, 30)
        self.flash_sub_spin.setValue(3)
        self.flash_sub_spin.setFixedWidth(50)
        row1.addWidget(self.flash_sub_spin)

        row1.addSpacing(10)
        row1.addWidget(QLabel("Tamanho (frames):"))
        self.flash_size_spin = QSpinBox()
        self.flash_size_spin.setRange(1, 60)
        self.flash_size_spin.setValue(2)
        self.flash_size_spin.setFixedWidth(50)
        row1.addWidget(self.flash_size_spin)

        row1.addSpacing(10)
        row1.addWidget(QLabel("Espaçamento (frames):"))
        self.flash_gap_spin = QSpinBox()
        self.flash_gap_spin.setRange(1, 300)
        self.flash_gap_spin.setValue(3)
        self.flash_gap_spin.setFixedWidth(60)
        row1.addWidget(self.flash_gap_spin)

        row1.addSpacing(10)
        row1.addWidget(QLabel("Seed:"))
        self.flash_seed_spin = QSpinBox()
        self.flash_seed_spin.setRange(0, 999999)
        self.flash_seed_spin.setValue(0)
        self.flash_seed_spin.setFixedWidth(70)
        row1.addWidget(self.flash_seed_spin)

        row1.addStretch()
        layout.addLayout(row1)

class GhostImagesOptionsWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        row1 = QHBoxLayout()
        row1.addWidget(QLabel("Frame Início:"))
        self.ghost_start_spin = QSpinBox()
        self.ghost_start_spin.setRange(0, 999999)
        self.ghost_start_spin.setValue(0)
        self.ghost_start_spin.setFixedWidth(80)
        row1.addWidget(self.ghost_start_spin)

        row1.addSpacing(10)
        row1.addWidget(QLabel("Frame Fim:"))
        self.ghost_end_spin = QSpinBox()
        self.ghost_end_spin.setRange(1, 999999)
        self.ghost_end_spin.setValue(300)
        self.ghost_end_spin.setFixedWidth(80)
        row1.addWidget(self.ghost_end_spin)

        row1.addSpacing(10)
        row1.addWidget(QLabel("Duração (seg):"))
        self.ghost_dur_spin = QSpinBox()
        self.ghost_dur_spin.setRange(1, 60)
        self.ghost_dur_spin.setValue(2)
        self.ghost_dur_spin.setFixedWidth(50)
        row1.addWidget(self.ghost_dur_spin)

        row1.addSpacing(10)
        row1.addWidget(QLabel("Opacidade:"))
        self.ghost_opacity_spin = QSpinBox()
        self.ghost_opacity_spin.setRange(1, 100)
        self.ghost_opacity_spin.setValue(30)
        self.ghost_opacity_spin.setFixedWidth(50)
        self.ghost_opacity_spin.setSuffix("%")
        row1.addWidget(self.ghost_opacity_spin)

        row1.addSpacing(10)
        row1.addWidget(QLabel("Escala Img:"))
        self.ghost_scale_spin = QSpinBox()
        self.ghost_scale_spin.setRange(10, 200)
        self.ghost_scale_spin.setValue(80)
        self.ghost_scale_spin.setFixedWidth(55)
        self.ghost_scale_spin.setSuffix("%")
        row1.addWidget(self.ghost_scale_spin)

        row1.addSpacing(10)
        row1.addWidget(QLabel("Viagem X:"))
        self.ghost_travel_spin = QSpinBox()
        self.ghost_travel_spin.setRange(1, 100)
        self.ghost_travel_spin.setValue(100)
        self.ghost_travel_spin.setFixedWidth(55)
        self.ghost_travel_spin.setSuffix("%")
        row1.addWidget(self.ghost_travel_spin)

        row1.addStretch()
        layout.addLayout(row1)


# ---------------------------------------------------------------------------
# Variable Speed – interactive speed-curve editor
# ---------------------------------------------------------------------------

class SpeedCurveWidget(QWidget):
    """
    Interactive piecewise-linear speed curve editor.

    X axis: normalized time [0, 1]  (optionally labeled in seconds)
    Y axis: speed multiplier [-4, +4]

    Left-click empty area  → add control point
    Left-click + drag      → move a control point
    Right-click on point   → remove it (endpoints are protected)
    """

    curve_changed = pyqtSignal()

    SPEED_MIN = -4.0
    SPEED_MAX = 4.0
    POINT_R = 6       # circle radius in pixels
    HIT_DIST = 12     # pixel distance to "hit" a point

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(380, 270)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        # Each point: [t_normalized, speed]
        self._points = [[0.0, 1.0], [1.0, 1.0]]
        self._drag_idx = None
        self._duration = 0.0   # video duration in seconds (0 = use percentages)
        self.setMouseTracking(True)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_control_points(self):
        return [list(p) for p in self._points]

    def set_duration(self, secs):
        self._duration = max(0.0, secs)
        self.update()

    def reset(self):
        self._points = [[0.0, 1.0], [1.0, 1.0]]
        self._drag_idx = None
        self.update()
        self.curve_changed.emit()

    # ------------------------------------------------------------------
    # Coordinate helpers
    # ------------------------------------------------------------------

    def _margins(self):
        return 40, 14, 14, 28   # left, top, right, bottom

    def _to_px(self, t, speed):
        ml, mt, mr, mb = self._margins()
        aw = self.width() - ml - mr
        ah = self.height() - mt - mb
        x = ml + t * aw
        y = mt + (self.SPEED_MAX - speed) / (self.SPEED_MAX - self.SPEED_MIN) * ah
        return x, y

    def _from_px(self, x, y):
        ml, mt, mr, mb = self._margins()
        aw = self.width() - ml - mr
        ah = self.height() - mt - mb
        t = (x - ml) / aw
        speed = self.SPEED_MAX - (y - mt) / ah * (self.SPEED_MAX - self.SPEED_MIN)
        return t, speed

    def _nearest_point(self, x, y):
        best_i, best_d = 0, float('inf')
        for i, (t, s) in enumerate(self._points):
            px, py = self._to_px(t, s)
            d = ((px - x) ** 2 + (py - y) ** 2) ** 0.5
            if d < best_d:
                best_d = d
                best_i = i
        return best_i, best_d

    # ------------------------------------------------------------------
    # Paint
    # ------------------------------------------------------------------

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        ml, mt, mr, mb = self._margins()
        aw = self.width() - ml - mr
        ah = self.height() - mt - mb

        # Background
        painter.fillRect(self.rect(), QColor(26, 26, 36))

        # Plot area border
        painter.setPen(QPen(QColor(65, 65, 85), 1))
        painter.drawRect(ml, mt, aw, ah)

        # Horizontal grid lines
        for speed in range(int(self.SPEED_MIN), int(self.SPEED_MAX) + 1):
            x1, y1 = self._to_px(0.0, float(speed))
            x2, _  = self._to_px(1.0, float(speed))
            if speed == 0:
                pen = QPen(QColor(85, 85, 120), 1)
            elif speed == 1:
                pen = QPen(QColor(45, 95, 45), 1, Qt.PenStyle.DashLine)
            else:
                pen = QPen(QColor(45, 45, 58), 1)
            painter.setPen(pen)
            painter.drawLine(int(x1), int(y1), int(x2), int(y1))

        # Y-axis labels
        font = QFont()
        font.setPointSize(8)
        painter.setFont(font)
        painter.setPen(QPen(QColor(130, 130, 155)))
        for speed in range(int(self.SPEED_MIN), int(self.SPEED_MAX) + 1):
            _, py = self._to_px(0.0, float(speed))
            label = f"{speed:+d}x" if speed != 0 else " 0x"
            painter.drawText(0, int(py) - 7, ml - 4, 16,
                             Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                             label)

        # X-axis labels (start, 25%, 50%, 75%, end)
        painter.setPen(QPen(QColor(110, 110, 135)))
        for frac in (0.0, 0.25, 0.5, 0.75, 1.0):
            px, _ = self._to_px(frac, 0.0)
            if self._duration > 0:
                t_sec = frac * self._duration
                label = (f"{int(t_sec // 60)}m{int(t_sec % 60):02d}s"
                         if t_sec >= 60 else f"{t_sec:.1f}s")
            else:
                label = f"{int(frac * 100)}%"
            painter.drawText(int(px) - 22, self.height() - mb + 3, 44, mb,
                             Qt.AlignmentFlag.AlignHCenter, label)

        # The curve lines
        if len(self._points) >= 2:
            painter.setPen(QPen(QColor(75, 175, 255), 2))
            for i in range(len(self._points) - 1):
                x1, y1 = self._to_px(*self._points[i])
                x2, y2 = self._to_px(*self._points[i + 1])
                painter.drawLine(int(x1), int(y1), int(x2), int(y2))

        # Control points
        for i, (t, speed) in enumerate(self._points):
            px, py = self._to_px(t, speed)
            is_endpoint = i == 0 or i == len(self._points) - 1
            if i == self._drag_idx:
                fill = QColor(255, 215, 50)
            elif is_endpoint:
                fill = QColor(210, 70, 70)
            else:
                fill = QColor(75, 175, 255)
            painter.setPen(QPen(QColor(240, 240, 255), 1))
            painter.setBrush(QBrush(fill))
            r = self.POINT_R
            painter.drawEllipse(int(px - r), int(py - r), r * 2, r * 2)

        # Drag tooltip
        if self._drag_idx is not None:
            t, speed = self._points[self._drag_idx]
            if self._duration > 0:
                t_str = f"{t * self._duration:.2f}s"
            else:
                t_str = f"{t * 100:.1f}%"
            info = f"t={t_str}  speed={speed:+.2f}x"
            font2 = QFont()
            font2.setPointSize(9)
            painter.setFont(font2)
            painter.setPen(QPen(QColor(210, 210, 240)))
            painter.drawText(ml + 6, mt + 4, 220, 18,
                             Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                             info)

        painter.end()

    # ------------------------------------------------------------------
    # Mouse interaction
    # ------------------------------------------------------------------

    def mousePressEvent(self, event):
        x, y = event.position().x(), event.position().y()

        if event.button() == Qt.MouseButton.LeftButton:
            idx, dist = self._nearest_point(x, y)
            if dist <= self.HIT_DIST:
                self._drag_idx = idx
            else:
                # Add new point
                t, speed = self._from_px(x, y)
                t = max(0.001, min(0.999, t))
                speed = max(self.SPEED_MIN, min(self.SPEED_MAX, speed))
                # Insert sorted by t
                ins = len(self._points) - 1
                for j, (pt, _) in enumerate(self._points):
                    if pt > t:
                        ins = j
                        break
                self._points.insert(ins, [t, speed])
                self._drag_idx = ins
                self.update()
                self.curve_changed.emit()

        elif event.button() == Qt.MouseButton.RightButton:
            idx, dist = self._nearest_point(x, y)
            if dist <= self.HIT_DIST and 0 < idx < len(self._points) - 1:
                self._points.pop(idx)
                self._drag_idx = None
                self.update()
                self.curve_changed.emit()

    def mouseMoveEvent(self, event):
        if self._drag_idx is None:
            return
        x, y = event.position().x(), event.position().y()
        t, speed = self._from_px(x, y)
        speed = max(self.SPEED_MIN, min(self.SPEED_MAX, speed))

        if self._drag_idx == 0:
            t = 0.0
        elif self._drag_idx == len(self._points) - 1:
            t = 1.0
        else:
            t_prev = self._points[self._drag_idx - 1][0]
            t_next = self._points[self._drag_idx + 1][0]
            t = max(t_prev + 0.001, min(t_next - 0.001, t))

        self._points[self._drag_idx] = [t, speed]
        self.update()
        self.curve_changed.emit()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_idx = None
            self.update()


class VariableSpeedOptionsWidget(QWidget):
    """Right-side panel shown when 'Velocidade Variável' is selected."""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 6, 6, 6)
        layout.setSpacing(6)

        title = QLabel("Curva de Velocidade")
        title.setStyleSheet("font-weight: bold; font-size: 13px;")
        layout.addWidget(title)

        hint = QLabel(
            "Clique: adicionar ponto  ·  Arrastar: mover  ·  Clique dir.: remover"
        )
        hint.setStyleSheet("color: #888; font-size: 10px;")
        layout.addWidget(hint)

        self.curve = SpeedCurveWidget()
        layout.addWidget(self.curve, 1)

        btn_reset = QPushButton("↺  Resetar para 1x")
        btn_reset.setFixedHeight(28)
        btn_reset.clicked.connect(self.curve.reset)
        layout.addWidget(btn_reset)

        self.setMinimumWidth(400)

    def get_control_points(self):
        return self.curve.get_control_points()

    def set_duration(self, secs):
        self.curve.set_duration(secs)
