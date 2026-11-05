"""Download the attributed Sintel trailer and prepare the short class demo clip."""
from pathlib import Path
import hashlib
import json
import subprocess
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
TRAILER_URL = "https://download.blender.org/durian/trailer/sintel_trailer-480p.mp4"
HLS_URL = "https://cdn.jsdelivr.net/npm/hls.js@1.6.13/dist/hls.min.js"
HLS_LICENSE_URL = "https://cdn.jsdelivr.net/npm/hls.js@1.6.13/LICENSE"
APACHE_LICENSE_URL = "https://www.apache.org/licenses/LICENSE-2.0.txt"


def download(url, destination):
    destination.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(url, timeout=60) as response:
        destination.write_bytes(response.read())


def main():
    import imageio_ffmpeg
    original = ROOT / ".cache" / "sintel_trailer-480p.mp4"
    if not original.exists():
        download(TRAILER_URL, original)
    (ROOT / "inputs").mkdir(exist_ok=True)
    subprocess.run([
        imageio_ffmpeg.get_ffmpeg_exe(), "-hide_banner", "-loglevel", "error", "-y",
        "-ss", "33", "-i", str(original), "-t", "6", "-an",
        "-vf", "scale=640:360:flags=lanczos,fps=24", "-c:v", "libx264",
        "-crf", "0", "-preset", "medium", "-pix_fmt", "yuv420p",
        "-movflags", "+faststart", str(ROOT / "inputs" / "real_clip.mp4")
    ], check=True)
    for url, name in [(HLS_URL, "hls.min.js"), (HLS_LICENSE_URL, "LICENSE.hls.js"), (APACHE_LICENSE_URL, "APACHE-2.0.txt")]:
        download(url, ROOT / "assets" / "vendor" / name)
    metadata = {
        "title": "Sintel trailer excerpt", "copyright": "Blender Foundation",
        "attribution": "(c) copyright Blender Foundation | durian.blender.org",
        "license": "Creative Commons Attribution 3.0 Unported",
        "license_url": "https://creativecommons.org/licenses/by/3.0/",
        "license_statement": "https://durian.blender.org/sharing/",
        "source_url": TRAILER_URL,
        "source_sha256": hashlib.sha256(original.read_bytes()).hexdigest(),
        "modifications": "Excerpt 00:33 to 00:39; resized to 640x360; sampled at 24 fps; audio removed; H.264 lossless storage of the decoded YUV420 reference.",
        "reference_note": "The downloaded trailer is already compressed. Lossless storage preserves this decoded excerpt; it does not recover the original production master.",
        "clip_sha256": hashlib.sha256((ROOT / "inputs" / "real_clip.mp4").read_bytes()).hexdigest(),
    }
    (ROOT / "inputs" / "real_clip_source.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    print("Prepared inputs/real_clip.mp4 and vendored hls.js 1.6.13")


if __name__ == "__main__":
    main()
