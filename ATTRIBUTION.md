# Media and library attribution

The generated test image and motion video are created by `assignment.py` for this assignment.

`inputs/real_clip.mp4` is an adapted six-second excerpt of the **Sintel trailer**, a Blender Foundation open movie project.

**(c) copyright Blender Foundation | durian.blender.org**

- Source: https://download.blender.org/durian/trailer/sintel_trailer-480p.mp4
- Copyright and license statement: https://durian.blender.org/sharing/
- License: Creative Commons Attribution 3.0 Unported, https://creativecommons.org/licenses/by/3.0/
- Adaptations: trailer time 00:33 to 00:39; resized to 640 x 360; 24 frames per second; audio removed. Comparisons, extracted frames, and processed videos are further adaptations.
- This excerpt is stored using lossless H.264 encoding of the decoded YUV420 frames. The downloaded trailer was already compressed; the excerpt is not an uncompressed production master.
- Source and excerpt SHA-256 checksums are recorded in `inputs/real_clip_source.json`.

The local streaming player uses **hls.js 1.6.13**, copyright its contributors, under the Apache License 2.0. The vendored source is `assets/vendor/hls.min.js`; its notices are in `assets/vendor/LICENSE.hls.js`, and the Apache license text is in `assets/vendor/APACHE-2.0.txt`. Source project: https://github.com/video-dev/hls.js

Python dependencies retain their respective licenses. The FFmpeg executable is supplied by `imageio-ffmpeg`; this repository does not redistribute the executable.
