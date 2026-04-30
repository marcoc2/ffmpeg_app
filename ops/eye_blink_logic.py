import os
import datetime

def build_command(files, config, metadata_cache):
    inp = files[0]
    cwd = os.path.dirname(inp)
    meta = metadata_cache.get(inp)
    if not meta:
        return None, None, "Metadata não disponível para o vídeo."

    width = meta.get("width", 1920)
    height = meta.get("height", 1080)
    # Use (height + 1) // 2 to ensure lids overlap slightly on odd heights instead of leaving a gap
    lid_h = (height + 1) // 2
    
    blink_dur = config.get("blink_duration", 10)
    centers = config.get("blink_centers", [])
    
    if not centers:
        return None, None, "Selecione pelo menos um ponto (frame) para a piscada."

    half = blink_dur / 2.0
    
    # Build a combined factor expression
    # factor = min(1, max(0, 1-abs(n-C1)/half) + max(0, 1-abs(n-C2)/half) + ...)
    factors = []
    for c in centers:
        factors.append(f"max(0, 1 - abs(n - {c}) / {half})")
    
    combined_factor = f"min(1, {' + '.join(factors)})"
    
    # Filter Complex:
    # 1. Create a black lid (half height)
    # 2. Split it in two (since labels can only be used once as input)
    # 3. Overlay top lid moving from -h to 0 (y = -h + h*factor)
    # 4. Overlay bottom lid moving from H to H/2 (y = H - h*factor)
    
    fc = (
        f"color=black:s={width}x{lid_h} [lid_orig]; "
        f"[lid_orig] split=2 [lid1][lid2]; "
        f"[0:v][lid1] overlay=x=0:y='-h + h*({combined_factor})':shortest=1 [v1]; "
        f"[v1][lid2] overlay=x=0:y='H - h*({combined_factor})':shortest=1 [out]"
    )
    
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    out = os.path.join(cwd, f"{os.path.splitext(os.path.basename(inp))[0]}_blinked_{ts}.mp4")
    
    cmd = [
        "ffmpeg", "-y", "-i", inp,
        "-filter_complex", fc,
        "-map", "[out]",
        "-map", "0:a?",
        "-c:v", "libx264", "-crf", "18", "-preset", "veryfast",
        "-c:a", "copy",
        out
    ]
    
    return cmd, out, None
