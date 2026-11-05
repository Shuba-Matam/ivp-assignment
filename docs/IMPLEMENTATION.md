# Implementation and metric map

`assignment.py` is the single runnable assignment program. With no selection
argument it runs all ten experiments and writes measured values to
`outputs/metrics.json` under keys `q1` through `q10`.

| Question | Main implementation | Report-facing output |
|---|---|---|
| 1 | Gaussian smoothing, 3x3 Sobel gradient, Canny | `outputs/q1/edge_detection_comparison.png` |
| 2 | PNG and JPEG decode, signed MSE and PSNR | `outputs/q2/compression_comparison.png` |
| 3 | Otsu threshold and 8-connected seeded Lab region growing | `outputs/q3/segmentation_comparison.png` |
| 4 | Decode and save every frame as PNG | `outputs/q4/extracted_frame_samples.png` |
| 5 | Keep every fourth frame, preserve duration, sample-and-hold comparison | `outputs/q5/time_aligned_hold_quality.png` |
| 6 | Per-frame translation, rotation, and scaling on a fixed canvas | `outputs/q6/geometric_transformations.png` |
| 7 | `int16` subtraction before absolute frame difference | `outputs/q7/frame_difference_comparison.png` |
| 8 | Deterministic salt-and-pepper noise and 3x3 median filtering on every frame | `outputs/q8/spatial_filtering_comparison.png` |
| 9 | H.264/libx264 compression and decoded frame quality | `outputs/q9/h264_size_quality_comparison.png`, `outputs/q9/h264_reconstructed_frame_evidence.png` |
| 10 | Three packaged HLS variants per source and localhost HTTP decode verification | `outputs/q10/bitrate_size_quality.png`, `outputs/q10/hls_bitrate_reconstructed_frame_evidence.png` |

Generated and processed AVI files use lossless FFV1 so experiment metrics match
their decoded saved outputs. The real Sintel file is a lossless storage of a
decoded excerpt from an already compressed trailer; it is a stable decoded
reference, not the original production master.

The `--serve` page distinguishes direct MP4 preview playback from HLS playback.
HLS uses the vendored `assets/vendor/hls.min.js` when the browser does not offer
native HLS support. Question 10 independently validates every variant by
decoding its playlist both from disk and through a temporary localhost server.
