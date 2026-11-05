# Image and Video Processing Assignment

**Shuba Bhuvi Matam — RA2311031010068**  
21CSE480T · Department of Networking and Communications · SRM Institute of Science and Technology

Ten reproducible experiments in Python, including image analysis, video processing, compression, and HTTP Live Streaming. The repository includes demo inputs, generated results, and the Word report.

## Run on Windows

Install **Python 3.13** (the tested version), with the standard Tcl/Tk option if you want the optional desktop viewer. The pinned dependencies require Python 3.12 or newer. Download this repository as a ZIP and extract it, or clone it:

```powershell
git clone https://github.com/Shuba-Matam/ivp-assignment.git
cd ivp-assignment
powershell -NoProfile -ExecutionPolicy Bypass -File .\setup.ps1
.\.venv\Scripts\python.exe assignment.py --all
```

You can also double-click **Run_Assignment.bat**. It sets up the environment on the first run, then runs all ten questions. Initial package installation requires Internet access. Once setup is complete, the bundled inputs and local streaming library allow the experiments to run offline.

The program saves outputs in `outputs/` and numerical results in `outputs/metrics.json`. Running it again regenerates its experiment outputs.

## See the results

For a desktop window that runs the real script, displays its execution log, and lets you inspect figures:

```powershell
.\.venv\Scripts\python.exe run_demo.py
```

For the local video streaming demonstration, double-click **View_Results.bat**, or run:

```powershell
.\.venv\Scripts\python.exe assignment.py --serve
```

Open the local address printed by the program in Chrome or Edge. Keep the command window open while playing the videos; press **Ctrl+C** to stop serving. The server listens only on this computer. The player uses the included copy of hls.js to play the HLS playlists.

## Experiments

| Question | Experiment |
| --- | --- |
| 1 | Sobel gradient magnitude and Canny edge detection |
| 2 | Lossless PNG and lossy JPEG compression, with MSE and PSNR |
| 3 | Otsu thresholding and seeded region growing |
| 4 | Video frame extraction to numbered PNG files |
| 5 | Reduced frame-rate sampling with unchanged duration |
| 6 | Translation, rotation, and scaling of video frames |
| 7 | Absolute difference between two video frames |
| 8 | Salt-and-pepper noise and median filtering |
| 9 | H.264 video compression with size and quality comparisons |
| 10 | Multiple bitrates, HLS packaging, and actual HTTP delivery checks |

Use `python assignment.py --help` to see the available question and input options.

To run one experiment, use `.\.venv\Scripts\python.exe assignment.py --question 3`. To recreate the generated image and video, use `--generate-inputs`, then run `--all` again so the saved outputs match the inputs.

## Files

- `assignment.py` — the complete ten-question implementation.
- `requirements.txt` — tested Python package versions.
- `inputs/` — generated test image and video, plus the attributed real-video excerpt.
- `outputs/` — reconstructed images, processed videos, extracted frames, figures, playlists, metrics, and execution evidence.
- `reports/IVP_Assignment_Report_Shuba_Bhuvi_Matam.docx` — the assignment report.
- `tools/prepare_media.py` — rebuilds the real-video excerpt and downloads the local streaming library.
- `tools/build_report.py` — regenerates the report using the experiment results; report-generation dependencies are separate from the assignment runtime.

To rebuild the Word report after a complete run, install the optional dependencies and run the builder:

```powershell
.\.venv\Scripts\python.exe -m pip install -r tools/requirements-report.txt
.\.venv\Scripts\python.exe tools/build_report.py
```

The report includes the supplied execution screenshot. If you change the experiment code, replace that screenshot with one from your own new run before rebuilding. Run `run_demo.py` for a convenient execution window.

## Reproducing the media

The generated inputs are created by `assignment.py`. To download the original Sintel trailer again and rebuild the included excerpt:

```powershell
.\.venv\Scripts\python.exe tools/prepare_media.py
```

The excerpt is six seconds at 640 × 360 and 24 fps. It is a lossless H.264 copy of decoded frames from an already compressed trailer. Compression ratios against this reference describe this experiment's storage choices; they do not represent typical savings when recompressing an ordinary MP4.

See [ATTRIBUTION.md](ATTRIBUTION.md) for the Blender Foundation CC BY 3.0 media attribution and the hls.js license. The original reference report supplied during preparation is not part of this repository.

## Reading the measurements

MSE is measured on decoded pixels after conversion to a signed floating-point type. PSNR is derived from MSE with a peak value of 255. Identical reconstructions have MSE zero and infinite PSNR. Video comparisons must use matching dimensions, frame counts, and timestamps; the frame-rate experiment uses held frames on the original timeline. PSNR describes pixel fidelity and should be interpreted alongside the visual comparisons.
