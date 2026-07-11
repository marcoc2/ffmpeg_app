import sys
import subprocess
import traceback
from datetime import datetime
from PyQt6.QtCore import QThread, pyqtSignal

class StderrRedirector:
    def __init__(self, filepath, original_stderr):
        self.filepath = filepath
        self.original_stderr = original_stderr

    def write(self, message):
        if message and message.strip():
            self.original_stderr.write(message)
            try:
                with open(self.filepath, "a", encoding="utf-8") as f:
                    f.write(f"\n--- STDERR AT {datetime.now()} ---\n")
                    f.write(message)
                    f.write("\n" + "-" * 30 + "\n")
            except Exception:
                pass
        elif message:
            self.original_stderr.write(message)

    def flush(self):
        self.original_stderr.flush()

sys.stderr = StderrRedirector("crash_report.txt", sys.stderr)

def exception_hook(exctype, value, tb):
    """Global exception hook to capture crashes that don't reach the console."""
    err_msg = "".join(traceback.format_exception(exctype, value, tb))
    print(err_msg, file=sys.stderr)
    sys.__excepthook__(exctype, value, tb)

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
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
            )

            for line in process.stdout:
                self.output_signal.emit(line.strip())

            process.wait()
            self.finished_signal.emit(process.returncode)
        except Exception as e:
            self.output_signal.emit(f"Error executing command: {str(e)}")
            self.finished_signal.emit(-1)


class SceneDetectionWorker(QThread):
    finished_signal = pyqtSignal(list)
    error_signal = pyqtSignal(str)
    progress_signal = pyqtSignal(int)

    def __init__(self, video_path, threshold):
        super().__init__()
        self.video_path = video_path
        self.threshold = threshold

    def run(self):
        try:
            import cv2
            import numpy as np

            cap = cv2.VideoCapture(self.video_path)
            if not cap.isOpened():
                self.error_signal.emit("Não foi possível abrir o vídeo.")
                return

            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            if total_frames <= 0:
                total_frames = 1

            cuts = []
            frame_idx = 0
            prev_gray = None
            min_scene_len = 15

            while True:
                ret, frame = cap.read()
                if not ret:
                    break

                small = cv2.resize(frame, (160, 120))
                gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)

                if prev_gray is not None:
                    diff = cv2.absdiff(gray, prev_gray)
                    mean_val = np.mean(diff)

                    if mean_val > self.threshold:
                        if not cuts or (frame_idx - cuts[-1]) >= min_scene_len:
                            cuts.append(frame_idx)

                prev_gray = gray
                frame_idx += 1

                if frame_idx % 10 == 0:
                    pct = int(frame_idx * 100 / total_frames)
                    self.progress_signal.emit(min(100, pct))

            cap.release()
            self.progress_signal.emit(100)
            self.finished_signal.emit(cuts)
        except Exception as e:
            self.error_signal.emit(str(e))


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
    "Imagens Fantasma (Ghost Slide)": "ghost_images",
    "Velocidade Variável": "variable_speed",
    "Piscada de Olho (POV)": "eye_blink",
    "Editar Frames (Pixel)": "frame_edit",
    "Video Trim (frame do meio)": "video_trim_center",
    "Fatiar Áudio (Segmentos)": "slice_audio",
    "Fatiar Vídeo (Video Slicing)": "video_slicing",
    "Inverter Vídeo e Áudio (Reverse)": "reverse",
    "Extrair Frame (PNG)": "extract_frame",
    "Extrair Frames de Transição": "extract_transitions",
}

