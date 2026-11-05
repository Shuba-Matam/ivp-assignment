"""Create a portable submission ZIP from the public project files."""
from pathlib import Path
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def main():
    paths = subprocess.check_output(
        ["git", "ls-files", "-z"], cwd=ROOT
    ).decode("utf-8").split("\0")
    destination = ROOT / "submission" / "IVP_Shuba_Bhuvi_Matam_RA2311031010068.zip"
    destination.parent.mkdir(exist_ok=True)
    report = ROOT / "reports" / "IVP_Assignment_Report_Shuba_Bhuvi_Matam.docx"
    if not report.is_file() or not (ROOT / "outputs" / "metrics.json").is_file():
        raise SystemExit("Generate the experiment results and final report before packaging.")
    with zipfile.ZipFile(destination, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for relative in paths:
            if relative and (ROOT / relative).is_file():
                archive.write(ROOT / relative, "ivp-assignment/" + relative)
    print(f"Created {destination} ({destination.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
