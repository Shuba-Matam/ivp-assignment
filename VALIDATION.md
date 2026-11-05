# Validation performed

The complete assignment was executed on Windows using Python 3.13.3, OpenCV 5.0.0, NumPy 2.5.4, matplotlib 3.11.2, and FFmpeg 9.0.2. The package requirements are pinned in `requirements.txt`.

- All ten experiments completed successfully from both the command line and the native desktop runner.
- Five focused unit tests passed: exact and known-error MSE/PSNR, deterministic impulse noise, exact FFV1 round-trip, generated-video properties, and result-section availability.
- All 96 extracted PNG frames were compared pixel-for-pixel with their source frames.
- All 24 retained frames in the 6 fps video were compared pixel-for-pixel with their corresponding source frames. The duration stayed four seconds.
- All 96 filtered saved frames matched a 3 x 3 median filter of their saved noisy counterparts. Recomputed MSE values matched the stored measurements.
- Each of the three geometrically transformed videos decoded all 96 frames.
- All 144 frames in the six-second real excerpt decoded successfully and were distinct.
- Each of six HLS variants decoded to the expected frame count; the SHA-256 of decoded RGB pixels was identical for local-file and localhost HTTP delivery.
- The persistent `--serve` command was launched from a different working directory. The player, vendored library, metrics, master playlist, and transport-stream segment returned HTTP 200 responses.
- The generated player JavaScript passed a syntax check.

The actual desktop execution screenshot is `outputs/screenshots/execution_success.png`. The run metrics include the experiment parameters, outputs, frame counts, sizes, quality measurements, and HTTP verification hashes.

The Word report was rendered through Microsoft Word and the managed document renderer to 18 pages with 13 figures. All pages passed automated checks for text and images inside page boundaries; the contents page matches section starts, identity fields are correct, and the reported measurements match the recorded run.

Browser visual playback was not independently tested during preparation. HLS delivery and decoding were tested with FFmpeg. Direct visual inspection of the report pages was unavailable in the preparation model; automated page checks do not replace a visual review.

To repeat the unit tests:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```
