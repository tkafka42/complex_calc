"""Graphs page: function, parametric, polar and scatter plots with
Window/Zoom, Trace, Analyze Graph (click lower/upper bound) and a table.

Functions are defined in the shared session (f1(x), f2(x), …), so the
Calculator page can use them and vice versa, like inside one problem on the
handheld.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np
import sympy as sp
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..analysis import graph_analysis as ga
from ..core.formatting import format_expr, format_float
from ..core.session import Session, normalize_name
from ..core.values import ListValue, UserFunction
from ..i18n import tr
from ..menus import GRAPHS_MENU, MenuItem
from .calculator_page import build_menu

# own palette for graphs (not the handheld colors)
COLORS = ["#2563eb", "#dc2626", "#16a34a", "#9333ea", "#ea580c", "#0891b2", "#be185d", "#4d7c0f"]
T = sp.Symbol("t")
THETA = sp.Symbol("θ")


@dataclass
class Plot:
    kind: str  # "function" | "parametric" | "polar" | "scatter"
    name: str  # f1, xt1/yt1, r1, s1
    exprs: list  # sympy expressions (function: [y], parametric: [x, y], polar: [r]) or lists (scatter)
    label: str
    color: str
    visible: bool = True
    t_range: tuple[float, float, float] = (0.0, 2 * math.pi, 0.0131)  # tmin, tmax, tstep


@dataclass
class Window:
    xmin: float = -10.0
    xmax: float = 10.0
    ymin: float = -6.67
    ymax: float = 6.67
    xscale: float = 1.0
    yscale: float = 1.0


@dataclass
class PendingAnalysis:
    action: str
    plot_index: int
    other_index: int | None = None
    clicks: list[float] = field(default_factory=list)


class WindowDialog(QDialog):
    def __init__(self, window: Window, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("Window Settings"))
        form = QFormLayout(self)
        self.edits = {}
        for key, label in (("xmin", "XMin"), ("xmax", "XMax"), ("xscale", "XScale"),
                           ("ymin", "YMin"), ("ymax", "YMax"), ("yscale", "YScale")):
            edit = QLineEdit(format_float(getattr(window, key), 6).rstrip("."))
            form.addRow(label, edit)
            self.edits[key] = edit
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

    def values(self, session: Session) -> dict[str, float]:
        out = {}
        for key, edit in self.edits.items():
            out[key] = float(session.evaluate(edit.text() or "0").evalf())
        return out


class GraphsPage(QWidget):
    def __init__(self, session: Session):
        super().__init__()
        self.setObjectName("Page")
        self.session = session
        self.plots: list[Plot] = []
        self.window = Window()
        self.scale = "linear"  # linear | semilogy | semilogx | loglog
        self.show_grid = True
        self.show_axes = True
        self.trace_index: int | None = None
        self.trace_x: float | None = None
        self.pending: PendingAnalysis | None = None
        self.marks: list[tuple[float, float, str]] = []
        self.shade: tuple[int, float, float] | None = None
        self.table_settings = (0.0, 1.0)
        self._drag = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)

        splitter = QSplitter(Qt.Horizontal)
        self.figure = Figure(figsize=(6, 4), layout="constrained")
        self.canvas = FigureCanvasQTAgg(self.figure)
        self.canvas.setFocusPolicy(Qt.StrongFocus)
        self.ax = self.figure.add_subplot(111)
        splitter.addWidget(self.canvas)

        side = QWidget()
        side_layout = QVBoxLayout(side)
        side_layout.setContentsMargins(0, 0, 0, 0)
        self.function_list = QListWidget()
        self.function_list.itemChanged.connect(self._toggle_visible)
        self.function_list.itemDoubleClicked.connect(self._edit_item)
        side_layout.addWidget(QLabel(tr("Functions & plots")))
        side_layout.addWidget(self.function_list, 1)
        self.table = QTableWidget(0, 1)
        self.table.hide()
        side_layout.addWidget(self.table, 2)
        splitter.addWidget(side)
        splitter.setSizes([700, 260])
        layout.addWidget(splitter, 1)

        self.status = QLabel(tr("Type a function and press Enter. Menu (Ctrl+M) → 6 Analyze Graph."))
        self.status.setObjectName("Hint")
        layout.addWidget(self.status)

        row = QHBoxLayout()
        self.menu_button = QPushButton(tr("Menu"))
        self.menu_button.setObjectName("Primary")
        self.menu_button.setFocusPolicy(Qt.NoFocus)
        self.menu_button.clicked.connect(self.open_menu)
        row.addWidget(self.menu_button)
        self.name_combo = QComboBox()
        self.name_combo.addItems([f"f{k}(x)=" for k in range(1, 100)])
        self.name_combo.setFocusPolicy(Qt.NoFocus)
        row.addWidget(self.name_combo)
        self.entry = QLineEdit()
        self.entry.setPlaceholderText(tr("e.g. x^2-3   or   sin(x)   (Enter graphs the function)"))
        self.entry.returnPressed.connect(self.submit_function)
        row.addWidget(self.entry, 1)
        layout.addLayout(row)

        self.menu = build_menu(self, GRAPHS_MENU, self.on_menu_item)
        shortcut = QShortcut(QKeySequence("Ctrl+M"), self, activated=self.open_menu)
        shortcut.setContext(Qt.WidgetWithChildrenShortcut)

        self.canvas.mpl_connect("button_press_event", self._on_press)
        self.canvas.mpl_connect("button_release_event", self._on_release)
        self.canvas.mpl_connect("motion_notify_event", self._on_motion)
        self.canvas.mpl_connect("scroll_event", self._on_scroll)
        self.canvas.mpl_connect("key_press_event", self._on_key)
        self.redraw()

    # ------------------------------------------------------------ menu
    def open_menu(self):
        from PySide6.QtCore import QPoint

        top_left = self.menu_button.mapToGlobal(QPoint(0, 0))
        self.menu.popup(top_left - QPoint(0, self.menu.sizeHint().height()))

    def on_menu_item(self, item: MenuItem):
        handler = getattr(self, f"action_{item.action}", None)
        if handler is not None:
            handler()

    # ------------------------------------------------------------ entering functions
    def _next_name(self, prefix: str) -> str:
        used = {p.name for p in self.plots}
        k = 1
        while f"{prefix}{k}" in used:
            k += 1
        return f"{prefix}{k}"

    def submit_function(self):
        text = self.entry.text().strip()
        if not text:
            return
        name = self.name_combo.currentText().split("(")[0]
        if "=" in text and text.split("=")[0].strip().endswith("(x)"):
            name, text = text.split("=", 1)[0].strip()[:-3], text.split("=", 1)[1]
        entry = self.session.run(f"Define {name}(x)={text}")
        if entry.error:
            self.status.setText(entry.text.splitlines()[0])
            return
        function = self.session.variables[normalize_name(name)]
        self._add_or_replace(Plot("function", name, [function.body.subs(function.params[0], ga.X)],
                                  f"{name}(x)={text}", self._color_for(name)))
        self.entry.clear()
        index = min(self.name_combo.findText(f"{self._next_name('f')}(x)="), 98)
        self.name_combo.setCurrentIndex(max(index, 0))

    def _color_for(self, name: str) -> str:
        existing = next((p.color for p in self.plots if p.name == name), None)
        return existing or COLORS[len(self.plots) % len(COLORS)]

    def _add_or_replace(self, plot: Plot):
        for k, existing in enumerate(self.plots):
            if existing.name == plot.name:
                self.plots[k] = plot
                break
        else:
            self.plots.append(plot)
        self._refresh_list()
        self.redraw()

    def _refresh_list(self):
        self.function_list.blockSignals(True)
        self.function_list.clear()
        for plot in self.plots:
            item = QListWidgetItem(plot.label)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked if plot.visible else Qt.Unchecked)
            item.setForeground(Qt.GlobalColor.black)
            item.setData(Qt.DecorationRole, None)
            item.setToolTip("Double-click to edit")
            self.function_list.addItem(item)
            item.setText("■ " + plot.label)
        self.function_list.blockSignals(False)
        for k, plot in enumerate(self.plots):
            from PySide6.QtGui import QColor

            self.function_list.item(k).setForeground(QColor(plot.color))

    def _toggle_visible(self, item: QListWidgetItem):
        k = self.function_list.row(item)
        self.plots[k].visible = item.checkState() == Qt.Checked
        self.redraw()

    def _edit_item(self, item: QListWidgetItem):
        plot = self.plots[self.function_list.row(item)]
        if plot.kind == "function":
            self.name_combo.setCurrentIndex(max(self.name_combo.findText(f"{plot.name}(x)="), 0))
            self.entry.setText(plot.label.split("=", 1)[1])
            self.entry.setFocus()

    # ------------------------------------------------------------ drawing
    def redraw(self):
        ax = self.ax
        ax.clear()
        w = self.window
        ax.set_xscale("log" if self.scale in ("semilogx", "loglog") else "linear")
        ax.set_yscale("log" if self.scale in ("semilogy", "loglog") else "linear")
        xmin = w.xmin if ax.get_xscale() == "linear" else max(w.xmin, 1e-6 if w.xmax > 1e-6 else 1e-9)
        ymin = w.ymin if ax.get_yscale() == "linear" else max(w.ymin, 1e-6 if w.ymax > 1e-6 else 1e-9)
        ax.set_xlim(xmin, w.xmax)
        ax.set_ylim(ymin, w.ymax)
        if self.show_grid:
            ax.grid(True, which="both", color="#e5e7eb", linewidth=0.7)
        if self.show_axes and ax.get_xscale() == "linear" and ax.get_yscale() == "linear":
            ax.axhline(0, color="#475569", linewidth=1)
            ax.axvline(0, color="#475569", linewidth=1)
        for spine in ax.spines.values():
            spine.set_color("#cbd5e1")

        if ax.get_xscale() == "log":
            xs = np.logspace(math.log10(xmin), math.log10(w.xmax), 1200)
        else:
            xs = np.linspace(xmin, w.xmax, 1200)
        for k, plot in enumerate(self.plots):
            if not plot.visible:
                continue
            try:
                self._draw_plot(ax, plot, xs)
            except Exception as exc:  # noqa: BLE001 - keep the page usable
                self.status.setText(f"{plot.name}: cannot be drawn ({exc})")
        if self.shade is not None:
            k, lo, hi = self.shade
            if 0 <= k < len(self.plots) and self.plots[k].kind == "function":
                sx = np.linspace(lo, hi, 400)
                sy = ga.numeric(self.plots[k].exprs[0])(sx)
                ax.fill_between(sx, sy, 0, color=self.plots[k].color, alpha=0.25)
        for x, y, text in self.marks:
            ax.plot([x], [y], "o", color="#111827", markersize=5)
            ax.annotate(text, (x, y), textcoords="offset points", xytext=(6, 6), fontsize=9,
                        bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="#cbd5e1"))
        if self.trace_index is not None and self.trace_x is not None and self.trace_index < len(self.plots):
            plot = self.plots[self.trace_index]
            y = ga.scalar(plot.exprs[0])(self.trace_x) if plot.kind == "function" else float("nan")
            if not math.isnan(y):
                ax.plot([self.trace_x], [y], "s", color=plot.color, markersize=7, fillstyle="none")
                self.status.setText(f"Trace {plot.name}:  x = {format_float(self.trace_x)}   "
                                    f"y = {format_float(y)}   (←/→ move, ↑/↓ other graph, Esc ends)")
        self.canvas.draw_idle()

    def _draw_plot(self, ax, plot: Plot, xs):
        if plot.kind == "function":
            ys = ga.numeric(plot.exprs[0])(xs)
            span = self.window.ymax - self.window.ymin
            jumps = np.abs(np.diff(ys)) > 4 * span  # break lines at poles (tan, 1/x)
            ys = ys.copy()
            ys[1:][jumps] = np.nan
            ax.plot(xs, ys, color=plot.color, linewidth=1.8)
        elif plot.kind == "parametric":
            tmin, tmax, tstep = plot.t_range
            ts = np.arange(tmin, tmax + tstep / 2, tstep)
            ax.plot(ga.numeric(plot.exprs[0], T)(ts), ga.numeric(plot.exprs[1], T)(ts), color=plot.color, linewidth=1.8)
        elif plot.kind == "polar":
            tmin, tmax, tstep = plot.t_range
            ts = np.arange(tmin, tmax + tstep / 2, tstep)
            rs = ga.numeric(plot.exprs[0], THETA)(ts)
            ax.plot(rs * np.cos(ts), rs * np.sin(ts), color=plot.color, linewidth=1.8)
        elif plot.kind == "scatter":
            ax.plot(plot.exprs[0], plot.exprs[1], "o", color=plot.color, markersize=5)

    # ------------------------------------------------------------ mouse & keys
    def _on_press(self, event):
        if event.inaxes is None:
            return
        if self.pending is not None and event.button == 1:
            self._analysis_click(event.xdata)
            return
        if event.button == 1:
            self._drag = (event.x, event.y, self.window.xmin, self.window.xmax, self.window.ymin, self.window.ymax)

    def _on_release(self, event):
        self._drag = None

    def _on_motion(self, event):
        if self._drag is not None and event.inaxes is not None and self.scale == "linear":
            x0, y0, xmin, xmax, ymin, ymax = self._drag
            bbox = self.ax.get_window_extent()
            dx = (event.x - x0) / bbox.width * (xmax - xmin)
            dy = (event.y - y0) / bbox.height * (ymax - ymin)
            self.window.xmin, self.window.xmax = xmin - dx, xmax - dx
            self.window.ymin, self.window.ymax = ymin - dy, ymax - dy
            self.redraw()
        elif self.trace_index is not None and event.inaxes is not None and event.xdata is not None:
            self.trace_x = float(event.xdata)
            self.redraw()

    def _on_scroll(self, event):
        if event.inaxes is None:
            return
        self._zoom(0.8 if event.button == "up" else 1.25, event.xdata, event.ydata)

    def _on_key(self, event):
        if self.trace_index is None:
            return
        step = (self.window.xmax - self.window.xmin) / 100
        if event.key == "right":
            self.trace_x = (self.trace_x or 0) + step
        elif event.key == "left":
            self.trace_x = (self.trace_x or 0) - step
        elif event.key in ("up", "down"):
            functions = [k for k, p in enumerate(self.plots) if p.kind == "function" and p.visible]
            if functions:
                pos = functions.index(self.trace_index) if self.trace_index in functions else 0
                self.trace_index = functions[(pos + (1 if event.key == "down" else -1)) % len(functions)]
        elif event.key == "escape":
            self.trace_index = None
            self.status.setText("Trace ended.")
        self.redraw()

    def _zoom(self, factor: float, cx: float | None = None, cy: float | None = None):
        w = self.window
        cx = (w.xmin + w.xmax) / 2 if cx is None else cx
        cy = (w.ymin + w.ymax) / 2 if cy is None else cy
        w.xmin, w.xmax = cx - (cx - w.xmin) * factor, cx + (w.xmax - cx) * factor
        w.ymin, w.ymax = cy - (cy - w.ymin) * factor, cy + (w.ymax - cy) * factor
        self.redraw()

    # ------------------------------------------------------------ helpers
    def _choose_function(self, title: str, exclude: int | None = None) -> int | None:
        options = [k for k, p in enumerate(self.plots) if p.kind == "function" and p.visible and k != exclude]
        if not options:
            QMessageBox.information(self, title, tr("Please graph a function first."))
            return None
        if len(options) == 1:
            return options[0]
        labels = [self.plots[k].label for k in options]
        choice, ok = QInputDialog.getItem(self, title, tr("Select graph:"), labels, 0, False)
        return options[labels.index(choice)] if ok else None

    def _start(self, action: str, needs_two: bool = False):
        index = self._choose_function(tr("Analyze Graph"))
        if index is None:
            return
        other = None
        if needs_two:
            other = self._choose_function(tr("Second graph"), exclude=index)
            if other is None:
                return
        self.pending = PendingAnalysis(action, index, other)
        prompt = tr("Click the point") if action == "dydx" else tr("Click the lower bound")
        self.status.setText(f"{prompt} {tr('(on the graph).')}")
        self.canvas.setFocus()

    def _analysis_click(self, x: float):
        pending = self.pending
        assert pending is not None
        pending.clicks.append(float(x))
        needed = 1 if pending.action == "dydx" else 2
        if len(pending.clicks) < needed:
            self.status.setText(tr("Click the upper bound."))
            return
        self.pending = None
        plot = self.plots[pending.plot_index]
        expr = plot.exprs[0]
        try:
            if pending.action == "zero":
                p = ga.zero(expr, *pending.clicks)
                self.marks.append((p.x, p.y, f"zero: {format_float(p.x)}"))
            elif pending.action in ("minimum", "maximum"):
                p = ga.extremum(expr, *pending.clicks, maximum=pending.action == "maximum")
                self.marks.append((p.x, p.y, f"{pending.action}: ({format_float(p.x)}, {format_float(p.y)})"))
            elif pending.action == "inflection":
                p = ga.inflection(expr, *pending.clicks)
                self.marks.append((p.x, p.y, f"inflection: ({format_float(p.x)}, {format_float(p.y)})"))
            elif pending.action == "intersection":
                p = ga.intersection(expr, self.plots[pending.other_index].exprs[0], *pending.clicks)
                self.marks.append((p.x, p.y, f"({format_float(p.x)}, {format_float(p.y)})"))
            elif pending.action == "dydx":
                x0 = pending.clicks[0]
                slope = ga.derivative_at(expr, x0)
                self.marks.append((x0, ga.scalar(expr)(x0), f"dy/dx = {format_float(slope)}"))
            elif pending.action == "integral":
                lo, hi = sorted(pending.clicks)
                value = ga.integral(expr, lo, hi)
                self.shade = (pending.plot_index, lo, hi)
                self.marks.append(((lo + hi) / 2, 0.0, f"∫ = {format_float(value)}"))
            self.status.setText(self.marks[-1][2] if self.marks else "")
        except ga.AnalysisError as exc:
            self.status.setText(f"{exc}")
        self.redraw()

    # ------------------------------------------------------------ menu actions
    def action_g_clear(self):
        self.plots.clear()
        self.marks.clear()
        self.shade = None
        self.trace_index = None
        self.table.hide()
        self.name_combo.setCurrentIndex(0)
        self._refresh_list()
        self.redraw()

    def add_scatter(self, x_name: str, y_name: str, xs: list[float], ys: list[float]):
        """Used by the Lists & Spreadsheet page (Quick Graph)."""
        name = self._next_name("s")
        self._add_or_replace(Plot("scatter", name, [xs, ys], f"{name}: x←{x_name}, y←{y_name}",
                                  self._color_for(name)))
        self.action_g_zoom_data()

    def action_g_toggle_list(self):
        self.function_list.setVisible(not self.function_list.isVisible())

    def action_g_toggle_entry(self):
        self.entry.setVisible(not self.entry.isVisible())
        self.name_combo.setVisible(self.entry.isVisible())

    def action_g_toggle_grid(self):
        self.show_grid = not self.show_grid
        self.redraw()

    def action_g_toggle_axes(self):
        self.show_axes = not self.show_axes
        self.redraw()

    def action_g_entry_function(self):
        self.entry.setFocus()

    def action_g_entry_parametric(self):
        name = self._next_name("xt")
        k = name[2:]
        x_text, ok = QInputDialog.getText(self, "Parametric", f"xt{k}(t)=")
        if not ok or not x_text:
            return
        y_text, ok = QInputDialog.getText(self, "Parametric", f"yt{k}(t)=")
        if not ok or not y_text:
            return
        exprs = []
        for prefix, text in (("xt", x_text), ("yt", y_text)):
            entry = self.session.run(f"Define {prefix}{k}(t)={text}")
            if entry.error:
                self.status.setText(entry.text.splitlines()[0])
                return
            f = self.session.variables[f"{prefix}{k}"]
            exprs.append(f.body.subs(f.params[0], T))
        self._add_or_replace(Plot("parametric", name, exprs, f"xt{k}(t)={x_text}, yt{k}(t)={y_text}",
                                  self._color_for(name)))

    def action_g_entry_polar(self):
        name = self._next_name("r")
        text, ok = QInputDialog.getText(self, "Polar", f"{name}(θ)=")
        if not ok or not text:
            return
        entry = self.session.run(f"Define {name}(θ)={text}")
        if entry.error:
            self.status.setText(entry.text.splitlines()[0])
            return
        f = self.session.variables[normalize_name(name)]
        self._add_or_replace(Plot("polar", name, [f.body.subs(f.params[0], THETA)], f"{name}(θ)={text}",
                                  self._color_for(name)))

    def action_g_entry_scatter(self):
        x_name, ok = QInputDialog.getText(self, "Scatter Plot", "x ← list variable or {…}:")
        if not ok or not x_name:
            return
        y_name, ok = QInputDialog.getText(self, "Scatter Plot", "y ← list variable or {…}:")
        if not ok or not y_name:
            return
        try:
            xs, ys = self.session.evaluate(x_name), self.session.evaluate(y_name)
            if not isinstance(xs, ListValue) or not isinstance(ys, ListValue) or len(xs) != len(ys):
                raise ValueError("two lists of equal length expected")
            xv = [float(sp.N(v)) for v in xs]
            yv = [float(sp.N(v)) for v in ys]
        except Exception as exc:  # noqa: BLE001
            self.status.setText(f"Scatter Plot: {exc}")
            return
        name = self._next_name("s")
        self._add_or_replace(Plot("scatter", name, [xv, yv], f"{name}: x←{x_name}, y←{y_name}",
                                  self._color_for(name)))

    def action_g_window(self):
        dialog = WindowDialog(self.window, self)
        if dialog.exec():
            try:
                values = dialog.values(self.session)
            except Exception as exc:  # noqa: BLE001
                self.status.setText(f"Window: {exc}")
                return
            if values["xmin"] >= values["xmax"] or values["ymin"] >= values["ymax"]:
                self.status.setText("Window: min must be smaller than max")
                return
            for key, value in values.items():
                setattr(self.window, key, value)
            self.redraw()

    def action_g_zoom_in(self):
        self._zoom(0.5)

    def action_g_zoom_out(self):
        self._zoom(2.0)

    def _set_window(self, xmin, xmax, ymin, ymax):
        self.window.xmin, self.window.xmax, self.window.ymin, self.window.ymax = xmin, xmax, ymin, ymax
        self.redraw()

    def action_g_zoom_standard(self):
        self._set_window(-10, 10, -6.67, 6.67)

    def action_g_zoom_quadrant1(self):
        self._set_window(0, 20, 0, 13.34)

    def action_g_zoom_trig(self):
        unit = {"rad": math.pi, "deg": 180.0, "grad": 200.0}[self.session.settings.angle]
        self._set_window(-2 * unit, 2 * unit, -4, 4)

    def action_g_zoom_square(self):
        bbox = self.ax.get_window_extent()
        w = self.window
        cy = (w.ymin + w.ymax) / 2
        half = (w.xmax - w.xmin) * bbox.height / bbox.width / 2
        self._set_window(w.xmin, w.xmax, cy - half, cy + half)

    def action_g_zoom_data(self):
        points = [(x, y) for p in self.plots if p.kind == "scatter" and p.visible for x, y in zip(*p.exprs)]
        if not points:
            self.status.setText("Zoom – Data needs a scatter plot.")
            return
        xs, ys = zip(*points)
        dx = (max(xs) - min(xs)) * 0.1 or 1
        dy = (max(ys) - min(ys)) * 0.1 or 1
        self._set_window(min(xs) - dx, max(xs) + dx, min(ys) - dy, max(ys) + dy)

    def action_g_zoom_fit(self):
        w = self.window
        xs = np.linspace(w.xmin, w.xmax, 600)
        values = []
        for p in self.plots:
            if p.visible and p.kind == "function":
                ys = ga.numeric(p.exprs[0])(xs)
                values.extend(ys[np.isfinite(ys)].tolist())
        if not values:
            return
        lo, hi = float(np.percentile(values, 1)), float(np.percentile(values, 99))
        pad = (hi - lo) * 0.1 or 1
        self._set_window(w.xmin, w.xmax, lo - pad, hi + pad)

    def action_g_trace(self):
        index = self._choose_function(tr("Graph Trace"))
        if index is None:
            return
        self.trace_index = index
        self.trace_x = (self.window.xmin + self.window.xmax) / 2
        self.canvas.setFocus()
        self.redraw()

    def action_g_zero(self):
        self._start("zero")

    def action_g_minimum(self):
        self._start("minimum")

    def action_g_maximum(self):
        self._start("maximum")

    def action_g_intersection(self):
        self._start("intersection", needs_two=True)

    def action_g_inflection(self):
        self._start("inflection")

    def action_g_dydx(self):
        self._start("dydx")

    def action_g_integral(self):
        self._start("integral")

    def action_g_table(self):
        functions = [p for p in self.plots if p.kind == "function"]
        if not functions:
            self.status.setText("Table: graph a function first.")
            return
        start, step = self.table_settings
        rows = 30
        self.table.clear()
        self.table.setColumnCount(1 + len(functions))
        self.table.setRowCount(rows)
        self.table.setHorizontalHeaderLabels(["x"] + [f"{p.name}(x)" for p in functions])
        for c, plot in enumerate(functions):
            for r, (x, y) in enumerate(ga.table(plot.exprs[0], start, step, rows)):
                if c == 0:
                    self.table.setItem(r, 0, QTableWidgetItem(format_float(x)))
                text = "undef" if y != y else format_float(y)
                self.table.setItem(r, c + 1, QTableWidgetItem(text))
        self.table.show()

    def action_g_table_remove(self):
        self.table.hide()

    def action_g_table_settings(self):
        start, ok = QInputDialog.getDouble(self, "Table Settings", "Table Start:", self.table_settings[0], -1e9, 1e9, 6)
        if not ok:
            return
        step, ok = QInputDialog.getDouble(self, "Table Settings", "Table Step:", self.table_settings[1], 1e-9, 1e9, 6)
        if not ok:
            return
        self.table_settings = (start, step)
        if self.table.isVisible():
            self.action_g_table()

    def _set_scale(self, scale: str):
        self.scale = scale
        w = self.window
        if scale in ("semilogx", "loglog") and w.xmax <= 0:
            w.xmin, w.xmax = 0.1, 100
        if scale in ("semilogy", "loglog") and w.ymax <= 0:
            w.ymin, w.ymax = 0.1, 100
        if scale in ("semilogx", "loglog") and w.xmin <= 0:
            w.xmin, w.xmax = 0.01, max(w.xmax, 100)
        if scale in ("semilogy", "loglog") and w.ymin <= 0:
            w.ymin, w.ymax = 0.01, max(w.ymax, 1000)
        self.redraw()

    def action_g_scale_linear(self):
        self._set_scale("linear")

    def action_g_scale_semilogy(self):
        self._set_scale("semilogy")

    def action_g_scale_semilogx(self):
        self._set_scale("semilogx")

    def action_g_scale_loglog(self):
        self._set_scale("loglog")
