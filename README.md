# FFmpeg Tools (Windows Context Menu)

A powerful visual tool to automate common FFmpeg tasks directly from the Windows context menu (right-click).

## 🚀 Features

### 🎬 Video Manipulation

- **Concatenate Videos**: Join multiple files into one.
  - **Smart Analysis**: The interface warns if videos have different resolutions or FPS.
  - **Safe Mode**: If there's an incompatibility, the `safe_concat.py` script automatically scales and normalizes the videos.
  - **Resolution Heuristics**: Choose how to resolve conflicts — Longest Duration, Highest Resolution, Majority, First File, or Manual.
  - **Adjustment Modes**: Letterbox (black bars) or Crop (Center, Top, Bottom, Left, Right).
- **Spatial Crop**: Crop a region (W×H) from a video or GIF, with manual (X, Y) or centered positioning.
- **Memory Flash**: Intercalate fragments from a second video into the first, creating a "memory flash" effect.
  - Configurable: number of fragments (randomized), subfragments per group, size, and spacing in frames.
  - Reproducible seed for consistent results.
- **Side-by-Side**: Combine two videos horizontally.
  - Automatically scales videos to matching heights.
- **Overlay / Watermark**: Place an image or video on top of another.
  - Custom positioning (X, Y) or automatic centering.
  - Custom scaling for the overlay element.
- **Ghost Images (Phantom Slide)**: Overlay multiple images with 30% transparency sliding across the screen.
  - Select 1 video and N images.
  - Images alternate sliding from Left or Right.
  - Configurable start/end frames and duration per image.
- **Cut Start/End**: Remove an exact number of frames from the beginning or end.
- **Loop End**: Extract the final segment and repeat it N times (Normal or Ping-Pong).
- **Resize**: Quickly convert to 720p.
- **Move/Remove Audio**: Mute the video or extract only the sound as MP3.

### 🖼️ Image and Audio

- **Image to Video**: Create a high-compatibility video from a single image, choosing duration (frames) and FPS.
- **Audio Mix**: Combine multiple audio files into a single mix.
- **Replace Audio**: Swap a video's soundtrack with an external audio file.

### 🔄 Conversion

- **Convert to MP4 (H.264)**: Ensure universal compatibility.
- **Convert to GIF**: Create optimized GIFs with smart color palettes.

## 🛠️ Requirements

- **Python 3.x**
- **PyQt6** (`pip install PyQt6`)
- **FFmpeg** installed and configured in your Windows PATH.

## 📥 How to Use

1. Clone or download this folder to your computer.
2. Ensure **FFmpeg** is accessible via the terminal.
3. Run the program through `main_gui.py` or the `ffmpeg_tools.bat` shortcut.
4. Drag and drop your files onto the interface and select the desired operation.

## 📂 Project Structure

- `main_gui.py`: Main PyQt6 interface with Drag-and-Drop support.
- `safe_concat.py`: Auxiliary script for robust concatenation of videos with mixed formats (resolution, FPS, audio).
- `ffmpeg_tools.bat`: Shortcut for quick interface execution.
- `ffmpeg_tools.ico`: Custom application icon.

---

_Developed to facilitate rapid video editing workflows._
