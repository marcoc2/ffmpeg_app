import os
import json
import subprocess
from datetime import datetime

def get_video_info(file_path):
    cmd = [
        "ffprobe",
        "-v", "quiet",
        "-print_format", "json",
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
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0,
        )
        if not result.stdout:
            return None
        info = json.loads(result.stdout)
        
        video_stream = next((s for s in info.get("streams", []) if s.get("codec_type") == "video"), None)
        audio_stream = next((s for s in info.get("streams", []) if s.get("codec_type") == "audio"), None)
        meta = {"width": 0, "height": 0, "fps": 0.0, "is_video": False, "has_audio": False, "sample_rate": 0, "channels": 0}
        
        if video_stream:
            meta["width"] = video_stream.get("width", 0)
            meta["height"] = video_stream.get("height", 0)
            fps_str = video_stream.get("r_frame_rate", "0/0")
            if "/" in fps_str:
                num, den = map(int, fps_str.split("/"))
                meta["fps"] = round(num / den, 2) if den != 0 else 0.0
            meta["is_video"] = True
            meta["nb_frames"] = int(video_stream.get("nb_frames", 0)) if video_stream.get("nb_frames") else 0
            
            duration_val = info.get("format", {}).get("duration")
            meta["duration"] = float(duration_val) if duration_val else 0.0
            
        if audio_stream:
            meta["has_audio"] = True
            meta["sample_rate"] = int(audio_stream.get("sample_rate", 0))
            meta["channels"] = int(audio_stream.get("channels", 0))
            
        return meta
    except Exception:
        return None

def build_command(operation, files, config, metadata_cache):
    """
    config: dict with UI values (frames, loops, fps, crop, heuristic, manual_w, manual_h, etc.)
    metadata_cache: dict {file_path: meta_dict}
    Returns (command_list, output_path, error_msg)
    """
    cwd = os.path.dirname(files[0])
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    if operation == "concat":
        # Check compatibility using cache
        first_path = files[0]
        base_meta = metadata_cache.get(first_path)
        if not base_meta or not base_meta.get("is_video"):
            return None, None, "Primeiro arquivo não é vídeo."
        
        is_compatible = True
        for f in files[1:]:
            m = metadata_cache.get(f)
            if not m:
                is_compatible = False
                break
            
            # Video compatibility
            if m["width"] != base_meta["width"] or \
               m["height"] != base_meta["height"] or \
               abs(m["fps"] - base_meta["fps"]) > 0.01:
                is_compatible = False
                break
                
            # Audio compatibility
            if m["has_audio"] != base_meta["has_audio"] or \
               m.get("sample_rate") != base_meta.get("sample_rate") or \
               m.get("channels") != base_meta.get("channels"):
                is_compatible = False
                break
        
        if not is_compatible:
            # Safe concat via script
            base_name = os.path.splitext(os.path.basename(files[0]))[0]
            out = os.path.join(cwd, f"{base_name}_safe_concat_{ts}.mp4")
            safe_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "safe_concat.py")
            
            h_map = {
                "Maior Duração Total": "longest_duration",
                "Maior Resolução": "highest",
                "Maioria (Contagem)": "majority",
                "Primeiro Arquivo": "first",
                "Manual": "manual",
            }
            c_map = {
                "Letterbox (Barras Pretas)": "letterbox",
                "Crop Centro": "center",
                "Crop Cima": "top",
                "Crop Baixo": "bottom",
                "Crop Esquerda": "left",
                "Crop Direita": "right",
            }
            
            heuristic = h_map.get(config.get("res_heuristic"), "longest_duration")
            crop = c_map.get(config.get("crop_mode"), "letterbox")
            
            cmd = ["python", safe_script, "--heuristic", heuristic, "--crop", crop]
            if heuristic == "manual":
                cmd.extend(["--width", str(config.get("manual_w", 1920)), "--height", str(config.get("manual_h", 1080))])
            cmd.extend(["-o", out, "--"])
            cmd.extend(files)
            return cmd, out, None
        
        # Fast concat
        concat_txt = os.path.join(cwd, f"concat_{ts}.txt")
        with open(concat_txt, "w", encoding="utf-8") as f:
            for file in files:
                f.write(f"file '{os.path.basename(file)}'\n")
        
        base_name = os.path.splitext(os.path.basename(files[0]))[0]
        out = os.path.join(cwd, f"{base_name}_and_others_concat_{ts}.mp4")
        return ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_txt, "-c", "copy", out], out, None

    elif operation == "extract_audio":
        inp = files[0]
        out = os.path.join(cwd, f"{os.path.splitext(os.path.basename(inp))[0]}_audio_{ts}.mp3")
        return ["ffmpeg", "-y", "-i", inp, "-vn", "-c:a", "libmp3lame", "-q:a", "2", out], out, None

    elif operation == "to_mp4":
        inp = files[0]
        out = os.path.splitext(inp)[0] + "_converted.mp4"
        return ["ffmpeg", "-y", "-i", inp, "-c:v", "libx264", "-preset", "fast", "-crf", "22", "-c:a", "aac", "-b:a", "128k", out], out, None

    elif operation == "to_gif":
        inp = files[0]
        out = os.path.splitext(inp)[0] + ".gif"
        vf = "fps=15,scale=480:-1:flags=lanczos,split[s0][s1];[s0]palettegen[p];[s1][p]paletteuse"
        return ["ffmpeg", "-y", "-i", inp, "-vf", vf, "-loop", "0", out], out, None

    elif operation == "scale_720p":
        inp = files[0]
        out = os.path.splitext(inp)[0] + "_720p.mp4"
        return ["ffmpeg", "-y", "-i", inp, "-vf", "scale=-2:720", "-c:v", "libx264", "-crf", "23", "-c:a", "copy", out], out, None

    elif operation == "mute":
        inp = files[0]
        out = os.path.splitext(inp)[0] + "_muted.mp4"
        return ["ffmpeg", "-y", "-i", inp, "-c:v", "copy", "-an", out], out, None

    elif operation == "mix_audio":
        out = os.path.join(cwd, f"{os.path.splitext(os.path.basename(files[0]))[0]}_mixed_audio_{ts}.mp3")
        cmd = ["ffmpeg", "-y"]
        for f in files: cmd.extend(["-i", f])
        cmd.extend(["-filter_complex", f"amix=inputs={len(files)}:duration=longest", "-c:a", "libmp3lame", "-q:a", "2", out])
        return cmd, out, None

    elif operation == "replace_audio":
        video_file, audio_file = (files[0], files[1]) if len(files) == 2 else (None, None)
        if not video_file:
            return None, None, "Requer 1 vídeo e 1 áudio."
        # Extension swap logic if needed
        out = os.path.splitext(video_file)[0] + f"_newaudio_{ts}.mp4"
        return ["ffmpeg", "-y", "-i", video_file, "-i", audio_file, "-c:v", "copy", "-c:a", "aac", "-map", "0:v:0", "-map", "1:a:0?", "-shortest", out], out, None

    elif operation == "cut_front":
        inp = files[0]
        frames = config.get("frames", 30)
        meta = metadata_cache.get(inp)
        fps = meta.get("fps", 30.0) if meta else 30.0
        # Calculate time offset from video frames
        t_offset = frames / fps
        out = os.path.splitext(inp)[0] + f"_cutfront_{frames}f.mp4"
        # Use -ss for seeking and re-encode for frame-accurate cut
        return [
            "ffmpeg", "-y", "-ss", f"{t_offset:.6f}", "-i", inp,
            "-c:v", "libx264", "-crf", "18", "-preset", "medium",
            "-c:a", "aac", "-b:a", "192k",
            out
        ], out, None

    elif operation == "cut_back":
        inp = files[0]
        frames = config.get("frames", 30)
        meta = metadata_cache.get(inp)
        if not meta or not meta.get("nb_frames"):
            return None, None, "Não foi possível determinar o total de frames."
        target = meta["nb_frames"] - frames
        if target <= 0:
            return None, None, "O corte é maior ou igual ao vídeo."
        out = os.path.splitext(inp)[0] + f"_cutback_{frames}f.mp4"
        return ["ffmpeg", "-y", "-i", inp, "-vframes", str(target), "-c:a", "copy", out], out, None

    elif operation in ("loop_end", "loop_pingpong"):
        from ops import loop_logic
        return loop_logic.build_command(files[0], files, config, metadata_cache, operation)

    elif operation == "image_to_video":
        inp = files[0]
        out = os.path.join(cwd, f"{os.path.splitext(os.path.basename(inp))[0]}_image_to_video_{ts}.mp4")
        return ["ffmpeg", "-y", "-loop", "1", "-i", inp, "-r", str(config.get("fps", 30)), "-frames:v", str(config.get("frames", 30)), "-c:v", "libx264", "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2", "-pix_fmt", "yuv420p", out], out, None

    elif operation == "memory_flash":
        from ops import memory_flash_logic
        return memory_flash_logic.build_command(files, config, metadata_cache)

    elif operation == "spatial_crop":
        inp = files[0]
        cw, ch = config["sc_w"], config["sc_h"]
        if config["sc_center"]: crop_f = f"crop={cw}:{ch}"
        else: crop_f = f"crop={cw}:{ch}:{config['sc_x']}:{config['sc_y']}"
        ext = os.path.splitext(inp)[1].lower()
        out = os.path.join(cwd, f"{os.path.splitext(os.path.basename(inp))[0]}_cropped_{ts}" + (".gif" if ext==".gif" else ".mp4"))
        cmd = ["ffmpeg", "-y", "-i", inp, "-vf", crop_f]
        if ext==".gif": cmd.extend(["-loop", "0", out])
        else: cmd.extend(["-c:a", "copy", out])
        return cmd, out, None

    elif operation == "side_by_side":
        v1, v2 = files[0], files[1]
        m1 = metadata_cache.get(v1)
        h1 = m1["height"] if m1 else 720
        out = os.path.join(cwd, f"side_by_side_{ts}.mp4")
        fc = f"[0:v]scale=-1:{h1}[v1];[1:v]scale=-1:{h1}[v2];[v1][v2]hstack=inputs=2[vout]"
        return ["ffmpeg", "-y", "-i", v1, "-i", v2, "-filter_complex", fc, "-map", "[vout]", "-c:v", "libx264", "-crf", "23", out], out, None

    elif operation == "overlay":
        v1, v2 = files[0], files[1]
        cw, ch = config["sc_w"], config["sc_h"]
        pos = "(W-w)/2:(H-h)/2" if config["sc_center"] else f"{config['sc_x']}:{config['sc_y']}"
        out = os.path.join(cwd, f"overlay_{ts}.mp4")
        fc = f"[1:v]scale={cw}:{ch}[ovl];[0:v][ovl]overlay={pos}[vout]"
        return ["ffmpeg", "-y", "-i", v1, "-i", v2, "-filter_complex", fc, "-map", "[vout]", "-c:v", "libx264", out], out, None

    elif operation == "ghost_images":
        from ops import ghost_images_logic
        return ghost_images_logic.build_command(files[0], files[1:], config, metadata_cache)

    elif operation == "variable_speed":
        from ops import variable_speed_logic
        inp = files[0]
        meta = metadata_cache.get(inp)
        if not meta or not meta.get("is_video"):
            return None, None, "Primeiro arquivo não é um vídeo válido."
        duration = meta.get("duration", 0.0)
        if duration <= 0:
            return None, None, "Não foi possível determinar a duração do vídeo."
        has_audio = meta.get("has_audio", False)
        control_points = config.get("varspeed_points", [[0.0, 1.0], [1.0, 1.0]])
        out = os.path.join(cwd, f"{os.path.splitext(os.path.basename(inp))[0]}_varspeed_{ts}.mp4")
        return variable_speed_logic.build_variable_speed_command(
            inp, control_points, has_audio, duration, out
        )

    elif operation == "eye_blink":
        from ops import eye_blink_logic
        return eye_blink_logic.build_command(files, config, metadata_cache)

    return None, None, "Operação desconhecida."


def build_frame_replace_command(video_path, replacements, output_path):
    """
    Build an ffmpeg command that replaces specific frames in video with edited images.

    replacements: dict {frame_number (int): image_path (str)}

    Strategy: chain overlay filters, one per replaced frame.
    Each image input uses -loop 1 so ffmpeg treats the still as an endless stream;
    the enable expression restricts the overlay to a single frame.
    """
    meta = get_video_info(video_path)
    w = meta.get("width", 1920) if meta else 1920
    h = meta.get("height", 1080) if meta else 1080
    has_audio = meta.get("has_audio", False) if meta else False
    duration = meta.get("duration", 0.0) if meta else 0.0
    fps = meta.get("fps", 30.0) if meta else 30.0
    if fps <= 0:
        fps = 30.0

    frame_numbers = sorted(replacements.keys())

    cmd = ["ffmpeg", "-y", "-i", video_path]
    for fn in frame_numbers:
        cmd.extend(["-loop", "1", "-i", replacements[fn]])

    filter_parts = []
    prev = "0:v"
    for i, fn in enumerate(frame_numbers):
        inp = i + 1
        out = "vout" if i == len(frame_numbers) - 1 else f"v{i}"
        # Use timestamp window instead of frame counter — more reliable across
        # different encodings and avoids n-counter drift with B-frames or dups.
        t_start = fn / fps
        t_end = (fn + 1) / fps
        filter_parts.append(
            f"[{inp}:v]scale={w}:{h},format=yuv420p[ovl{i}];"
            f"[{prev}][ovl{i}]overlay=0:0:enable='between(t,{t_start:.8f},{t_end:.8f})'[{out}]"
        )
        prev = out

    cmd += ["-filter_complex", ";".join(filter_parts)]
    cmd += ["-map", "[vout]", "-c:v", "libx264", "-crf", "18", "-preset", "medium"]
    if has_audio:
        cmd += ["-map", "0:a?", "-c:a", "copy"]
    else:
        cmd += ["-an"]
    if duration > 0:
        cmd += ["-t", f"{duration:.6f}"]
    else:
        cmd += ["-shortest"]
    cmd.append(output_path)
    return cmd
