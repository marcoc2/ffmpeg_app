import sys
import os
import subprocess
import json
import random
import traceback
from datetime import datetime
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QListWidget,
    QAbstractItemView,
    QListWidgetItem,
    QLabel,
    QMessageBox,
    QTextEdit,
    QComboBox,
    QFileDialog,
    QSpinBox,
    QCheckBox,
)
from PyQt6.QtCore import QThread, pyqtSignal


def exception_hook(exctype, value, tb):
    """Global exception hook to capture crashes that don't reach the console."""
    err_msg = "".join(traceback.format_exception(exctype, value, tb))
    print(err_msg, file=sys.stderr)
    try:
        with open("crash_report.txt", "a", encoding="utf-8") as f:
            f.write(f"\n--- CRASH AT {datetime.now()} ---\n")
            f.write(err_msg)
            f.write("-" * 30 + "\n")
    except Exception:
        pass
    sys.__excepthook__(exctype, value, tb)


sys.excepthook = exception_hook

# Set AppUserModelID for correct taskbar icon on Windows
if sys.platform == "win32":
    import ctypes

    myappid = "mycompany.myproduct.subproduct.version"  # arbitrary string
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)


class FFmpegWorker(QThread):
    output_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(int)

    def __init__(self, command, cwd):
        super().__init__()
        self.command = command
        self.cwd = cwd

    def run(self):
        try:
            process = subprocess.Popen(
                self.command,
                cwd=self.cwd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )

            for line in process.stdout:
                self.output_signal.emit(line.strip())

            process.wait()
            self.finished_signal.emit(process.returncode)
        except Exception as e:
            self.output_signal.emit(f"Error executing command: {str(e)}")
            self.finished_signal.emit(-1)


OPERATIONS = {
    "Concatenar Videos": "concat",
    "Extrair Audio (MP3)": "extract_audio",
    "Converter para MP4 (H.264)": "to_mp4",
    "Converter para GIF": "to_gif",
    "Redimensionar (720p)": "scale_720p",
    "Remover Audio (Mute)": "mute",
    "Mix de Audio": "mix_audio",
    "Substituir Audio de Video": "replace_audio",
    "Cortar Início (Frames)": "cut_front",
    "Cortar Fim (Frames)": "cut_back",
    "Loop Final (Frames)": "loop_end",
    "Loop Final (Ping-Pong)": "loop_pingpong",
    "Imagem para Vídeo": "image_to_video",
    "Crop Espacial": "spatial_crop",
    "Flash de Memória": "memory_flash",
    "Lado a Lado (Side-by-Side)": "side_by_side",
    "Marca d'água / Overlay": "overlay",
}


class FFmpegApp(QMainWindow):
    def __init__(self, initial_operation=None, initial_files=None):
        super().__init__()
        self.setWindowTitle("FFmpeg Tools")
        self.resize(650, 500)

        # Set window icon
        icon_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "ffmpeg_tools.ico"
        )
        if os.path.exists(icon_path):
            from PyQt6.QtGui import QIcon

            self.setWindowIcon(QIcon(icon_path))

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)

        # Operation selector
        op_layout = QHBoxLayout()
        op_layout.addWidget(QLabel("Operação:"))
        self.op_combo = QComboBox()
        self.op_combo.addItems(OPERATIONS.keys())
        self.op_combo.setMinimumWidth(250)

        op_layout.addWidget(self.op_combo)

        op_layout.addSpacing(20)

        self.frames_lbl_title = QLabel("Frames p/ Cortar/Loop:")
        op_layout.addWidget(self.frames_lbl_title)
        self.frames_spin = QSpinBox()
        self.frames_spin.setRange(1, 999999)
        self.frames_spin.setValue(30)
        self.frames_spin.setFixedWidth(80)
        op_layout.addWidget(self.frames_spin)

        op_layout.addSpacing(10)

        self.loop_lbl_title = QLabel("Vezes (Loop):")
        op_layout.addWidget(self.loop_lbl_title)
        self.loop_spin = QSpinBox()
        self.loop_spin.setRange(1, 999)
        self.loop_spin.setValue(3)
        self.loop_spin.setFixedWidth(50)
        op_layout.addWidget(self.loop_spin)

        op_layout.addSpacing(10)

        self.fps_lbl_title = QLabel("FPS de Saída:")
        op_layout.addWidget(self.fps_lbl_title)
        self.fps_spin = QSpinBox()
        self.fps_spin.setRange(1, 120)
        self.fps_spin.setValue(30)
        self.fps_spin.setFixedWidth(50)
        op_layout.addWidget(self.fps_spin)

        self.file_metadata = {}  # Cache for probe results

        op_layout.addStretch()
        self.main_layout.addLayout(op_layout)

        # Connect combo box to hide/show logic
        self.op_combo.currentTextChanged.connect(self._on_operation_changed)

        # Video Info Label
        self.info_label = QLabel("Nenhum vídeo carregado.")
        self.info_label.setStyleSheet("color: #666; font-size: 11px;")
        self.main_layout.addWidget(self.info_label)

        # Instructions
        self.label = QLabel("Arraste e solte arquivos aqui, ou use o botão Adicionar:")
        self.main_layout.addWidget(self.label)

        # List Widget for files
        self.list_widget = QListWidget()
        self.list_widget.setSelectionMode(
            QAbstractItemView.SelectionMode.ExtendedSelection
        )
        self.list_widget.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.list_widget.setAcceptDrops(True)
        self.list_widget.viewport().setAcceptDrops(True)
        self.main_layout.addWidget(self.list_widget)

        # Compatibility Status Label
        self.compat_label = QLabel("")
        self.compat_label.setStyleSheet("font-weight: bold; margin-bottom: 5px;")
        self.compat_label.setWordWrap(True)
        self.main_layout.addWidget(self.compat_label)

        # Concat resolution options (visible only for incompatible concat)
        self.concat_opts_widget = QWidget()
        concat_opts_layout = QVBoxLayout(self.concat_opts_widget)
        concat_opts_layout.setContentsMargins(0, 0, 0, 0)

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
        concat_opts_layout.addLayout(row1)

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
        concat_opts_layout.addLayout(row2)

        self.concat_opts_widget.setVisible(False)
        self.main_layout.addWidget(self.concat_opts_widget)

        self.res_heuristic_combo.currentTextChanged.connect(self._on_heuristic_changed)
        self._on_heuristic_changed(self.res_heuristic_combo.currentText())

        # Spatial crop options (visible only for spatial_crop operation)
        self.spatial_crop_widget = QWidget()
        sc_layout = QHBoxLayout(self.spatial_crop_widget)
        sc_layout.setContentsMargins(0, 0, 0, 0)

        sc_layout.addWidget(QLabel("W:"))
        self.sc_w_spin = QSpinBox()
        self.sc_w_spin.setRange(2, 7680)
        self.sc_w_spin.setValue(480)
        self.sc_w_spin.setSingleStep(2)
        self.sc_w_spin.setFixedWidth(70)
        sc_layout.addWidget(self.sc_w_spin)

        sc_layout.addWidget(QLabel("H:"))
        self.sc_h_spin = QSpinBox()
        self.sc_h_spin.setRange(2, 4320)
        self.sc_h_spin.setValue(480)
        self.sc_h_spin.setSingleStep(2)
        self.sc_h_spin.setFixedWidth(70)
        sc_layout.addWidget(self.sc_h_spin)

        sc_layout.addSpacing(10)

        self.sc_center_cb = QCheckBox("Centro")
        self.sc_center_cb.setChecked(True)
        self.sc_center_cb.toggled.connect(self._on_sc_center_toggled)
        sc_layout.addWidget(self.sc_center_cb)

        sc_layout.addSpacing(10)

        self.sc_x_lbl = QLabel("X:")
        sc_layout.addWidget(self.sc_x_lbl)
        self.sc_x_spin = QSpinBox()
        self.sc_x_spin.setRange(0, 7680)
        self.sc_x_spin.setValue(0)
        self.sc_x_spin.setFixedWidth(70)
        self.sc_x_spin.setEnabled(False)
        sc_layout.addWidget(self.sc_x_spin)

        self.sc_y_lbl = QLabel("Y:")
        sc_layout.addWidget(self.sc_y_lbl)
        self.sc_y_spin = QSpinBox()
        self.sc_y_spin.setRange(0, 4320)
        self.sc_y_spin.setValue(0)
        self.sc_y_spin.setFixedWidth(70)
        self.sc_y_spin.setEnabled(False)
        sc_layout.addWidget(self.sc_y_spin)

        sc_layout.addStretch()

        self.spatial_crop_widget.setVisible(False)
        self.main_layout.addWidget(self.spatial_crop_widget)

        # Memory flash options
        self.flash_widget = QWidget()
        flash_main = QVBoxLayout(self.flash_widget)
        flash_main.setContentsMargins(0, 0, 0, 0)

        flash_row1 = QHBoxLayout()
        flash_row1.addWidget(QLabel("Fragmentos:"))
        self.flash_count_spin = QSpinBox()
        self.flash_count_spin.setRange(1, 50)
        self.flash_count_spin.setValue(4)
        self.flash_count_spin.setFixedWidth(50)
        self.flash_count_spin.setToolTip("Grupos de flashes (posição sorteada)")
        flash_row1.addWidget(self.flash_count_spin)

        flash_row1.addSpacing(10)

        flash_row1.addWidget(QLabel("Subfragmentos:"))
        self.flash_sub_spin = QSpinBox()
        self.flash_sub_spin.setRange(1, 30)
        self.flash_sub_spin.setValue(3)
        self.flash_sub_spin.setFixedWidth(50)
        self.flash_sub_spin.setToolTip("Flashes por fragmento (espaçados igualmente)")
        flash_row1.addWidget(self.flash_sub_spin)

        flash_row1.addSpacing(10)

        flash_row1.addWidget(QLabel("Tamanho (frames):"))
        self.flash_size_spin = QSpinBox()
        self.flash_size_spin.setRange(1, 60)
        self.flash_size_spin.setValue(2)
        self.flash_size_spin.setFixedWidth(50)
        self.flash_size_spin.setToolTip("Frames consecutivos por subfragmento")
        flash_row1.addWidget(self.flash_size_spin)

        flash_row1.addSpacing(10)

        flash_row1.addWidget(QLabel("Espaçamento (frames):"))
        self.flash_gap_spin = QSpinBox()
        self.flash_gap_spin.setRange(1, 300)
        self.flash_gap_spin.setValue(3)
        self.flash_gap_spin.setFixedWidth(60)
        self.flash_gap_spin.setToolTip("Frames de vídeo 1 entre subfragmentos")
        flash_row1.addWidget(self.flash_gap_spin)

        flash_row1.addSpacing(10)

        flash_row1.addWidget(QLabel("Seed:"))
        self.flash_seed_spin = QSpinBox()
        self.flash_seed_spin.setRange(0, 999999)
        self.flash_seed_spin.setValue(0)
        self.flash_seed_spin.setToolTip("0 = aleatório. Mesmo seed = mesmos resultados.")
        self.flash_seed_spin.setFixedWidth(70)
        flash_row1.addWidget(self.flash_seed_spin)

        flash_row1.addStretch()
        flash_main.addLayout(flash_row1)

        self.flash_widget.setVisible(False)
        self.main_layout.addWidget(self.flash_widget)

        # Drag-and-drop from OS
        self.list_widget.dragEnterEvent = self._dragEnterEvent
        self.list_widget.dragMoveEvent = self._dragMoveEvent
        self.list_widget.dropEvent = self._dropEvent

        # Buttons
        btn_layout = QHBoxLayout()

        self.btn_add = QPushButton("Adicionar Arquivos")
        self.btn_add.clicked.connect(self.add_files_dialog)

        self.btn_up = QPushButton("▲")
        self.btn_up.setFixedWidth(32)
        self.btn_up.clicked.connect(self.move_up)

        self.btn_down = QPushButton("▼")
        self.btn_down.setFixedWidth(32)
        self.btn_down.clicked.connect(self.move_down)

        self.btn_remove = QPushButton("Remover")
        self.btn_remove.clicked.connect(self.remove_selected)

        self.btn_run = QPushButton("▶  Executar FFmpeg")
        self.btn_run.setStyleSheet(
            "font-weight: bold; background-color: #4CAF50; color: white; padding: 6px 16px;"
        )
        self.btn_run.clicked.connect(self.run_ffmpeg)

        btn_layout.addWidget(self.btn_add)
        btn_layout.addWidget(self.btn_up)
        btn_layout.addWidget(self.btn_down)
        btn_layout.addWidget(self.btn_remove)
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_run)
        self.main_layout.addLayout(btn_layout)

        # Log console
        self.log_console = QTextEdit()
        self.log_console.setReadOnly(True)
        self.log_console.hide()
        self.main_layout.addWidget(self.log_console)

        # Populate initial files
        if initial_files:
            for f in initial_files:
                abs_f = os.path.abspath(f)
                if os.path.exists(abs_f):
                    self.add_file(abs_f)

        # Pre-select operation if provided
        if initial_operation:
            for k, v in OPERATIONS.items():
                if v == initial_operation:
                    self.op_combo.setCurrentText(k)
                    break

        # Trigger initial state
        self._on_operation_changed(self.op_combo.currentText())

    def _on_operation_changed(self, text):
        operation = OPERATIONS.get(text, "")

        # Determine visibility
        show_frames = operation in (
            "cut_front",
            "cut_back",
            "loop_end",
            "loop_pingpong",
            "image_to_video",
        )
        show_loop = operation in ("loop_end", "loop_pingpong")
        show_fps = operation == "image_to_video"

        # Apply visibility
        self.frames_lbl_title.setVisible(show_frames)
        self.frames_spin.setVisible(show_frames)

        if operation == "cut_front":
            self.frames_lbl_title.setText("Cortar no Início (Frames):")
        elif operation == "cut_back":
            self.frames_lbl_title.setText("Cortar no Fim (Frames):")
        elif operation in ("loop_end", "loop_pingpong"):
            self.frames_lbl_title.setText("Tamanho do Trecho (Frames):")
        elif operation == "image_to_video":
            self.frames_lbl_title.setText("Frames Totais:")

        self.loop_lbl_title.setVisible(show_loop)
        self.loop_spin.setVisible(show_loop)

        self.fps_lbl_title.setVisible(show_fps)
        self.fps_spin.setVisible(show_fps)

        self.spatial_crop_widget.setVisible(operation in ("spatial_crop", "overlay"))
        self.flash_widget.setVisible(operation == "memory_flash")

        self.analyze_compatibility()

    def _on_heuristic_changed(self, text):
        is_manual = text == "Manual"
        self.manual_lbl.setVisible(is_manual)
        self.manual_w_spin.setVisible(is_manual)
        self.manual_h_lbl.setVisible(is_manual)
        self.manual_h_spin.setVisible(is_manual)

    def _on_sc_center_toggled(self, checked):
        self.sc_x_spin.setEnabled(not checked)
        self.sc_y_spin.setEnabled(not checked)

    # --- Drag and Drop ---
    def _dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            super(QListWidget, self.list_widget).dragEnterEvent(event)

    def _dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            super(QListWidget, self.list_widget).dragMoveEvent(event)

    def _dropEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
            for url in event.mimeData().urls():
                if url.isLocalFile():
                    self.add_file(url.toLocalFile())
            self.analyze_compatibility()
        else:
            super(QListWidget, self.list_widget).dropEvent(event)
            self.analyze_compatibility()

    # --- File management ---
    def add_file(self, file_path):
        for i in range(self.list_widget.count()):
            if self.list_widget.item(i).data(32) == file_path:
                return
        item = QListWidgetItem(os.path.basename(file_path), self.list_widget)
        item.setData(32, file_path)  # Store actual path in data
        self.update_video_info(file_path)
        self.analyze_compatibility()

    def update_video_info(self, file_path):
        if file_path in self.file_metadata:
            info_data = self.file_metadata[file_path]
            self._display_info(info_data)
            return

        cmd = [
            "ffprobe",
            "-v",
            "quiet",
            "-print_format",
            "json",
            "-show_format",
            "-show_streams",
            file_path,
        ]
        try:
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            if not result.stdout:
                self.info_label.setText("Nenhuma informação disponível.")
                return
            info = json.loads(result.stdout)

            video_stream = next(
                (s for s in info.get("streams", []) if s.get("codec_type") == "video"),
                None,
            )

            meta = {"width": 0, "height": 0, "fps": 0.0, "is_video": False}

            if video_stream:
                width = video_stream.get("width", 0)
                height = video_stream.get("height", 0)
                fps_str = video_stream.get("r_frame_rate", "0/0")
                fps = 0.0
                if "/" in fps_str:
                    try:
                        num, den = map(int, fps_str.split("/"))
                        if den != 0:
                            fps = round(num / den, 2)
                    except Exception:
                        pass

                meta.update(
                    {"width": width, "height": height, "fps": fps, "is_video": True}
                )

                try:
                    duration_val = info.get("format", {}).get("duration")
                    meta["duration"] = float(duration_val) if duration_val else 0.0
                except Exception:
                    meta["duration"] = 0.0

            # Check for audio only
            meta["has_audio"] = any(
                s.get("codec_type") == "audio" for s in info.get("streams", [])
            )

            self.file_metadata[file_path] = meta
            self._display_info(meta)

        except Exception as e:
            self.info_label.setText(f"⚠ Erro ao ler informações: {str(e)}")

    def _display_info(self, meta):
        if meta.get("is_video"):
            dur = meta.get("duration", 0)
            dur_str = f"{int(dur // 60)}m {int(dur % 60)}s"
            self.info_label.setText(
                f"🎥 Info: {meta['width']}x{meta['height']} | {meta['fps']} FPS | {dur_str}"
            )
        elif meta.get("has_audio"):
            self.info_label.setText("🎵 Info: Áudio carregado")
        else:
            self.info_label.setText("🖼 Info: Imagem carregada")

    def analyze_compatibility(self):
        if self.list_widget.count() < 1:
            self.compat_label.setText("")
            self.concat_opts_widget.setVisible(False)
            return False

        operation = OPERATIONS[self.op_combo.currentText()]
        if operation != "concat":
            self.compat_label.setText("")
            self.concat_opts_widget.setVisible(False)
            return False

        first_path = self.list_widget.item(0).data(32)
        if first_path not in self.file_metadata:
            self.concat_opts_widget.setVisible(False)
            return False

        base = self.file_metadata[first_path]
        if not base.get("is_video"):
            self.compat_label.setText("⚠ Primeiro arquivo não é vídeo.")
            self.compat_label.setStyleSheet("color: #d32f2f;")
            self.concat_opts_widget.setVisible(False)
            return False

        issues = []
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            path = item.data(32)
            meta = self.file_metadata.get(path)

            if not meta:
                continue

            spec_str = (
                f"({meta['width']}x{meta['height']}, {meta['fps']} FPS)"
                if meta.get("is_video")
                else "(Sem Vídeo)"
            )
            item.setText(f"{os.path.basename(path)}   -   {spec_str}")

            if i > 0:
                if (
                    meta.get("width") != base["width"]
                    or meta.get("height") != base["height"]
                ):
                    issues.append(f"Resolução diferente no item {i + 1}")
                if abs(meta.get("fps", 0) - base["fps"]) > 0.01:
                    issues.append(f"FPS diferente no item {i + 1}")

        if issues:
            self.compat_label.setText(
                f"⚠ Incompatibilidade: {'; '.join(issues[:2])}{'...' if len(issues) > 2 else ''}"
            )
            self.compat_label.setStyleSheet("color: #d32f2f;")
            self.concat_opts_widget.setVisible(True)
            return False
        else:
            self.compat_label.setText(
                "✅ Arquivos compatíveis para concatenação rápida."
            )
            self.compat_label.setStyleSheet("color: #2e7d32;")
            self.concat_opts_widget.setVisible(False)
            return True

    def add_files_dialog(self):
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Selecionar arquivos",
            "",
            "Videos (*.mp4 *.mkv *.avi *.mov *.webm *.gif);;Todos (*)",
        )
        for f in files:
            self.add_file(f)

    def move_up(self):
        row = self.list_widget.currentRow()
        if row > 0:
            item = self.list_widget.takeItem(row)
            self.list_widget.insertItem(row - 1, item)
            self.list_widget.setCurrentRow(row - 1)
            self.analyze_compatibility()

    def move_down(self):
        row = self.list_widget.currentRow()
        if row < self.list_widget.count() - 1 and row != -1:
            item = self.list_widget.takeItem(row)
            self.list_widget.insertItem(row + 1, item)
            self.list_widget.setCurrentRow(row + 1)
            self.analyze_compatibility()

    def remove_selected(self):
        for item in self.list_widget.selectedItems():
            path = item.data(32)
            self.list_widget.takeItem(self.list_widget.row(item))
            # Optional: check if path is still in list before removing from cache
            still_present = False
            for i in range(self.list_widget.count()):
                if self.list_widget.item(i).data(32) == path:
                    still_present = True
                    break
            if not still_present and path in self.file_metadata:
                del self.file_metadata[path]
        self.analyze_compatibility()

    # --- Log ---
    def log(self, message):
        self.log_console.append(message)
        scrollbar = self.log_console.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    # --- FFmpeg execution ---
    def run_ffmpeg(self):
        try:
            self._run_ffmpeg_inner()
        except Exception:
            tb = traceback.format_exc()
            self.log_console.show()
            self.log(f"--- ERRO INTERNO ---\n{tb}")

    def _run_ffmpeg_inner(self):
        if self.list_widget.count() == 0:
            QMessageBox.warning(self, "Aviso", "Nenhum arquivo selecionado.")
            return

        files = [
            self.list_widget.item(i).data(32) for i in range(self.list_widget.count())
        ]
        operation = OPERATIONS[self.op_combo.currentText()]
        cwd = os.path.dirname(files[0])
        command = []

        if operation == "concat":
            if len(files) < 2:
                QMessageBox.warning(
                    self, "Aviso", "Concatenar requer pelo menos 2 arquivos."
                )
                return

            # Check for compatibility
            is_compatible = self.analyze_compatibility()

            if not is_compatible:
                # Use the separate safe_concat.py script
                ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                base = os.path.splitext(os.path.basename(files[0]))[0]
                out_name = os.path.join(cwd, f"{base}_safe_concat_{ts}.mp4")

                safe_script = os.path.join(
                    os.path.dirname(os.path.abspath(__file__)), "safe_concat.py"
                )

                heuristic_map = {
                    "Maior Duração Total": "longest_duration",
                    "Maior Resolução": "highest",
                    "Maioria (Contagem)": "majority",
                    "Primeiro Arquivo": "first",
                    "Manual": "manual",
                }
                crop_map = {
                    "Letterbox (Barras Pretas)": "letterbox",
                    "Crop Centro": "center",
                    "Crop Cima": "top",
                    "Crop Baixo": "bottom",
                    "Crop Esquerda": "left",
                    "Crop Direita": "right",
                }
                heuristic = heuristic_map.get(
                    self.res_heuristic_combo.currentText(), "longest_duration"
                )
                crop = crop_map.get(self.crop_combo.currentText(), "letterbox")

                command = [
                    "python", safe_script,
                    "--heuristic", heuristic,
                    "--crop", crop,
                ]
                if heuristic == "manual":
                    command.extend([
                        "--width", str(self.manual_w_spin.value()),
                        "--height", str(self.manual_h_spin.value()),
                    ])
                command.extend(["-o", out_name, "--"])
                command.extend(files)

                self.launch_worker(command, cwd)
                return

            concat_txt_path = os.path.join(cwd, "concat.txt")
            try:
                with open(concat_txt_path, "w", encoding="utf-8") as f:
                    for file in files:
                        rel_path = os.path.basename(file)
                        f.write(f"file '{rel_path}'\n")
            except Exception as e:
                QMessageBox.critical(self, "Erro", f"Erro ao criar concat.txt:\n{e}")
                return

            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            base = os.path.splitext(os.path.basename(files[0]))[0]
            out_name = os.path.join(cwd, f"{base}_and_others_concat_{ts}.mp4")

            command = [
                "ffmpeg",
                "-y",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                concat_txt_path,
                "-c",
                "copy",
                out_name,
            ]

        elif operation == "extract_audio":
            inp = files[0]
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            base = os.path.splitext(os.path.basename(inp))[0]
            out = os.path.join(cwd, f"{base}_audio_{ts}.mp3")
            command = [
                "ffmpeg",
                "-y",
                "-i",
                inp,
                "-vn",
                "-c:a",
                "libmp3lame",
                "-q:a",
                "2",
                out,
            ]

        elif operation == "to_mp4":
            inp = files[0]
            out = os.path.splitext(inp)[0] + "_converted.mp4"
            command = [
                "ffmpeg",
                "-y",
                "-i",
                inp,
                "-c:v",
                "libx264",
                "-preset",
                "fast",
                "-crf",
                "22",
                "-c:a",
                "aac",
                "-b:a",
                "128k",
                out,
            ]

        elif operation == "to_gif":
            inp = files[0]
            out = os.path.splitext(inp)[0] + ".gif"
            vf = "fps=15,scale=480:-1:flags=lanczos,split[s0][s1];[s0]palettegen[p];[s1][p]paletteuse"
            command = ["ffmpeg", "-y", "-i", inp, "-vf", vf, "-loop", "0", out]

        elif operation == "scale_720p":
            inp = files[0]
            out = os.path.splitext(inp)[0] + "_720p.mp4"
            command = [
                "ffmpeg",
                "-y",
                "-i",
                inp,
                "-vf",
                "scale=-2:720",
                "-c:v",
                "libx264",
                "-crf",
                "23",
                "-c:a",
                "copy",
                out,
            ]

        elif operation == "mute":
            inp = files[0]
            out = os.path.splitext(inp)[0] + "_muted.mp4"
            command = ["ffmpeg", "-y", "-i", inp, "-c:v", "copy", "-an", out]

        elif operation == "mix_audio":
            if len(files) < 2:
                QMessageBox.warning(
                    self, "Aviso", "Mix de áudio requer pelo menos 2 arquivos."
                )
                return

            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            base = os.path.splitext(os.path.basename(files[0]))[0]
            out = os.path.join(cwd, f"{base}_mixed_audio_{ts}.mp3")

            command = ["ffmpeg", "-y"]
            for f in files:
                command.extend(["-i", f])

            command.extend(
                [
                    "-filter_complex",
                    f"amix=inputs={len(files)}:duration=longest",
                    "-c:a",
                    "libmp3lame",
                    "-q:a",
                    "2",
                    out,
                ]
            )

        elif operation == "replace_audio":
            if len(files) != 2:
                QMessageBox.warning(
                    self,
                    "Aviso",
                    "Substituição de áudio requer exatamente 1 vídeo e 1 áudio.",
                )
                return

            v_exts = {".mp4", ".mkv", ".avi", ".mov", ".webm"}
            a_exts = {".mp3", ".wav", ".aac", ".flac", ".ogg", ".m4a"}

            video_file = None
            audio_file = None

            for f in files:
                ext = os.path.splitext(f)[1].lower()
                if ext in v_exts:
                    video_file = f
                elif ext in a_exts:
                    audio_file = f

            if not video_file or not audio_file:
                # Fallback se a extensão não for listada, assumimos a ordem: primeiro vídeo, segundo áudio
                video_file, audio_file = files[0], files[1]

            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            out = os.path.splitext(video_file)[0] + f"_newaudio_{ts}.mp4"

            command = [
                "ffmpeg",
                "-y",
                "-i",
                video_file,
                "-i",
                audio_file,
                "-c:v",
                "copy",
                "-c:a",
                "aac",
                "-map",
                "0:v:0",
                "-map",
                "1:a:0?",  # ? in case audio stream index is weird, but 1:a:0 is standard
                "-shortest",
                out,
            ]

        elif operation == "cut_front":
            inp = files[0]
            frames = self.frames_spin.value()
            out = os.path.splitext(inp)[0] + f"_cutfront_{frames}f.mp4"

            # Calculate start time based on precise frame counting
            # By calculating exact duration per frame, we use -ss for accuracy
            # A simpler way with ffmpeg video filters:
            command = [
                "ffmpeg",
                "-y",
                "-i",
                inp,
                "-vf",
                f"select='gte(n\,{frames})',setpts=PTS-STARTPTS",
                "-af",
                f"aselect='gte(n\,{frames})',asetpts=PTS-STARTPTS",
                out,
            ]

        elif operation == "cut_back":
            inp = files[0]
            frames = self.frames_spin.value()
            out = os.path.splitext(inp)[0] + f"_cutback_{frames}f.mp4"

            # Get total frames first to know where to stop

            cmd = [
                "ffprobe",
                "-v",
                "quiet",
                "-print_format",
                "json",
                "-show_streams",
                inp,
            ]
            try:
                result = subprocess.run(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    creationflags=subprocess.CREATE_NO_WINDOW,
                )
                info = json.loads(result.stdout)
                video_stream = next(
                    (
                        s
                        for s in info.get("streams", [])
                        if s.get("codec_type") == "video"
                    ),
                    None,
                )
                if not video_stream or "nb_frames" not in video_stream:
                    QMessageBox.warning(
                        self,
                        "Aviso",
                        "Não foi possível determinar o total de frames do vídeo.",
                    )
                    return

                total_frames = int(video_stream["nb_frames"])
                target_frames = total_frames - frames
                if target_frames <= 0:
                    QMessageBox.warning(
                        self, "Aviso", "O corte é maior ou igual ao tamanho do vídeo."
                    )
                    return

                command = [
                    "ffmpeg",
                    "-y",
                    "-i",
                    inp,
                    "-vframes",
                    str(target_frames),
                    "-c:a",
                    "copy",
                    out,
                ]
            except Exception as e:
                QMessageBox.critical(self, "Erro", f"Erro ao ler frames: {e}")
                return

        elif operation in ("loop_end", "loop_pingpong"):
            inp = files[0]
            frames = self.frames_spin.value()
            loops = self.loop_spin.value()

            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            base = os.path.splitext(os.path.basename(inp))[0]
            suffix = "loop" if operation == "loop_end" else "pingpong"
            out = os.path.join(cwd, f"{base}_{suffix}_end_{ts}.mp4")

            cmd = [
                "ffprobe",
                "-v",
                "quiet",
                "-print_format",
                "json",
                "-show_streams",
                inp,
            ]
            try:
                result = subprocess.run(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    creationflags=subprocess.CREATE_NO_WINDOW,
                )
                info = json.loads(result.stdout)
                video_stream = next(
                    (
                        s
                        for s in info.get("streams", [])
                        if s.get("codec_type") == "video"
                    ),
                    None,
                )
                if not video_stream or "nb_frames" not in video_stream:
                    QMessageBox.warning(
                        self,
                        "Aviso",
                        "Não foi possível determinar o total de frames do vídeo.",
                    )
                    return

                total_frames = int(video_stream["nb_frames"])
                start_frame = total_frames - frames

                if start_frame < 0:
                    start_frame = 0

                has_audio = any(
                    s.get("codec_type") == "audio" for s in info.get("streams", [])
                )

                # Get exact FPS to calculate start time in seconds
                fps_str = video_stream.get("r_frame_rate", "0/0")
                if "/" in fps_str:
                    num, den = fps_str.split("/")
                    fps = float(num) / float(den) if float(den) != 0 else 30.0
                else:
                    fps = float(fps_str)

                t_start = start_frame / fps

                if start_frame <= 0:
                    # Loop entire video
                    # For pingpong on the entire video it would need a complex filter anyway
                    # Since this is a very rare edge case (looping/pingponging the whole video using this tool),
                    # We will treat it as prefix=0, and suffix=entire video
                    pass

                filter_complex = ""
                concat_str = ""

                # Part 0 is prefix (which can be 0 seconds if start_frame <= 0)
                # Part 1 is Original suffix
                # Parts 2..loops+1 are the repetitions
                n_parts = loops + 2

                # Split video and audio streams into n_parts
                split_v = (
                    f"[0:v:0]split={n_parts}"
                    + "".join(f"[v_in{i}]" for i in range(n_parts))
                    + ";"
                )
                filter_complex += split_v

                if has_audio:
                    split_a = (
                        f"[0:a:0]asplit={n_parts}"
                        + "".join(f"[a_in{i}]" for i in range(n_parts))
                        + ";"
                    )
                    filter_complex += split_a

                # Apply trimming for prefix (part 0) and suffixes (parts 1..N)
                for i in range(n_parts):
                    is_rev = False
                    if operation == "loop_pingpong" and i > 0 and (i - 1) % 2 == 1:
                        # (i-1) is the repeat index (0 is original, 1 is 1st repeat, 2 is 2nd...)
                        # 1st repeat is backwards, 2nd is forwards, 3rd is backwards...
                        is_rev = True

                    if i == 0:
                        v_trim = f"[v_in0]trim=end={t_start},setpts=PTS-STARTPTS[v0];"
                        filter_complex += v_trim
                        if has_audio:
                            a_trim = (
                                f"[a_in0]atrim=end={t_start},asetpts=PTS-STARTPTS[a0];"
                            )
                            filter_complex += a_trim
                    else:
                        v_trim = f"[v_in{i}]trim=start={t_start},setpts=PTS-STARTPTS"
                        if is_rev:
                            v_trim += ",reverse"
                        v_trim += f"[v{i}];"
                        filter_complex += v_trim
                        if has_audio:
                            a_trim = (
                                f"[a_in{i}]atrim=start={t_start},asetpts=PTS-STARTPTS"
                            )
                            if is_rev:
                                a_trim += ",areverse"
                            a_trim += f"[a{i}];"
                            filter_complex += a_trim

                    if has_audio:
                        concat_str += f"[v{i}][a{i}]"
                    else:
                        concat_str += f"[v{i}]"

                # Concatenate everything back
                a_val = "1" if has_audio else "0"
                concat_filter = f"{concat_str}concat=n={n_parts}:v=1:a={a_val}[v]"
                if has_audio:
                    concat_filter += "[a]"

                filter_complex += concat_filter

                command = [
                    "ffmpeg",
                    "-y",
                    "-i",
                    inp,
                    "-filter_complex",
                    filter_complex,
                    "-map",
                    "[v]",
                ]
                if has_audio:
                    command.extend(["-map", "[a]"])
                command.append(out)
                # If audio is needed, we could add [0:a]atrim...

            except Exception as e:
                QMessageBox.critical(
                    self, "Erro", f"Erro ao executar operação de loop: {e}"
                )
                return

        elif operation == "image_to_video":
            inp = files[0]
            frames = self.frames_spin.value()
            fps = self.fps_spin.value()

            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            base = os.path.splitext(os.path.basename(inp))[0]
            out = os.path.join(cwd, f"{base}_image_to_video_{ts}.mp4")

            command = [
                "ffmpeg",
                "-y",
                "-loop",
                "1",
                "-i",
                inp,
                "-r",
                str(fps),
                "-frames:v",
                str(frames),
                "-c:v",
                "libx264",
                "-vf",
                "scale=trunc(iw/2)*2:trunc(ih/2)*2",
                "-pix_fmt",
                "yuv420p",
                out,
            ]

        elif operation == "memory_flash":
            if len(files) != 2:
                QMessageBox.warning(
                    self,
                    "Aviso",
                    "Flash de Memória requer exatamente 2 vídeos.",
                )
                return

            v1, v2 = files[0], files[1]
            meta1 = self.file_metadata.get(v1)
            meta2 = self.file_metadata.get(v2)

            if not meta1 or not meta1.get("is_video") or not meta2 or not meta2.get("is_video"):
                QMessageBox.warning(self, "Aviso", "Ambos os arquivos devem ser vídeos.")
                return

            fps1 = meta1["fps"]
            dur1 = meta1.get("duration", 0)
            total_frames = int(dur1 * fps1)

            n_fragments = self.flash_count_spin.value()
            n_subs = self.flash_sub_spin.value()
            sub_size = self.flash_size_spin.value()
            sub_gap = self.flash_gap_spin.value()
            seed_val = self.flash_seed_spin.value()

            rng = random.Random() if seed_val == 0 else random.Random(seed_val)

            # A fragment spans: n_subs * sub_size + (n_subs - 1) * sub_gap frames
            frag_span = n_subs * sub_size + (n_subs - 1) * sub_gap
            total_occupied = n_fragments * frag_span

            if total_occupied >= total_frames:
                QMessageBox.warning(
                    self, "Aviso",
                    f"Fragmentos ocupam {total_occupied} frames mas o vídeo tem {total_frames}.",
                )
                return

            # Place fragments randomly (non-overlapping, sorted)
            available = total_frames - total_occupied
            slots = sorted(rng.sample(range(available), n_fragments))
            frag_starts = []
            offset = 0
            for s in slots:
                pos = s + offset
                frag_starts.append(pos)
                offset += frag_span

            # Expand each fragment into a list of (v1_start, v1_end, v2_start, v2_end) events
            # Timeline is a sequence of segments: v1, v2_sub, v1_gap, v2_sub, ..., v1
            # We collect all cut points as a flat list of segments with their source
            segments = []  # list of (source, start_frame, end_frame)
            prev_end = 0

            for frag_start in frag_starts:
                # v1 segment before this fragment
                if frag_start > prev_end:
                    segments.append(("v1", prev_end, frag_start))

                for s in range(n_subs):
                    sub_start = frag_start + s * (sub_size + sub_gap)
                    sub_end = sub_start + sub_size

                    # v1 gap between subfragments (within the fragment)
                    if s > 0:
                        gap_start = frag_start + (s - 1) * (sub_size + sub_gap) + sub_size
                        gap_end = sub_start
                        if gap_end > gap_start:
                            segments.append(("v1", gap_start, gap_end))

                    # v2 subfragment (same temporal position)
                    segments.append(("v2", sub_start, sub_end))

                prev_end = frag_start + frag_span

            # Final v1 segment
            if prev_end < total_frames:
                segments.append(("v1", prev_end, total_frames))

            # Count splits needed
            n_v1 = sum(1 for src, _, _ in segments if src == "v1")
            n_v2 = sum(1 for src, _, _ in segments if src == "v2")
            total_segs = len(segments)

            has_audio_1 = meta1.get("has_audio", False)
            has_audio_2 = meta2.get("has_audio", False)
            has_audio = has_audio_1 and has_audio_2

            # Build filter_complex
            fc = ""
            fc += f"[0:v]split={n_v1}" + "".join(f"[v1_{i}]" for i in range(n_v1)) + ";"
            fc += f"[1:v]split={n_v2}" + "".join(f"[v2_{i}]" for i in range(n_v2)) + ";"
            if has_audio:
                fc += f"[0:a]asplit={n_v1}" + "".join(f"[a1_{i}]" for i in range(n_v1)) + ";"
                fc += f"[1:a]asplit={n_v2}" + "".join(f"[a2_{i}]" for i in range(n_v2)) + ";"

            concat_pads = ""
            v1_idx = 0
            v2_idx = 0

            for seg_i, (src, sf, ef) in enumerate(segments):
                t_start = sf / fps1
                t_end = ef / fps1
                if src == "v1":
                    fc += f"[v1_{v1_idx}]trim=start={t_start:.6f}:end={t_end:.6f},setpts=PTS-STARTPTS[seg{seg_i}];"
                    if has_audio:
                        fc += f"[a1_{v1_idx}]atrim=start={t_start:.6f}:end={t_end:.6f},asetpts=PTS-STARTPTS[aseg{seg_i}];"
                    v1_idx += 1
                else:
                    fc += f"[v2_{v2_idx}]trim=start={t_start:.6f}:end={t_end:.6f},setpts=PTS-STARTPTS[seg{seg_i}];"
                    if has_audio:
                        fc += f"[a2_{v2_idx}]atrim=start={t_start:.6f}:end={t_end:.6f},asetpts=PTS-STARTPTS[aseg{seg_i}];"
                    v2_idx += 1

                if has_audio:
                    concat_pads += f"[seg{seg_i}][aseg{seg_i}]"
                else:
                    concat_pads += f"[seg{seg_i}]"

            a_val = "1" if has_audio else "0"
            fc += f"{concat_pads}concat=n={total_segs}:v=1:a={a_val}[vout]"
            if has_audio:
                fc += "[aout]"

            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            base = os.path.splitext(os.path.basename(v1))[0]
            out = os.path.join(cwd, f"{base}_flash_{ts}.mp4")

            command = [
                "ffmpeg", "-y",
                "-i", v1,
                "-i", v2,
                "-filter_complex", fc,
                "-map", "[vout]",
            ]
            if has_audio:
                command.extend(["-map", "[aout]"])
            command.extend(["-c:v", "libx264", "-crf", "20", "-c:a", "aac", "-b:a", "192k", out])

        elif operation == "spatial_crop":
            inp = files[0]
            cw = self.sc_w_spin.value()
            ch = self.sc_h_spin.value()

            if self.sc_center_cb.isChecked():
                crop_filter = f"crop={cw}:{ch}"
            else:
                cx = self.sc_x_spin.value()
                cy = self.sc_y_spin.value()
                crop_filter = f"crop={cw}:{ch}:{cx}:{cy}"

            ext = os.path.splitext(inp)[1].lower()
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            base = os.path.splitext(os.path.basename(inp))[0]

            if ext == ".gif":
                out = os.path.join(cwd, f"{base}_cropped_{ts}.gif")
                command = [
                    "ffmpeg", "-y", "-i", inp,
                    "-vf", crop_filter,
                    "-loop", "0",
                    out,
                ]
            else:
                out = os.path.join(cwd, f"{base}_cropped_{ts}.mp4")
                command = [
                    "ffmpeg", "-y", "-i", inp,
                    "-vf", crop_filter,
                    "-c:a", "copy",
                    out,
                ]

        elif operation == "side_by_side":
            if len(files) != 2:
                QMessageBox.warning(self, "Aviso", "Lado a Lado requer exatamente 2 vídeos.")
                return
            
            v1, v2 = files[0], files[1]
            out = os.path.join(cwd, f"side_by_side_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4")
            
            # Simple side-by-side: scale both to the same height (height of v1)
            meta1 = self.file_metadata.get(v1)
            h1 = meta1.get("height", 720) if meta1 else 720
            
            filter_complex = (
                f"[0:v]scale=-1:{h1}[v1];"
                f"[1:v]scale=-1:{h1}[v2];"
                f"[v1][v2]hstack=inputs=2[vout]"
            )
            
            command = [
                "ffmpeg", "-y",
                "-i", v1, "-i", v2,
                "-filter_complex", filter_complex,
                "-map", "[vout]",
                "-c:v", "libx264", "-crf", "23", "-preset", "veryfast",
                out
            ]

        elif operation == "overlay":
            if len(files) != 2:
                QMessageBox.warning(self, "Aviso", "Overlay requer exatamente 2 arquivos (Fundo e Sobreposição).")
                return
            
            v1, v2 = files[0], files[1]
            out = os.path.join(cwd, f"overlay_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4")
            
            # Use spatial crop UI for overlay coordinates
            cw = self.sc_w_spin.value()
            ch = self.sc_h_spin.value()
            
            if self.sc_center_cb.isChecked():
                overlay_pos = "(W-w)/2:(H-h)/2"
            else:
                cx = self.sc_x_spin.value()
                cy = self.sc_y_spin.value()
                overlay_pos = f"{cx}:{cy}"
            
            # We also scale the overlay file to WxH from the UI
            filter_complex = (
                f"[1:v]scale={cw}:{ch}[ovl];"
                f"[0:v][ovl]overlay={overlay_pos}[vout]"
            )
            
            command = [
                "ffmpeg", "-y",
                "-i", v1, "-i", v2,
                "-filter_complex", filter_complex,
                "-map", "[vout]",
                "-c:v", "libx264", "-crf", "23", "-preset", "veryfast",
                out
            ]

        else:
            QMessageBox.critical(self, "Erro", f"Operação desconhecida: {operation}")
            return

        self.launch_worker(command, cwd)

    def launch_worker(self, command, cwd):
        self.btn_run.setEnabled(False)
        self.log_console.clear()
        self.log_console.show()
        self.log(f"Executando:\n{' '.join(command)}\n")

        self.worker = FFmpegWorker(command, cwd)
        self.worker.output_signal.connect(self.log)
        self.worker.finished_signal.connect(self.on_process_finished)
        self.worker.start()

    def on_process_finished(self, returncode):
        self.btn_run.setEnabled(True)
        if returncode == 0:
            self.log("\n--- SUCESSO ---")
            operation = OPERATIONS[self.op_combo.currentText()]
            if operation == "concat":
                try:
                    cwd = os.path.dirname(self.list_widget.item(0).data(32))
                    concat_path = os.path.join(cwd, "concat.txt")
                    if os.path.exists(concat_path):
                        os.remove(concat_path)
                except Exception:
                    pass
        else:
            self.log(f"\n--- FALHOU (Código {returncode}) ---")
            self.log("Verifique a saída do FFmpeg acima.")


if __name__ == "__main__":
    app = QApplication(sys.argv)

    op = None
    files = []

    if len(sys.argv) > 1:
        # Check if the first argument is an operation key (used by context menu)
        if sys.argv[1] in OPERATIONS.values():
            op = sys.argv[1]
            files = sys.argv[2:]
        else:
            files = sys.argv[1:]

    window = FFmpegApp(initial_operation=op, initial_files=files)
    window.show()
    sys.exit(app.exec())
