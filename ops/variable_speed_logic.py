import os
from datetime import datetime


def _build_atempo_chain(speed):
    """
    Decompose a speed factor into a chain of atempo filters (each in [0.5, 2.0]).
    Returns a string like ",atempo=2.0,atempo=1.5" or "" for speed==1.0.
    """
    speed = max(0.1, min(4.0, speed))

    if abs(speed - 1.0) < 0.001:
        return ""

    filters = []
    remaining = speed

    if remaining > 1.0:
        while remaining > 2.0 + 1e-9:
            filters.append("atempo=2.0")
            remaining /= 2.0
        if remaining > 1.0 + 1e-6:
            filters.append(f"atempo={remaining:.6f}")
    else:
        while remaining < 0.5 - 1e-9:
            filters.append("atempo=0.5")
            remaining /= 0.5   # dividing by 0.5 = multiply by 2, moving remaining toward 1
        if remaining < 1.0 - 1e-6:
            filters.append(f"atempo={remaining:.6f}")

    return "," + ",".join(filters) if filters else ""


def build_variable_speed_command(input_file, control_points, has_audio, duration, output_file):
    """
    Build an FFmpeg command for variable-speed video using a piecewise-linear speed curve.

    control_points : list of [t_normalized, speed] sorted by t_normalized.
                     t_normalized in [0, 1], speed in [-4, 4].
                     Negative speed means the segment plays in reverse.
    has_audio      : bool – whether the input has an audio stream.
    duration       : float – video duration in seconds.
    output_file    : str   – output path.

    Returns (cmd_list, output_path, error_msg).
    """
    if not control_points or len(control_points) < 2:
        return None, None, "A curva de velocidade precisa de ao menos 2 pontos."

    n_seg = len(control_points) - 1
    filter_parts = []
    seg_idx = 0   # sequential index for valid segments only

    for i in range(n_seg):
        t0, s0 = control_points[i]
        t1, s1 = control_points[i + 1]

        start = t0 * duration
        end = t1 * duration

        if end <= start:
            continue

        # Average speed for this segment (linear interpolation midpoint)
        avg_speed = (s0 + s1) / 2.0
        abs_speed = max(0.1, abs(avg_speed))
        is_reversed = avg_speed < 0
        pts_factor = 1.0 / abs_speed

        # --- Video ---
        v = f"[0:v]trim=start={start:.6f}:end={end:.6f},setpts=PTS-STARTPTS"
        if is_reversed:
            v += ",reverse"
        v += f",setpts={pts_factor:.6f}*PTS[v{seg_idx}]"
        filter_parts.append(v)

        if has_audio:
            # --- Audio ---
            a = f"[0:a]atrim=start={start:.6f}:end={end:.6f},asetpts=PTS-STARTPTS"
            if is_reversed:
                a += ",areverse"
            a += _build_atempo_chain(abs_speed)
            a += f"[a{seg_idx}]"
            filter_parts.append(a)

        seg_idx += 1

    if seg_idx == 0:
        return None, None, "Nenhum segmento válido na curva."

    valid_segs = seg_idx

    if has_audio:
        # concat expects interleaved inputs: [v0][a0][v1][a1]...[vN][aN]
        interleaved = "".join(f"[v{i}][a{i}]" for i in range(valid_segs))
        filter_parts.append(
            f"{interleaved}concat=n={valid_segs}:v=1:a=1[vout][aout]"
        )
    else:
        v_refs = "".join(f"[v{i}]" for i in range(valid_segs))
        filter_parts.append(f"{v_refs}concat=n={valid_segs}:v=1:a=0[vout]")

    filter_complex = ";".join(filter_parts)

    cmd = [
        "ffmpeg", "-y", "-i", input_file,
        "-filter_complex", filter_complex,
        "-map", "[vout]",
    ]
    if has_audio:
        cmd += ["-map", "[aout]", "-c:a", "aac", "-b:a", "192k"]
    cmd += ["-c:v", "libx264", "-preset", "fast", "-crf", "18", output_file]

    return cmd, output_file, None
