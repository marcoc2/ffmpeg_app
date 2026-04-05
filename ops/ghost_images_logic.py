import os
from datetime import datetime

def build_command(video_file, image_files, config, metadata_cache):
    """
    video_file: background video
    image_files: list of images to overlay
    config: start_frame, end_frame, ghost_dur, ghost_opacity, ghost_scale, ghost_travel
    metadata_cache: shared metadata
    """
    meta = metadata_cache.get(video_file)
    if not meta or not meta.get("is_video"):
        return None, None, "Vídeo base não encontrado ou inválido."

    fps = meta.get("fps", 30.0)
    H = meta.get("height", 720)
    
    start_f = config.get("ghost_start", 0)
    end_f = config.get("ghost_end", 300)
    dur_per_img = config.get("ghost_dur", 2)
    opacity = config.get("ghost_opacity", 30) / 100.0
    scale_factor = config.get("ghost_scale", 80) / 100.0
    travel_factor = config.get("ghost_travel", 100) / 100.0
    
    cwd = os.path.dirname(video_file)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = os.path.join(cwd, f"ghost_slide_{ts}.mp4")
    
    # Calculate timestamps
    t_start_global = start_f / fps
    t_end_global = end_f / fps
    total_avail_time = t_end_global - t_start_global
    
    if total_avail_time <= 0:
        return None, None, "Frame Fim deve ser maior que Frame Início."

    # Build Filter Complex
    fc = ""
    last_v = "0:v"
    
    # Target height for images based on scale_factor
    target_h = int(H * scale_factor)

    for i, img_path in enumerate(image_files):
        t_img_start = t_start_global + i * dur_per_img
        if t_img_start >= t_end_global:
            break
            
        t_img_actual_end = min(t_img_start + dur_per_img, t_end_global)
        input_idx = i + 1
        
        # Scaling: Fit images to a percentage of the video height
        # Opacity and FADE OUT (last 30% of dur_per_img, capped at 0.5s)
        fade_dur = min(0.5, dur_per_img * 0.3)
        fade_start = t_img_actual_end - fade_dur
        
        img_filters = f"scale=-1:{target_h},format=rgba,colorchannelmixer=aa={opacity}"
        img_filters += f",fade=t=out:st={fade_start}:d={fade_dur}:alpha=1"
        fc += f"[{input_idx}:v]{img_filters}[ovl{i}];"
        
        # Movement: slide alternating Left/Right
        direction = 1 if i % 2 == 0 else -1
        t_rel = f"(t-{t_img_start})"
        
        # travel_dist is total pixels to travel. Full screen is W + w.
        # User travel_factor (0-1) multiplies this.
        full_travel = "W+w"
        
        if direction == 1:
            # Left to Right: starts at -w
            x_expr = f"-w+({full_travel})*{travel_factor}*{t_rel}/{dur_per_img}"
        else:
            # Right to Left: starts at W
            x_expr = f"W-({full_travel})*{travel_factor}*{t_rel}/{dur_per_img}"
        
        # Center Y coordinate
        y_expr = f"(H-h)/2"
        
        fc += f"[{last_v}][ovl{i}]overlay=x='{x_expr}':y='{y_expr}':enable='between(t,{t_img_start},{t_img_actual_end})'[v_next{i}];"
        last_v = f"v_next{i}"

    # Rename last output to [vout]
    fc = fc.replace(f"[{last_v}]", "[vout]")
    
    if "[vout]" not in fc:
        return ["ffmpeg", "-y", "-i", video_file, "-c", "copy", out], out, None

    cmd = ["ffmpeg", "-y", "-i", video_file]
    for img in image_files:
        cmd.extend(["-i", img])
        
    cmd.extend([
        "-filter_complex", fc.rstrip(';'),
        "-map", "[vout]",
    ])
    
    if meta.get("has_audio"):
        cmd.extend(["-map", "0:a"])

    cmd.extend(["-c:v", "libx264", "-crf", "23", out])
    
    return cmd, out, None
