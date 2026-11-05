"""Render a DOCX via installed Word and the managed skill's Poppler renderer.

Windows bundles no LibreOffice in this Codex runtime. This explicit fallback
replaces only the DOCX-to-PDF conversion function in memory; the packaged
render_docx.py performs rasterization. Page images require visual inspection
by a reviewer with image access.
"""
from pathlib import Path
import argparse
import importlib.util
import os
import subprocess


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("document", type=Path)
    parser.add_argument("--output-dir", type=Path, default=Path("reports/qa"))
    args = parser.parse_args()
    runtime = Path.home() / ".cache/codex-runtimes/codex-primary-runtime"
    skill = Path.home() / ".codex/plugins/cache/openai-primary-runtime/documents/26.1104.12130/skills/documents/render_docx.py"
    poppler = runtime / "dependencies/native/poppler/Library/bin"
    os.environ["PATH"] = str(poppler) + os.pathsep + os.environ.get("PATH", "")
    spec = importlib.util.spec_from_file_location("packaged_render_docx", skill)
    renderer = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(renderer)

    def word_convert(input_path, user_profile, convert_tmp_dir, stem, verbose=False):
        output = Path(convert_tmp_dir) / (stem + ".pdf")
        command = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
                   str(Path(__file__).with_name("export_word_pdf.ps1")),
                   "-InputDocx", str(Path(input_path).resolve()), "-OutputPdf", str(output.resolve())]
        result = subprocess.run(command, capture_output=True, text=True, timeout=120)
        if result.returncode or not output.exists():
            raise RuntimeError(result.stdout + result.stderr)
        print(result.stdout.strip())
        return str(output), result.stdout

    renderer.convert_to_pdf = word_convert
    renderer.rasterize(str(args.document.resolve()), str(args.output_dir.resolve()), 120, False, True)


if __name__ == "__main__":
    main()
