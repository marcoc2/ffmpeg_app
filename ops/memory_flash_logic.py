import os
import random
from datetime import datetime

def build_command(files, config, metadata_cache):
    v1, v2 = files[0], files[1]
    m1, m2 = metadata_cache.get(v1), metadata_cache.get(v2)
    
    cwd = os.path.dirname(v1)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    fps1, dur1 = m1["fps"], m1["duration"]
    total_frames = int(dur1 * fps1)
    n_frag, n_sub, sub_size, sub_gap = config["flash_count"], config["flash_sub"], config["flash_size"], config["flash_gap"]
    frag_span = n_sub * sub_size + (n_sub - 1) * sub_gap
    
    if n_frag * frag_span >= total_frames:
        return None, None, "Vídeo muito curto para os fragmentos."
    
    rng = random.Random(config.get("seed", 0)) if config.get("seed", 0) != 0 else random.Random()
    slots = sorted(rng.sample(range(total_frames - n_frag * frag_span), n_frag))
    frag_starts = [s + i*frag_span for i, s in enumerate(slots)]
    
    segments = []
    prev_end = 0
    for start in frag_starts:
        if start > prev_end: segments.append(("v1", prev_end, start))
        for s in range(n_sub):
            sub_s = start + s*(sub_size + sub_gap)
            if s > 0: segments.append(("v1", sub_s - sub_gap, sub_s))
            segments.append(("v2", sub_s, sub_s + sub_size))
        prev_end = start + frag_span
    if prev_end < total_frames: segments.append(("v1", prev_end, total_frames))
    
    n_v1 = sum(1 for src,_,_ in segments if src == "v1")
    n_v2 = sum(1 for src,_,_ in segments if src == "v2")
    has_audio = m1["has_audio"] and m2["has_audio"]
    
    fc = f"[0:v]split={n_v1}" + "".join(f"[v1_{i}]" for i in range(n_v1)) + ";"
    fc += f"[1:v]split={n_v2}" + "".join(f"[v2_{i}]" for i in range(n_v2)) + ";"
    if has_audio:
        fc += f"[0:a]asplit={n_v1}" + "".join(f"[a1_{i}]" for i in range(n_v1)) + ";"
        fc += f"[1:a]asplit={n_v2}" + "".join(f"[a2_{i}]" for i in range(n_v2)) + ";"
        
    c_pads, v1i, v2i = "", 0, 0
    for i, (src, sf, ef) in enumerate(segments):
        t1, t2 = sf/fps1, ef/fps1
        tag = f"1_{v1i}" if src=="v1" else f"2_{v2i}"
        fc += f"[v{tag}]trim={t1:.4f}:{t2:.4f},setpts=PTS-STARTPTS[seg{i}];"
        if has_audio: fc += f"[a{tag}]atrim={t1:.4f}:{t2:.4f},asetpts=PTS-STARTPTS[aseg{i}];"
        c_pads += f"[seg{i}][aseg{i}]" if has_audio else f"[seg{i}]"
        if src=="v1": v1i+=1
        else: v2i+=1
        
    fc += f"{c_pads}concat=n={len(segments)}:v=1:a={'1' if has_audio else '0'}[vout]"
    if has_audio: fc += "[aout]"
    
    out = os.path.join(cwd, f"{os.path.splitext(os.path.basename(v1))[0]}_flash_{ts}.mp4")
    cmd = ["ffmpeg", "-y", "-i", v1, "-i", v2, "-filter_complex", fc, "-map", "[vout]"]
    if has_audio: cmd.extend(["-map", "[aout]"])
    cmd.extend(["-c:v", "libx264", "-crf", "20", "-c:a", "aac", out])
    
    return cmd, out, None
