import os
from datetime import datetime

def build_command(video_file, image_files, config, metadata_cache):
    """
    video_file: background video
    image_files: list of images to overlay
    config: start_frame, end_frame, ghost_dur, ghost_opacity
    metadata_cache: shared metadata
    """
    meta = metadata_cache.get(video_file)
    if not meta or not meta.get("is_video"):
        return None, None, "Vídeo base não encontrado ou inválido."

    fps = meta.get("fps", 30.0)
    W, H = meta.get("width", 1280), meta.get("height", 720)
    
    start_f = config.get("ghost_start", 0)
    end_f = config.get("ghost_end", 300)
    dur_per_img = config.get("ghost_dur", 2)
    opacity = config.get("ghost_opacity", 30) / 100.0
    
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
    # [0:v] is the video. [1:v]..[N:v] are images.
    fc = ""
    last_v = "0:v"
    
    # Process each image that fits in the window
    for i, img_path in enumerate(image_files):
        t_img_start = t_start_global + i * dur_per_img
        t_img_end = t_img_start + dur_per_img
        
        # If image starts after the global end, stop adding more images
        if t_img_start >= t_end_global:
            break
            
        # Clamp image end to global end
        t_img_actual_end = min(t_img_end, t_end_global)
        
        input_idx = i + 1
        
        # Scaling and Opacity
        # We also need to force the frame rate of the image or just use it as is?
        # Usually overlaying handles it, but let's scale and set alpha.
        fc += f"[{input_idx}:v]scale={W}:{H}:force_original_aspect_ratio=decrease,pad={W}:{H}:(ow-iw)/2:(oh-ih)/2,format=rgba,colorchannelmixer=aa={opacity}[ovl{i}];"
        
        # Movement: slide alternating Left/Right
        direction = 1 if i % 2 == 0 else -1
        # t_rel goes from 0 to actual_dur
        t_rel = f"(t-{t_img_start})"
        
        if direction == 1:
            # Left to Right: x starts at -W, ends at W
            # Expression: -W + (W + w) * (t - t_start) / dur
            x_expr = f"-W+(W+w)*{t_rel}/{dur_per_img}"
        else:
            # Right to Left: x starts at W, ends at -w
            x_expr = f"W-(W+w)*{t_rel}/{dur_per_img}"
        
        fc += f"[{last_v}][ovl{i}]overlay=x='{x_expr}':y=0:enable='between(t,{t_img_start},{t_img_actual_end})'[v_next{i}];"
        last_v = f"v_next{i}"

    # Rename last output to [vout]
    fc = fc.replace(f"[{last_v}]", "[vout]")
    # Safety if no images are processed
    if not fc:
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
