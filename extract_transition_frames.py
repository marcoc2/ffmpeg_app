import os
import sys
import argparse
import subprocess
import json

def get_video_frames(file_path):
    cmd = [
        "ffprobe", "-v", "quiet",
        "-print_format", "json",
        "-show_streams", "-show_format",
        file_path
    ]
    try:
        res = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        )
        if not res.stdout:
            return 0
        info = json.loads(res.stdout)
        video_stream = next((s for s in info.get("streams", []) if s.get("codec_type") == "video"), None)
        if video_stream:
            nb_frames = int(video_stream.get("nb_frames", 0))
            if nb_frames > 0:
                return nb_frames
            # Fallback to duration * fps
            duration = float(info.get("format", {}).get("duration", 0.0))
            fps_str = video_stream.get("r_frame_rate", "30/1")
            if "/" in fps_str:
                num, den = map(int, fps_str.split("/"))
                fps = num / den if den != 0 else 30.0
            else:
                fps = float(fps_str)
            if duration > 0.0:
                return int(round(duration * fps))
        return 0
    except Exception:
        return 0

def main():
    parser = argparse.ArgumentParser(description="Extract transition frames from adjacent videos")
    parser.add_argument("--videos", required=True, help="Comma-separated list of video file paths")
    parser.add_argument("--out-dir", required=True, help="Output directory")
    parser.add_argument("--ts", required=True, help="Timestamp suffix")
    args = parser.parse_args()

    video_paths = [v.strip() for v in args.videos.split(",") if v.strip()]
    if len(video_paths) < 2:
        print("Error: Requer pelo menos 2 vídeos para encontrar transições adjacentes.")
        sys.exit(1)

    os.makedirs(args.out_dir, exist_ok=True)

    # 1. Probe all videos to get their frame counts
    frame_counts = []
    for path in video_paths:
        frames = get_video_frames(path)
        if frames <= 0:
            print(f"Error: Não foi possível determinar o número de frames do vídeo: {path}")
            sys.exit(1)
        frame_counts.append(frames)

    # 2. Extract frames
    n = len(video_paths)
    for i in range(n - 1):
        pair_num = f"{i+1:02d}_{i+2:02d}" # e.g. "01_02" for 1st-to-2nd transition
        
        # Last frame of video i
        v_left = video_paths[i]
        v_left_name = os.path.splitext(os.path.basename(v_left))[0]
        last_frame_idx = frame_counts[i] - 1
        out_left = os.path.join(args.out_dir, f"trans_{pair_num}_{v_left_name}_last_{args.ts}.png")
        
        # First frame of video i+1
        v_right = video_paths[i+1]
        v_right_name = os.path.splitext(os.path.basename(v_right))[0]
        out_right = os.path.join(args.out_dir, f"trans_{pair_num}_{v_right_name}_first_{args.ts}.png")

        # Extract last frame of video i
        print(f"Extraindo último frame de {v_left_name} (frame {last_frame_idx}) -> {os.path.basename(out_left)}...")
        cmd_left = [
            "ffmpeg", "-y", "-i", v_left,
            "-vf", f"select=eq(n\\,{last_frame_idx})",
            "-update", "1", "-vframes", "1",
            out_left
        ]
        res_left = subprocess.run(
            cmd_left,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        )
        if res_left.returncode != 0:
            print(f"Error ao extrair frame de {v_left_name}: {res_left.stderr.decode('utf-8', errors='replace')}")
            sys.exit(1)

        # Extract first frame of video i+1 (frame 0)
        print(f"Extraindo primeiro frame de {v_right_name} (frame 0) -> {os.path.basename(out_right)}...")
        cmd_right = [
            "ffmpeg", "-y", "-i", v_right,
            "-vf", "select=eq(n\\,0)",
            "-update", "1", "-vframes", "1",
            out_right
        ]
        res_right = subprocess.run(
            cmd_right,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        )
        if res_right.returncode != 0:
            print(f"Error ao extrair frame de {v_right_name}: {res_right.stderr.decode('utf-8', errors='replace')}")
            sys.exit(1)

    print("Extração de frames de transição concluída com sucesso!")

if __name__ == "__main__":
    main()
