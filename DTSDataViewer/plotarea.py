#! /usr/bin/env python
# -*- coding: utf-8 -*-
#
import inspect
from enum import Enum

import matplotlib.offsetbox
import numpy as np
from PyQt5 import QtWidgets
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
from matplotlib.ticker import NullLocator
from dts_file_reader import slice


class PlotArea(QtWidgets.QVBoxLayout):
    """
    Plots an Experiment
    """

    def __init__(self, parent=None):
        super(PlotArea, self).__init__()

        self.current_sample_rate = None
        self.underlay_peak_index = None
        self.plot_annotate = None
        self.fig = Figure((5.0, 4.0), facecolor='#e2e2e2', edgecolor=None, frameon=True)
        self.canvas = FigureCanvas(self.fig)
        self.canvas.setParent(parent)
        # self.fig.canvas.mpl_connect('draw_event', self.on_draw)

        # Create the navigation toolbar, tied to the canvas
        mpl_toolbar = NavigationToolbar(self.canvas, parent)

        # Since we have only one plot, we can use add_axes
        # instead of add_subplot, but then the subplot
        # configuration tool in the navigation toolbar wouldn't
        # work.
        self.axes = self.fig.subplots(nrows=4, ncols=2, sharex=True, sharey=False)
        (row_count, col_count) = self.axes.shape

        # independent scaled plot object
        self.y2 = None

        # notate axis units
        for row_i in range(0, row_count):
            self.axes[row_i, 0].set_ylabel('')
            self.axes[row_i, 1].set_ylabel('')

        self.axes[3, 0].set_xlabel('Time(ms)')
        self.axes[3, 1].set_xlabel('Time(ms)')

        # add gridlines to plot
        for row_i in range(0, row_count):
            for col_i in range(0, col_count):
                self.axes[row_i, col_i].grid(color='#eeeeee')

        self.addWidget(self.canvas)
        self.addWidget(mpl_toolbar)

        # initialize summarybox and provide reference
        # self.summaryBox = []
        self.selected_xspan = []
        self.positive_phase_area = None
        self.axes[0, 0].leg = None

        # init plot history
        self.reset_history()

        # store any annotations for easier clearing
        self.annotation_list = []

        # keep track of this for entire plot area
        self.display_annotations = False

        # this worked best for tigtening up the canvas. tight_layout only accounts for plot elements(axis, labels) and
        # complains with lots of cells. A tight_layout rectangle didn't work either
        # this handles suptitle well and other text
        #self.fig.subplots_adjust(left=0.045, bottom=0.06, right=0.98, top=0.92, wspace=0.15, hspace=0.15)
        self.fig.subplots_adjust(left=0.04, bottom=0.054, right=0.985, top=0.943, wspace=0.104, hspace=0.202)

    def plot(self, experiment, plot_annotate):
        """ new way of plotting

            0,0 = head axis 1
            1,0 = head axis 2
            2,0 = head axis 3
            3,0 = head axis resultant
            0,1 = machine sensor primary axis only
            1,1 = plot all three linear channels
            2,1 = head primary(coronal) plotted with head resultant
            3,1 = machine primary with head resultant

            When mounted on head:
            Axis 1 = rotation along an axis that goes from nose to back (CORONAL)
            Axis 2 = rotation along an axis that runs from ear to ear (SAGITTAL)
            Axis 3 = rotation along an axis that runs from the bottom to top of head (AXIAL)

            Display 1/8 of a second
        """

        if experiment.channel_data is None:
            return

        self.fig.suptitle(experiment.get_label())

        # display window
        window_samples = int(experiment.channel_data[0].meta_data.sample_rate_hz / 8)
        pre_peak_samples = int(window_samples/4)
        post_peak_sample = int(pre_peak_samples*3)

        # need summary data of a primary channel to determine location of peak
        # to window the data to 1/8 of a second
        # the head sensor will not be reliable as its orientation will change
        # machine sensor orientation is fixed so use that channel to get summary data
        machine_summary = experiment.channel_data[8].get_channel_summary(method='machine')
        head_summary = experiment.channel_data[0].get_channel_summary(method='head')

        # window large data vector around peak velocity value
        # first use the machine sensor, then try the head sensor
        # otherwise, a meaningless window of data at the start of the vector
        if machine_summary.peak_index == 0:
            if head_summary.peak_index == 0:
                plot_x_start = 0
                plot_x_end = window_samples
            else:
                plot_x_start = head_summary.peak_index - pre_peak_samples - 1
                plot_x_end = head_summary.peak_index + post_peak_sample - 1
        else:
            plot_x_start = machine_summary.peak_index - pre_peak_samples - 1
            plot_x_end = machine_summary.peak_index + post_peak_sample - 1

        min_y = -150
        max_y = 350
        x_tick_loc = np.arange(0,
                               (int(experiment.channel_data[0].meta_data.sample_rate_hz / 8) +
                                int((experiment.channel_data[0].meta_data.sample_rate_hz / 8) / 5)
                                ),
                               int((experiment.channel_data[0].meta_data.sample_rate_hz / 8) / 5)
                               )
        x_tick_lab = np.arange(0, 150, 25)
        nav_coor_div = 1/(experiment.channel_data[0].meta_data.sample_rate_hz/1000)
        y_tick_loc = np.arange(min_y, max_y, 50)
        y_tick_labels = ['', '-100', '', '0', '', '100', '', '200', '', '300']

        # get head resultant, use entire vector so that this resultant can be passed to get_summary()
        # which works only on full timeseries.
        # down below where we plot the data we will window the resultant to display window
        head_resultant = slice.get_resultant(experiment.channel_data, (0, 1, 2))

        ##############################################################################################################
        # Head - Coronal
        ##############################################################################################################
        self.axes[0, 0].set_title('Head - Coronal',
                                  pad=3.0, loc='center',
                                  fontdict={'fontsize': 10, 'fontweight': 'normal', 'color': 'black',
                                            'verticalalignment': 'baseline', 'horizontalalignment': 'center'}
                                  )
        self.axes[0, 0].set_ylim(min_y, max_y)
        self.axes[0, 0].yaxis.set_ticks(y_tick_loc)
        self.axes[0, 0].set_yticklabels(y_tick_labels)
        self.axes[0, 0].set_ylabel(experiment.channel_data[0].meta_data.eu)
        plot_data = experiment.channel_data[0].get_filtered_data(start=plot_x_start, stop=plot_x_end)
        self.axes[0, 0].plot(plot_data, color='#000000', linewidth=1)
        # only show summary if it is populated
        if experiment.channel_data[0].summary_data.peak_vel.value is not None:
            if plot_annotate:
                self.axes[0, 0].plot(
                    [head_summary.rise_start_index-plot_x_start, head_summary.peak_index-plot_x_start, head_summary.rise_end_index-plot_x_start],
                    [plot_data[head_summary.rise_start_index-plot_x_start], plot_data[head_summary.peak_index-plot_x_start], plot_data[head_summary.rise_end_index-plot_x_start]],
                    '.',
                    markersize='5',
                    color="red"
                )
            self.axes[0, 0].add_artist(self.get_summary_box(head_summary))
        # control the plot coordinate display in navigation toolbar
        self.axes[0, 0].format_coord = lambda x, y: '{:0.0f} ms'.format(x*nav_coor_div) + ', ' + '{:0.2f} rad/s'.format(y)

        ##############################################################################################################
        # Head - Sagittal
        ##############################################################################################################
        self.axes[1, 0].set_title('Head - Sagittal',
                                  pad=3.0, loc='center',
                                  fontdict={'fontsize': 10, 'fontweight': 'normal', 'color': 'black',
                                            'verticalalignment': 'baseline', 'horizontalalignment': 'center'}
                                  )
        self.axes[1, 0].set_ylim(min_y, max_y)
        self.axes[1, 0].yaxis.set_ticks(y_tick_loc)
        self.axes[1, 0].set_yticklabels(y_tick_labels)
        self.axes[1, 0].set_ylabel(experiment.channel_data[1].meta_data.eu)
        self.axes[1, 0].plot(experiment.channel_data[1].get_filtered_data(start=plot_x_start, stop=plot_x_end),
                             color='green', linewidth=1)
        self.axes[1, 0].format_coord = lambda x, y: '{:0.0f} ms'.format(x*nav_coor_div) + ', ' + '{:0.2f} rad/s'.format(y)

        ##############################################################################################################
        # Head - Axial
        ##############################################################################################################
        self.axes[2, 0].set_title('Head - Axial',
                                  pad=3.0, loc='center',
                                  fontdict={'fontsize': 10,'fontweight': 'normal', 'color': 'black',
                                            'verticalalignment': 'baseline', 'horizontalalignment': 'center'}
                                  )
        self.axes[2, 0].set_ylim(min_y, max_y)
        self.axes[2, 0].yaxis.set_ticks(y_tick_loc)
        self.axes[2, 0].set_yticklabels(y_tick_labels)
        self.axes[2, 0].set_ylabel(experiment.channel_data[2].meta_data.eu)
        self.axes[2, 0].plot(experiment.channel_data[2].get_filtered_data(start=plot_x_start, stop=plot_x_end),
                             color='orange', linewidth=1)
        self.axes[2, 0].format_coord = lambda x, y: '{:0.0f} ms'.format(x*nav_coor_div) + ', ' + '{:0.2f} rad/s'.format(y)

        ##############################################################################################################
        # Head - Resultant
        ##############################################################################################################
        self.axes[3, 0].set_title('Head - Rotation Resultant',
                                  pad=3.0, loc='center',
                                  fontdict={'fontsize': 10, 'fontweight': 'normal', 'color': 'black',
                                            'verticalalignment': 'baseline', 'horizontalalignment': 'center'}
                                  )
        self.axes[3, 0].set_ylim(min_y, max_y)
        self.axes[3, 0].yaxis.set_ticks(y_tick_loc)
        self.axes[3, 0].set_yticklabels(y_tick_labels)
        self.axes[3, 0].set_ylabel(experiment.channel_data[0].meta_data.eu)
        self.axes[3, 0].plot(head_resultant[plot_x_start:plot_x_end], color='#db3e27', linewidth=1)
        self.axes[3, 0].set_xlim(0, 5000)
        self.axes[3, 0].xaxis.set_ticks(x_tick_loc)
        self.axes[3, 0].xaxis.set_ticklabels(x_tick_lab)
        self.axes[3, 0].xaxis.set_minor_locator(NullLocator())
        self.axes[3, 0].format_coord = lambda x, y: '{:0.0f} ms'.format(x*nav_coor_div) + ', ' + '{:0.2f} rad/s'.format(y)

        head_resultant_summary = slice.get_data_summary(method='head',
                                                        sample_rate_hz=experiment.channel_data[0].meta_data.sample_rate_hz,
                                                        data=head_resultant)
        # only show summary if it is populated
        if head_resultant_summary.peak_vel.value is not None:
            if plot_annotate:
                self.axes[3, 0].plot(
                    [head_resultant_summary.rise_start_index-plot_x_start, head_resultant_summary.peak_index-plot_x_start, head_resultant_summary.rise_end_index-plot_x_start],
                    [head_resultant[head_resultant_summary.rise_start_index], head_resultant[head_resultant_summary.peak_index], head_resultant[head_resultant_summary.rise_end_index]],
                    '.',
                    markersize='5',
                    color="#000000"
                )
            self.axes[3, 0].add_artist(self.get_summary_box(head_resultant_summary))

        ##############################################################################################################
        # Machine - Primary Axis
        ##############################################################################################################
        self.axes[0, 1].set_title('Machine - Primary Axis',
                                  pad=3.0, loc='center',
                                  fontdict={'fontsize': 10,'fontweight': 'normal', 'color': 'black',
                                            'verticalalignment': 'baseline', 'horizontalalignment': 'center'}
                                  )
        self.axes[0, 1].yaxis.set_ticks(y_tick_loc)
        self.axes[0, 1].set_yticklabels(y_tick_labels)
        self.axes[0, 1].set_ylim(min_y, max_y)
        self.axes[0, 1].set_ylabel(experiment.channel_data[8].meta_data.eu)
        plot_data = experiment.channel_data[8].get_filtered_data(start=plot_x_start, stop=plot_x_end)
        self.axes[0, 1].plot(plot_data, color='#000000', linewidth=1)
        if experiment.channel_data[8].summary_data.peak_vel.value is not None:
            if plot_annotate:
                self.axes[0, 1].plot(
                    [machine_summary.rise_start_index-plot_x_start, machine_summary.peak_index-plot_x_start, machine_summary.rise_end_index-plot_x_start],
                    [plot_data[machine_summary.rise_start_index-plot_x_start], plot_data[machine_summary.peak_index-plot_x_start], plot_data[machine_summary.rise_end_index-plot_x_start]],
                    '.',
                    markersize='5',
                    color="red"
                )
            self.axes[0, 1].add_artist(self.get_summary_box(machine_summary))
        self.axes[0, 1].format_coord = lambda x, y: '{:0.0f} ms'.format(x*nav_coor_div) + ', ' + '{:0.2f} rad/s'.format(y)

        ##############################################################################################################
        # All Accelerometers
        ##############################################################################################################
        self.axes[1, 1].set_title('Head - Translations',
                                  pad=3.0, loc='center',
                                  fontdict={'fontsize': 10, 'fontweight': 'normal', 'color': 'black',
                                            'verticalalignment': 'baseline', 'horizontalalignment': 'center'}
                                  )
        self.axes[1, 1].set_ylim(-500, 500)
        self.axes[1, 1].set_ylabel(experiment.channel_data[3].meta_data.eu)
        self.axes[1, 1].plot(experiment.channel_data[3].get_filtered_data(start=plot_x_start, stop=plot_x_end),
                             label='Coronal', color='#000000', linewidth=1)
        self.axes[1, 1].plot(experiment.channel_data[4].get_filtered_data(start=plot_x_start, stop=plot_x_end),
                             label='Sagittal', color='green', linewidth=1)
        self.axes[1, 1].plot(experiment.channel_data[5].get_filtered_data(start=plot_x_start, stop=plot_x_end),
                             label='Axial', color='orange', linewidth=1)
        self.axes[1, 1].format_coord = lambda x, y: '{:0.0f} ms'.format(x*nav_coor_div) + ', ' + '{:0.2f} g'.format(y)
        self.axes[1, 1].legend()

        ##############################################################################################################
        # head primary plotted with head resultant
        ##############################################################################################################
        self.axes[2, 1].set_title('Head - Coronal and Rotation Resultant',
                                  pad=3.0, loc='center',
                                  fontdict={'fontsize': 10,'fontweight': 'normal','color': 'black',
                                            'verticalalignment': 'baseline', 'horizontalalignment': 'center'}
                                  )
        self.axes[2, 1].set_ylim(min_y, max_y)
        self.axes[2, 1].yaxis.set_ticks(y_tick_loc)
        self.axes[2, 1].set_yticklabels(y_tick_labels)
        self.axes[2, 1].set_ylabel(experiment.channel_data[0].meta_data.eu)
        self.axes[2, 1].plot(experiment.channel_data[0].get_filtered_data(start=plot_x_start, stop=plot_x_end),
                             label='Coronal', color='#000000', linewidth=1)
        self.axes[2, 1].plot(head_resultant[plot_x_start:plot_x_end],
                             label='Rotation Resultant', color='#db3e27', linewidth=1)
        self.axes[2, 1].format_coord = lambda x, y: '{:0.0f} ms'.format(x*nav_coor_div) + ', ' + '{:0.2f} rad/s'.format(y)
        self.axes[2, 1].legend()

        ##############################################################################################################
        # machine primary plotted with head resultant
        ##############################################################################################################
        self.axes[3, 1].set_title('Machine Primary and Head Rotation Resultant',
                                  pad=3.0, loc='center',
                                  fontdict={'fontsize': 10, 'fontweight': 'normal', 'color': 'black',
                                            'verticalalignment': 'baseline', 'horizontalalignment': 'center'}
                                  )
        self.axes[3, 1].set_ylim(min_y, max_y)
        self.axes[3, 1].yaxis.set_ticks(y_tick_loc)
        self.axes[3, 1].set_yticklabels(y_tick_labels)
        self.axes[3, 1].set_ylabel(experiment.channel_data[8].meta_data.eu)
        self.axes[3, 1].plot(experiment.channel_data[8].get_filtered_data(start=plot_x_start, stop=plot_x_end),
                             label='Machine Primary', color='#000000', linewidth=1)
        self.axes[3, 1].plot(head_resultant[plot_x_start:plot_x_end],
                             label='Head Rotation Resultant', color='#db3e27', linewidth=1)
        self.axes[3, 1].set_xlim(1, 5000)
        self.axes[3, 1].format_coord = lambda x, y: '{:0.0f} ms'.format(x*nav_coor_div) + ', ' + '{:0.2f} rad/s'.format(y)
        self.axes[3, 1].legend()

        # add code version to plot. Retreive from caller
        daq_version_str = 'Version: ' + inspect.currentframe().f_back.f_globals['__version__']
        self.fig.text(0.98, 0.00, daq_version_str, fontsize=6, horizontalalignment='right', verticalalignment='bottom',
                      transform=self.fig.transFigure)

        # refresh canvas so plot is updated
        self.canvas.draw()

    def clear_plot(self):
        """ clear the plot """

        (row_count, col_count) = self.axes.shape

        for row_i in range(0, row_count):
            for col_i in range(0, col_count):
                # remove all plots
                del self.axes[row_i, col_i].lines[:]
                self.reset_history()

                # remove all text boxes
                del self.axes[row_i, col_i].artists[:]

                # clean up legend if it is initialized
                if self.axes[row_i, col_i].get_legend() is not None:
                    self.axes[row_i, col_i].get_legend().remove()
                    self.axes[row_i, col_i].legend_ = None

        # remove positive phase and reset reference
        if self.positive_phase_area is not None:
            self.positive_phase_area.remove()
            self.positive_phase_area = None

        # clean up legend if it is initialized
        if self.axes[0, 0].leg is not None:
            self.axes[0, 0].leg.remove()
            self.axes[0, 0].leg = None

        # remove annotations
        for ann in self.annotation_list:
            ann.remove()
        self.annotation_list = []

        # remove independent y plot
        if self.y2 is not None:
            self.y2.remove()
            self.y2 = None

        self.fig.suptitle('')

        # refresh canvas
        self.canvas.draw()

    def reset_history(self):
        """ clear plot history """
        # init plot history
        self.underlay_peak_index = 0
        self.current_sample_rate = 0

    def get_summary_box(self, summary: slice.Channel.Summary) -> matplotlib.offsetbox.AnchoredText:
        """
        Return anchored text object to place in plot
        :rtype: matplotlib.offsetbox.AnchoredText
        :param summary:
        :return:
        """
        from matplotlib.offsetbox import AnchoredText

        summary_txt = "{}{:0.2f} ${}$\n{}{:0.2f} ${}$  {}{:0.2f} ${}$\n{}{:0.2f} ${}$  {}{:0.2f} ${}$".format(
            'Peak: ', summary.peak_vel.value, summary.peak_vel.unit,
            'Acc: ', summary.time_to_peak.value, summary.time_to_peak.unit,
            'Dec: ', summary.decel_time.value, summary.decel_time.unit,
            'Fwhm: ', summary.fwhm.value, summary.fwhm.unit,
            'Delta t: ', summary.delta_t.value, summary.delta_t.unit
        )

        # add anchor box artist to plot
        # NOTE: this works as long as my only artists are summary boxes
        anchored_text = AnchoredText(summary_txt, loc='upper right',
                                     prop=dict(family='sans-serif', size=10, weight='bold', linespacing=1.0))
        anchored_text.patch.set_boxstyle("round, pad=0.0, rounding_size=0.2")
        anchored_text.patch.set_facecolor('white')
        anchored_text.patch.set_edgecolor('gray')
        anchored_text.patch.set_linewidth(1)
        anchored_text.patch.set_alpha(0.95)

        return anchored_text
