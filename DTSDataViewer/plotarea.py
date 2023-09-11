#! /usr/bin/env python
# -*- coding: utf-8 -*-
#
import inspect

import matplotlib.offsetbox
import numpy as np
from PyQt5 import QtWidgets
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
from matplotlib.ticker import NullLocator
from matplotlib.widgets import Cursor
from dts_file_reader import slice
from DTSDataViewer.experiment import Experiment


class AnnotatedCursor(Cursor):
    """
    A crosshair cursor like `~matplotlib.widgets.Cursor` with a text showing \
    the current coordinates.

    For the cursor to remain responsive you must keep a reference to it.
    The data of the axis specified as *dataaxis* must be in ascending
    order. Otherwise, the `numpy.searchsorted` call might fail and the text
    disappears. You can satisfy the requirement by sorting the data you plot.
    Usually the data is already sorted (if it was created e.g. using
    `numpy.linspace`), but e.g. scatter plots might cause this problem.
    The cursor sticks to the plotted line.

    Parameters
    ----------
    line : `matplotlib.lines.Line2D`
        The plot line from which the data coordinates are displayed.

    numberformat : `python format string <https://docs.python.org/3/\
    library/string.html#formatstrings>`_, optional, default: "{0:.4g};{1:.4g}"
        The displayed text is created by calling *format()* on this string
        with the two coordinates.

    offset : (float, float) default: (5, 5)
        The offset in display (pixel) coordinates of the text position
        relative to the cross hair.

    dataaxis : {"x", "y"}, optional, default: "x"
        If "x" is specified, the vertical cursor line sticks to the mouse
        pointer. The horizontal cursor line sticks to *line*
        at that x value. The text shows the data coordinates of *line*
        at the pointed x value. If you specify "y", it works in the opposite
        manner. But: For the "y" value, where the mouse points to, there might
        be multiple matching x values, if the plotted function is not biunique.
        Cursor and text coordinate will always refer to only one x value.
        So if you use the parameter value "y", ensure that your function is
        biunique.

    Other Parameters
    ----------------
    textprops : `matplotlib.text` properties as dictionary
        Specifies the appearance of the rendered text object.

    **cursorargs : `matplotlib.widgets.Cursor` properties
        Arguments passed to the internal `~matplotlib.widgets.Cursor` instance.
        The `matplotlib.axes.Axes` argument is mandatory! The parameter
        *useblit* can be set to *True* in order to achieve faster rendering.

    """

    def __init__(self, line, numberformat="{0:.4g};{1:.4g}", offset=(20, 25),
                 dataaxis='x', textprops=None, **cursorargs):
        if textprops is None:
            textprops = {}
        # The line object, for which the coordinates are displayed
        self.line = line
        # The format string, on which .format() is called for creating the text
        self.numberformat = numberformat
        # Text position offset
        self.offset = np.array(offset)
        # The axis in which the cursor position is looked up
        self.dataaxis = dataaxis

        # First call baseclass constructor.
        # Draws cursor and remembers background for blitting.
        # Saves ax as class attribute.
        super().__init__(**cursorargs)

        if self.dataaxis == 'x' or self.dataaxis == 'y':
            # Default value for position of text.
            self.set_position(self.line.get_xdata()[0], self.line.get_ydata()[0])

        # Create invisible animated text
        self.text = self.ax.text(
            self.ax.get_xbound()[0],
            self.ax.get_ybound()[0],
            "0, 0",
            animated=bool(self.useblit),
            visible=False, **textprops,
            snap=True,
            bbox=dict(boxstyle='square', fc=textprops['backgroundcolor'], ec='none', pad=0.3)
        )
        # The position at which the cursor was last drawn
        self.lastdrawnplotpoint = None

    def onmove(self, event):
        """
        Overridden draw callback for cursor. Called when moving the mouse.
        """
        # Leave method under the same conditions as in overridden method
        if self.ignore(event):
            self.lastdrawnplotpoint = None
            return
        if not self.canvas.widgetlock.available(self):
            self.lastdrawnplotpoint = None
            return

        # If the mouse left drawable area, we now make the text invisible.
        # Baseclass will redraw complete canvas after, which makes both text
        # and cursor disappear.
        if event.inaxes != self.ax:
            self.lastdrawnplotpoint = None
            self.text.set_visible(False)
            super().onmove(event)
            return

        if self.dataaxis == 'x' or self.dataaxis == 'y':
            # crosshairs locked to plot
            # Get the coordinates, which should be displayed as text,
            # if the event coordinates are valid.
            plotpoint = None
            if event.xdata is not None and event.ydata is not None:
                # Get plot point related to current x position.
                # These coordinates are displayed in text.
                plotpoint = self.set_position(event.xdata, event.ydata)
                # Modify event, such that the cursor is displayed on the
                # plotted line, not at the mouse pointer,
                # if the returned plot point is valid
                if plotpoint is not None:
                    event.xdata = plotpoint[0]
                    event.ydata = plotpoint[1]

        else:
            # crosshairs not locked to plot
            plotpoint = (event.xdata, event.ydata)

        # If the plotpoint is given, compare to last drawn plotpoint and
        # return if they are the same.
        # Skip even the call of the base class, because this would restore the
        # background, draw the cursor lines and would leave us the job to
        # re-draw the text.
        if plotpoint is not None and plotpoint == self.lastdrawnplotpoint:
            return

        # Baseclass redraws canvas and cursor. Due to blitting,
        # the added text is removed in this call, because the
        # background is redrawn.
        super().onmove(event)

        # Check if the display of text is still necessary.
        # If not, just return.
        # This behaviour is also cloned from the base class.
        if not self.get_active() or not self.visible:
            return

        # Draw the widget, if event coordinates are valid.
        if plotpoint is not None:
            # Update position and displayed text.
            # Position: Where the event occurred.
            # Text: Determined by set_position() method earlier
            # Position is transformed to pixel coordinates,
            # an offset is added there and this is transformed back.
            temp = [event.xdata, event.ydata]
            temp = self.ax.transData.transform(temp)
            temp = temp + self.offset
            temp = self.ax.transData.inverted().transform(temp)
            self.text.set_position(temp)
            self.text.set_text(self.numberformat.format(*plotpoint))
            self.text.set_visible(self.visible)

            # Tell base class, that we have drawn something.
            # Baseclass needs to know, that it needs to restore a clean
            # background, if the cursor leaves our figure context.
            self.needclear = True

            # Remember the recently drawn cursor position, so events for the
            # same position (mouse moves slightly between two plot points)
            # can be skipped
            self.lastdrawnplotpoint = plotpoint
        # otherwise, make text invisible
        else:
            self.text.set_visible(False)

        # Draw changes. Cannot use _update method of baseclass,
        # because it would first restore the background, which
        # is done already and is not necessary.
        if self.useblit:
            self.ax.draw_artist(self.text)
            self.canvas.blit(self.ax.bbox)
        else:
            # If blitting is deactivated, the overridden _update call made
            # by the base class immediately returned.
            # We still have to draw the changes.
            self.canvas.draw_idle()

    def set_position(self, xpos, ypos):
        """
        Finds the coordinates, which have to be shown in text.

        The behaviour depends on the *dataaxis* attribute. Function looks
        up the matching plot coordinate for the given mouse position.

        Parameters
        ----------
        xpos : float
            The current x position of the cursor in data coordinates.
            Important if *dataaxis* is set to 'x'.
        ypos : float
            The current y position of the cursor in data coordinates.
            Important if *dataaxis* is set to 'y'.

        Returns
        -------
        ret : {2D array-like, None}
            The coordinates which should be displayed.
            *None* is the fallback value.
        """

        # Get plot line data
        xdata = self.line.get_xdata()
        ydata = self.line.get_ydata()

        # The dataaxis attribute decides, in which axis we look up which cursor
        # coordinate.
        if self.dataaxis == 'x':
            pos = xpos
            data = xdata
            lim = self.ax.get_xlim()
        elif self.dataaxis == 'y':
            pos = ypos
            data = ydata
            lim = self.ax.get_ylim()
        else:
            raise ValueError(f"The data axis specifier {self.dataaxis} should "
                             f"be 'x' or 'y'")

        # If position is valid and in valid plot data range.
        if pos is not None and lim[0] <= pos <= lim[-1]:
            # Find closest x value in sorted x vector.
            # This requires the plotted data to be sorted.
            index = np.searchsorted(data, pos)
            # Return none, if this index is out of range.
            if index < 0 or index >= len(data):
                return None
            # Return plot point as tuple.
            return xdata[index], ydata[index]

        # Return none if there is no good related point for this x position.
        return None

    def clear(self, event):
        """
        Overridden clear callback for cursor, called before drawing the figure.
        """

        # The base class saves the clean background for blitting.
        # Text and cursor are invisible,
        # until the first mouse move event occurs.
        super().clear(event)
        if self.ignore(event):
            return
        self.text.set_visible(False)

    def _update(self):
        """
        Overridden method for either blitting or drawing the widget canvas.

        Passes call to base class if blitting is activated, only.
        In other cases, one draw_idle call is enough, which is placed
        explicitly in this class (see *onmove()*).
        In that case, `~matplotlib.widgets.Cursor` is not supposed to draw
        something using this method.
        """

        if self.useblit:
            super()._update()


class PlotArea(QtWidgets.QVBoxLayout):
    """
    Plots an Experiment
    """

    def __init__(self, parent=None):
        super(PlotArea, self).__init__()

        # reference for experiment - 20230603
        self.experiment = Experiment()

        self.current_sample_rate = None
        self.underlay_peak_index = None
        self.fig = Figure((5.0, 4.0), facecolor='#e2e2e2', edgecolor=None, frameon=True)
        self.canvas = FigureCanvas(self.fig)
        self.canvas.setParent(parent)
        # connect button event to callback for manual user peak selection
        self.fig.canvas.mpl_connect('button_release_event', self.user_peak_selected)
        self.gui_axes_fontsize = 'small'

        # Create the navigation toolbar, tied to the canvas
        mpl_toolbar = NavigationToolbar(self.canvas, parent)

        # Since we have only one plot, we can use add_axes
        # instead of add_subplot, but then the subplot
        # configuration tool in the navigation toolbar wouldn't
        # work.
        self.axes = self.fig.subplots(nrows=4, ncols=2, sharex=True, sharey=False)
        (row_count, col_count) = self.axes.shape

        # annotated cursors reference
        self.cursors = np.empty(self.axes.shape, dtype=AnnotatedCursor)

        # independent scaled plot object
        self.y2 = None

        # notate axis units
        for row_i in range(0, row_count):
            self.axes[row_i, 0].set_ylabel('', fontsize=self.gui_axes_fontsize)
            self.axes[row_i, 1].set_ylabel('', fontsize=self.gui_axes_fontsize)

        self.axes[3, 0].set_xlabel('Time(ms)', fontsize=self.gui_axes_fontsize)
        self.axes[3, 1].set_xlabel('Time(ms)', fontsize=self.gui_axes_fontsize)

        # add gridlines to plot
        for row_i in range(0, row_count):
            for col_i in range(0, col_count):
                self.axes[row_i, col_i].grid(color='#eeeeee')

        self.addWidget(self.canvas)
        self.addWidget(mpl_toolbar)

        # initialize summarybox and provide reference
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
        self.fig.subplots_adjust(top=0.938, bottom=0.061, left=0.036, right=0.985, hspace=0.187, wspace=0.094)

    def plot(self, experiment, plot_annotate, plot_cursor_tracks_data):
        """ plotting

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

        # experiment reference - 20230603
        self.experiment = experiment

        if experiment.channel_data is None:
            return

        self.fig.suptitle(experiment.get_label(), fontsize='medium')


        # data display window
        x_data = list(map(lambda x: x/(experiment.channel_data[0].meta_data.sample_rate_hz/1000), range(0, experiment.window_samples)))
        min_y = -150
        max_y = 350
        x_tick_loc = list(map(lambda x: x/(experiment.channel_data[0].meta_data.sample_rate_hz/1000), np.arange(0,
                                                                                                                (int(experiment.channel_data[0].meta_data.sample_rate_hz / 8) +
                                                                                                                 int((experiment.channel_data[0].meta_data.sample_rate_hz / 8) / 5)
                                                                                                                 ), int((experiment.channel_data[0].meta_data.sample_rate_hz / 8) / 5)
                                                                                                                )
                              )
                          )

        x_tick_labels = list(map(lambda x: int(x), x_tick_loc))
        y_tick_loc = np.arange(min_y, max_y, 50)
        y_tick_labels = ['', '-100', '', '0', '', '100', '', '200', '', '300']

        ##############################################################################################################
        # Head - Coronal
        ##############################################################################################################
        # axes id used for identification not to be visible to user. callbacks depend on these
        self.axes[0, 0].set_label('id_head_rot_cor')
        self.axes[0, 0].set_title('Head - Coronal',
                                  pad=3.0, loc='center',
                                  fontdict={'fontsize': self.gui_axes_fontsize, 'fontweight': 'normal', 'color': 'black',
                                            'verticalalignment': 'baseline', 'horizontalalignment': 'center'}
                                  )
        self.axes[0, 0].set_ylim(min_y, max_y)
        self.axes[0, 0].yaxis.set_ticks(y_tick_loc)
        self.axes[0, 0].set_yticklabels(y_tick_labels, fontsize=self.gui_axes_fontsize)
        self.axes[0, 0].xaxis.set_ticks(x_tick_loc)
        self.axes[0, 0].set_xticklabels(x_tick_labels, fontsize=self.gui_axes_fontsize)
        self.axes[0, 0].set_xlim(x_tick_labels[0], x_tick_labels[-1])
        self.axes[0, 0].set_ylabel(experiment.get_channel('head_rot_cor').meta_data.eu, fontsize=self.gui_axes_fontsize)
        y_data = experiment.get_channel('head_rot_cor').get_filtered_data(start=experiment.data_window_start, stop=experiment.data_window_end)
        self.axes[0, 0].plot(x_data, y_data, color='#000000', linewidth=1, snap=True, label='id_trace')

        # only show summary if it is populated
        if experiment.get_channel('head_rot_cor').summary_data.peak_vel.value is not None:
            if plot_annotate:
                # markers and summary value locations visible
                self.axes[0, 0].plot(
                    [(experiment.head_summary.rise_start_index-experiment.data_window_start)/(experiment.get_channel('head_rot_cor').meta_data.sample_rate_hz/1000), (experiment.head_summary.peak_index-experiment.data_window_start)/(experiment.get_channel('head_rot_cor').meta_data.sample_rate_hz/1000), (experiment.head_summary.rise_end_index-experiment.data_window_start)/(experiment.get_channel('head_rot_cor').meta_data.sample_rate_hz/1000)],
                    [y_data[experiment.head_summary.rise_start_index-experiment.data_window_start], y_data[experiment.head_summary.peak_index-experiment.data_window_start], y_data[experiment.head_summary.rise_end_index-experiment.data_window_start]],
                    '.',
                    markersize='4',
                    color="red",
                    # label for program identification
                    label='id_annot'
                )

            self.axes[0, 0].add_artist(self.get_summary_box(experiment.head_summary))

        # animated cursor visible
        self.cursors[0, 0] = AnnotatedCursor(
            line=self.axes[0, 0].lines[0],
            color='#000000',
            numberformat="{:0.3f} ms; {:0.2f} rad/s",
            dataaxis=plot_cursor_tracks_data,
            textprops={'color': '#000000', 'fontweight': 'normal', 'fontsize': 'small', 'backgroundcolor': '#F3F3F3'},
            ax=self.axes[0, 0],
            useblit=True,
            linewidth=0.5, linestyle='dotted')

        # control the plot coordinate display in navigation toolbar
        self.axes[0, 0].format_coord = self.format_coord

        ##############################################################################################################
        # Head - Sagittal
        ##############################################################################################################
        self.axes[1, 0].set_title('Head - Sagittal',
                                  pad=3.0, loc='center',
                                  fontdict={'fontsize': self.gui_axes_fontsize, 'fontweight': 'normal', 'color': 'black',
                                            'verticalalignment': 'baseline', 'horizontalalignment': 'center'}
                                  )
        self.axes[1, 0].set_ylim(min_y, max_y)
        self.axes[1, 0].yaxis.set_ticks(y_tick_loc)
        self.axes[1, 0].set_yticklabels(y_tick_labels, fontsize=self.gui_axes_fontsize)
        self.axes[1, 0].xaxis.set_ticks(x_tick_loc)
        self.axes[1, 0].set_xticklabels(x_tick_labels, fontsize=self.gui_axes_fontsize)
        self.axes[1, 0].set_ylabel(experiment.get_channel('head_rot_sag').meta_data.eu, fontsize=self.gui_axes_fontsize)
        self.axes[1, 0].plot(x_data, experiment.get_channel('head_rot_sag').get_filtered_data(start=experiment.data_window_start, stop=experiment.data_window_end),
                             color='green', linewidth=1, snap=True)
        self.axes[1, 0].format_coord = self.format_coord

        # animated cursor visible
        self.cursors[1, 0] = AnnotatedCursor(
            line=self.axes[1, 0].lines[0],
            color='#000000',
            numberformat="{:0.3f} ms; {:0.2f} rad/s",
            dataaxis=plot_cursor_tracks_data,
            textprops={'color': '#000000', 'fontweight': 'normal', 'fontsize': 'small', 'backgroundcolor': '#F3F3F3'},
            ax=self.axes[1, 0],
            useblit=True,
            linewidth=0.5, linestyle='dotted')

        ##############################################################################################################
        # Head - Axial
        ##############################################################################################################
        self.axes[2, 0].set_title('Head - Axial',
                                  pad=3.0, loc='center',
                                  fontdict={'fontsize': self.gui_axes_fontsize, 'fontweight': 'normal', 'color': 'black',
                                            'verticalalignment': 'baseline', 'horizontalalignment': 'center'}
                                  )
        self.axes[2, 0].set_ylim(min_y, max_y)
        self.axes[2, 0].yaxis.set_ticks(y_tick_loc)
        self.axes[2, 0].set_yticklabels(y_tick_labels, fontsize=self.gui_axes_fontsize)
        self.axes[2, 0].xaxis.set_ticks(x_tick_loc)
        self.axes[2, 0].set_xticklabels(x_tick_labels, fontsize=self.gui_axes_fontsize)
        self.axes[2, 0].set_ylabel(experiment.get_channel('head_rot_axi').meta_data.eu, fontsize=self.gui_axes_fontsize)
        self.axes[2, 0].plot(x_data, experiment.get_channel('head_rot_axi').get_filtered_data(start=experiment.data_window_start, stop=experiment.data_window_end),
                             color='orange', linewidth=1, snap=True)
        self.axes[2, 0].format_coord = self.format_coord

        # animated cursor visible
        self.cursors[2, 0] = AnnotatedCursor(
            line=self.axes[2, 0].lines[0],
            color='#000000',
            numberformat="{:0.3f} ms; {:0.2f} rad/s",
            dataaxis=plot_cursor_tracks_data,
            textprops={'color': '#000000', 'fontweight': 'normal', 'fontsize': 'small', 'backgroundcolor': '#F3F3F3'},
            ax=self.axes[2, 0],
            useblit=True,
            linewidth=0.5, linestyle='dotted')

        ##############################################################################################################
        # Head - Resultant
        ##############################################################################################################
        self.axes[3, 0].set_label('id_head_rot_res')
        self.axes[3, 0].set_title('Head - Rotation Resultant',
                                  pad=3.0, loc='center',
                                  fontdict={'fontsize': self.gui_axes_fontsize, 'fontweight': 'normal', 'color': 'black',
                                            'verticalalignment': 'baseline', 'horizontalalignment': 'center'}
                                  )
        self.axes[3, 0].set_ylim(min_y, max_y)
        self.axes[3, 0].yaxis.set_ticks(y_tick_loc)
        self.axes[3, 0].set_yticklabels(y_tick_labels, fontsize=self.gui_axes_fontsize)
        self.axes[3, 0].set_ylabel(experiment.get_channel('head_rot_cor').meta_data.eu, fontsize=self.gui_axes_fontsize)
        self.axes[3, 0].plot(x_data, experiment.head_resultant[experiment.data_window_start:experiment.data_window_end], color='#db3e27', linewidth=1, snap=True, label='id_trace')
        self.axes[3, 0].xaxis.set_ticks(x_tick_loc)
        self.axes[3, 0].set_xticklabels(x_tick_labels, fontsize=self.gui_axes_fontsize)
        self.axes[3, 0].xaxis.set_minor_locator(NullLocator())
        self.axes[3, 0].format_coord = self.format_coord

        # only show summary if it is populated
        if experiment.head_resultant_summary.peak_vel.value is not None:
            if plot_annotate:
                self.axes[3, 0].plot(
                    [(experiment.head_resultant_summary.rise_start_index-experiment.data_window_start)/(experiment.get_channel('head_rot_cor').meta_data.sample_rate_hz/1000), (experiment.head_resultant_summary.peak_index-experiment.data_window_start)/(experiment.get_channel('head_rot_cor').meta_data.sample_rate_hz/1000), (experiment.head_resultant_summary.rise_end_index-experiment.data_window_start)/(experiment.get_channel('head_rot_cor').meta_data.sample_rate_hz/1000)],
                    [experiment.head_resultant[experiment.head_resultant_summary.rise_start_index], experiment.head_resultant[experiment.head_resultant_summary.peak_index], experiment.head_resultant[experiment.head_resultant_summary.rise_end_index]],
                    '.',
                    markersize='4',
                    color="#000000",
                    label='id_annot'
                )

            self.axes[3, 0].add_artist(self.get_summary_box(experiment.head_resultant_summary))

        # animated cursor visible
        self.cursors[3, 0] = AnnotatedCursor(
            line=self.axes[3, 0].lines[0],
            color='#000000',
            numberformat="{:0.3f} ms; {:0.2f} rad/s",
            dataaxis=plot_cursor_tracks_data,
            textprops={'color': '#000000', 'fontweight': 'normal', 'fontsize': 'small', 'backgroundcolor': '#F3F3F3'},
            ax=self.axes[3, 0],
            useblit=True,
            linewidth=0.5, linestyle='dotted')

        ##############################################################################################################
        # Machine - Primary Axis
        ##############################################################################################################
        self.axes[0, 1].set_label('id_mach_rot_pri')
        self.axes[0, 1].set_title('Machine - Primary Axis',
                                  pad=3.0, loc='center',
                                  fontdict={'fontsize': self.gui_axes_fontsize, 'fontweight': 'normal', 'color': 'black',
                                            'verticalalignment': 'baseline', 'horizontalalignment': 'center'}
                                  )
        self.axes[0, 1].yaxis.set_ticks(y_tick_loc)
        self.axes[0, 1].set_yticklabels(y_tick_labels, fontsize=self.gui_axes_fontsize)
        self.axes[0, 1].set_ylim(min_y, max_y)
        self.axes[0, 1].set_ylabel(experiment.get_channel('mach_rot_pri').meta_data.eu, fontsize=self.gui_axes_fontsize)
        self.axes[0, 1].xaxis.set_ticks(x_tick_loc)
        self.axes[0, 1].set_xticklabels(x_tick_labels, fontsize=self.gui_axes_fontsize)
        y_data = experiment.get_channel('mach_rot_pri').get_filtered_data(start=experiment.data_window_start, stop=experiment.data_window_end)
        self.axes[0, 1].plot(x_data, y_data, color='#000000', linewidth=1, snap=True, label="id_trace")
        if experiment.get_channel('mach_rot_pri').summary_data.peak_vel.value is not None:
            if plot_annotate:
                self.axes[0, 1].plot(
                    [(experiment.machine_summary.rise_start_index-experiment.data_window_start)/(experiment.get_channel('mach_rot_pri').meta_data.sample_rate_hz/1000), (experiment.machine_summary.peak_index-experiment.data_window_start)/(experiment.get_channel('mach_rot_pri').meta_data.sample_rate_hz/1000), (experiment.machine_summary.rise_end_index-experiment.data_window_start)/(experiment.get_channel('mach_rot_pri').meta_data.sample_rate_hz/1000)],
                    [y_data[experiment.machine_summary.rise_start_index-experiment.data_window_start], y_data[experiment.machine_summary.peak_index-experiment.data_window_start], y_data[experiment.machine_summary.rise_end_index-experiment.data_window_start]],
                    '.',
                    markersize='4',
                    color="red",
                    label="id_annot"
                )

            self.axes[0, 1].add_artist(self.get_summary_box(experiment.machine_summary))

        # animated cursor visible
        self.cursors[0, 1] = AnnotatedCursor(
            line=self.axes[0, 1].lines[0],
            color='#000000',
            numberformat="{:0.3f} ms; {:0.2f} rad/s",
            dataaxis=plot_cursor_tracks_data,
            textprops={'color': '#000000', 'fontweight': 'normal', 'fontsize': 'small', 'backgroundcolor': '#F3F3F3'},
            ax=self.axes[0, 1],
            useblit=True,
            linewidth=0.5, linestyle='dotted')

        self.axes[0, 1].format_coord = self.format_coord

        ##############################################################################################################
        # All Accelerometers
        ##############################################################################################################
        self.axes[1, 1].set_title('Head - Translations',
                                  pad=3.0, loc='center',
                                  fontdict={'fontsize': self.gui_axes_fontsize, 'fontweight': 'normal', 'color': 'black',
                                            'verticalalignment': 'baseline', 'horizontalalignment': 'center'}
                                  )
        self.axes[1, 1].set_ylim(-500, 500)
        self.axes[1, 1].set_ylabel(experiment.get_channel('head_tran_cor').meta_data.eu, fontsize=self.gui_axes_fontsize)
        self.axes[1, 1].xaxis.set_ticks(x_tick_loc)
        self.axes[1, 1].set_xticklabels(x_tick_labels, fontsize=self.gui_axes_fontsize)
        self.axes[1, 1].tick_params(labelsize=self.gui_axes_fontsize)
        self.axes[1, 1].plot(x_data, experiment.get_channel('head_tran_cor').get_filtered_data(start=experiment.data_window_start, stop=experiment.data_window_end),
                             label='Coronal', color='#000000', linewidth=1, snap=True)
        self.axes[1, 1].plot(x_data, experiment.get_channel('head_tran_sag').get_filtered_data(start=experiment.data_window_start, stop=experiment.data_window_end),
                             label='Sagittal', color='green', linewidth=1, snap=True)
        self.axes[1, 1].plot(x_data, experiment.get_channel('head_tran_axi').get_filtered_data(start=experiment.data_window_start, stop=experiment.data_window_end),
                             label='Axial', color='orange', linewidth=1, snap=True)
        self.axes[1, 1].format_coord = lambda x, y: '{:0.0f} ms'.format(x) + ', ' + '{:0.2f} g'.format(y)

        # animated cursor visible
        self.cursors[1, 1] = AnnotatedCursor(
            line=self.axes[1, 1].lines[0],
            color='#000000',
            numberformat="{:0.3f} ms; {:0.2f} g",
            dataaxis='off',
            textprops={'color': '#000000', 'fontweight': 'normal', 'fontsize': 'small', 'backgroundcolor': '#F3F3F3'},
            ax=self.axes[1, 1],
            useblit=True,
            linewidth=0.5, linestyle='dotted')

        self.axes[1, 1].legend(fontsize=self.gui_axes_fontsize, loc='upper right')

        ##############################################################################################################
        # head primary plotted with head resultant
        ##############################################################################################################
        self.axes[2, 1].set_title('Head - Coronal and Rotation Resultant',
                                  pad=3.0, loc='center',
                                  fontdict={'fontsize': self.gui_axes_fontsize, 'fontweight': 'normal', 'color': 'black',
                                            'verticalalignment': 'baseline', 'horizontalalignment': 'center'}
                                  )
        self.axes[2, 1].set_ylim(min_y, max_y)
        self.axes[2, 1].yaxis.set_ticks(y_tick_loc)
        self.axes[2, 1].set_yticklabels(y_tick_labels, fontsize=self.gui_axes_fontsize)
        self.axes[2, 1].xaxis.set_ticks(x_tick_loc)
        self.axes[2, 1].set_xticklabels(x_tick_labels, fontsize=self.gui_axes_fontsize)
        self.axes[2, 1].set_ylabel(experiment.get_channel('head_rot_cor').meta_data.eu, fontsize=self.gui_axes_fontsize)
        self.axes[2, 1].plot(x_data, experiment.get_channel('head_rot_cor').get_filtered_data(start=experiment.data_window_start, stop=experiment.data_window_end),
                             label='Coronal', color='#000000', linewidth=1, snap=True)
        self.axes[2, 1].plot(x_data, experiment.head_resultant[experiment.data_window_start:experiment.data_window_end],
                             label='Rotation Resultant', color='#db3e27', linewidth=1, snap=True)
        self.axes[2, 1].format_coord = self.format_coord

        # animated cursor visible
        self.cursors[2, 1] = AnnotatedCursor(
            line=self.axes[2, 1].lines[0],
            color='#000000',
            numberformat="{:0.3f} ms; {:0.2f} rad/s",
            dataaxis='off',
            textprops={'color': '#000000', 'fontweight': 'normal', 'fontsize': 'small', 'backgroundcolor': '#F3F3F3'},
            ax=self.axes[2, 1],
            useblit=True,
            linewidth=0.5, linestyle='dotted')

        self.axes[2, 1].legend(fontsize=self.gui_axes_fontsize, loc='upper right')

        ##############################################################################################################
        # machine primary plotted with head resultant
        ##############################################################################################################
        self.axes[3, 1].set_title('Machine Primary and Head Rotation Resultant',
                                  pad=3.0, loc='center',
                                  fontdict={'fontsize': self.gui_axes_fontsize, 'fontweight': 'normal', 'color': 'black',
                                            'verticalalignment': 'baseline', 'horizontalalignment': 'center'}
                                  )
        self.axes[3, 1].set_ylim(min_y, max_y)
        self.axes[3, 1].yaxis.set_ticks(y_tick_loc)
        self.axes[3, 1].set_yticklabels(y_tick_labels, fontsize=self.gui_axes_fontsize)
        self.axes[3, 1].set_ylabel(experiment.get_channel('mach_rot_pri').meta_data.eu, fontsize=self.gui_axes_fontsize)
        self.axes[3, 1].xaxis.set_ticks(x_tick_loc)
        self.axes[3, 1].set_xticklabels(x_tick_labels, fontsize=self.gui_axes_fontsize)
        self.axes[3, 1].plot(x_data, experiment.get_channel('mach_rot_pri').get_filtered_data(start=experiment.data_window_start, stop=experiment.data_window_end),
                             label='Machine Primary', color='#000000', linewidth=1, snap=True)
        self.axes[3, 1].plot(x_data, experiment.head_resultant[experiment.data_window_start:experiment.data_window_end],
                             label='Head Rotation Resultant', color='#db3e27', linewidth=1, snap=True)
        self.axes[3, 1].format_coord = self.format_coord

        # animated cursor visible
        self.cursors[3, 1] = AnnotatedCursor(
            line=self.axes[3, 1].lines[0],
            color='#000000',
            numberformat="{:0.3f} ms; {:0.2f} rad/s",
            dataaxis='off',
            textprops={'color': '#000000', 'fontweight': 'normal', 'fontsize': 'small', 'backgroundcolor': '#F3F3F3'},
            ax=self.axes[3, 1],
            useblit=True,
            linewidth=0.5, linestyle='dotted')

        self.axes[3, 1].legend(fontsize=self.gui_axes_fontsize, loc='upper right')

        # add code version to plot. Retreive from caller
        daq_version_str = 'Version: ' + inspect.currentframe().f_back.f_globals['__version__']
        self.fig.text(0.98, 0.00, daq_version_str, fontsize='x-small', horizontalalignment='right', verticalalignment='bottom', transform=self.fig.transFigure)

        # adjust layout
        # self.fig.subplots_adjust(top=0.938, bottom=0.061, left=0.036, right=0.985, hspace=0.187, wspace=0.094)
        self.fig.subplots_adjust(top=0.938, bottom=0.066, left=0.041, right=0.99, hspace=0.169, wspace=0.119)

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

        # reset the crosshair cursors
        self.cursors = np.empty(self.axes.shape, dtype=AnnotatedCursor)

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

        summary_txt = "{}{:0.2f} ${}$   {}{:0.2f}\n{}{:0.2f} ${}$  {}{:0.2f} ${}$\n{}{:0.2f} ${}$  {}{:0.2f} ${}$".format(
            'Peak: ', summary.peak_vel.value, summary.peak_vel.unit,
            'Slope: ', summary.rise_to_peak_slope,
            'Acc: ', summary.time_to_peak.value, summary.time_to_peak.unit,
            'Dec: ', summary.decel_time.value, summary.decel_time.unit,
            'Fwhm: ', summary.fwhm.value, summary.fwhm.unit,
            'Delta t: ', summary.delta_t.value, summary.delta_t.unit
        )

        # add anchor box artist to plot
        # NOTE: this works as long as my only artists are summary boxes
        anchored_text = AnchoredText(summary_txt, loc='upper right',
                                     prop=dict(family='sans-serif', size=self.gui_axes_fontsize, weight='bold', linespacing=1.0))
        # give box a label so that we can pick it out for dynamic updates
        anchored_text.set_label('id_data_summary_box')
        anchored_text.patch.set_boxstyle("round, pad=0.0, rounding_size=0.2")
        anchored_text.patch.set_facecolor('white')
        anchored_text.patch.set_edgecolor('gray')
        anchored_text.patch.set_linewidth(1)
        anchored_text.patch.set_alpha(0.95)
        # if the peak is user selected we want to indicate that visually
        if summary.is_peak_user_selected:
            anchored_text.patch.set_edgecolor('red')
            anchored_text.patch.set_facecolor('#ffe6e6')
            anchored_text.patch.set_linestyle('dashed')

        return anchored_text

    @staticmethod
    def format_coord(x, y):
        return 'Cursor {:0.3f} ms'.format(x) + '; ' + '{:0.2f} rad/s'.format(y)

    def user_peak_selected(self, event):
        """
        A callback function for user click on plots to manually select
        a different peak.
        """
        from matplotlib.backend_bases import MouseButton
        if event.button != MouseButton.RIGHT:
            return

        # filter to axes of interest by axes label id
        if event.inaxes.get_label() in ['id_head_rot_cor', 'id_mach_rot_pri', 'id_head_rot_res']:

            # data channel id for pulling data from experiment
            channel_id = "_".join(event.inaxes.get_label().split('_')[1:])
            # device_id for determining summary data
            device_id = event.inaxes.get_label().split('_')[1]
            # axis for distinguishing both axis and single vs resultant
            axis_id = event.inaxes.get_label().split('_')[3]

            if axis_id == 'res':
                if device_id == 'head':
                    y_data_full = self.experiment.head_resultant
                    summary_data = self.experiment.head_resultant_summary
                else:
                    y_data_full = self.experiment.machine_resultant
                    summary_data = self.experiment.machine_resultant_summary
            else:
                y_data_full = self.experiment.get_channel(channel_id).get_filtered_data()
                summary_data = self.experiment.get_channel(channel_id).summary_data

            for line in event.inaxes.lines:
                # use trace plot to select peak
                if line.get_label() == 'id_trace':
                    # let user select on x axis values alone to make it easier
                    # and because these are unique ascending values
                    x_index = np.searchsorted(line.get_xdata(), event.xdata)
                    # to be consistent with default peak_index,
                    # adjust user selected peak value to make it relative to all data
                    # not just the windowed data
                    # If the user exports the windowed data the peak_index is incorrect for that
                    user_selected_peak_index = x_index + self.experiment.data_window_start
                    # update the channel summary values relevant to a new peak_index
                    slice.set_user_selected_peak(
                        summary_data,
                        y_data_full,
                        self.experiment.get_channel('head_rot_cor').meta_data.sample_rate_hz,
                        user_selected_peak_index
                    )
                    # update the channel data in the experiment so that if the user
                    # exports data it will reflect the user peak selected
                    if axis_id == 'res':
                        if device_id == 'head':
                            self.experiment.head_resultant_summary = summary_data
                        else:
                            self.experiment.machine_resultant_summary = summary_data
                    else:
                        self.experiment.get_channel(channel_id).summary_data = summary_data

                    for plot_artist in event.inaxes.artists:
                        # find the data summary box
                        if plot_artist.get_label() == 'id_data_summary_box':
                            # clear the box and add a new one with update values
                            event.inaxes.artists[0].remove()
                            summary_box = self.get_summary_box(summary_data)
                            event.inaxes.add_artist(summary_box)
                            # we are done with artist objects
                            break

                # find the annotation plot and assume it is after the trace plot
                if line.get_label() == 'id_annot':
                    # update the data for the annotation plot
                    line.set_data([(summary_data.rise_start_index - self.experiment.data_window_start) /
                                   (self.experiment.get_channel('head_rot_cor').meta_data.sample_rate_hz / 1000),
                                   (summary_data.peak_index - self.experiment.data_window_start) /
                                   (self.experiment.get_channel('head_rot_cor').meta_data.sample_rate_hz / 1000),
                                   (summary_data.rise_end_index - self.experiment.data_window_start) /
                                   (self.experiment.get_channel('head_rot_cor').meta_data.sample_rate_hz / 1000)],
                                   [y_data_full[summary_data.rise_start_index],
                                   y_data_full[summary_data.peak_index],
                                   y_data_full[summary_data.rise_end_index]
                                  ])

                    # after annot plot we are done
                    break

            # refresh canvas to make summary box and plot changes visible
            self.canvas.draw()
