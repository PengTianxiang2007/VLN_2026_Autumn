"""Export the recorded Codex TV approach with its original RGB, scene raster and model-response grouping."""
import argparse
import base64
import hashlib
import io
import json
from pathlib import Path

from fontTools import subset
from fontTools.ttLib import TTFont
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "outputs/inverse_rollback/codex_tools_v001/run_20261126_03_tv"
MAP = ROOT / "outputs/offline_route_dataset/v001/run_20261118_01/geometry/kujiale_0036/geometry.json"
CORE = ROOT / "core"


def read(path):
    return json.loads(path.read_bytes())


def uri(kind, content):
    return "data:" + kind + ";base64," + base64.b64encode(content).decode("ascii")


def export(destination):
    summary = read(RUN / "summary.json")
    rows = read(RUN / "call-timeline.json")
    grid = read(MAP)
    width, height = grid["width"], grid["height"]
    raster = base64.b64decode(grid["walkable"].split(",", 1)[1])
    assert Image.open(io.BytesIO(raster)).size == (width, height)

    def project(x, y):
        return [round((x-grid["low"][0])/grid["resolution"], 4),
                round((grid["high"][1]-y)/grid["resolution"], 4)]

    frames = []
    for row in rows:
        png = (RUN / row["png"]).read_bytes()
        assert hashlib.sha256(png).hexdigest() == row["image_sha256"]
        xy = row["after_xyz_m"][:2]
        point = project(*xy)
        assert 0 <= point[0] < width and 0 <= point[1] < height
        frames.append(dict(row, img=uri("image/png", png), point=point))
    assert [f["sequence"] for f in frames] == list(range(1,summary["total_robot_calls"]+1))
    geom = summary["geometry"]
    bounds = {obj["path"]:obj for obj in read(RUN / "operator/objects.json")["objects"]}
    shapes = {}
    for name in ("cabinet","screen"):
        obj = bounds[geom[name]]
        left, top = project(obj["minimum"][0],obj["maximum"][1])
        right, bottom = project(obj["maximum"][0],obj["minimum"][1])
        shapes[name] = [left,top,right-left,bottom-top]

    prompt = (RUN / "source/prompt.txt").read_text().strip()
    prompt_en = ("Control the robot and walk to a position directly in front of the TV cabinet. Face the TV and stop "
                 "about one metre from the cabinet. You may use vlnverse observe() and step(). Decide for yourself when to "
                 "observe, how many steps to take and when to turn. When you judge that you have arrived, end the task and "
                 "briefly describe the visual evidence. If you cannot reach the target, report that honestly.\n\n"
                 "Use only the vlnverse robot tools for this task and finish with a text response. finish_return is reserved "
                 "for returning to A. An image returned by a tool is the robot’s forward view. In Code Mode, you can view "
                 "images with image(...) and read the status with text(...).")
    answer_en = ("I have stopped, facing the TV. The TV is in the centre of the view, the front of the cabinet is "
                 "roughly aligned, and I estimate that I am about one metre from the cabinet.")
    data = dict(frames=frames, summary=summary, grid=dict(img=grid["walkable"], w=width, h=height,
                resolution=grid["resolution"]), shapes=shapes, prompt=[prompt,prompt_en],
                answer=[summary["final_text"],answer_en])
    template = (CORE / "codex_tv_replay.html").read_text()
    theme = (CORE / "roundtrip_comparison.html").read_text().split("<style>",1)[1].split("</style>",1)[0]
    font_cfg = read(CORE / "crossing_visualization_template.json")
    with TTFont(font_cfg["font"], fontNumber=0) as font:
        sub = subset.Subsetter()
        sub.populate(text=template + prompt + prompt_en + summary["final_text"] + answer_en)
        sub.subset(font)
        buffer = io.BytesIO()
        font.save(buffer)
    theme = theme.replace("url(replay.ttf)", "url(" + uri("font/ttf",buffer.getvalue()) + ")")
    page = template.replace("/*__STYLE__*/",theme).replace("/*__DATA__*/",json.dumps(data,ensure_ascii=False,
                             separators=(",",":"),allow_nan=False).replace("</","<\\/"))
    page += "\n<!-- " + Path(font_cfg["font_license"]).read_text().replace("--","—") + " -->\n"
    destination.mkdir(parents=True, exist_ok=False)
    (destination / "index.html").write_text(page)
    sources = [Path(__file__), CORE/"codex_tv_replay.html", CORE/"roundtrip_comparison.html", MAP,
               RUN/"call-timeline.json", RUN/"summary.json", RUN/"operator/objects.json"]
    manifest = dict(calls=len(frames), html_sha256=hashlib.sha256(page.encode()).hexdigest(),
                    sources_sha256={str(path.relative_to(ROOT)):hashlib.sha256(path.read_bytes()).hexdigest()
                                    for path in sources})
    (destination/"export.json").write_text(json.dumps(manifest,indent=2)+"\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination", type=Path)
    export(parser.parse_args().destination)
