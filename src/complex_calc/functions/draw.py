"""CX II graphics commands for programs: Clear, DrawArc, DrawCircle, DrawLine,
DrawPoly, DrawRect, DrawText, FillArc, FillCircle, FillPoly, FillRect, PlotXY,
SetColor, SetPen, SetWindow, UseBuffer, PaintBuffer.

Drawing area: 318 × 212 pixels, white background, origin top left (until
SetWindow sets a logical window with the origin bottom left).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..core.errors import ArgumentError, DomainError
from ..core.values import ListValue, StringValue
from .registry import builtin, to_float, to_int

WIDTH, HEIGHT = 318, 212


@dataclass
class Canvas:
    ops: list[tuple] = field(default_factory=list)
    color: tuple[int, int, int] = (0, 0, 0)
    thickness: int = 1
    style: int = 1
    window: tuple[float, float, float, float] | None = None  # xmin, xmax, ymin, ymax

    def map_point(self, x: float, y: float) -> tuple[float, float]:
        if self.window is None:
            return x, y
        xmin, xmax, ymin, ymax = self.window
        return (x - xmin) / (xmax - xmin) * WIDTH, HEIGHT - (y - ymin) / (ymax - ymin) * HEIGHT

    def map_size(self, w: float, h: float) -> tuple[float, float]:
        if self.window is None:
            return w, h
        xmin, xmax, ymin, ymax = self.window
        return w / (xmax - xmin) * WIDTH, h / (ymax - ymin) * HEIGHT

    def add(self, kind: str, *data: Any) -> None:
        self.ops.append((kind, self.color, self.thickness, self.style, *data))


def canvas(ctx) -> Canvas:
    session = ctx.session
    if getattr(session, "canvas", None) is None:
        session.canvas = Canvas()
    return session.canvas


def _num(value, label="argument") -> float:
    return to_float(value, label)


def _points(args) -> list[tuple[float, float]]:
    if len(args) == 2 and isinstance(args[0], ListValue) and isinstance(args[1], ListValue):
        xs, ys = list(args[0]), list(args[1])
        if len(xs) != len(ys):
            raise ArgumentError("Dimension mismatch")
        pairs = zip(xs, ys)
    else:
        if len(args) % 2:
            raise ArgumentError("Coordinates must come in x,y pairs")
        pairs = zip(args[0::2], args[1::2])
    return [(_num(x, "x"), _num(y, "y")) for x, y in pairs]


def _rect_args(c: Canvas, x, y, w, h):
    px, py = c.map_point(_num(x, "x"), _num(y, "y"))
    pw, ph = c.map_size(_num(w, "width"), _num(h, "height"))
    if c.window is not None:  # (x,y) is the bottom-left corner in window coordinates
        py -= ph
    return px, py, pw, ph


CMD = dict(command=True)


@builtin("Clear", "Clear [x,y,width,height]", 0, 4, **CMD, summary="Clear the drawing area (or a rectangle)")
def clear_(ctx, *args):
    c = canvas(ctx)
    if not args:
        c.ops.clear()
        c.add("clear", None)
    elif len(args) == 4:
        c.add("clear", _rect_args(c, *args))
    else:
        raise ArgumentError("Clear takes no arguments or x,y,width,height")
    return None


@builtin("DrawLine", "DrawLine x1,y1,x2,y2", 4, **CMD, summary="Draw a line")
def draw_line(ctx, x1, y1, x2, y2):
    c = canvas(ctx)
    c.add("line", [c.map_point(_num(x1), _num(y1)), c.map_point(_num(x2), _num(y2))])
    return None


def _poly(ctx, args, fill: bool):
    c = canvas(ctx)
    points = [c.map_point(x, y) for x, y in _points(args)]
    c.add("polygon" if fill else "polyline", points, fill)
    return None


@builtin("DrawPoly", "DrawPoly xlist,ylist  |  DrawPoly x1,y1,x2,y2,…", 2, 200, **CMD, summary="Draw a polygon")
def draw_poly(ctx, *args):
    return _poly(ctx, args, False)


@builtin("FillPoly", "FillPoly xlist,ylist  |  FillPoly x1,y1,x2,y2,…", 2, 200, **CMD, summary="Fill a polygon")
def fill_poly(ctx, *args):
    return _poly(ctx, args, True)


@builtin("DrawRect", "DrawRect x,y,width,height", 4, **CMD, summary="Draw a rectangle")
def draw_rect(ctx, x, y, w, h):
    c = canvas(ctx)
    c.add("rect", _rect_args(c, x, y, w, h), False)
    return None


@builtin("FillRect", "FillRect x,y,width,height", 4, **CMD, summary="Fill a rectangle")
def fill_rect(ctx, x, y, w, h):
    c = canvas(ctx)
    c.add("rect", _rect_args(c, x, y, w, h), True)
    return None


def _circle(ctx, x, y, r, fill: bool):
    c = canvas(ctx)
    cx, cy = c.map_point(_num(x, "x"), _num(y, "y"))
    rx, ry = c.map_size(_num(r, "radius"), _num(r, "radius"))
    c.add("ellipse", (cx - rx, cy - ry, 2 * rx, 2 * ry), fill)
    return None


@builtin("DrawCircle", "DrawCircle x,y,radius", 3, **CMD, summary="Draw a circle")
def draw_circle(ctx, x, y, r):
    return _circle(ctx, x, y, r, False)


@builtin("FillCircle", "FillCircle x,y,radius", 3, **CMD, summary="Fill a circle")
def fill_circle(ctx, x, y, r):
    return _circle(ctx, x, y, r, True)


def _arc(ctx, x, y, w, h, start, sweep, fill: bool):
    c = canvas(ctx)
    c.add("arc", _rect_args(c, x, y, w, h), _num(start, "startAngle"), _num(sweep, "arcAngle"), fill)
    return None


@builtin("DrawArc", "DrawArc x,y,width,height,startAngle,arcAngle", 6, **CMD, summary="Draw an arc (degrees)")
def draw_arc(ctx, x, y, w, h, start, sweep):
    return _arc(ctx, x, y, w, h, start, sweep, False)


@builtin("FillArc", "FillArc x,y,width,height,startAngle,arcAngle", 6, **CMD, summary="Fill a sector (degrees)")
def fill_arc(ctx, x, y, w, h, start, sweep):
    return _arc(ctx, x, y, w, h, start, sweep, True)


@builtin("DrawText", "DrawText x,y,exprOrString1[,exprOrString2]…", 3, 99, **CMD, summary="Draw text")
def draw_text(ctx, x, y, *values):
    from ..core.formatting import format_value

    c = canvas(ctx)
    text = " ".join(str(v) if isinstance(v, StringValue) else format_value(v, ctx.settings) for v in values)
    c.add("text", c.map_point(_num(x, "x"), _num(y, "y")), text)
    return None


@builtin("PlotXY", "PlotXY x,y,shape", 3, **CMD, summary="Plot a point shape (1–13)")
def plot_xy(ctx, x, y, shape):
    s = to_int(shape, "shape")
    if not 1 <= s <= 13:
        raise DomainError("shape must be 1…13")
    c = canvas(ctx)
    c.add("point", c.map_point(_num(x, "x"), _num(y, "y")), s)
    return None


@builtin("SetColor", "SetColor Red-value,Green-value,Blue-value", 3, **CMD, summary="Set the drawing color")
def set_color(ctx, r, g, b):
    values = tuple(to_int(v, "color") for v in (r, g, b))
    if any(not 0 <= v <= 255 for v in values):
        raise DomainError("Color values must be 0…255")
    canvas(ctx).color = values
    return None


@builtin("SetPen", "SetPen thickness,style", 2, **CMD, summary="Pen thickness (1–3) and style (1 smooth, 2 dotted, 3 dashed)")
def set_pen(ctx, thickness, style):
    t, s = to_int(thickness, "thickness"), to_int(style, "style")
    if not (1 <= t <= 3 and 1 <= s <= 3):
        raise DomainError("thickness and style must be 1…3")
    c = canvas(ctx)
    c.thickness, c.style = t, s
    return None


@builtin("SetWindow", "SetWindow xMin,xMax,yMin,yMax", 4, **CMD, summary="Logical drawing window (0,0,0,0 = reset)")
def set_window(ctx, xmin, xmax, ymin, ymax):
    values = [_num(v) for v in (xmin, xmax, ymin, ymax)]
    c = canvas(ctx)
    if values == [0, 0, 0, 0]:
        c.window = None
        return None
    if values[0] >= values[1] or values[2] >= values[3]:
        raise DomainError("xMin must be < xMax and yMin < yMax")
    c.window = tuple(values)
    return None


@builtin("UseBuffer", "UseBuffer", 0, **CMD, summary="Draw off screen until PaintBuffer")
def use_buffer(ctx):
    return None


@builtin("PaintBuffer", "PaintBuffer", 0, **CMD, summary="Show the off-screen buffer")
def paint_buffer(ctx):
    return None


# ------------------------------------------------------------------ rendering (Pillow)


def _ellipse_points(x, y, w, h, start=0.0, sweep=360.0, steps=96):
    import math

    cx, cy, rx, ry = x + w / 2, y + h / 2, w / 2, h / 2
    return [(cx + rx * math.cos(math.radians(start + sweep * k / steps)),
             cy - ry * math.sin(math.radians(start + sweep * k / steps))) for k in range(steps + 1)]


def _styled_line(draw, points, color, width, style, scale):
    """Smooth (1), dotted (2) or dashed (3) polyline."""
    import math

    if style == 1:
        draw.line(points, fill=color, width=width, joint="curve")
        return
    on, off = (1.5 * scale, 3 * scale) if style == 2 else (6 * scale, 4 * scale)
    pattern_pos, drawing = 0.0, True
    for (x1, y1), (x2, y2) in zip(points, points[1:]):
        length = math.hypot(x2 - x1, y2 - y1)
        t = 0.0
        while t < length:
            segment = (on if drawing else off) - pattern_pos
            step = min(segment, length - t)
            if drawing:
                a = t / length if length else 0
                b = (t + step) / length if length else 0
                draw.line([(x1 + (x2 - x1) * a, y1 + (y2 - y1) * a), (x1 + (x2 - x1) * b, y1 + (y2 - y1) * b)],
                          fill=color, width=width)
            t += step
            pattern_pos += step
            if pattern_pos >= (on if drawing else off) - 1e-9:
                pattern_pos, drawing = 0.0, not drawing


def render(ops: list[tuple], scale: int = 2):
    """Render drawing operations to a Pillow image (scaled for sharpness)."""
    from PIL import Image, ImageDraw

    image = Image.new("RGB", (WIDTH * scale, HEIGHT * scale), (255, 255, 255))
    draw = ImageDraw.Draw(image)

    def s(v):
        return v * scale

    def outline(points, color, width, style):
        _styled_line(draw, [(s(x), s(y)) for x, y in points], color, width, style, scale)

    for op in ops:
        kind, color, thickness, style = op[:4]
        data = op[4:]
        width = max(1, int(thickness * scale))
        if kind == "clear":
            box = data[0]
            if box is None:
                draw.rectangle([0, 0, WIDTH * scale, HEIGHT * scale], fill=(255, 255, 255))
            else:
                x, y, w, h = box
                draw.rectangle([s(x), s(y), s(x + w), s(y + h)], fill=(255, 255, 255))
        elif kind == "line":
            outline(data[0], color, width, style)
        elif kind in ("polygon", "polyline"):
            if kind == "polygon":
                draw.polygon([(s(x), s(y)) for x, y in data[0]], fill=color)
            else:
                outline(list(data[0]) + list(data[0][:1]), color, width, style)
        elif kind == "rect":
            (x, y, w, h), fill = data
            if fill:
                draw.rectangle([s(x), s(y), s(x + w), s(y + h)], fill=color)
            else:
                outline([(x, y), (x + w, y), (x + w, y + h), (x, y + h), (x, y)], color, width, style)
        elif kind == "ellipse":
            (x, y, w, h), fill = data
            if fill:
                draw.ellipse([s(x), s(y), s(x + w), s(y + h)], fill=color)
            else:
                outline(_ellipse_points(x, y, w, h), color, width, style)
        elif kind == "arc":
            (x, y, w, h), start, sweep, fill = data
            # handheld: angles in degrees, counter-clockwise from 3 o'clock
            points = _ellipse_points(x, y, w, h, start, sweep)
            if fill:
                cx, cy = x + w / 2, y + h / 2
                draw.polygon([(s(cx), s(cy))] + [(s(px), s(py)) for px, py in points], fill=color)
            else:
                outline(points, color, width, style)
        elif kind == "text":
            (x, y), text = data
            draw.text((s(x), s(y) - 12 * scale), text, fill=color, font_size=11 * scale)
        elif kind == "point":
            (x, y), shape = data
            size = {1: 3, 2: 3, 3: 3, 4: 3, 5: 3, 6: 3, 7: 1, 8: 2, 9: 2, 10: 3, 11: 3, 12: 4, 13: 4}[shape] * scale
            box = [s(x) - size, s(y) - size, s(x) + size, s(y) + size]
            if shape in (1, 8, 10, 12):
                draw.ellipse(box, fill=color)
            elif shape in (2, 9, 11, 13):
                draw.ellipse(box, outline=color, width=scale)
            elif shape == 3:
                draw.rectangle(box, fill=color)
            elif shape == 4:
                draw.rectangle(box, outline=color, width=scale)
            elif shape == 5:
                draw.line([box[0], box[1], box[2], box[3]], fill=color, width=scale)
                draw.line([box[0], box[3], box[2], box[1]], fill=color, width=scale)
            elif shape == 6:
                draw.line([s(x) - size, s(y), s(x) + size, s(y)], fill=color, width=scale)
                draw.line([s(x), s(y) - size, s(x), s(y) + size], fill=color, width=scale)
            else:
                draw.point((s(x), s(y)), fill=color)
    return image
