"""
(*)~---------------------------------------------------------------------------
Pupil - eye tracking platform
Copyright (C) 2012-2020 Pupil Labs

Distributed under the terms of the GNU
Lesser General Public License (LGPL v3.0).
See COPYING and COPYING.LESSER for license details.
---------------------------------------------------------------------------~(*)
"""
import numpy as np
import OpenGL.GL as gl
import pyglui.cygl.utils as cygl_utils
from pyglui import ui
from pyglui.pyfontstash import fontstash as fs
from pylsl import StreamInlet, resolve_stream
from eeg_channel import EEG_Channel
import pylsl
import math

import data_changed
import gl_utils
from observable import Observable
from plugin import System_Plugin_Base
from collections import deque

COLOR_LEGEND_WORLD = cygl_utils.RGBA(0.66, 0.86, 0.461, 1.0)
COLOR_LEGEND_EYE_RIGHT = cygl_utils.RGBA(0.9844, 0.5938, 0.4023, 1.0)
COLOR_LEGEND_EYE_LEFT = cygl_utils.RGBA(0.668, 0.6133, 0.9453, 1.0)
NUMBER_SAMPLES_TIMELINE = 4000

plot_duration = 5  # how many seconds of data to show
update_interval = 0.06  # ms between screen updates
pull_interval = 0.5


class EEG_Timelines(Observable, System_Plugin_Base):
    def __init__(self, g_pool):
        super().__init__(g_pool)

        streams = resolve_stream('type', 'EEG')
        # create a new inlet to read from the stream
        if len(streams) == 0:
            raise Exception('No device')
        self.dtypes = [[], np.float32, np.float64, None, np.int32, np.int16, np.int8, np.int64]
        info = streams[0]
        self.inlet = StreamInlet(info)
        self.timelines = []
        self.channels = info.channel_count()


        bufsize = (2 * math.ceil(info.nominal_srate() * plot_duration), info.channel_count())
        self.buffer = np.empty(bufsize, dtype=self.dtypes[info.channel_format()])

        self.fudge_factor = pull_interval * .002
        self.plot_time = pylsl.local_clock()
        self.x = dict(zip(range(self.channels), [np.array([]) for _ in range(self.channels)]))
        self.y = dict(zip(range(self.channels), [np.array([]) for _ in range(self.channels)]))
        self.xlim = [0, plot_duration]
        self.ylim = [0., 0.1]
        self.update_time = pylsl.local_clock()
        self.cache_data()

    def init_ui(self):
        self.glfont = fs.Context()
        self.glfont.add_font("opensans", ui.get_opensans_font_path())
        self.glfont.set_font("opensans")

        for i in range(self.channels):
            eeg_channel = EEG_Channel(i)
            timeline = eeg_channel.set_timeline(self.x, self.y, self.xlim, self.ylim, self.glfont)
            timeline.content_height *= 1
            self.timelines.append(timeline)
            self.g_pool.user_timelines.append(timeline)

    def recent_events(self, events):
        self.cache_data()
        current = pylsl.local_clock()
        if current - self.update_time > update_interval:

            self.update_time = current
            for timeline in self.timelines:
                timeline.refresh()

    def deinit_ui(self):
        for timeline in self.timelines:
            self.g_pool.user_timelines.remove(timeline)
        self.timelines = None

    def cache_data(self):
        current = pylsl.local_clock()
        if current - self.plot_time > pull_interval:
            self.plot_time = current
            mintime = pylsl.local_clock() - plot_duration
            _, ts = self.inlet.pull_chunk(timeout=0.0,
                                          max_samples=self.buffer.shape[0],
                                          dest_obj=self.buffer)
            # ts will be empty if no samples were pulled, a list of timestamps otherwise
            if ts:
                ts = np.asarray(ts)
                y = self.buffer[0:ts.size, :]

                for ch_ix in range(self.channels):

                    old_x = self.x[ch_ix]
                    old_y = self.y[ch_ix]

                    old_offset = old_x.searchsorted(mintime)
                    # same for the new data, in case we pulled more data than
                    # can be shown at once
                    new_offset = ts.searchsorted(mintime)
                    # append new timestamps to the trimmed old timestamps
                    this_x = np.hstack((old_x[old_offset:], ts[new_offset:]))
                    # append new data to the trimmed old data
                    this_y = np.hstack((old_y[old_offset:], y[new_offset:, ch_ix] - ch_ix))
                    if len(this_x) > 0:
                        self.x[ch_ix]=this_x
                        self.y[ch_ix]=this_y


    def draw_data(self, width, height, scale, channel):
        with gl_utils.Coord_System(*self.cache["xlim"], *self.cache["ylim"]):
            channels = np.shape(self.cache["data"])[1]
            for i in range(channels):
                channel_data =np.reshape(self.cache["data"][:,channel],(-1)).tolist()
                whole_data = tuple(zip(channel_data, self.timestamps))
                if len(channel_data) ==1:
                    return
                cygl_utils.draw_points(
                    whole_data, size=2 * scale, color=COLOR_LEGEND_WORLD
                )

    def draw_legend(self, width, height, scale, channel):
        self.glfont.push_state()
        self.glfont.set_align_string(v_align="right", h_align="top")
        self.glfont.set_size(15.0 * scale)
        self.glfont.draw_text(width, 0, 'channel '+str(channel))

        legend_height = 13.0 * scale
        pad = 10 * scale

        channels = np.shape(self.cache["data"])[1]
        for i in range(channels):
            self.glfont.draw_text(width, legend_height, "channel "+str(channel))
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
