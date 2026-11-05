"""Create the final academic DOCX from the completed IVP run artifacts."""

from __future__ import annotations

import argparse
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from PIL import Image
from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Inches, Pt, RGBColor


ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"
OUTPUTS = ROOT / "outputs"
METRICS = OUTPUTS / "metrics.json"
SOURCE = ROOT / "assignment.py"
SCREENSHOT = OUTPUTS / "screenshots" / "execution_success.png"
FINAL = REPORTS / "IVP_Assignment_Report_Shuba_Bhuvi_Matam.docx"

AUTHOR = "Shuba Bhuvi Matam"
REGISTER = "RA2311031010068"
COURSE = "21CSE480T Image and Video Processing"
REPO = "https://github.com/Shuba-Matam/ivp-assignment"
NAVY, PALE, BORDER, TEXT, MUTED = "183B5B", "F3F7FA", "D9D9D9", "1F2933", "52606D"

TITLES = {
    1: "Edge Detection Using Sobel and Canny",
    2: "Lossless and Lossy Image Compression",
    3: "Thresholding and Region Based Segmentation",
    4: "Video Frame Extraction",
    5: "Sampling of Video by Reducing the Frame Rate",
    6: "Geometric Transformations on Video Frames",
    7: "Comparison of Two Video Frames Using Image Difference",
    8: "Spatial Filtering of Video Frames",
    9: "Video Compression Before Streaming",
    10: "Video Streaming at Different Bitrates",
}

PROBLEMS = {
    1: "Implement edge detection using Sobel and Canny operators.",
    2: "Implement lossless and lossy image compression and compare reconstructed images using MSE and PSNR.",
    3: "Implement image segmentation using thresholding and region based segmentation techniques and compare the results.",
    4: "Implement video frame extraction and save the extracted frames as individual image files.",
    5: "Implement sampling of video signals by reducing frame rate and compare the original and sampled videos.",
    6: "Demonstrate translation, rotation, and scaling on video frames and analyze their effects.",
    7: "Compare two video frames using image difference.",
    8: "Implement spatial filtering on video frames to remove noise and enhance video quality.",
    9: "Implement video compression before streaming and compare file size and quality before and after compression.",
    10: "Demonstrate video streaming with different bitrates and analyze the resulting video quality.",
}

CODE_EXCERPTS = {
    1: """blurred = cv2.GaussianBlur(gray, (5, 5), 1.1)
gx = cv2.Sobel(blurred, cv2.CV_64F, 1, 0, ksize=3)
gy = cv2.Sobel(blurred, cv2.CV_64F, 0, 1, ksize=3)
magnitude = cv2.magnitude(gx.astype(np.float32), gy.astype(np.float32))
canny = cv2.Canny(blurred, 70, 150, L2gradient=True)""",
    2: """save_image(png_path, image, [cv2.IMWRITE_PNG_COMPRESSION, 9])
save_image(jpg_path, image, [cv2.IMWRITE_JPEG_QUALITY, 35])
png_mse, png_psnr = mse_psnr(image, png_decoded)
jpg_mse, jpg_psnr = mse_psnr(image, jpg_decoded)""",
    3: """otsu_value, otsu = cv2.threshold(
    gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU
)
region = seeded_region_grow(image, seed, threshold=27.0)
iou = intersection / union if union else 1.0""",
    4: """for index, frame in iter_video(DEMO_VIDEO):
    save_image(
        frames_dir / f\"frame_{index:04d}.png\", frame,
        [cv2.IMWRITE_PNG_COMPRESSION, 6],
    )
    count += 1""",
    5: """factor = 4
for index, frame in iter_video(DEMO_VIDEO):
    original_frames.append(frame)
    if index % factor == 0:
        sampled_frames.append(frame.copy())
        writer.write(frame)""",
    6: """center = (size[0] / 2, size[1] / 2)
translation_matrix = np.float32([[1, 0, tx], [0, 1, ty]])
translated = cv2.warpAffine(frame, translation_matrix, size)
rotation_matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
rotated = cv2.warpAffine(frame, rotation_matrix, size)
scale_matrix = cv2.getRotationMatrix2D(center, 0, scale)
scaled = cv2.warpAffine(frame, scale_matrix, size)""",
    7: """signed = second.astype(np.int16) - first.astype(np.int16)
absolute = np.abs(signed).astype(np.uint8)
gray_abs = cv2.cvtColor(absolute, cv2.COLOR_BGR2GRAY)
_, changed = cv2.threshold(gray_abs, 28, 255, cv2.THRESH_BINARY)""",
    8: """for index, original in iter_video(DEMO_VIDEO):
    noisy = add_salt_pepper(original, rng, amount=0.035)
    filtered = cv2.medianBlur(noisy, 3)
    noisy_writer.write(noisy)
    filtered_writer.write(filtered)""",
    9: """encoded = out / f\"{name}_h264_crf{crf}.mp4\"
encode_h264(source, encoded, crf)
quality = compare_decoded_videos(source, encoded)
ratio = source_info[\"size_bytes\"] / encoded_info[\"size_bytes\"]""",
    10: """playlists = create_hls_ladder(source, destination)
playlist = playlists[\"low\"]
with local_http_server(0) as port:
    verification = verify_hls_local_http(
        playlist, port, source_info[\"width\"], source_info[\"height\"]
    )""",
}


def metrics() -> dict[str, Any]:
    return json.loads(METRICS.read_text(encoding="utf-8"))


def val(value: Any, digits: int = 2) -> str:
    if value is None:
        return "infinite"
    if isinstance(value, bool):
        return "Yes" if value else "No"
    if isinstance(value, int):
        return f"{value:,}"
    if isinstance(value, float):
        return "infinite" if math.isinf(value) else f"{value:,.{digits}f}"
    return str(value)


def kib(value: int) -> str:
    return f"{value / 1024:,.1f} KiB"


def font(run, size: float, bold: bool = False, color: str = TEXT, name: str = "Aptos") -> None:
    run.font.name = name
    rfonts = run._element.get_or_add_rPr().get_or_add_rFonts()
    rfonts.set(qn("w:ascii"), name)
    rfonts.set(qn("w:hAnsi"), name)
    run.font.size = Pt(size)
    run.bold = bold
    run.font.color.rgb = RGBColor.from_string(color)


def shade(cell, color: str) -> None:
    tcpr = cell._tc.get_or_add_tcPr()
    node = tcpr.find(qn("w:shd")) or OxmlElement("w:shd")
    node.set(qn("w:fill"), color)
    if node.getparent() is None:
        tcpr.append(node)


def margins(cell, amount: int = 90) -> None:
    tcpr = cell._tc.get_or_add_tcPr()
    node = tcpr.first_child_found_in("w:tcMar") or OxmlElement("w:tcMar")
    if node.getparent() is None:
        tcpr.append(node)
    for edge in ("top", "start", "bottom", "end"):
        part = node.find(qn(f"w:{edge}")) or OxmlElement(f"w:{edge}")
        part.set(qn("w:w"), str(amount))
        part.set(qn("w:type"), "dxa")
        if part.getparent() is None:
            node.append(part)


def borders(table) -> None:
    tblpr = table._tbl.tblPr
    box = tblpr.first_child_found_in("w:tblBorders") or OxmlElement("w:tblBorders")
    if box.getparent() is None:
        tblpr.append(box)
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        part = box.find(qn(f"w:{edge}")) or OxmlElement(f"w:{edge}")
        for key, value in (("val", "single"), ("sz", "6"), ("color", BORDER)):
            part.set(qn(f"w:{key}"), value)
        if part.getparent() is None:
            box.append(part)


def styles(doc: Document) -> None:
    normal = doc.styles["Normal"]
    normal.font.name = "Aptos"
    normal._element.rPr.rFonts.set(qn("w:ascii"), "Aptos")
    normal._element.rPr.rFonts.set(qn("w:hAnsi"), "Aptos")
    normal.font.size = Pt(9.3)
    normal.font.color.rgb = RGBColor.from_string(TEXT)
    normal.paragraph_format.space_after = Pt(4.2)
    normal.paragraph_format.line_spacing = 1.06
    title = doc.styles["Title"]
    title.font.name = "Aptos Display"
    title.font.size = Pt(25)
    title.font.bold = True
    title.font.color.rgb = RGBColor(0, 0, 0)
    for name, size in (("Heading 1", 16.5), ("Heading 2", 11.2), ("Heading 3", 10)):
        style = doc.styles[name]
        style.font.name = "Aptos Display"
        style._element.rPr.rFonts.set(qn("w:ascii"), "Aptos Display")
        style._element.rPr.rFonts.set(qn("w:hAnsi"), "Aptos Display")
        style.font.size = Pt(size)
        style.font.bold = True
        style.font.color.rgb = RGBColor(0, 0, 0)
        style.paragraph_format.keep_with_next = True
        style.paragraph_format.space_after = Pt(5)
    caption = doc.styles["Caption"]
    caption.font.name = "Aptos"
    caption.font.size = Pt(8)
    caption.font.italic = True
    caption.font.color.rgb = RGBColor.from_string(MUTED)
    caption.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
    caption.paragraph_format.space_after = Pt(4)


def layout(section) -> None:
    section.page_width, section.page_height = Cm(21), Cm(29.7)
    section.top_margin, section.bottom_margin = Cm(1.8), Cm(1.65)
    section.left_margin, section.right_margin = Cm(2.8), Cm(2.0)
    section.header_distance, section.footer_distance = Cm(0.75), Cm(0.75)


def field(paragraph, instruction: str) -> None:
    run = paragraph.add_run()
    begin, separate, end = (OxmlElement("w:fldChar") for _ in range(3))
    begin.set(qn("w:fldCharType"), "begin")
    separate.set(qn("w:fldCharType"), "separate")
    end.set(qn("w:fldCharType"), "end")
    text = OxmlElement("w:instrText")
    text.set(qn("xml:space"), "preserve")
    text.text = f" {instruction} "
    shown = OxmlElement("w:t")
    shown.text = "1"
    run._r.extend((begin, text, separate, shown, end))
    font(run, 8, color=MUTED)


def numbering(section, kind: str, start: int) -> None:
    node = section._sectPr.find(qn("w:pgNumType")) or OxmlElement("w:pgNumType")
    node.set(qn("w:fmt"), kind)
    node.set(qn("w:start"), str(start))
    if node.getparent() is None:
        section._sectPr.append(node)


def footer(section) -> None:
    section.footer.is_linked_to_previous = False
    p = section.footer.paragraphs[0]
    p.clear()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run(f"{AUTHOR}  {REGISTER}   |   ")
    font(r, 8, color=MUTED)
    field(p, "PAGE")


def header(section) -> None:
    section.header.is_linked_to_previous = False
    p = section.header.paragraphs[0]
    p.clear()
    p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    r = p.add_run("21CSE480T  IMAGE AND VIDEO PROCESSING")
    font(r, 7.6, True, MUTED)


def heading(doc: Document, lead: str, title: str) -> None:
    p = doc.add_paragraph(style="Heading 1")
    if lead:
        font(p.add_run(lead + "  "), 16.5, True, NAVY, "Aptos Display")
    font(p.add_run(title), 16.5, True, "000000", "Aptos Display")


def labeled(doc: Document, lead: str, body: str) -> None:
    p = doc.add_paragraph()
    font(p.add_run(lead + " "), 9.3, True, NAVY)
    font(p.add_run(body), 9.3)


def table(doc: Document, headers: list[str], rows: Iterable[Iterable[Any]], widths: list[float] | None = None, size: float = 7.9) -> None:
    rows = [list(row) for row in rows]
    tbl = doc.add_table(rows=1, cols=len(headers))
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    tbl.autofit = False
    borders(tbl)
    trpr = tbl.rows[0]._tr.get_or_add_trPr()
    repeat = OxmlElement("w:tblHeader")
    repeat.set(qn("w:val"), "true")
    trpr.append(repeat)
    for index, text in enumerate(headers):
        cell = tbl.rows[0].cells[index]
        shade(cell, NAVY)
        margins(cell)
        cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        font(p.add_run(text), size, True, "FFFFFF")
    for row_index, values in enumerate(rows):
        cells = tbl.add_row().cells
        for index, value in enumerate(values):
            cell = cells[index]
            margins(cell)
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            if row_index % 2:
                shade(cell, PALE)
            p = cell.paragraphs[0]
            p.paragraph_format.space_after = Pt(0)
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT if index == 0 else WD_ALIGN_PARAGRAPH.CENTER
            font(p.add_run(str(value)), size)
    if widths:
        for row in tbl.rows:
            for index, width in enumerate(widths):
                row.cells[index].width = Inches(width)
    doc.add_paragraph().paragraph_format.space_after = Pt(0)


def figure(doc: Document, relative: str | Path, caption: str, max_w: float = 6.25, max_h: float = 3.45) -> None:
    path = Path(relative)
    if not path.is_absolute():
        path = ROOT / path
    with Image.open(path) as image:
        ratio = image.width / image.height
    width = min(max_w, max_h * ratio)
    height = width / ratio
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.keep_with_next = True
    picture = p.add_run().add_picture(str(path), width=Inches(width), height=Inches(height))
    picture._inline.docPr.set("descr", caption)
    picture._inline.docPr.set("title", caption)
    doc.add_paragraph(caption, style="Caption").paragraph_format.keep_together = True


def code(doc: Document, number: int) -> None:
    doc.add_paragraph("Core implementation excerpt", style="Heading 2")
    p = doc.add_paragraph()
    p.paragraph_format.left_indent = Cm(0.3)
    p.paragraph_format.right_indent = Cm(0.15)
    p.paragraph_format.space_after = Pt(4)
    shd = OxmlElement("w:shd")
    shd.set(qn("w:fill"), "F2F4F7")
    p._p.get_or_add_pPr().append(shd)
    selected = CODE_EXCERPTS[number].splitlines()
    for index, line in enumerate(selected):
        r = p.add_run(line)
        font(r, 7.1, color="263238", name="Consolas")
        if index + 1 < len(selected):
            r.add_break()


def question(doc: Document, number: int, algorithm: str) -> None:
    heading(doc, f"QUESTION {number}", TITLES[number])
    labeled(doc, "Problem", PROBLEMS[number])
    labeled(doc, "Algorithm", algorithm)
    code(doc, number)


def cover(doc: Document) -> None:
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(32)
    font(p.add_run(COURSE.upper()), 13, True, "000000")
    p = doc.add_paragraph("Assignment Problem Implementation Report", style="Title")
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(38)
    p.paragraph_format.space_after = Pt(34)
    for text, size, bold in (
        ("Submitted by", 10, False), (AUTHOR, 17, True), (f"Register Number  {REGISTER}", 11, False),
        ("B.Tech Computer Science Engineering", 10.3, False),
        ("with specialization in Information Technology", 10.3, False),
    ):
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_after = Pt(3)
        font(p.add_run(text), size, bold, "000000")
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(28)
    font(p.add_run("Submitted to"), 10, color=MUTED)
    for text in ("Dr. R. Abirami", "Assistant Professor", "Department of Networking and Communications"):
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_after = Pt(2)
        font(p.add_run(text), 10.3, text == "Dr. R. Abirami", "000000")
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(28)
    lines = ["DEPARTMENT OF NETWORKING AND COMMUNICATIONS", "SCHOOL OF COMPUTING", "COLLEGE OF ENGINEERING AND TECHNOLOGY", "SRM INSTITUTE OF SCIENCE AND TECHNOLOGY", "KATTANKULATHUR 603 203", "NOVEMBER 2026"]
    for index, text in enumerate(lines):
        r = p.add_run(text)
        font(r, 10.3, index in (0, 3), "000000")
        if index + 1 < len(lines):
            r.add_break()


def contents(doc: Document) -> None:
    heading(doc, "", "Table of Contents")
    entries = [
        ("Overview", "1"), ("1  Edge Detection Using Sobel and Canny", "2"),
        ("2  Lossless and Lossy Image Compression", "3"), ("3  Thresholding and Region Based Segmentation", "4"),
        ("4  Video Frame Extraction", "5"), ("5  Sampling by Reducing Frame Rate", "6"),
        ("6  Geometric Transformations", "7"), ("7  Video Frame Difference", "8"),
        ("8  Spatial Filtering", "9"), ("9  Compression Before Streaming", "10"),
        ("10  Streaming at Different Bitrates", "12"), ("Consolidated Results", "14"),
        ("Execution Evidence", "15"), ("References", "16"),
    ]
    table(doc, ["Section", "Page"], entries, [5.55, 0.65], 8.5)
    labeled(doc, "Navigation", "Page numbering restarts with the Overview after the front matter.")


def overview(doc: Document, m: dict[str, Any]) -> None:
    heading(doc, "", "Overview")
    env, inputs, run = m["environment"], m["inputs"], m["run_summary"]
    labeled(doc, "Scope", f"One Python program completed all {run['question_count']} experiments in {run['total_runtime_seconds']:.3f} seconds. Every value and figure in this report comes from the completed run and outputs/metrics.json.")
    table(doc, ["Component", "Recorded version"], [("Python", env["python"]), ("OpenCV", env["opencv"]), ("NumPy", env["numpy"]), ("FFmpeg", env["ffmpeg_version"].split(" Copyright")[0]), ("Platform", env["platform"])], [1.3, 5.0], 7.8)
    doc.add_paragraph("Experiment inputs", style="Heading 2")
    table(doc, ["Input", "Dimensions", "Frames", "Rate", "Duration", "Size"], [
        ("Generated image", "480 x 320", "-", "-", "-", kib(inputs["generated_image"]["size_bytes"])),
        ("Generated video", "480 x 320", 96, "24 fps", "4.0 s", kib(inputs["generated_video"]["size_bytes"])),
        ("Sintel excerpt", "640 x 360", 144, "24 fps", "6.0 s", kib(inputs["real_video"]["size_bytes"])),
    ], [1.35, 1.0, .65, .65, .65, .8], 7.5)
    labeled(doc, "Metrics", "MSE measures average squared pixel error. PSNR is 10 log10 of 255 squared divided by MSE; a higher value indicates a closer reconstruction. Ratios compare only the explicitly named files.")
    labeled(doc, "Reproducibility", f"Source and run instructions are available at {REPO}. Run python assignment.py --all to regenerate outputs and python assignment.py --serve to view the local player.")


def q1(doc: Document, q: dict[str, Any]) -> None:
    question(doc, 1, "Convert to grayscale, smooth with a 5 by 5 Gaussian filter, compute Sobel derivatives and magnitude, then apply Canny non maximum suppression and hysteresis thresholds 70 and 150.")
    figure(doc, q["outputs"]["comparison_figure"], "Figure 1  Original image Sobel magnitude and Canny edges")
    table(doc, ["Measure", "Value"], [("Sobel maximum magnitude", val(q["sobel"]["maximum_magnitude"])), ("Canny edge pixels", val(q["canny"]["edge_pixels"])), ("Canny edge area", f"{q['canny']['edge_percentage']:.3f} %")], [3.5, 2.4])
    labeled(doc, "Observation", f"Sobel preserves graded edge strength, while Canny produces thin, connected contours. Canny marked only {q['canny']['edge_percentage']:.3f} percent of pixels, making it the more selective outline representation for this input.")


def q2(doc: Document, q: dict[str, Any]) -> None:
    question(doc, 2, "Encode the same image as PNG at compression level 9 and JPEG at quality 35, decode both files, and compare every color sample with the reference using MSE and PSNR.")
    figure(doc, q["outputs"]["comparison_figure"], "Figure 2  Reference lossless PNG lossy JPEG and JPEG difference")
    table(doc, ["Reconstruction", "Size", "MSE", "PSNR"], [("PNG lossless", kib(q["png"]["size_bytes"]), "0.000", "infinite"), ("JPEG quality 35", kib(q["jpeg"]["size_bytes"]), f"{q['jpeg']['mse']:.3f}", f"{q['jpeg']['psnr_db']:.2f} dB")], [2.2, 1.2, 1.2, 1.4])
    labeled(doc, "Observation", f"PNG reconstructed every pixel exactly. JPEG was {q['jpeg']['size_reduction_vs_png_percent']:.2f} percent smaller than the PNG output but introduced ringing and texture error concentrated around high contrast boundaries.")


def q3(doc: Document, q: dict[str, Any]) -> None:
    question(doc, 3, "Find one global grayscale threshold with Otsu selection, then grow an 8 connected Lab color region from seed 30 30 with distance threshold 27.")
    figure(doc, q["outputs"]["comparison_figure"], "Figure 3  Otsu mask seeded region and connected overlay")
    table(doc, ["Method", "Parameter", "Pixels", "Area"], [("Otsu", f"threshold {q['otsu']['threshold']:.0f}", val(q["otsu"]["foreground_pixels"]), f"{q['otsu']['foreground_percentage']:.2f} %"), ("Region growth", "seed 30 30 distance 27", val(q["seeded_region_growing"]["region_pixels"]), f"{q['seeded_region_growing']['region_percentage']:.2f} %")], [1.25, 2.25, 1.1, 1.0], 7.5)
    labeled(doc, "Observation", f"The masks have intersection over union {q['comparison']['intersection_over_union']:.3f}. This value measures agreement between the two masks, not segmentation accuracy against ground truth. Otsu selects a global intensity class; region growth returns only the connected, color-similar component attached to the seed.")


def q4(doc: Document, q: dict[str, Any]) -> None:
    question(doc, 4, "Decode the source sequentially and write each frame as a zero padded PNG. Check the written count against the video metadata.")
    figure(doc, q["outputs"]["sample_figure"], "Figure 4  First middle and last extracted frames")
    e = q["extraction"]
    table(doc, ["Property", "Result"], [("Frames written", val(e["frame_count"])), ("Source count matched", val(e["matches_reported_source_count"])), ("First file", e["first_file"]), ("Last file", e["last_file"]), ("Total PNG data", kib(e["total_png_bytes"]))], [1.65, 4.4], 7.7)
    labeled(doc, "Observation", f"All {e['frame_count']} frames were saved in playback order. Individual lossless files support direct inspection and later per-frame processing without decoding the source again.")


def q5(doc: Document, q: dict[str, Any]) -> None:
    question(doc, 5, "Keep every fourth frame and write the retained sequence at one quarter of the source rate. Hold each sample for four original time instants during quality comparison.")
    figure(doc, q["outputs"]["comparison_figure"], "Figure 5  Original held low rate frame and temporal difference")
    h = q["time_aligned_sample_and_hold"]
    table(doc, ["Property", "Original", "Sampled"], [("Frame rate", "24 fps", "6 fps"), ("Frame count", 96, 24), ("Duration", "4.0 s", "4.0 s"), ("Held comparison", "-", f"MSE {h['mse']:.3f}  PSNR {h['psnr_db']:.2f} dB")], [1.4, 1.5, 3.15], 7.6)
    labeled(doc, "Observation", f"Duration is preserved because frame count and playback rate are reduced together. Motion updates only {q['sampled']['fps']:.0f} times per second, so the error appears around moving content between retained samples.")


def q6(doc: Document, q: dict[str, Any]) -> None:
    question(doc, 6, "Apply independent affine translation rotation and scale matrices to every frame on the fixed 480 by 320 canvas, filling uncovered coordinates with dark pixels.")
    figure(doc, q["outputs"]["comparison_figure"], "Figure 6  Translation rotation and scaling on a fixed canvas")
    table(doc, ["Transform", "Range", "Effect"], [("Translation", "x -55 to 55  y -25 to 25", "Uncovered borders and clipping"), ("Rotation", "-18 to 18 degrees", "Interpolation and filled corners"), ("Scaling", "0.70 to 1.15", "Detail loss or edge clipping")], [1.15, 2.1, 2.8], 7.5)
    labeled(doc, "Observation", "All outputs retain the source dimensions. Translation and enlargement can remove edge content, rotation creates corners with no source samples, and downscaling represents detail with fewer pixels.")


def q7(doc: Document, q: dict[str, Any]) -> None:
    question(doc, 7, "Convert frames 20 and 68 to signed 16 bit values before subtraction, take the absolute difference, convert it to grayscale, and threshold values above 28.")
    figure(doc, q["outputs"]["comparison_figure"], "Figure 7  Compared frames absolute difference and changed mask")
    d = q["difference"]
    table(doc, ["Measure", "Value"], [("Compared frames", "20 and 68"), ("Mean absolute difference", f"{d['mean_absolute_difference']:.3f}"), ("Maximum difference", d["maximum_absolute_difference"]), ("Changed pixels", f"{d['changed_pixels']:,}  ({d['changed_percentage']:.3f} %)")], [2.7, 3.3])
    labeled(doc, "Observation", f"Only {d['changed_percentage']:.3f} percent of pixels exceeded the threshold, so the fixed background largely cancels while moving objects remain. Signed conversion avoids unsigned-subtraction wraparound.")


def q8(doc: Document, q: dict[str, Any]) -> None:
    question(doc, 8, "Add deterministic salt and pepper noise to 3.5 percent of pixel locations in all frames, then apply a 3 by 3 median filter and compare both videos with the clean source.")
    figure(doc, q["outputs"]["comparison_figure"], "Figure 8  Clean impulse noisy and median filtered frame")
    table(doc, ["Video", "MSE", "PSNR"], [("With impulse noise", f"{q['before_filtering']['mse_vs_original']:.3f}", f"{q['before_filtering']['psnr_db_vs_original']:.2f} dB"), ("After median filter", f"{q['after_filtering']['mse_vs_original']:.3f}", f"{q['after_filtering']['psnr_db_vs_original']:.2f} dB")], [2.6, 1.6, 1.8])
    labeled(doc, "Observation", f"Median filtering reduced MSE by {q['after_filtering']['mse_reduction_percent']:.2f} percent and improved PSNR by {q['after_filtering']['psnr_improvement_db']:.2f} dB across all 96 frames.")


def q9a(doc: Document, q: dict[str, Any]) -> None:
    question(doc, 9, "Encode generated and real reference clips with H 264 libx264 medium preset and YUV420 at CRF 29 and 30. Decode every frame and compare with the corresponding decoded reference.")
    figure(doc, q["outputs"]["comparison_figure"], "Figure 9  H 264 file reduction and decoded PSNR", max_h=2.95)
    rows = []
    for name in ("generated", "real"):
        d = q["sources"][name]
        rows.append((name.capitalize(), f"CRF {d['encoder']['crf']}", kib(d["reference"]["size_bytes"]), kib(d["compressed"]["size_bytes"]), f"{d['size_reduction_percent']:.2f} %", f"{d['quality']['psnr_db']:.2f} dB"))
    table(doc, ["Source", "Setting", "Reference", "H 264", "Reduction", "PSNR"], rows, [1.0, .75, 1.0, .9, 1.0, .9], 7.2)
    labeled(doc, "Result", "Both encodes preserved frame count frame rate and dimensions. The generated graphics compress especially strongly because their spatial and temporal content is highly predictable.")


def q9b(doc: Document, q: dict[str, Any]) -> None:
    heading(doc, "QUESTION 9", "Reconstruction Evidence and Interpretation")
    figure(doc, q["outputs"]["reconstructed_frame_evidence"], "Figure 10  Decoded references H 264 reconstructions and center crops", 6.5, 5.25)
    real = q["sources"]["real"]
    labeled(doc, "Real clip interpretation", f"The 00:33 to 00:39 Sintel excerpt is stored as lossless H 264 CRF 0 over decoded YUV420 frames. The downloaded trailer was already compressed. Therefore the {real['compression_ratio_reference_to_compressed']:.2f} to 1 ratio and {real['size_reduction_percent']:.2f} percent reduction compare experiment files only and do not represent compression from a production master.")
    labeled(doc, "Quality", f"The CRF 30 reconstruction measured {real['quality']['psnr_db']:.2f} dB over all {real['quality']['paired_frame_count']} paired frames. Detail crops show where quantization affects texture despite high numerical similarity.")
    labeled(doc, "Attribution", "Sintel trailer excerpt  (c) copyright Blender Foundation | durian.blender.org  Creative Commons Attribution 3.0 Unported.")


def variant_rows(q: dict[str, Any]) -> list[tuple[str, ...]]:
    rows = []
    for source in ("generated", "real"):
        for level in ("low", "medium", "high"):
            d = q["sources"][source]["variants"][level]
            rows.append((f"{source.capitalize()} {level}", d["target_bitrate"], f"{d['actual_segment_data_bitrate_kbps']:.1f}", kib(d["package_size_bytes"]), f"{d['quality_vs_reference']['psnr_db']:.2f}", val(d["local_vs_http_verification"]["decoded_content_matches"])))
    return rows


def q10a(doc: Document, q: dict[str, Any]) -> None:
    question(doc, 10, "Encode independent H 264 renditions at 180 420 and 850 kbit per second, package two second HLS segments, serve them on ephemeral localhost, and compare decoded frames with the source.")
    figure(doc, q["outputs"]["quality_size_plot"], "Figure 11  Target bitrate against decoded quality and HLS package size", max_h=2.9)
    table(doc, ["Source level", "Target kbps", "TS payload kbps", "Package", "PSNR", "HTTP equals local"], variant_rows(q), [1.15, .7, .85, .85, .65, 1.2], 6.7)
    real_variants = q["sources"]["real"]["variants"]
    low_psnr = real_variants["low"]["quality_vs_reference"]["psnr_db"]
    high_psnr = real_variants["high"]["quality_vs_reference"]["psnr_db"]
    labeled(doc, "Observation", f"Quality rises with bitrate, while package size also increases. The generated sequence gains little above 420 kbit/s, whereas Sintel improves from {low_psnr:.2f} dB at 180 kbit/s to {high_psnr:.2f} dB at 850 kbit/s.")


def q10b(doc: Document, q: dict[str, Any]) -> None:
    heading(doc, "QUESTION 10", "HLS Reconstruction and Delivery Verification")
    figure(doc, q["outputs"]["reconstructed_frame_evidence"], "Figure 12  Sintel reference and three HLS reconstructions with detail crops", 6.5, 5.25)
    labeled(doc, "Delivery verification", "Every generated variant decoded 96 frames and every real variant decoded 144 frames through local file and HTTP playlist access. Local and HTTP decoded RGB SHA 256 values match for all six variants, so transport introduced no additional pixel change beyond encoding.")
    labeled(doc, "Player", "FFmpeg validated HTTP delivery for all six HLS variants by comparing locally decoded and HTTP-delivered RGB frame hashes. The browser player uses vendored hls.js 1.6.13 and offers Auto, 180, 420, and 850 kbit/s selections.")
    labeled(doc, "Interpretation", "This fixed six-second clip demonstrates the bitrate-quality tradeoff. The bitrate required for a given quality depends on content, resolution, motion, texture, encoder settings, and the acceptable reconstruction error.")


def results(doc: Document, m: dict[str, Any]) -> None:
    heading(doc, "", "Consolidated Results")
    q = {n: m[f"q{n}"] for n in range(1, 11)}
    rows = [
        (1, "Edge detection", f"Canny {q[1]['canny']['edge_pixels']:,} edge pixels"),
        (2, "Image compression", f"PNG exact  JPEG {q[2]['jpeg']['psnr_db']:.2f} dB"),
        (3, "Segmentation", f"Otsu {q[3]['otsu']['foreground_percentage']:.2f} %  region {q[3]['seeded_region_growing']['region_percentage']:.2f} %"),
        (4, "Frame extraction", f"{q[4]['extraction']['frame_count']} PNG frames saved"),
        (5, "Frame rate sampling", f"{q[5]['original']['fps']:.0f} to {q[5]['sampled']['fps']:.0f} fps  {q[5]['time_aligned_sample_and_hold']['psnr_db']:.2f} dB"),
        (6, "Geometry", "Three affine transformation videos"),
        (7, "Frame difference", f"{q[7]['difference']['changed_percentage']:.3f} % changed"),
        (8, "Median filtering", f"PSNR gain {q[8]['after_filtering']['psnr_improvement_db']:.2f} dB"),
        (9, "H 264 compression", f"Sintel CRF 30  {q[9]['sources']['real']['quality']['psnr_db']:.2f} dB"),
        (10, "HLS ladder", f"Sintel {q[10]['sources']['real']['variants']['low']['quality_vs_reference']['psnr_db']:.2f} to {q[10]['sources']['real']['variants']['high']['quality_vs_reference']['psnr_db']:.2f} dB at 180 to 850 kbit/s"),
    ]
    table(doc, ["Q", "Task", "Evidence backed result"], rows, [.55, 1.7, 3.9], 7.5)
    labeled(doc, "Image findings", "Canny produced sparse contours, PNG was exact, JPEG traded detail for size, and global thresholding differed from seed connected segmentation.")
    labeled(doc, "Video findings", "Frame rate reduction lowered temporal fidelity, median filtering removed most impulse noise, and additional streaming bitrate improved the detailed real clip more consistently than the generated scene.")
    labeled(doc, "Limitations", "The study uses one generated image, one four-second generated video, and one six-second adapted trailer excerpt. PSNR measures pixel similarity rather than perceived quality, and every compression result depends on the stated codec parameters and reference files.")


def execution(doc: Document, m: dict[str, Any]) -> None:
    heading(doc, "", "Execution Evidence")
    labeled(doc, "Completed run", f"The native desktop launcher executed assignment.py as a real subprocess. Its status file recorded exit code 0, and outputs/metrics.json records all ten questions completed in {m['run_summary']['total_runtime_seconds']:.3f} seconds.")
    figure(doc, SCREENSHOT, "Figure 13  Native Tkinter execution window after successful completion", 6.45, 5.8)
    labeled(doc, "Evidence scope", "The screenshot demonstrates successful Python execution and access to the generated figures. HLS transport correctness is supported separately by the six FFmpeg local versus HTTP decoded RGB hash comparisons recorded in metrics.json.")


def hyperlink(paragraph, text: str, url: str) -> None:
    rid = paragraph.part.relate_to(url, "http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink", is_external=True)
    link = OxmlElement("w:hyperlink")
    link.set(qn("r:id"), rid)
    run = OxmlElement("w:r")
    rpr = OxmlElement("w:rPr")
    color, under = OxmlElement("w:color"), OxmlElement("w:u")
    color.set(qn("w:val"), NAVY)
    under.set(qn("w:val"), "single")
    rpr.extend((color, under))
    node = OxmlElement("w:t")
    node.text = text
    run.extend((rpr, node))
    link.append(run)
    paragraph._p.append(link)


def references(doc: Document) -> None:
    heading(doc, "", "References")
    refs = [
        ("SRM Institute of Science and Technology", "21CSE480T assignment problem implementation brief", None),
        ("OpenCV", "Image processing and video input output documentation", "https://docs.opencv.org/"),
        ("FFmpeg Project", "Formats codecs and HLS documentation", "https://ffmpeg.org/documentation.html"),
        ("Video dev community", "hls.js 1.6.13 project and Apache License 2.0", "https://github.com/video-dev/hls.js"),
        ("Blender Foundation", "Sintel trailer source", "https://download.blender.org/durian/trailer/sintel_trailer-480p.mp4"),
        ("Blender Foundation", "Sintel sharing and copyright information", "https://durian.blender.org/sharing/"),
        ("Creative Commons", "Attribution 3.0 Unported license", "https://creativecommons.org/licenses/by/3.0/"),
        (AUTHOR, "IVP assignment repository", REPO),
    ]
    for index, (author, title, url) in enumerate(refs, 1):
        p = doc.add_paragraph()
        p.paragraph_format.left_indent = Cm(.6)
        p.paragraph_format.first_line_indent = Cm(-.6)
        p.paragraph_format.space_after = Pt(7)
        font(p.add_run(f"[{index}] {author}. {title}."), 9.1)
        if url:
            p.add_run(" ")
            hyperlink(p, url, url)
    labeled(doc, "Media attribution", "The adapted Sintel trailer excerpt covers 00:33 to 00:39, is 640 by 360 at 24 fps with audio removed, and is licensed under CC BY 3.0. (c) copyright Blender Foundation | durian.blender.org.")


def build(output: Path) -> Path:
    m = metrics()
    REPORTS.mkdir(parents=True, exist_ok=True)
    doc = Document()
    styles(doc)
    layout(doc.sections[0])
    doc.core_properties.title = "Image and Video Processing Assignment Problem Implementation Report"
    doc.core_properties.subject = COURSE
    doc.core_properties.author = AUTHOR
    doc.core_properties.last_modified_by = AUTHOR
    now = datetime.now(timezone.utc)
    doc.core_properties.created = now
    doc.core_properties.modified = now
    doc.core_properties.comments = ""
    cover(doc)
    front = doc.add_section(WD_SECTION.NEW_PAGE)
    layout(front)
    numbering(front, "lowerRoman", 1)
    footer(front)
    contents(doc)
    main = doc.add_section(WD_SECTION.NEW_PAGE)
    layout(main)
    numbering(main, "decimal", 1)
    header(main)
    footer(main)
    overview(doc, m)
    for number, fn in enumerate((q1, q2, q3, q4, q5, q6, q7, q8), 1):
        doc.add_page_break()
        fn(doc, m[f"q{number}"])
    for fn, key in ((q9a, "q9"), (q9b, "q9"), (q10a, "q10"), (q10b, "q10")):
        doc.add_page_break()
        fn(doc, m[key])
    doc.add_page_break(); results(doc, m)
    doc.add_page_break(); execution(doc, m)
    doc.add_page_break(); references(doc)
    update = OxmlElement("w:updateFields")
    update.set(qn("w:val"), "true")
    doc.settings._element.append(update)
    doc.save(output)
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=FINAL)
    args = parser.parse_args()
    print(build(args.output.resolve()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
