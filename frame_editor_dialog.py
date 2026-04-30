"""
Frame Editor Dialog – extract frames around a selected point, copy/paste
via system clipboard for external editing, then reinsert into the video.
"""

import os
import sys
import subprocess
import tempfile
import shutil
from datetime import datetime

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QSpinBox, QScrollArea, QWidget, QFrame, QApplication, QMessageBox,
    QSizePolicy, QTextEdit
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QPixmap, QImage


# ---------------------------------------------------------------------------
# Worker threads
# ---------------------------------------------------------------------------

class FrameExtractWorker(QThread):
    finished = pyqtSignal(bool, str)

    def __init__(self, video_path, start_frame, end_frame, output_dir):
        super().__init__()
        self.video_path = video_path
        self.start_frame = start_frame
        self.end_frame = end_frame
        self.output_dir = output_dir

    def run(self):
        out_pattern = os.path.join(self.output_dir, "frame_%05d.png")
        cmd = [
            "ffmpeg", "-y", "-hide_banner",
            "-i", self.video_path,
            "-vf", f"select='between(n,{self.start_frame},{self.end_frame})',setpts=PTS-STARTPTS",
            "-fps_mode", "passthrough",
            out_pattern,
        ]
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
        if result.returncode == 0:
            self.finished.emit(True, "")
        else:
            err = result.stderr.decode("utf-8", errors="replace")
            self.finished.emit(False, err)


class FrameReplaceWorker(QThread):
    output_signal = pyqtSignal(str)
    finished = pyqtSignal(int, str)  # returncode, output_path

    def __init__(self, cmd, output_path):
        super().__init__()
        self.cmd = cmd
        self.output_path = output_path

    def run(self):
        try:
            process = subprocess.Popen(
                self.cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
            )
            for line in process.stdout:
                self.output_signal.emit(line.strip())
            process.wait()
            self.finished.emit(process.returncode, self.output_path)
        except Exception as e:
            self.finished.emit(-1, str(e))


# ---------------------------------------------------------------------------
# Frame card widget
# ---------------------------------------------------------------------------

THUMB_W = 240
THUMB_H = 135


class FrameCard(QFrame):
    """Single frame thumbnail with copy / paste clipboard controls."""

    def __init__(self, frame_number, target_path, is_center=False, parent=None):
        super().__init__(parent)
        self.frame_number = frame_number
        self.target_path = target_path
        self._edited = False

        self.setFrameShape(QFrame.Shape.Box)
        self.setLineWidth(2)
        self._base_style = "QFrame { border: 2px solid #3a3a4a; }"
        self._center_style = "QFrame { border: 2px solid #1976D2; }"
        self._edited_style = "QFrame { border: 2px solid #4CAF50; }"
        self.setStyleSheet(self._center_style if is_center else self._base_style)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(4)

        # Thumbnail
        self.img_label = QLabel()
        self.img_label.setFixedSize(THUMB_W, THUMB_H)
        self.img_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.img_label.setStyleSheet("background: #111; border: none;")
        layout.addWidget(self.img_label)

        # Frame number label
        marker = " ★" if is_center else ""
        self.num_label = QLabel(f"Frame {frame_number}{marker}")
        self.num_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.num_label.setStyleSheet("font-size: 11px; color: #aaa; font-family: monospace; border: none;")
        layout.addWidget(self.num_label)

        # Edited indicator
        self.edited_label = QLabel("")
        self.edited_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.edited_label.setStyleSheet("font-size: 10px; color: #4CAF50; border: none;")
        layout.addWidget(self.edited_label)

        # Copy / Paste buttons
        btn_row = QHBoxLayout()
        self.btn_copy = QPushButton("Copiar")
        self.btn_copy.setToolTip("Copiar este frame para a area de transferencia")
        self.btn_copy.clicked.connect(self._copy_to_clipboard)
        btn_row.addWidget(self.btn_copy)

        self.btn_paste = QPushButton("Colar")
        self.btn_paste.setToolTip("Colar imagem editada da area de transferencia")
        self.btn_paste.clicked.connect(self._paste_from_clipboard)
        btn_row.addWidget(self.btn_paste)
        layout.addLayout(btn_row)

        # Load image if it exists
        if os.path.exists(target_path):
            self._refresh_thumbnail()

    def _refresh_thumbnail(self):
        pixmap = QPixmap(self.target_path)
        if not pixmap.isNull():
            scaled = pixmap.scaled(
                THUMB_W, THUMB_H,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            self.img_label.setPixmap(scaled)

    def _copy_to_clipboard(self):
        if not os.path.exists(self.target_path):
            QMessageBox.warning(self, "Aviso", "Imagem do frame nao disponivel.")
            return
        pixmap = QPixmap(self.target_path)
        if pixmap.isNull():
            return
        QApplication.clipboard().setPixmap(pixmap)

    def _paste_from_clipboard(self):
        image = QApplication.clipboard().image()
        if image.isNull():
            QMessageBox.information(self, "Aviso", "Nao ha imagem na area de transferencia.")
            return
        if not image.save(self.target_path):
            QMessageBox.warning(self, "Erro", "Nao foi possivel salvar a imagem colada.")
            return
        self._edited = True
        self.setStyleSheet(self._edited_style)
        self.edited_label.setText("[editado]")
        self._refresh_thumbnail()

    def is_edited(self):
        return self._edited


# ---------------------------------------------------------------------------
# Main dialog
# ---------------------------------------------------------------------------

class FrameEditorDialog(QDialog):
    def __init__(self, video_path, fps, total_frames, center_frame=0, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Editor de Frames")
        self.setMinimumSize(700, 480)
        self.resize(960, 540)

        self.video_path = video_path
        self.fps = fps if fps > 0 else 30.0
        self.total_frames = max(total_frames, 1)
        self.center_frame = center_frame

        self._temp_dir = tempfile.mkdtemp(prefix="ffmpeg_frame_ed_")
        self._frame_cards: dict[int, FrameCard] = {}
        self._extract_start = 0
        self._extract_end = 0
        self._extract_worker = None
        self._replace_worker = None

        self._setup_ui()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        title = QLabel("Editor de Frames")
        title.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(title)

        hint = QLabel(
            "Selecione um frame, copie para a area de transferencia, edite no aplicativo de imagens que preferir e cole de volta."
        )
        hint.setStyleSheet("color: #888; font-size: 11px;")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        # Controls row
        ctrl_row = QHBoxLayout()
        ctrl_row.addWidget(QLabel("Frame central:"))
        self.center_spin = QSpinBox()
        self.center_spin.setRange(0, self.total_frames - 1)
        self.center_spin.setValue(self.center_frame)
        self.center_spin.setFixedWidth(90)
        ctrl_row.addWidget(self.center_spin)

        ctrl_row.addSpacing(20)
        ctrl_row.addWidget(QLabel("Frames ao redor:"))
        self.radius_spin = QSpinBox()
        self.radius_spin.setRange(0, 20)
        self.radius_spin.setValue(2)
        self.radius_spin.setFixedWidth(60)
        ctrl_row.addWidget(self.radius_spin)

        ctrl_row.addSpacing(20)
        self.btn_load = QPushButton("Carregar Frames")
        self.btn_load.setStyleSheet(
            "background-color: #1976D2; color: white; padding: 4px 14px;"
        )
        self.btn_load.clicked.connect(self._load_frames)
        ctrl_row.addWidget(self.btn_load)
        ctrl_row.addStretch()
        layout.addLayout(ctrl_row)

        # Status
        self.status_label = QLabel("Configure os parametros e clique 'Carregar Frames'.")
        self.status_label.setStyleSheet("color: #888; font-size: 11px;")
        layout.addWidget(self.status_label)

        # Scroll area for frame cards (horizontal)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll.setMinimumHeight(280)

        self._cards_widget = QWidget()
        self.cards_layout = QHBoxLayout(self._cards_widget)
        self.cards_layout.setContentsMargins(6, 6, 6, 6)
        self.cards_layout.setSpacing(10)
        self.cards_layout.addStretch()
        self.scroll.setWidget(self._cards_widget)
        layout.addWidget(self.scroll, 1)

        # Log console (hidden by default)
        self.log_console = QTextEdit()
        self.log_console.setReadOnly(True)
        self.log_console.setMaximumHeight(100)
        self.log_console.hide()
        layout.addWidget(self.log_console)

        # Bottom buttons
        bottom_row = QHBoxLayout()
        self.btn_apply = QPushButton("Aplicar ao Video")
        self.btn_apply.setStyleSheet(
            "font-weight: bold; background-color: #4CAF50; color: white; padding: 6px 18px;"
        )
        self.btn_apply.setEnabled(False)
        self.btn_apply.clicked.connect(self._apply_to_video)
        bottom_row.addWidget(self.btn_apply)

        bottom_row.addStretch()

        self.btn_close = QPushButton("Fechar")
        self.btn_close.clicked.connect(self.close)
        bottom_row.addWidget(self.btn_close)
        layout.addLayout(bottom_row)

    # ------------------------------------------------------------------
    # Frame loading
    # ------------------------------------------------------------------

    def _load_frames(self):
        center = self.center_spin.value()
        radius = self.radius_spin.value()
        start = max(0, center - radius)
        end = min(self.total_frames - 1, center + radius)

        # Clear existing cards
        for card in self._frame_cards.values():
            card.setParent(None)
            card.deleteLater()
        self._frame_cards.clear()
        while self.cards_layout.count():
            item = self.cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Clean temp dir
        for f in os.listdir(self._temp_dir):
            try:
                os.remove(os.path.join(self._temp_dir, f))
            except OSError:
                pass

        self._extract_start = start
        self._extract_end = end
        self.status_label.setText(f"Extraindo frames {start} a {end}, aguarde...")
        self.btn_load.setEnabled(False)
        self.btn_apply.setEnabled(False)

        self._extract_worker = FrameExtractWorker(
            self.video_path, start, end, self._temp_dir
        )
        self._extract_worker.finished.connect(self._on_extract_finished)
        self._extract_worker.start()

    def _on_extract_finished(self, success, error_msg):
        self.btn_load.setEnabled(True)
        if not success:
            self.status_label.setText("Erro na extracao de frames.")
            QMessageBox.warning(
                self, "Erro de extracao",
                f"O ffmpeg falhou ao extrair os frames:\n{error_msg[-600:]}"
            )
            return

        start = self._extract_start
        end = self._extract_end
        center = self.center_spin.value()

        for i, frame_num in enumerate(range(start, end + 1)):
            target = os.path.join(self._temp_dir, f"frame_{i+1:05d}.png")
            card = FrameCard(frame_num, target, is_center=(frame_num == center))
            self._frame_cards[frame_num] = card
            self.cards_layout.addWidget(card)

        self.cards_layout.addStretch()
        self.btn_apply.setEnabled(True)
        total = end - start + 1
        self.status_label.setText(
            f"{total} frame(s) carregado(s) (frames {start} a {end}). "
            "Use Copiar/Colar para editar, depois clique 'Aplicar ao Video'."
        )

    # ------------------------------------------------------------------
    # Applying edits
    # ------------------------------------------------------------------

    def _apply_to_video(self):
        edited = {
            fn: card.target_path
            for fn, card in self._frame_cards.items()
            if card.is_edited() and os.path.exists(card.target_path)
        }
        if not edited:
            QMessageBox.information(
                self, "Nenhuma edicao",
                "Nenhum frame foi editado ainda.\n"
                "Clique 'Copiar' em um frame, edite externamente e clique 'Colar'."
            )
            return

        base = os.path.splitext(self.video_path)[0]
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = f"{base}_edited_{ts}.mp4"

        from ffmpeg_logic import build_frame_replace_command
        cmd = build_frame_replace_command(self.video_path, edited, output_path)

        self.btn_apply.setEnabled(False)
        self.log_console.clear()
        self.log_console.show()
        self._log(f"Executando:\n{' '.join(cmd)}\n")
        self.status_label.setText("Aplicando edicoes ao video, aguarde...")

        self._replace_worker = FrameReplaceWorker(cmd, output_path)
        self._replace_worker.output_signal.connect(self._log)
        self._replace_worker.finished.connect(self._on_replace_finished)
        self._replace_worker.start()

    def _on_replace_finished(self, returncode, output_path):
        self.btn_apply.setEnabled(True)
        if returncode == 0:
            self.status_label.setText(f"Salvo: {os.path.basename(output_path)}")
            QMessageBox.information(
                self, "Sucesso",
                f"Video editado salvo em:\n{output_path}"
            )
        else:
            self.status_label.setText("Erro ao aplicar edicoes.")
            QMessageBox.warning(self, "Erro", "O ffmpeg falhou ao aplicar as edicoes ao video.")

    def _log(self, text):
        self.log_console.append(text)
        self.log_console.verticalScrollBar().setValue(
            self.log_console.verticalScrollBar().maximum()
        )

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    def closeEvent(self, event):
        if self._temp_dir and os.path.exists(self._temp_dir):
            shutil.rmtree(self._temp_dir, ignore_errors=True)
        event.accept()
