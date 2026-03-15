import os
def build_command(inp, files, config, metadata_cache, operation):
    frames = config.get("frames", 30)
    loops = config.get("loops", 3)
    meta = metadata_cache.get(inp)
    if not meta or not meta.get("nb_frames"): return None, None, "Erro ao ler frames."
    
    cwd = os.path.dirname(inp)
    ts = os.path.basename(inp).split('_')[-1].split('.')[0] # Try to reuse TS or generate new
    from datetime import datetime
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    start_frame = max(0, meta["nb_frames"] - frames)
    fps = meta.get("fps", 30.0)
    t_start = start_frame / fps
    has_audio = meta.get("has_audio", False)
    
    n_parts = loops + 2
    fc = f"[0:v]split={n_parts}" + "".join(f"[v_in{i}]" for i in range(n_parts)) + ";"
    if has_audio: fc += f"[0:a]asplit={n_parts}" + "".join(f"[a_in{i}]" for i in range(n_parts)) + ";"
    
    concat_str = ""
    for i in range(n_parts):
        is_rev = operation == "loop_pingpong" and i > 0 and (i - 1) % 2 == 1
        if i == 0:
            fc += f"[v_in0]trim=end={t_start},setpts=PTS-STARTPTS[v0];"
            if has_audio: fc += f"[a_in0]atrim=end={t_start},asetpts=PTS-STARTPTS[a0];"
        else:
            v_trim = f"[v_in{i}]trim=start={t_start},setpts=PTS-STARTPTS" + (",reverse" if is_rev else "") + f"[v{i}];"
            fc += v_trim
            if has_audio:
                a_trim = f"[a_in{i}]atrim=start={t_start},asetpts=PTS-STARTPTS" + (",areverse" if is_rev else "") + f"[a{i}];"
                fc += a_trim
        concat_str += f"[v{i}][a{i}]" if has_audio else f"[v{i}]"
        
    a_val = "1" if has_audio else "0"
    fc += f"{concat_str}concat=n={n_parts}:v=1:a={a_val}[v]"
    if has_audio: fc += "[a]"
    
    out = os.path.join(cwd, f"{os.path.splitext(os.path.basename(inp))[0]}_{'pingpong' if 'pingpong' in operation else 'loop'}_end_{ts}.mp4")
    cmd = ["ffmpeg", "-y", "-i", inp, "-filter_complex", fc, "-map", "[v]"]
    if has_audio: cmd.extend(["-map", "[a]"])
    cmd.append(out)
    return cmd, out, None
