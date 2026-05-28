import os
import sys
import argparse
import subprocess

def main():
    parser = argparse.ArgumentParser(description="Frame-accurate video slicing with zero-start timestamps")
    parser.add_argument("--input", required=True, help="Input video file path")
    parser.add_argument("--times", required=True, help="Comma-separated segment times (seconds)")
    parser.add_argument("--out-pattern", required=True, help="Output pattern (e.g. out_%03d.mp4)")
    parser.add_argument("--has-audio", type=int, default=1, help="1 if has audio, 0 otherwise")
    parser.add_argument("--duration", type=float, default=0.0, help="Total duration of input video")
    parser.add_argument("--min-duration", type=float, default=0.0, help="Minimum duration of segments to keep")
    args = parser.parse_args()

    # Parse segment times
    split_times = sorted([float(x) for x in args.times.split(",") if x.strip()])
    
    # Determine video duration
    duration = args.duration
    if duration <= 0.0:
        try:
            cmd_ffprobe = ["ffprobe", "-v", "quiet", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", args.input]
            res_ffprobe = subprocess.run(cmd_ffprobe, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            duration = float(res_ffprobe.stdout.strip())
        except Exception:
            duration = split_times[-1] + 9999.0 if split_times else 9999.0

    timeline = [0.0] + split_times + [duration]

    out_dir = os.path.dirname(args.out_pattern)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

    output_idx = 0
    for i in range(len(timeline) - 1):
        start = timeline[i]
        end = timeline[i+1]
        seg_dur = end - start

        if seg_dur <= 0.0001:
            continue

        if args.min_duration > 0.0 and seg_dur < args.min_duration:
            print(f"Skipping segment {i} ({start:.3f}s -> {end:.3f}s) because its duration ({seg_dur:.3f}s) is less than {args.min_duration:.3f}s")
            continue

        out_path = args.out_pattern % output_idx
        output_idx += 1

        cmd_cut = [
            "ffmpeg", "-y",
            "-ss", f"{start:.6f}",
            "-i", args.input,
            "-t", f"{seg_dur:.6f}",
            "-c:v", "libx264", "-crf", "18", "-preset", "medium"
        ]
        if args.has_audio:
            cmd_cut.extend(["-c:a", "aac", "-b:a", "192k"])
        else:
            cmd_cut.append("-an")
        cmd_cut.append(out_path)

        print(f"Generating segment {i} ({start:.3f}s -> {end:.3f}s, duration={seg_dur:.3f}s) -> {out_path}...")
        res = subprocess.run(cmd_cut, stdout=sys.stdout, stderr=sys.stderr)
        if res.returncode != 0:
            print(f"Error: Cutting segment {i} failed")
            sys.exit(res.returncode)

    print("Slicing completed successfully!")

if __name__ == "__main__":
    main()
