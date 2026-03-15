import sys
import argparse
import subprocess
import json
from collections import defaultdict

CREATE_NO_WINDOW = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0


def probe_file(file_path):
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
            capture_output=True,
            text=True,
            check=True,
            creationflags=CREATE_NO_WINDOW,
        )
        return json.loads(result.stdout)
    except Exception:
        return {}


def get_video_meta(info):
    """Extract video metadata from probe info."""
    v_stream = next(
        (s for s in info.get("streams", []) if s.get("codec_type") == "video"),
        None,
    )
    if not v_stream:
        return None

    w = v_stream.get("width", 0)
    h = v_stream.get("height", 0)

    fps_raw = v_stream.get("r_frame_rate", "30/1")
    try:
        num, den = map(int, fps_raw.split("/"))
        fps = num / den if den != 0 else 30.0
    except Exception:
        fps = 30.0

    try:
        duration = float(info.get("format", {}).get("duration", 0))
    except Exception:
        duration = 0
    if duration <= 0:
        try:
            duration = float(v_stream.get("duration", 5.0))
        except Exception:
            duration = 5.0
    if duration <= 0:
        duration = 5.0

    has_audio = any(
        s.get("codec_type") == "audio" for s in info.get("streams", [])
    )

    return {
        "width": w,
        "height": h,
        "fps": fps,
        "duration": duration,
        "has_audio": has_audio,
    }


def pick_resolution(metas, heuristic, manual_w=None, manual_h=None):
    """Pick target resolution based on the chosen heuristic."""
    video_metas = [m for m in metas if m is not None]
    if not video_metas:
        return 1920, 1080

    if heuristic == "manual":
        return manual_w, manual_h

    if heuristic == "first":
        return video_metas[0]["width"], video_metas[0]["height"]

    if heuristic == "highest":
        best = max(video_metas, key=lambda m: m["width"] * m["height"])
        return best["width"], best["height"]

    if heuristic == "majority":
        counts = defaultdict(int)
        for m in video_metas:
            counts[(m["width"], m["height"])] += 1
        # Tie-break: highest pixel count
        winner = max(counts.keys(), key=lambda k: (counts[k], k[0] * k[1]))
        return winner

    # Default: longest_duration
    durations = defaultdict(float)
    for m in video_metas:
        durations[(m["width"], m["height"])] += m["duration"]
    # Tie-break: highest pixel count
    winner = max(durations.keys(), key=lambda k: (durations[k], k[0] * k[1]))
    return winner


def pick_fps(metas):
    """Pick target FPS: most common, tie-break highest."""
    video_metas = [m for m in metas if m is not None]
    if not video_metas:
        return 30.0

    fps_counts = defaultdict(int)
    for m in video_metas:
        fps_rounded = round(m["fps"], 2)
        fps_counts[fps_rounded] += 1
    return max(fps_counts.keys(), key=lambda f: (fps_counts[f], f))


def build_video_filter(idx, target_w, target_h, target_fps, crop_mode):
    """Build the video filter chain for a single input stream."""
    if crop_mode == "letterbox":
        return (
            f"[{idx}:v]scale={target_w}:{target_h}:"
            f"force_original_aspect_ratio=decrease,"
            f"pad={target_w}:{target_h}:(ow-iw)/2:(oh-ih)/2,"
            f"setsar=1,fps={target_fps}[v{idx}];"
        )

    # Crop modes: scale up to cover, then crop
    crop_expr = {
        "center": f"crop={target_w}:{target_h}",
        "top": f"crop={target_w}:{target_h}:(iw-{target_w})/2:0",
        "bottom": f"crop={target_w}:{target_h}:(iw-{target_w})/2:ih-{target_h}",
        "left": f"crop={target_w}:{target_h}:0:(ih-{target_h})/2",
        "right": f"crop={target_w}:{target_h}:iw-{target_w}:(ih-{target_h})/2",
    }
    crop = crop_expr.get(crop_mode, crop_expr["center"])

    return (
        f"[{idx}:v]scale={target_w}:{target_h}:"
        f"force_original_aspect_ratio=increase,"
        f"{crop},"
        f"setsar=1,fps={target_fps}[v{idx}];"
    )


def main():
    parser = argparse.ArgumentParser(description="Safe video concatenation with normalization")
    parser.add_argument(
        "--heuristic",
        choices=["longest_duration", "highest", "majority", "first", "manual"],
        default="longest_duration",
    )
    parser.add_argument("--crop", default="letterbox",
                        choices=["letterbox", "center", "top", "bottom", "left", "right"])
    parser.add_argument("--width", type=int, default=None)
    parser.add_argument("--height", type=int, default=None)
    parser.add_argument("-o", "--output", required=True)
    parser.add_argument("input_files", nargs="+")

    args = parser.parse_args()

    if args.heuristic == "manual" and (not args.width or not args.height):
        print("Erro: Heuristica 'manual' requer --width e --height.")
        sys.exit(1)

    input_files = args.input_files
    output_file = args.output

    # 1. Probe all files
    file_infos = [probe_file(f) for f in input_files]
    metas = [get_video_meta(info) for info in file_infos]

    if not any(m is not None for m in metas):
        print("Erro: Nenhum arquivo de video valido encontrado.")
        sys.exit(1)

    # 2. Pick target resolution and FPS
    target_w, target_h = pick_resolution(
        metas, args.heuristic, args.width, args.height
    )
    # Ensure even dimensions (required by libx264)
    target_w = target_w if target_w % 2 == 0 else target_w + 1
    target_h = target_h if target_h % 2 == 0 else target_h + 1

    target_fps = pick_fps(metas)

    print(f"Alvo: {target_w}x{target_h} @ {target_fps} FPS")
    print(f"Heuristica: {args.heuristic} | Ajuste: {args.crop}")

    # 3. Build FFmpeg command
    cmd = ["ffmpeg", "-y"]
    for f in input_files:
        cmd.extend(["-i", f])

    filter_complex = ""
    concat_inputs = ""

    for i, f in enumerate(input_files):
        meta = metas[i]
        has_v = meta is not None
        has_a = meta["has_audio"] if meta else False
        duration = meta["duration"] if meta else 5.0

        # Video path
        if has_v:
            filter_complex += build_video_filter(
                i, target_w, target_h, target_fps, args.crop
            )
        else:
            filter_complex += (
                f"color=c=black:s={target_w}x{target_h}"
                f":r={target_fps}:d={duration}[v{i}];"
            )

        # Audio path
        if has_a:
            filter_complex += (
                f"[{i}:a]aresample=44100,"
                f"aformat=sample_fmts=fltp:channel_layouts=stereo[a{i}];"
            )
        else:
            filter_complex += (
                f"anullsrc=r=44100:cl=stereo[silence{i}];"
                f"[silence{i}]atrim=duration={duration}[a{i}];"
            )

        concat_inputs += f"[v{i}][a{i}]"

    filter_complex += f"{concat_inputs}concat=n={len(input_files)}:v=1:a=1[vout][aout]"

    cmd.extend(
        [
            "-filter_complex",
            filter_complex,
            "-map",
            "[vout]",
            "-map",
            "[aout]",
            "-c:v",
            "libx264",
            "-preset",
            "slow",
            "-crf",
            "20",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-pix_fmt",
            "yuv420p",
            output_file,
        ]
    )

    print("Executando Safe Concat...")
    result = subprocess.run(cmd, creationflags=CREATE_NO_WINDOW)
    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
