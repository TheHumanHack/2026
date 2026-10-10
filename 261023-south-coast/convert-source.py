"""Recreate the deck-local Reveal source from the original PowerPoint (stdlib only).

Text stays editable HTML; source images/video are extracted byte-for-byte. Shapes
are inline SVG, including the organiser's custom logo paths. Run from any folder:
    python 261023-south-coast/convert-source.py
Regeneration overwrites slides.md and source-assets.json, not meta.json.
"""

from pathlib import Path
import hashlib
import html
import json
import posixpath
import re
import zipfile
import xml.etree.ElementTree as ET
from html.parser import HTMLParser

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
SOURCE = HERE / "Human Hack - South Coast 2026.pptx"
ASSETS = ROOT / "content/261023-south-coast"
URL = "https://raw.githubusercontent.com/TheHumanHack/2026/main/content/261023-south-coast/"
TOPIC_GRAPHICS = {
    8: "delivery-constraints.svg",      # #/7
    10: "consulting-mindsets.svg",      # #/9
    11: "decisions-context-1.svg",      # #/9/1
    12: "decisions-context-2.svg",      # #/9/2
    13: "ownership-map-1.svg",          # #/9/3
    14: "ownership-map-2.svg",          # #/9/4
    15: "elastic-leadership.svg",       # #/10
    16: "leadership-stages.svg",        # #/10/1
    17: "situational-leadership.svg",   # #/11
    18: "competence-confidence.svg",    # #/12
    19: "passion-requirement.svg",      # #/13
    20: "motivation-needs.svg",         # #/14
    21: "conflict-management.svg",      # #/15
}
NS = {
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
}
SCALE = 1 / 9525  # 13 1/3 x 7 1/2 inch source -> host's 1280 x 720 canvas
def esc(value, quote=True):
    # Blank lines inside XML image descriptions must not split Markdown HTML.
    return html.escape(value, quote=quote).replace("\r", "").replace("\n", "&#10;")


def find(node, path):
    return node.find(path, NS) if node is not None else None


def all_nodes(node, path):
    return node.findall(path, NS) if node is not None else []


def num(node, key, default=0):
    return float(node.get(key, default)) if node is not None else default


def px(value):
    return float(value) * SCALE


def fmt(value):
    return f"{value:.3f}".rstrip("0").rstrip(".")


def relationships(part):
    parent, name = posixpath.split(part)
    rel = f"{parent}/_rels/{name}.rels"
    if rel not in archive.namelist():
        return {}
    return {
        r.get("Id"): {
            "path": posixpath.normpath(posixpath.join(parent, r.get("Target"))),
            "type": r.get("Type").rsplit("/", 1)[-1],
            "external": r.get("TargetMode") == "External",
        }
        for r in ET.fromstring(archive.read(rel))
    }


def color(node, default="#1D2842"):
    if node is None:
        return default
    c = next((c for c in node if c.tag.rsplit("}", 1)[-1] in
              ("srgbClr", "schemeClr", "sysClr", "prstClr")), None)
    if c is None:
        return default
    tag = c.tag.rsplit("}", 1)[-1]
    raw = c.get("val", "")
    raw = colors.get(raw, "1D2842") if tag == "schemeClr" else c.get("lastClr", raw)
    if tag == "prstClr":
        return raw
    rgb = [int(raw[i:i + 2], 16) for i in (0, 2, 4)]
    for mod in c:
        kind = mod.tag.rsplit("}", 1)[-1]
        v = num(mod, "val") / 100000
        if kind == "tint":
            rgb = [round(t + (255 - t) * v) for t in rgb]
        elif kind == "shade":
            rgb = [round(t * v) for t in rgb]
    alpha = find(c, "a:alpha")
    if alpha is not None:
        return f"rgba({','.join(map(str, rgb))},{fmt(num(alpha, 'val') / 100000)})"
    return "#" + "".join(f"{min(255, max(0, t)):02X}" for t in rgb)


def solid(node, default="none"):
    if find(node, "a:noFill") is not None:
        return "none"
    return color(find(node, "a:solidFill"), default)


def box(shape, inherited=None):
    transform = find(shape, "p:spPr/a:xfrm")
    if transform is None:
        transform = find(inherited, "p:spPr/a:xfrm")
    off, size = find(transform, "a:off"), find(transform, "a:ext")
    return transform, px(num(off, "x")), px(num(off, "y")), px(num(size, "cx")), px(num(size, "cy"))


def custom_geometry(geom, w, h):
    """Translate the actual source move/line/Bezier paths, without redrawing logos."""
    result = []
    for path in all_nodes(geom, "a:pathLst/a:path"):
        pw, ph = num(path, "w", w), num(path, "h", h)
        points = []
        for command in path:
            tag = command.tag.rsplit("}", 1)[-1]
            ps = [(num(p, "x") * w / pw, num(p, "y") * h / ph)
                  for p in command if p.tag.endswith("}pt")]
            if tag == "close":
                points.append("Z")
            elif tag in ("moveTo", "lnTo", "cubicBezTo", "quadBezTo"):
                letter = {"moveTo": "M", "lnTo": "L", "cubicBezTo": "C", "quadBezTo": "Q"}[tag]
                points.append(letter + " ".join(f"{fmt(x)},{fmt(y)}" for x, y in ps))
            else:
                raise ValueError(f"Unsupported custom path: {tag}")
        result.append(f'<path d="{" ".join(points)}"' +
                      (' fill="none"' if path.get("fill") == "none" else '') + "/>")
    return "".join(result)


def vector(shape, w, h):
    props = find(shape, "p:spPr")
    geom = find(props, "a:prstGeom")
    custom = find(props, "a:custGeom")
    if geom is None and custom is None:
        return ""
    fill = solid(props)
    line = find(props, "a:ln")
    stroke = solid(line) if line is not None else "none"
    width = px(num(line, "w", 12700))
    if fill == stroke == "none":
        return ""
    kind = geom.get("prst") if geom is not None else "custom"
    if kind == "custom":
        drawing = custom_geometry(custom, w, h)
    elif kind in ("rect", "roundRect"):
        radius = min(w, h) * .12 if kind == "roundRect" else 0
        drawing = f'<rect width="{fmt(w)}" height="{fmt(h)}" rx="{fmt(radius)}"/>'
    elif kind == "ellipse":
        drawing = f'<ellipse cx="{fmt(w / 2)}" cy="{fmt(h / 2)}" rx="{fmt(w / 2)}" ry="{fmt(h / 2)}"/>'
    elif kind == "triangle":
        drawing = f'<path d="M{fmt(w / 2)},0 L{fmt(w)},{fmt(h)} L0,{fmt(h)} Z"/>'
    elif kind in ("line", "straightConnector1"):
        drawing = f'<path d="M0,0 L{fmt(w)},{fmt(h)}"/>'
    else:
        raise ValueError(f"Unsupported shape: {kind}")
    dash = find(line, "a:prstDash")
    dashed = ' stroke-dasharray="6 5"' if dash is not None and dash.get("val") != "solid" else ""
    # Arrowheads on the source leadership/context axes.
    arrow = find(line, "a:tailEnd")
    head = find(line, "a:headEnd")
    definitions = ""
    attrs = ""
    if any(a is not None and a.get("type", "none") != "none" for a in (head, arrow)):
        marker = f"arrow-{slide_number}-{shape_id(shape)}"
        definitions = f'<defs><marker id="{marker}" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto-start-reverse" markerUnits="strokeWidth"><path d="M0,0 L8,4 L0,8 Z" fill="{stroke}"/></marker></defs>'
        if head is not None and head.get("type", "none") != "none":
            attrs += f' marker-start="url(#{marker})"'
        if arrow is not None and arrow.get("type", "none") != "none":
            attrs += f' marker-end="url(#{marker})"'
    return f'<svg class="sc-vector" width="{fmt(max(w, 1))}" height="{fmt(max(h, 1))}" viewBox="0 0 {fmt(max(w, 1))} {fmt(max(h, 1))}" aria-hidden="true">{definitions}<g fill="{fill}" stroke="{stroke}" stroke-width="{fmt(width)}"{dashed}{attrs}>{drawing}</g></svg>'


def shape_id(shape):
    return find(shape, ".//p:cNvPr").get("id")


def text(shape, inherited=None):
    body = find(shape, "p:txBody")
    if body is None or not any(t.text for t in all_nodes(body, ".//a:t")):
        return ""
    body_props = find(body, "a:bodyPr")
    padding = [px(num(body_props, k, d)) for k, d in
               (("tIns", 45720), ("rIns", 91440), ("bIns", 45720), ("lIns", 91440))]
    anchor = {"ctr": "center", "b": "flex-end"}.get(body_props.get("anchor") if body_props is not None else None, "flex-start")
    paras = []
    for para in all_nodes(body, "a:p"):
        pp = find(para, "a:pPr")
        default = find(pp, "a:defRPr")
        if default is None:
            default = find(body, "a:lstStyle/a:lvl1pPr/a:defRPr")
        if default is None:
            default = find(inherited, "p:txBody/a:lstStyle/a:lvl1pPr/a:defRPr")
        spans = []
        largest = 0
        for run in para:
            if run.tag.endswith("}br"):
                spans.append("<br>")
                continue
            t = find(run, "a:t")
            if t is None:
                continue
            rp = find(run, "a:rPr")
            def attr(key, fallback):
                return rp.get(key, default.get(key, fallback) if default is not None else fallback) if rp is not None else default.get(key, fallback) if default is not None else fallback
            size = float(attr("sz", "1800")) / 100 * 4 / 3
            largest = max(largest, size)
            c = color(find(rp, "a:solidFill"), color(find(default, "a:solidFill")))
            font = find(rp, "a:latin")
            if font is None:
                font = find(default, "a:latin")
            face = font.get("typeface") if font is not None else "Krona One"
            if face.startswith("+"):
                face = "Calibri"
            style = f"font-size:{fmt(size)}px;color:{c};font-family:'{esc(face, quote=True)}','Segoe UI',Arial,sans-serif;font-weight:{'700' if attr('b', '0') == '1' else '400'};"
            if attr("i", "0") == "1":
                style += "font-style:italic;"
            if attr("u", "none") != "none":
                style += "text-decoration:underline;"
            spans.append(f'<span style="{style}">{esc(t.text or "")}</span>')
        align = {"ctr": "center", "r": "right", "just": "justify"}.get(pp.get("algn") if pp is not None else None, "left")
        before = num(find(pp, "a:spcBef/a:spcPts"), "val") / 100 * 4 / 3
        after = num(find(pp, "a:spcAft/a:spcPts"), "val") / 100 * 4 / 3
        line = num(find(pp, "a:lnSpc/a:spcPct"), "val", 110000) / 100000
        bullet = find(pp, "a:buChar")
        if bullet is not None:
            spans.insert(0, esc(bullet.get("char", "•")) + " ")
        paras.append(f'<p style="text-align:{align};margin:{fmt(before)}px 0 {fmt(after)}px;line-height:{fmt(line)};font-size:{fmt(largest or 24)}px">{"".join(spans) or "<br>"}</p>')
    return f'<div class="sc-text" style="padding:{" ".join(fmt(p) + "px" for p in padding)};justify-content:{anchor}">{"".join(paras)}</div>'


def placeholder(shape):
    ph = find(shape, ".//p:ph")
    return (ph.get("type", "body"), ph.get("idx", "0")) if ph is not None else None


def render(shape, rels, inherited=None, layer="slide"):
    tag = shape.tag.rsplit("}", 1)[-1]
    if tag == "grpSp":
        xf = find(shape, "p:grpSpPr/a:xfrm")
        off, ext = find(xf, "a:off"), find(xf, "a:ext")
        child_off, child_ext = find(xf, "a:chOff"), find(xf, "a:chExt")
        sx = num(ext, "cx") / max(num(child_ext, "cx"), 1)
        sy = num(ext, "cy") / max(num(child_ext, "cy"), 1)
        tx = px(num(off, "x") - num(child_off, "x") * sx)
        ty = px(num(off, "y") - num(child_off, "y") * sy)
        inside = "".join(render(s, rels, layer=layer) for s in shape)
        return f'<div class="sc-group" style="transform:translate({fmt(tx)}px,{fmt(ty)}px) scale({fmt(sx)},{fmt(sy)})">{inside}</div>'
    if tag == "graphicFrame":
        table = find(shape, "a:graphic/a:graphicData/a:tbl")
        if table is None:
            raise ValueError("Unsupported graphic frame")
        xf = find(shape, "p:xfrm")
        off, extent = find(xf, "a:off"), find(xf, "a:ext")
        x, y = px(num(off, "x")), px(num(off, "y"))
        w, h = px(num(extent, "cx")), px(num(extent, "cy"))
        columns = [px(num(c, "w")) for c in all_nodes(table, "a:tblGrid/a:gridCol")]
        cells = []
        row_y = 0
        for row in all_nodes(table, "a:tr"):
            row_h = px(num(row, "h"))
            cell_x = 0
            for index, cell in enumerate(all_nodes(row, "a:tc")):
                props = find(cell, "a:tcPr")
                # Reuse text conversion after adapting table DrawingML to a shape.
                proxy = ET.Element("{" + NS["p"] + "}sp")
                body = ET.fromstring(ET.tostring(find(cell, "a:txBody")))
                body.tag = "{" + NS["p"] + "}txBody"
                body_props = find(body, "a:bodyPr")
                body_props.set("anchor", props.get("anchor", "ctr"))
                for target, source_attr in (("lIns", "marL"), ("rIns", "marR"), ("tIns", "marT"), ("bIns", "marB")):
                    body_props.set(target, props.get(source_attr, "0"))
                proxy.append(body)
                cells.append(f'<div class="sc-object" style="left:{fmt(cell_x)}px;top:{fmt(row_y)}px;width:{fmt(columns[index])}px;height:{fmt(row_h)}px;background:{solid(props, "#FFFFFF")};border-bottom:1px solid #D8E5EA">{text(proxy)}</div>')
                cell_x += columns[index]
            row_y += row_h
        return f'<div class="sc-object" data-source-shape="{layer}-{shape_id(shape)}" style="left:{fmt(x)}px;top:{fmt(y)}px;width:{fmt(w)}px;height:{fmt(h)}px">{"".join(cells)}</div>'
    if tag not in ("sp", "pic", "cxnSp"):
        return ""
    xf, x, y, w, h = box(shape, inherited)
    if not w and not h:
        return ""
    content = ""
    if tag == "pic":
        video = find(shape, ".//a:videoFile")
        blip = find(shape, "p:blipFill/a:blip")
        target = rels.get(blip.get(f"{{{NS['r']}}}embed"), {}) if blip is not None else {}
        image_url = URL + posixpath.basename(target.get("path", ""))
        info = find(shape, ".//p:cNvPr")
        alt = " ".join(info.get("title", info.get("descr", info.get("name", ""))).split()).replace(chr(34), chr(39))
        if video is not None:
            video_part = rels[video.get(f"{{{NS['r']}}}link")]["path"]
            content = f'<video class="sc-media" data-autoplay muted loop playsinline controls preload="metadata" poster="{image_url}" src="{URL + posixpath.basename(video_part)}" aria-label="{esc(alt)}"></video>'
        else:
            crop = find(shape, "p:blipFill/a:srcRect")
            l, t, r, b = [num(crop, k) / 100000 for k in ("l", "t", "r", "b")]
            width, height = 100 / (1 - l - r), 100 / (1 - t - b)
            style = f"width:{fmt(width)}%;height:{fmt(height)}%;left:{fmt(-l * width)}%;top:{fmt(-t * height)}%;"
            geom = find(shape, "p:spPr/a:prstGeom")
            # Contributor portraits use custom rounded paths in the source.
            rounded = "border-radius:12px;" if find(shape, "p:spPr/a:custGeom") is not None else "border-radius:50%;" if geom is not None and geom.get("prst") == "ellipse" else ""
            content = f'<div class="sc-picture" style="{rounded}"><img style="{style}" src="{image_url}" alt="{esc(alt)}"></div>'
    else:
        content = vector(shape, w, h) + text(shape, inherited)
    if not content:
        return ""
    rotation = num(xf, "rot") / 60000
    flip_x = -1 if xf is not None and xf.get("flipH") == "1" else 1
    flip_y = -1 if xf is not None and xf.get("flipV") == "1" else 1
    transform = f"transform:rotate({fmt(rotation)}deg) scale({flip_x},{flip_y});" if rotation or flip_x * flip_y != 1 or flip_x == -1 else ""
    return f'<div class="sc-object" data-source-shape="{layer}-{shape_id(shape)}" data-id="sc-{layer}-{shape_id(shape)}" style="left:{fmt(x)}px;top:{fmt(y)}px;width:{fmt(w)}px;height:{fmt(h)}px;{transform}">{content}</div>'


STYLE = """<style>
/* Rapport: assemble the six SVG layers from the foundation upward. */
.reveal .slides section.sc-261023 .sc-rapport-graphic { position:absolute; left:56px; top:155px; width:1168px; height:500px; }
.reveal .slides section.sc-261023 .sc-rapport-svg { display:block; width:100%; height:100%; overflow:visible; }
.reveal .slides section.sc-261023.present > .sc-canvas:not(.sc-hub-canvas) .sc-rapport-tier { animation:sc-rapport-build .7s cubic-bezier(.16,1,.3,1) backwards; animation-delay:calc(.15s + var(--sc-rapport-order) * .13s); transform-box:fill-box; transform-origin:center; }
.reveal .slides section.sc-261023.present > .sc-canvas:not(.sc-hub-canvas) .sc-rapport-trust { animation:sc-rapport-trust-in .4s ease-out 1.05s backwards; }
.reveal .slides section.sc-261023.present > .sc-canvas:not(.sc-hub-canvas) .sc-rapport-trust-line { stroke-dasharray:1; animation:sc-rapport-draw .65s ease-out 1.05s backwards; }
@keyframes sc-rapport-build { from { opacity:0; transform:translateY(45px) scale(.94); } to { opacity:1; transform:translateY(0) scale(1); } }
@keyframes sc-rapport-trust-in { from { opacity:0; } to { opacity:1; } }
@keyframes sc-rapport-draw { from { stroke-dashoffset:1; } to { stroke-dashoffset:0; } }
.reveal.overview .slides section.sc-261023 .sc-rapport-svg * { animation:none !important; }
@media (prefers-reduced-motion:reduce) { .reveal .slides section.sc-261023 .sc-rapport-svg * { animation:none !important; } }
/* Consulting mindset (#/9): consistent framing across all five views. */
.reveal .slides section.sc-261023.sc-mindset .sc-mindset-title p { font-size:32px !important; line-height:1.25 !important; }
.reveal .slides section.sc-261023.sc-mindset .sc-mindset-title span { font-size:32px !important; color:#1BDBB0 !important; }
.reveal .slides section.sc-261023.sc-mindset .sc-mindset-subtitle { left:55.392px !important; top:183.6px !important; }
.reveal .slides section.sc-261023.sc-mindset .sc-mindset-subtitle p, .reveal .slides section.sc-261023.sc-mindset .sc-mindset-subtitle span { font-size:18px !important; color:#1D2842 !important; }
.reveal .slides section.sc-261023.sc-mindset .sc-mindset-role p:first-child, .reveal .slides section.sc-261023.sc-mindset .sc-mindset-role p:first-child span { font-size:calc(20px / var(--sc-focus-scale)) !important; line-height:1.15 !important; }
.reveal .slides section.sc-261023.sc-mindset .sc-mindset-mercenary p:first-child span { color:#008BEF !important; }
.reveal .slides section.sc-261023.sc-mindset .sc-mindset-missionary p:first-child span { color:#00AD91 !important; }
.reveal .slides section.sc-261023.sc-mindset .sc-mindset-role p:not(:first-child), .reveal .slides section.sc-261023.sc-mindset .sc-mindset-role p:not(:first-child) span { font-size:calc(18px / var(--sc-focus-scale)) !important; line-height:1.25 !important; }
.reveal .slides section.sc-261023.sc-mindset .sc-mindset-role-detail p, .reveal .slides section.sc-261023.sc-mindset .sc-mindset-role-detail span { font-size:calc(16px / var(--sc-focus-scale)) !important; color:#1D2842 !important; }
.reveal .slides section.sc-261023.sc-mindset .sc-mindset-role-detail--axis { top:var(--sc-axis-detail-top,344px) !important; }
.reveal .slides section.sc-261023.sc-mindset .sc-mindset-summary { left:55.392px !important; top:582px !important; width:1120px !important; height:72px !important; }
.reveal .slides section.sc-261023.sc-mindset .sc-mindset-summary p, .reveal .slides section.sc-261023.sc-mindset .sc-mindset-summary span { font-size:18px !important; line-height:1.35 !important; color:#1D2842 !important; }
@font-face { font-family:'Krona One'; src:url('https://raw.githubusercontent.com/TheHumanHack/2026/main/content/261023-south-coast/fonts/KronaOne-Regular.ttf') format('truetype'); font-weight:400; font-style:normal; font-display:swap; }
.reveal .slides section.sc-261023 { padding:0; width:100%; height:100%; text-align:left; }
.reveal .slides section.sc-261023 .sc-canvas { position:absolute; width:100%; height:100%; inset:0; overflow:hidden; container-type:size; }
.reveal .slides section.sc-261023 .sc-artboard { position:absolute; left:50%; top:50%; width:1280px; height:720px; transform-origin:center; transform:translate(-50%,-50%) scale(min(calc(100cqw / 1280px),calc(100cqh / 720px))); }
.reveal .slides section.sc-261023 .sc-object { position:absolute; box-sizing:border-box; }
.reveal .slides section.sc-261023 .sc-group { position:absolute; inset:0; transform-origin:top left; }
.reveal .slides section.sc-261023 .sc-vector { position:absolute; inset:0; max-width:none; max-height:none; overflow:visible; }
.reveal .slides section.sc-261023 .sc-text { position:absolute; inset:0; display:flex; flex-direction:column; box-sizing:border-box; }
.reveal .slides section.sc-261023 .sc-text p { padding:0; letter-spacing:normal; text-transform:none; white-space:pre-wrap; overflow-wrap:normal; font-family:'Krona One','Segoe UI',Arial,sans-serif; }
.reveal .slides section.sc-261023 .sc-picture { position:absolute; inset:0; overflow:hidden; }
.reveal .slides section.sc-261023 .sc-picture img { position:absolute; max-width:none; max-height:none; margin:0; border:0; box-shadow:none; object-fit:fill; }
.reveal .slides section.sc-261023 .sc-media { width:100%; height:100%; max-width:none; max-height:none; margin:0; object-fit:contain; }
/* Shared event header: one geometry and font hierarchy on every slide. */
.reveal .slides section.sc-261023 .sc-event-header { position:absolute; left:906px; top:21px; width:350px; height:120px; padding:13px; box-sizing:border-box; display:flex; align-items:center; gap:19px; background:#FFF; border-radius:12px; color:#1D2842; z-index:2; }
.reveal .slides section.sc-261023 .sc-event-header-copy { flex:1; min-width:0; text-align:right; font-family:'Krona One','Segoe UI',Arial,sans-serif; }
.reveal .slides section.sc-261023 .sc-event-header-name { display:block; font-size:13.333px; line-height:1.4; font-weight:400; letter-spacing:normal; }
.reveal .slides section.sc-261023 .sc-event-header-date { display:block; margin-top:6px; font-size:10.667px; line-height:1.4; font-weight:400; letter-spacing:normal; }
.reveal .slides section.sc-261023 img.sc-event-header-logo { position:static; display:block; flex:none; width:98px; height:94px; object-fit:contain; max-width:none; max-height:none; margin:0; border:0; box-shadow:none; }
/* Community uses the same mint heading and compact branded footer. */
.reveal .slides section.sc-261023 .sc-community-heading { position:absolute; left:56px; top:50px; margin:0; color:#1BDBB0; font:36px/1.3 'Krona One','Segoe UI',sans-serif; text-transform:none; }
.reveal .slides section.sc-261023 .sc-community-photos { position:absolute; left:56px; top:155px; width:1168px; height:469px; box-sizing:border-box; padding:20px; display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:16px; overflow:hidden; border:1px solid #DCE9ED; border-top:4px solid #1BDBB0; border-radius:18px; background:linear-gradient(135deg,#F4F8FA,#EAF8F4); }
.reveal .slides section.sc-261023 .sc-community-photos img { display:block; width:100%; height:100%; min-height:0; margin:0; object-fit:cover; border-radius:12px; }
.reveal:has(.sc-261023) .controls { color:#008BEF; }
.reveal:has(.sc-261023) .progress { color:#1BDBB0; }
.reveal .slides section.sc-261023[data-slide-hub] > .sc-canvas:not(.sc-hub-canvas) { display:none; }
.reveal .slides section.sc-261023 .sc-hub-panel { position:absolute; inset:0; padding:36px 48px; background:linear-gradient(180deg,rgba(7,16,31,.85),rgba(7,16,31,.45)); }
.reveal .slides section.sc-261023 .sc-hub-panel h2 { margin:0 0 12px; color:#1BDBB0; font:36px 'Krona One','Segoe UI',sans-serif; text-transform:none; }
.reveal .slides section.sc-261023 .sc-hub-panel > p { margin:0 0 28px; color:#fff; font:18px 'Segoe UI',sans-serif; }
.reveal .slides section.sc-261023 .sc-hub-grid { display:grid; grid-template-columns:repeat(5,minmax(0,1fr)); gap:24px 18px; }
.reveal .slides section.sc-261023 a.sc-hub-card { display:block; overflow:hidden; color:#fff; border:1px solid rgba(27,219,176,.65); border-radius:12px; background:rgba(16,36,66,.94); text-decoration:none; box-shadow:0 10px 24px #0005; transition:transform .25s ease,box-shadow .25s ease,border-color .25s ease; }
.reveal .slides section.sc-261023 a.sc-hub-card:hover, .reveal .slides section.sc-261023 a.sc-hub-card:focus-visible { transform:translateY(-8px) scale(1.03); border-color:#1BDBB0; box-shadow:0 16px 34px #0009,0 0 20px #1BDBB044; outline:3px solid #1BDBB0; outline-offset:3px; }
.reveal .slides section.sc-261023 .sc-hub-card > span { display:flex; align-items:center; min-height:62px; padding:8px 12px; box-sizing:border-box; font:14px/1.4 'Krona One','Segoe UI',sans-serif; }
.reveal .slides section.sc-261023 .sc-hub-footer { position:absolute; bottom:30px; left:48px; right:48px; display:flex; justify-content:space-between; color:#fff; font:15px 'Segoe UI',sans-serif; }
.reveal .slides section.sc-261023 .sc-topic-focus { position:absolute; inset:0; transform-origin:top left; }
.reveal .slides section.sc-261023 .sc-topic-footer { position:absolute; left:0; top:645px; width:1280px; height:75px; background:#102442; }
.reveal .slides section.sc-261023 .sc-footer-art { position:absolute; inset:0; transform-origin:top left; transform:translateY(-299.08px) scale(.52); }
/* Sponsor and contributor slides, plus topics, branches and discussion. */
.reveal .slides section.sc-261023.sc-slim-footer .sc-topic-footer { top:668px; height:52px; background:#102442 url('https://raw.githubusercontent.com/TheHumanHack/2026/main/content/261023-south-coast/image1.png') center / 100% 100% no-repeat; }
.reveal .slides section.sc-261023.sc-slim-footer .sc-topic-footer::before { content:''; position:absolute; left:34.36%; top:0; width:40.15%; height:100%; background:url('https://raw.githubusercontent.com/TheHumanHack/2026/main/content/261023-south-coast/image2.png') center / 100% 100% no-repeat; }
.reveal .slides section.sc-261023.sc-slim-footer .sc-footer-logo { position:absolute; top:50%; transform:translateY(-50%); }
.reveal .slides section.sc-261023.sc-slim-footer .sc-footer-logo-art { position:absolute; inset:0; transform-origin:top left; }
.reveal .slides section.sc-261023.sc-slim-footer .sc-footer-logo--south-coast { left:56px; width:135.309px; height:35.805px; }
.reveal .slides section.sc-261023.sc-slim-footer .sc-footer-logo--south-coast .sc-footer-logo-art { transform:scale(.58) translate(-56.693px,-611.421px); }
.reveal .slides section.sc-261023.sc-slim-footer .sc-footer-logo--meetup { left:582.467px; width:115.066px; height:31.270px; }
.reveal .slides section.sc-261023.sc-slim-footer .sc-footer-logo--meetup .sc-footer-logo-art { transform:scale(.58) translate(-537.174px,-612.270px); }
.reveal .slides section.sc-261023.sc-slim-footer .sc-footer-logo--microsoft { right:56px; width:125.257px; height:26.785px; }
.reveal .slides section.sc-261023.sc-slim-footer .sc-footer-logo--microsoft .sc-footer-logo-art { transform:scale(.58) translate(-1007.512px,-620.025px); }
.reveal .slides section.sc-261023.sc-slim-footer .slide-portal-return { left:905px; right:auto; top:694px; transform:translate(-50%,-50%); padding:7px 12px; font-size:13px; }
.reveal .slides section.sc-261023.sc-slim-footer .slide-portal-depth { left:365px; right:auto; top:694px; transform:translate(-50%,-50%); padding:7px 12px; font-size:13px; }
.reveal .slides section.sc-261023.sc-slim-footer .sc-hub-footer { bottom:68px; }
.reveal:has(.slides section.sc-slim-footer.present) .controls { bottom:calc(7.2222% + 12px); }
.reveal .slides section.sc-261023.present > .sc-hub-canvas .sc-hub-card { animation:sc-topic-arrival .75s cubic-bezier(.16,1,.3,1) backwards; animation-delay:calc(var(--topic-order,0) * .075s); }
.reveal .slides section.sc-261023 .sc-hub-card:nth-child(2) { --topic-order:1; }
.reveal .slides section.sc-261023 .sc-hub-card:nth-child(3) { --topic-order:2; }
.reveal .slides section.sc-261023 .sc-hub-card:nth-child(4) { --topic-order:3; }
.reveal .slides section.sc-261023 .sc-hub-card:nth-child(5) { --topic-order:4; }
.reveal .slides section.sc-261023 .sc-hub-card:nth-child(6) { --topic-order:5; }
.reveal .slides section.sc-261023 .sc-hub-card:nth-child(7) { --topic-order:6; }
.reveal .slides section.sc-261023 .sc-hub-card:nth-child(8) { --topic-order:7; }
.reveal .slides section.sc-261023 .sc-hub-card:nth-child(9) { --topic-order:8; }
.reveal .slides section.sc-261023 .sc-hub-card:nth-child(10) { --topic-order:9; }
@keyframes sc-topic-arrival {
  from { opacity:0; transform:perspective(900px) translate3d(0,100px,-180px) rotateX(18deg) scale(.8); }
  to { opacity:1; transform:perspective(900px) translate3d(0,0,0) rotateX(0) scale(1); }
}
.reveal .slides section.sc-261023 .sc-bio-heading { position:absolute; left:56px; top:50px; margin:0; color:#1BDBB0; font:36px/1.3 'Krona One','Segoe UI',sans-serif; text-transform:none; }
.reveal .slides section.sc-261023 .sc-bio-panel { position:absolute; left:56px; top:150px; width:280px; height:474px; border-radius:26px; background:linear-gradient(150deg,#1D2842,#102442); border-top:5px solid #1BDBB0; box-shadow:0 14px 30px #1D28421A; }
.reveal .slides section.sc-261023 img.sc-bio-photo { position:absolute; margin:0; max-width:none; max-height:none; background:#FFF; border:3px solid #FFF; box-sizing:border-box; box-shadow:0 5px 15px #1D284218; }
.reveal .slides section.sc-261023 .sc-bio-roster-current { position:absolute; top:54px; width:52px; height:52px; border-radius:50%; background:#1BDBB0; color:#1D2842; display:grid; place-items:center; font:18px 'Krona One','Segoe UI',sans-serif; }
.reveal .slides section.sc-261023 .sc-bio-connect { position:absolute; left:76px; top:422px; width:240px; text-align:center; }
.reveal .slides section.sc-261023 .sc-bio-connect h3 { color:#FFF; margin:0 0 12px; font:13px 'Krona One','Segoe UI',sans-serif; letter-spacing:.08em; text-transform:uppercase; }
.reveal .slides section.sc-261023 .sc-bio-qr-row { display:flex; gap:12px; align-items:center; justify-content:center; }
.reveal .slides section.sc-261023 .sc-bio-qr-row img { display:block; margin:0; width:114px; height:114px; object-fit:contain; background:#FFF; border:7px solid #FFF; border-radius:10px; box-sizing:border-box; }
.reveal .slides section.sc-261023 .sc-bio-qr-row img:only-child { width:144px; height:144px; }
.reveal .slides section.sc-261023 .sc-bio-company { margin:12px auto 0; height:39px; padding:5px 12px; background:#FFF; border-radius:8px; box-sizing:border-box; }
.reveal .slides section.sc-261023 .sc-bio-company img { display:block; margin:0; width:100%; height:29px; max-height:100%; object-fit:contain; }
.reveal .slides section.sc-261023 .sc-bio-identity { position:absolute; left:380px; top:150px; width:844px; }
.reveal .slides section.sc-261023 .sc-bio-identity h2 { margin:0 0 18px; color:#1D2842; font:46px/1.2 'Krona One','Segoe UI',sans-serif; text-transform:none; letter-spacing:-.03em; }
.reveal .slides section.sc-261023 .sc-bio-identity p { margin:0; color:#008BEF; font:19px/1.5 'Krona One','Segoe UI',sans-serif; }
.reveal .slides section.sc-261023 .sc-bio-summary { position:absolute; left:380px; top:272px; width:844px; }
.reveal .slides section.sc-261023 .sc-bio-summary p { margin:0; color:#1D2842; font:18px/1.65 'Krona One','Segoe UI',sans-serif; }
.reveal .slides section.sc-261023 .sc-bio-card { position:absolute; padding:24px; border-radius:18px; box-sizing:border-box; border:1px solid #DCE9ED; background:#F4F8FA; }
.reveal .slides section.sc-261023 .sc-bio-focus { left:380px; width:400px; border-top:4px solid #1BDBB0; }
.reveal .slides section.sc-261023 .sc-bio-awards { left:800px; width:424px; border-top:4px solid #008BEF; }
.reveal .slides section.sc-261023 .sc-bio-card h3 { margin:0 0 16px; color:#008BEF; font:13px 'Krona One','Segoe UI',sans-serif; letter-spacing:.06em; text-transform:uppercase; }
.reveal .slides section.sc-261023 .sc-bio-card ul { display:block; margin:0; padding:0; list-style:none; }
.reveal .slides section.sc-261023 .sc-bio-card li { margin:0 0 10px; color:#1D2842; font:18px/1.5 'Krona One','Segoe UI',sans-serif; }
.reveal .slides section.sc-261023 .sc-bio-awards--art ul { padding-right:96px; }
.reveal .slides section.sc-261023 .sc-bio-award-art { position:absolute; right:20px; top:57px; width:80px; height:80px; margin:0; object-fit:contain; }
.reveal .slides section.sc-261023 .sc-closing-section.fragment { opacity:0; transform:none; filter:none; transition:none; }
.reveal .slides section.sc-261023 .sc-closing-section.fragment.visible { opacity:1; }
.reveal .slides section.sc-261023 .sc-closing-section.fragment .sc-type-char { opacity:0; }
.reveal .slides section.sc-261023.present .sc-closing-section.fragment.visible .sc-type-char { animation:sc-fast-type 1ms step-end both; animation-delay:calc(var(--sc-type-order) * 6ms); }
@keyframes sc-fast-type { from { opacity:0; } to { opacity:1; } }
.reveal .slides section.sc-261023 .sc-closing-section { position:absolute; inset:0; }
.reveal .slides section.sc-261023 .sc-closing-section .sc-text p { line-height:1.15 !important; }
.reveal .slides section.sc-261023 .sc-closing-section .sc-text span { font-size:25px !important; }
.reveal .slides section.sc-261023 .sc-closing-section [data-source-shape="slide-8"] span, .reveal .slides section.sc-261023 .sc-closing-section [data-source-shape="slide-9"] span, .reveal .slides section.sc-261023 .sc-closing-section [data-source-shape="slide-11"] span { font-size:28px !important; }
@media (prefers-reduced-motion:reduce) {
  .reveal:has(.sc-261023) .slides section, .reveal:has(.sc-261023) .slide-background { transition:none !important; }
  .reveal .slides section.sc-261023 a.sc-hub-card { transition:none; }
  .reveal .slides section.sc-261023 a.sc-hub-card:hover, .reveal .slides section.sc-261023 a.sc-hub-card:focus-visible { transform:none; }
  .reveal .slides section.sc-261023.present > .sc-hub-canvas .sc-hub-card { animation:none; }
  .reveal .slides section.sc-261023 .sc-closing-section.fragment { transition:none; transform:none; filter:none; }
  .reveal .slides section.sc-261023 .sc-closing-section .sc-type-char { opacity:1 !important; animation:none !important; }
  .reveal .slides section.sc-261023 [data-auto-animate-target] { transition:none !important; }
}
</style>"""

STYLE = STYLE.replace("</style>", (ASSETS / "topic-graphics.css").read_text(encoding="utf-8") + "\n</style>")

TOPIC_HUB = """<div class="sc-canvas sc-hub-canvas"><div class="sc-artboard"><div class="sc-hub-panel">
<h2>Discussion topics</h2>
<p data-slide-portal-status role="status">Choose a window to explore a topic. Use &ldquo;Back to topics&rdquo; to return to the fireside.</p>
<nav class="sc-hub-grid" aria-label="Discussion topics">
<a class="sc-hub-card" href="#/8" data-slide-preview="8"><span>Delivery constraints</span></a>
<a class="sc-hub-card" href="#/9" data-slide-preview="9"><span>Rapport</span></a>
<a class="sc-hub-card" href="#/10" data-slide-preview="10"><span>Consulting mindset</span></a>
<a class="sc-hub-card" href="#/11" data-slide-preview="15"><span>Elastic leadership</span></a>
<a class="sc-hub-card" href="#/12" data-slide-preview="17"><span>Situational leadership</span></a>
<a class="sc-hub-card" href="#/13" data-slide-preview="18"><span>Competence and confidence</span></a>
<a class="sc-hub-card" href="#/14" data-slide-preview="19"><span>Passion and requirement</span></a>
<a class="sc-hub-card" href="#/15" data-slide-preview="20"><span>Motivation</span></a>
<a class="sc-hub-card" href="#/16" data-slide-preview="21"><span>Conflict management</span></a>
<a class="sc-hub-card" href="#/17" data-slide-preview="22"><span>Closing thoughts</span></a>
</nav>
<div class="sc-hub-footer"><span>SOUTH COAST USER GROUP &middot; 23RD OCTOBER 2026</span><span>Human Hack &middot; Fireside discussion</span></div>
</div></div></div>"""

EVENT_HEADER = (
    '<div class="sc-event-header" data-id="sc-event-header" role="group" aria-label="Presentation event">'
    '<div class="sc-event-header-copy">'
    '<span class="sc-event-header-name">SOUTH COAST<br>USER GROUP</span>'
    '<span class="sc-event-header-date">23RD OCTOBER 2026</span></div>'
    '<img class="sc-event-header-logo" src="https://raw.githubusercontent.com/TheHumanHack/2026/main/content/261023-south-coast/image38.png" alt="Meetup">'
    '</div>'
)


# Source slide numbers: title (#/0), fireplace (#/6) and topic hub (#/7).
EVENT_HEADER_EXCLUDED_SOURCE_SLIDES = {1, 6, 7}


def community_slide(footer):
    """Retain the added Community slide and its photo-folder marker on conversion."""
    attrs = ('class="sc-261023 sc-slim-footer sc-community" data-community-slide '
             'data-background-color="#FFFFFF" data-transition="fade" '
             'data-background-transition="fade" data-auto-animate '
             'data-auto-animate-id="sc-261023" data-auto-animate-duration="0.8" '
             'data-auto-animate-easing="cubic-bezier(0.16,1,0.3,1)"')
    return (f'<!-- .slide: {attrs} -->\n\n'
            '<div class="sc-canvas"><div class="sc-artboard">'
            '<h1 class="sc-community-heading">Community</h1>'
            '<div class="sc-community-photos" data-photo-folder="https://github.com/itweedie/community-photos/tree/main/for-slides"></div>'
            + footer + EVENT_HEADER + '</div></div>')


def remove_source_event_header(markup):
    """Remove imported top-right event shapes without changing other slide markup."""
    candidates = list(re.finditer(
        r'<div class="sc-object"[^>]*style="left:([-\d.]+)px;top:([-\d.]+)px;[^>]*>', markup))
    for match in reversed(candidates):
        x, y = map(float, match.groups())
        if x < 900 or y >= 140:
            continue
        depth = 0
        for tag in re.finditer(r'<div\b[^>]*>|</div>', markup[match.start():]):
            depth += -1 if tag[0] == '</div>' else 1
            if depth == 0:
                end = match.start() + tag.end()
                item = markup[match.start():end]
                label = re.sub(r'\s+', '', html.unescape(re.sub(r'<[^>]*>', '', item))).upper()
                if label in ('SOUTHCOASTUSERGROUP', '23RDOCTOBER2026') or re.search(r'<img\b[^>]*alt="Meetup', item):
                    markup = markup[:match.start()] + markup[end:]
                break
    return markup


VERTICAL_CHILDREN = {11, 12, 13, 14, 16}
SLIM_FOOTER_SLIDES = {2, 3, 4, 5, *range(7, 24)}


def is_footer_object(item):
    shape = re.search(r'data-source-shape="master-(\d+)"', item)
    position = re.search(r'top:([-\d.]+)px', item)
    return shape is not None and position is not None and float(position[1]) >= 575


def slim_footer(content):
    """Preserve the original logo pieces, scaling each brand independently."""
    items = {int(re.search(r'data-source-shape="master-(\d+)"', item)[1]): item
             for item in filter(None, content) if is_footer_object(item)}
    groups = (("south-coast", "South Coast User Group", range(18, 33)),
              ("meetup", "Meetup", (8,)),
              ("microsoft", "Microsoft", range(36, 45)))
    logos = []
    for name, label, shapes in groups:
        artwork = "".join(items[shape] for shape in shapes)
        logos.append(f'<div class="sc-footer-logo sc-footer-logo--{name}" role="img" aria-label="{label}"><div class="sc-footer-logo-art">{artwork}</div></div>')
    return '<div class="sc-topic-footer">' + "".join(logos) + '</div>'


CONTRIBUTOR_FIELDS = {
    3: {"name": 4, "role": 5, "bio": 6, "focus": 7, "awards": 8, "photo": 11, "qr": (15, 2), "badge": 17, "logo": 10, "header": (21, 22, 23)},
    4: {"name": 18, "role": 20, "focus": 24, "awards": 26, "photo": 14, "qr": (30,), "badge": 31, "header": (35, 36, 37)},
    5: {"name": 4, "role": 5, "bio": 6, "focus": 7, "awards": 8, "photo": 13, "qr": (12,), "header": (17, 18, 19)},
}


class ContributorParts(HTMLParser):
    def __init__(self):
        super().__init__()
        self.paragraphs, self.images = [], []
        self.paragraph = None

    def handle_starttag(self, tag, attributes):
        if tag == "p":
            self.paragraph = ""
        elif tag == "br" and self.paragraph is not None:
            self.paragraph += "\n"
        elif tag == "img":
            self.images.append(dict(attributes)["src"])

    def handle_data(self, value):
        if self.paragraph is not None:
            self.paragraph += value

    def handle_endtag(self, tag):
        if tag == "p" and self.paragraph is not None:
            self.paragraphs.append(self.paragraph)
            self.paragraph = None


def contributor_content(content, number):
    """Keep source copy/media in a coordinated profile layout and animated roster."""
    fields = CONTRIBUTOR_FIELDS[number]
    items = {re.search(r'data-source-shape="([^"]+)"', item)[1]: item
             for item in filter(None, content)}
    def extract(shape):
        parser = ContributorParts()
        parser.feed(items[f"slide-{shape}"])
        return parser
    def paragraphs(key):
        return extract(fields[key]).paragraphs if key in fields else []
    def image(shape):
        return extract(shape).images[0]
    name = paragraphs("name")[0]
    biography = paragraphs("bio")
    index = number - 3
    roster = (("dan", "Dan Barber", "image33.jpeg"), ("areti", "Areti Iles", "image39.jpeg"), ("ian", "Ian Tweedie", "image42.jpeg"))
    portraits = []
    for position, (key, label, filename) in enumerate(roster):
        active = position == index
        x, y, size = (78, 174, 236) if active else (632 + position * 78, 54, 52)
        # Use square originals/edits for the featured portrait; retain source roster photos.
        if active:
            filename = {"dan": "dan-barber-square.png", "ian": "ian-tweedie-square.jpeg"}.get(key, filename)
        fit = "cover" if active or key == "areti" else "contain"
        portraits.append(f'<img class="sc-bio-photo" data-id="sc-bio-photo-{key}" src="{URL + filename}" alt="{label}" style="left:{x}px;top:{y}px;width:{size}px;height:{size}px;border-radius:{20 if active else 50}px;object-fit:{fit};">')
    qr_images = "".join(f'<img src="{image(shape)}" alt="{esc(name)} ? original connection QR {position + 1}">' for position, shape in enumerate(fields["qr"]))
    logo = f'<div class="sc-bio-company"><img src="{image(fields["logo"])}" alt="{esc(name)} company logo"></div>' if "logo" in fields else ""
    badge = f'<img class="sc-bio-award-art" src="{image(fields["badge"])}" alt="{esc(name)} original award artwork">' if "badge" in fields else ""
    body = "".join(f'<p>{esc(paragraph)}</p>' for paragraph in biography)
    focus = "".join(f'<li>{esc(paragraph)}</li>' for paragraph in paragraphs("focus") for paragraph in paragraph.splitlines())
    awards = "".join(f'<li>{esc(paragraph)}</li>' for paragraph in paragraphs("awards"))
    footer_items = [item for shape, item in items.items() if shape.startswith("master-")]
    footer = (slim_footer(footer_items) if number in SLIM_FOOTER_SLIDES else
              '<div class="sc-topic-footer"><div class="sc-footer-art">' + "".join(footer_items) + '</div></div>')
    header = "".join(items[f"slide-{shape}"] for shape in fields["header"])
    cards_top = 432 if biography else 316
    cards_height = 192 if biography else 308
    return (
        '<h1 class="sc-bio-heading" data-id="sc-bio-heading">Contributors</h1>'
        + header
        + '<div class="sc-bio-panel" data-id="sc-bio-panel"></div>'
        + f'<div class="sc-bio-roster-current" data-id="sc-bio-roster-current" style="left:{632 + index * 78}px">{index + 1:02}</div>'
        + "".join(portraits)
        + '<div class="sc-bio-connect" data-id="sc-bio-connect"><h3>Connect</h3>'
        + f'<div class="sc-bio-qr-row">{qr_images}</div>{logo}</div>'
        + f'<div class="sc-bio-identity"><h2>{esc(name)}</h2><p>{esc(paragraphs("role")[0])}</p></div>'
        + f'<div class="sc-bio-summary">{body}</div>'
        + f'<div class="sc-bio-card sc-bio-focus" data-id="sc-bio-focus" style="top:{cards_top}px;height:{cards_height}px"><h3>Focus</h3><ul class="no-fragment">{focus}</ul></div>'
        + f'<div class="sc-bio-card sc-bio-awards{" sc-bio-awards--art" if badge else ""}" data-id="sc-bio-awards" style="top:{cards_top}px;height:{cards_height}px"><h3>Awards</h3><ul class="no-fragment">{awards}</ul>{badge}</div>'
        + footer
    )


def fast_type_section(section):
    """Stagger characters without changing text layout or Reveal fragment state."""
    order = 0
    def decorate(match):
        nonlocal order
        characters = []
        for character in html.unescape(match[2]):
            characters.append(f'<span class="sc-type-char" style="--sc-type-order:{order}">{esc(character)}</span>')
            order += 1
        opening = match[1][:-1] + f' data-type-text="{esc(html.unescape(match[2]))}">'
        return opening + "".join(characters) + match[3]
    return re.sub(r'(<span\b[^>]*>)([^<]*)(</span>)', decorate, section)


def topic_content(content, number):
    footer, header, focus = [], [], []
    for item in filter(None, content):
        position = re.search(r'left:([-\d.]+)px;top:([-\d.]+)px;width:([-\d.]+)px;height:([-\d.]+)px', item)
        if not position:
            raise ValueError(f"Missing coordinates on slide {number}")
        x, y, w, h = map(float, position.groups())
        shape = re.search(r'data-source-shape="([^"]+)"', item).group(1)
        # Explanatory captions on the leadership branch belong in speaker notes.
        if number in (15, 16) and shape in ({"slide-3", "slide-14"} if number == 15 else {"slide-3"}):
            continue
        # Keep branding and subtitles unscaled; reclaim footer space for the subject.
        if shape.startswith("master-") and y >= 575:
            footer.append(item)
        elif y < 140 or (number in range(11, 17) and shape == "slide-3"):
            header.append(item)
        else:
            focus.append((item, x, y, w, h))

    if number in TOPIC_GRAPHICS:
        # Inline SVG groups keep text editable and let entry animations replay.
        if 10 <= number <= 16:
            # Keep existing explanations in notes, as on the previous layouts.
            if number != 10:
                header = [item for item in header if 'data-source-shape="slide-3"' not in item]
        if number in (*range(10, 17), 19):
            title_shape = "slide-7" if number == 10 else "slide-19" if number == 19 else "slide-2"
            header = [item.replace('class="sc-object"', 'class="sc-object sc-graphic-title"', 1)
                      if f'data-source-shape="{title_shape}"' in item else item for item in header]
        svg = (ASSETS / TOPIC_GRAPHICS[number]).read_text(encoding="utf-8")
        svg = re.sub(r">\s+<", "><", svg.strip())
        return ("".join(header)
                + f'<div class="sc-topic-focus"><div class="sc-diagram-graphic" data-id="sc-topic-graphic-{number}">' + svg + '</div></div>'
                + slim_footer(footer))

    if number == 9:
        # Inline the editable asset so slide entry can animate its SVG groups.
        svg = (ASSETS / "rapport-pyramid.svg").read_text(encoding="utf-8")
        svg = re.sub(r">\s+<", "><", svg.strip())
        return ("".join(header)
                + '<div class="sc-topic-focus"><div class="sc-rapport-graphic" data-id="sc-rapport-pyramid">' + svg + '</div></div>'
                + slim_footer(footer))

    leadership_source = ""
    if number in (15, 16):
        source_shape = "slide-15" if number == 15 else "slide-26"
        source = next(entry for entry in focus if f'data-source-shape="{source_shape}"' in entry[0])
        focus.remove(source)
        leadership_source = re.sub(r'(left:[-\d.]+px;top:)[-\d.]+(px;)',
                                   r'\g<1>610\2', source[0], count=1)
        # Enlarge the diagram vertically and its text without stretching glyphs.
        stretch = 1.8 if number == 15 else 1.2
        anchor = min(y for _, _, y, _, _ in focus)
        expanded = []
        for item, x, y, w, h in focus:
            y = anchor + (y - anchor) * stretch
            if 'class="sc-text"' in item:
                item = re.sub(r'font-size:([\d.]+)px',
                              lambda match: f'font-size:{fmt(float(match[1]) * 1.1)}px', item)
                h *= 1.1
            elif number == 16 and 'data-source-shape="slide-15"' in item:
                item = item.replace(fmt(h), fmt(h * stretch))
                h *= stretch
            item = re.sub(r'(left:[-\d.]+px;top:)[-\d.]+(px;)',
                          lambda match: match[1] + fmt(y) + match[2], item, count=1)
            item = re.sub(r'(width:[-\d.]+px;height:)[-\d.]+(px;)',
                          lambda match: match[1] + fmt(h) + match[2], item, count=1)
            expanded.append((item, x, y, w, h))
        focus = expanded

    chart_properties = ""
    if number in (13, 14):
        # Fill the space freed by the explanatory notes without distorting text/dots.
        stretch = 1.35
        anchor = next(y for item, _, y, _, _ in focus if 'data-source-shape="slide-8"' in item)
        axis_bottom = next(y + h for item, _, y, _, h in focus if 'data-source-shape="slide-6"' in item)
        chart_y = lambda y: anchor + (y - anchor) * stretch
        chart_properties = f'--sc-axis-detail-top:{fmt(chart_y(344))}px;'
        expanded = []
        for item, x, y, w, h in focus:
            shape = re.search(r'data-source-shape="([^"]+)"', item).group(1)
            if shape != "slide-28":
                y = chart_y(y)
                if shape == "slide-9":
                    y = chart_y(axis_bottom) + 14
                if shape == "slide-6":
                    item = item.replace(fmt(h), fmt(h * stretch))
                    h *= stretch
                item = re.sub(r'(left:[-\d.]+px;top:)[-\d.]+(px;)',
                              lambda match: match[1] + fmt(y) + match[2], item, count=1)
            expanded.append((item, x, y, w, h))
        focus = expanded
    bounds = [entry for entry in focus if not (number in (13, 14) and 'data-source-shape="slide-28"' in entry[0])]
    left = min(x for _, x, _, _, _ in bounds)
    top = min(y for _, _, y, _, _ in bounds)
    right = max(x + w for _, x, _, w, _ in bounds)
    bottom = max(y + h for _, _, y, _, h in bounds)
    available_top = 190 if number in range(11, 17) else 145
    if number in (13, 14):
        available_top = 165
    if number in (15, 16):
        available_top = 165
    available_bottom = 590 if number in (15, 16) else 630
    scale = min(1216 / (right - left), (available_bottom - available_top) / (bottom - top))
    dx = 640 - (left + right) * scale / 2
    dy = available_top - top * scale
    if 10 <= number <= 12:
        # Add room below the title without shrinking the text or diagrams.
        dy += 30
    focus_html = "".join(item for item, *_ in focus)
    framing = ""
    if 10 <= number <= 14:
        if number == 10:
            focus_html = focus_html.replace(URL + 'image47.png', URL + 'consulting-balance-blue-teal.png')
        title_shape = "slide-7" if number == 10 else "slide-2"
        header = [item.replace('class="sc-object"', 'class="sc-object sc-mindset-title"', 1)
                  if f'data-source-shape="{title_shape}"' in item else
                  item.replace('class="sc-object"', 'class="sc-object sc-mindset-subtitle"', 1)
                  if number != 10 and 'data-source-shape="slide-3"' in item else item
                  for item in header]
        roles = {10: (4, 3), 11: (16, 18), 12: (16, 18), 13: (10, 12), 14: (10, 12)}[number]
        for shape, role in zip(roles, ("mercenary", "missionary")):
            focus_html = focus_html.replace(f'class="sc-object" data-source-shape="slide-{shape}"',
                                            f'class="sc-object sc-mindset-role sc-mindset-{role}" data-source-shape="slide-{shape}"')
        if number != 10:
            details = (17, 19) if number in (11, 12) else (11, 13)
            detail_class = 'sc-mindset-role-detail' + (' sc-mindset-role-detail--axis' if number in (13, 14) else '')
            for shape in details:
                focus_html = focus_html.replace(f'class="sc-object" data-source-shape="slide-{shape}"',
                                                f'class="sc-object {detail_class}" data-source-shape="slide-{shape}"')
            summary_shape = 20 if number in (11, 12) else 28
            summary = next(item for item, *_ in focus if f'data-source-shape="slide-{summary_shape}"' in item)
            focus_html = focus_html.replace(summary, '')
            framing = summary.replace('class="sc-object"', 'class="sc-object sc-mindset-summary"', 1)
            if number in (11, 12, 13, 14):
                # /9/1 through /9/4 keep the diagram; their explanation is in notes.
                header = [item for item in header if 'data-source-shape="slide-3"' not in item]
                framing = ""
    if number == 22:
        sections = []
        for index, shapes in enumerate((("slide-8", "slide-3"), ("slide-9", "slide-10"), ("slide-11", "slide-12"))):
            # Type the heading before its body, independent of PowerPoint shape order.
            section = "".join(item for shape in shapes for item, *_ in focus
                              if f'data-source-shape="{shape}"' in item)
            sections.append(f'<div class="fragment sc-closing-section" data-fragment-index="{index}">{fast_type_section(section)}</div>')
        focus_html = "".join(sections)
    return (
        "".join(header)
        + f'<div class="sc-topic-focus" style="' + chart_properties + (f'--sc-focus-scale:{fmt(scale)};' if 10 <= number <= 14 else '')
        + f'transform:translate({fmt(dx)}px,{fmt(dy)}px) scale({fmt(scale)});">{focus_html}</div>'
        + framing + leadership_source
        + (slim_footer(footer) if number in SLIM_FOOTER_SLIDES else '<div class="sc-topic-footer"><div class="sc-footer-art">' + "".join(footer) + "</div></div>")
    )


def animation_ids(content, number):
    if number not in (10, 11, 12, 13, 14, 15, 16):
        return content
    prefix = "context" if number in (11, 12) else "ownership" if number in (13, 14) else str(number)
    content = re.sub(r'data-id="sc-slide-(\d+)"', lambda match: f'data-id="sc-{prefix}-{match[1]}"', content)
    shared = {}
    if number in (11, 12):
        shared = {16: "mercenary", 18: "missionary"}
    elif number in (13, 14):
        shared = {10: "mercenary", 12: "missionary"}
    elif number == 15:
        shared = {4: "leadership-line", 5: "leadership-1", 6: "survival", 8: "leadership-2", 9: "learning", 11: "leadership-3", 12: "organizing"}
    elif number == 16:
        shared = {4: "leadership-line", 5: "leadership-1", 6: "survival", 7: "leadership-2", 8: "learning", 9: "leadership-3", 10: "organizing"}
    for shape, name in shared.items():
        content = content.replace(f'data-id="sc-{prefix}-{shape}"', f'data-id="sc-{name}"')
    return content


if __name__ == "__main__":
    ASSETS.mkdir(parents=True, exist_ok=True)
    manifest = {"source": SOURCE.name, "sourceSha256": hashlib.sha256(SOURCE.read_bytes()).hexdigest(), "media": [], "slides": [], "fonts": [
        {"url": URL + "fonts/" + name,
         "source": "https://raw.githubusercontent.com/google/fonts/main/ofl/kronaone/" + name,
         "sha256": hashlib.sha256((ASSETS / "fonts" / name).read_bytes()).hexdigest()}
        for name in ("KronaOne-Regular.ttf", "OFL.txt")
    ]}
    slides = []
    with zipfile.ZipFile(SOURCE) as archive:
        colors = {}
        theme = ET.fromstring(archive.read("ppt/theme/theme1.xml"))
        for c in find(theme, "a:themeElements/a:clrScheme"):
            colors[c.tag.rsplit("}", 1)[-1]] = list(c)[0].get("lastClr", list(c)[0].get("val"))
        master = ET.fromstring(archive.read("ppt/slideMasters/slideMaster1.xml"))
        for key, value in find(master, "p:clrMap").attrib.items():
            colors[key] = colors[value]
        for name in archive.namelist():
            if name.startswith("ppt/media/"):
                data = archive.read(name)
                (ASSETS / posixpath.basename(name)).write_bytes(data)
                manifest["media"].append({"source": name, "url": URL + posixpath.basename(name), "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)})
        presentation = ET.fromstring(archive.read("ppt/presentation.xml"))
        pres_rels = relationships("ppt/presentation.xml")
        ordered = [pres_rels[s.get(f"{{{NS['r']}}}id")]["path"] for s in find(presentation, "p:sldIdLst")]
        for slide_number, part in enumerate(ordered, 1):
            source = ET.fromstring(archive.read(part))
            rels = relationships(part)
            layout_part = next(r["path"] for r in rels.values() if r["type"] == "slideLayout")
            layout = ET.fromstring(archive.read(layout_part))
            layout_rels = relationships(layout_part)
            master_part = next(r["path"] for r in layout_rels.values() if r["type"] == "slideMaster")
            slide_master = ET.fromstring(archive.read(master_part))
            inherited = {placeholder(s): s for s in find(layout, "p:cSld/p:spTree") if placeholder(s)}
            content = []
            # Placeholder date/footer/title examples belong to authoring UI, not the slide.
            if source.get("showMasterSp", "1") != "0" and layout.get("showMasterSp", "1") != "0":
                content.extend(render(s, relationships(master_part), layer="master") for s in find(slide_master, "p:cSld/p:spTree") if placeholder(s) is None)
            content.extend(render(s, layout_rels, layer="layout") for s in find(layout, "p:cSld/p:spTree") if placeholder(s) is None)
            content.extend(render(s, rels, inherited.get(placeholder(s))) for s in find(source, "p:cSld/p:spTree"))
            background = "#FFFFFF"
            for parent in (source, layout, slide_master):
                bg = find(parent, "p:cSld/p:bg/p:bgPr")
                if bg is not None:
                    background = solid(bg, background)
                    break
            title_shape = next((s for s in find(source, "p:cSld/p:spTree") if placeholder(s) and placeholder(s)[0] in ("title", "ctrTitle")), None)
            title = " ".join(t.text or "" for t in all_nodes(title_shape, ".//a:t")) or ("Fireplace With Fire" if slide_number == 6 else f"Slide {slide_number}")
            notes = []
            notes_part = next((r["path"] for r in rels.values() if r["type"] == "notesSlide"), None)
            if notes_part:
                notes_xml = ET.fromstring(archive.read(notes_part))
                for s in all_nodes(notes_xml, "p:cSld/p:spTree/p:sp"):
                    ph = placeholder(s)
                    if ph and ph[0] == "body":
                        notes.extend("".join(t.text or "" for t in all_nodes(p, ".//a:t")) for p in all_nodes(s, "p:txBody/a:p"))
            if slide_number in (11, 12, 13, 14, 15, 16):
                explanations = (3, 20 if slide_number in (11, 12) else 28) if slide_number <= 14 else ((3, 14) if slide_number == 15 else (3,))
                for shape in explanations:
                    explanation = next(item for item in filter(None, content) if f'data-source-shape="slide-{shape}"' in item)
                    parser = ContributorParts()
                    parser.feed(explanation)
                    notes.extend(parser.paragraphs)
            attrs = f'class="sc-261023" data-source-slide="{slide_number}" data-background-color="{background}" data-transition="fade" data-background-transition="fade"'
            hub_footer = slim_footer(content) if slide_number == 7 else ""
            if slide_number == 7:
                attrs = f'class="sc-261023" data-source-slide="7" data-slide-hub data-slide-hub-animate data-background-color="#07101F" data-background-video="{URL}media1.mp4" data-background-video-loop data-background-video-muted data-background-size="contain" data-transition="fade" data-background-transition="fade"'
            if slide_number != 6:
                attrs += ' data-auto-animate data-auto-animate-id="sc-261023" data-auto-animate-duration="0.8" data-auto-animate-easing="cubic-bezier(0.16,1,0.3,1)"'
            if slide_number in CONTRIBUTOR_FIELDS:
                attrs = attrs.replace('class="sc-261023"', 'class="sc-261023 sc-contributor"')
                content = [contributor_content(content, slide_number)]
            if 8 <= slide_number <= 22:
                content = [topic_content(content, slide_number)]
            if 10 <= slide_number <= 14:
                attrs = attrs.replace('class="sc-261023', 'class="sc-261023 sc-mindset', 1)
            if slide_number in (2, 23):
                footer = slim_footer(content)
                content = [item for item in filter(None, content) if not is_footer_object(item)] + [footer]
            if slide_number in SLIM_FOOTER_SLIDES:
                attrs = attrs.replace('class="sc-261023', 'class="sc-261023 sc-slim-footer', 1)
            content = [animation_ids(item, slide_number) for item in content]
            if slide_number in (10, 11, 12, 13, 15):
                h = 10 if slide_number <= 13 else 11
                v = slide_number - 9 if slide_number <= 13 else 1
                content.append(f'<a class="slide-portal-depth" href="#/{h}/{v}" data-slide-next="{slide_number + 1}">Explore deeper &#8595;</a>')
            body = f'<!-- .slide: {attrs} -->\n\n<!-- Source slide {slide_number}: {esc(title)} -->\n\n'
            if slide_number == 1:
                body += STYLE + "\n\n"
            if slide_number == 7:
                body += TOPIC_HUB.replace('</div></div></div>', '</div>' + hub_footer + '</div></div>') + "\n\n"
            event_header = "" if slide_number in EVENT_HEADER_EXCLUDED_SOURCE_SLIDES else EVENT_HEADER
            body += '<div class="sc-canvas"><div class="sc-artboard">' + remove_source_event_header("".join(content)) + event_header + "</div></div>"
            if notes:
                body += "\n\nNotes:\n" + "\n\n".join(esc(n) for n in notes)
            slides.append(body)
            if slide_number == 2:
                slides.append(community_slide(footer))
            manifest["slides"].append({"number": slide_number, "part": part, "title": title, "notes": notes, "text": [t.text or "" for t in all_nodes(source, ".//a:t")]})
    output = slides[0]
    for body in slides[1:]:
        source_number = re.search(r'data-source-slide="(\d+)"', body)
        number = int(source_number[1]) if source_number else None
        separator = "--" if number in VERTICAL_CHILDREN else "---"
        output += f"\n\n{separator}\n\n{body}"
    (HERE / "slides.md").write_text(output + "\n", encoding="utf-8")
    (HERE / "source-assets.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Converted {len(slides)} slides; extracted {len(manifest['media'])} media files.")
