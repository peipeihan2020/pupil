import numpy as np
import OpenGL.GL as gl
import pyglui.cygl.utils as cygl_utils
from pyglui import ui
from pyglui.pyfontstash import fontstash as fs
from pylsl import StreamInlet, resolve_stream


import data_changed
import gl_utils
from observable import Observable

COLOR_LEGEND_WORLD = cygl_utils.RGBA(0.66, 0.86, 0.461, 1.0)
COLOR_LEGEND_EYE_RIGHT = cygl_utils.RGBA(0.9844, 0.5938, 0.4023, 1.0)
COLOR_LEGEND_EYE_LEFT = cygl_utils.RGBA(0.668, 0.6133, 0.9453, 1.0)
NUMBER_SAMPLES_TIMELINE = 4000


class EEG_Channel:
    def __init__(self, channel):
        self.channel = channel

    def set_timeline(self, x, y, xlim, ylim, glfont):
       self.x = x
       self.y = y
       self.xlim = xlim
       self.ylim = ylim
       self.glfont = glfont
       return ui.Timeline(
            "EEG", self.draw_data, self.draw_legend
        )

    def draw_data(self, width, height, scale):

        if len(self.x[self.channel]) == 0:
            return

        x = self.x[self.channel] - self.x[self.channel][0]
        xlim = [min(x), max(x)+0.01]
        ylim = [min(self.y[self.channel]), max(self.y[self.channel])+0.00001]

        with gl_utils.Coord_System(*xlim, *ylim):
            whole_data = tuple(zip(self.x[self.channel]-self.x[self.channel][0], self.y[self.channel]))
            cygl_utils.draw_points(
                whole_data, size=2 * scale, color=COLOR_LEGEND_WORLD
            )

    def draw_legend(self, width, height, scale):
        self.glfont.push_state()
        self.glfont.set_align_string(v_align="right", h_align="top")
        self.glfont.set_size(15.0 * scale)

        legend_height = 13.0 * scale
        pad = 10 * scale

        self.glfont.draw_text(width, legend_height, "channel "+str(self.channel+1))
        cygl_utils.draw_polyline(
            [
                (pad, legend_height + pad * 2 / 3),
                (width / 2, legend_height + pad * 2 / 3),
            ],
            color=COLOR_LEGEND_WORLD,
            line_type=gl.GL_LINES,
            thickness=4.0 * scale,
        )
        legend_height += 1.5 * pad

        self.glfont.pop_state()