import os
import datetime
from dts_file_reader import slice
import numpy as np


class Experiment:
    """
    An instance of data collection either from the sensor or a data file.
    Settings specific to that instance and its data.
    """

    def __init__(self):

        # initiate container for data
        self.channel_data = None

        # experiment provides channel map specific to our experiment
        # DTS slice reader is dependent on what user entered in DTS channel setup. That should be generic.
        self.channel_map = {
            'head_rot_cor': 0,
            'head_rot_sag': 1,
            'head_rot_axi': 2,
            'head_tran_cor': 3,
            'head_tran_sag': 4,
            'head_tran_axi': 5,
            'mach_rot_sec': 6,
            'mach_rot_ter': 7,
            'mach_rot_pri': 8,
        }

        # now store summary and resultants in experiment for export
        self.machine_summary = slice.Channel.Summary()
        self.head_summary = slice.Channel.Summary()
        self.head_resultant = None
        self.data_window_start = 0
        self.data_window_end = 0

        # From where did we last open a DTS file?
        self.lastDataPath = ''
        self.lastExportPath = ''

    def get_label(self):
        """
        name for experiment
        """
        # remove file extension
        # and remove head
        return self.file_name.split('.')[0]

    @classmethod
    def load(cls, data_file_path):

        experiment = Experiment()
        experiment.lastDataPath = os.path.sep.join(str(data_file_path).split('/')[0:-1])
        experiment.file_name = str(data_file_path).split('/')[-1]
        experiment.channel_data = slice.Reader().parse(str(data_file_path))

        # need summary data of a primary channel to determine location of peak
        # to window the data to 1/8 of a second
        # the head sensor will not be reliable as its orientation will change
        # machine sensor orientation is fixed so use that channel to get summary data
        experiment.machine_summary = experiment.get_channel('mach_rot_pri').get_channel_summary(method='machine')
        experiment.head_summary = experiment.get_channel('head_rot_cor').get_channel_summary(method='head')

        # get head resultant, use entire vector so that this resultant can be passed to get_summary()
        # which works only on full timeseries.
        # down below where we plot the data we will window the resultant to display window
        experiment.head_resultant = slice.get_resultant(experiment.channel_data, (0, 1, 2))
        experiment.head_resultant_summary = slice.get_data_summary(method='head',
                                                        sample_rate_hz=experiment.get_channel('head_rot_cor').meta_data.sample_rate_hz,
                                                        data=experiment.head_resultant)
        
        # data display/export window
        experiment.data_window_start = 0
        experiment.data_window_end = 0
        experiment.window_samples = int(experiment.get_channel('head_rot_cor').meta_data.sample_rate_hz / 8)
        pre_peak_samples = int(experiment.window_samples/4)
        post_peak_sample = int(pre_peak_samples*3)
        #print(f"pre:{pre_peak_samples}, post:{post_peak_sample}")

        # window large data vector around peak velocity value
        # first use the machine sensor, then try the head sensor
        # otherwise, a meaningless window of data at the start of the vector
        if experiment.machine_summary.peak_index == 0:
            if experiment.head_summary.peak_index == 0:
                experiment.data_window_start = 0
                experiment.data_window_end = experiment.window_samples
            else:
                experiment.data_window_start = experiment.head_summary.peak_index - pre_peak_samples - 1
                experiment.data_window_end = experiment.head_summary.peak_index + post_peak_sample - 1
        else:
            experiment.data_window_start = experiment.machine_summary.peak_index - pre_peak_samples - 1
            experiment.data_window_end = experiment.machine_summary.peak_index + post_peak_sample - 1


        return experiment

    def get_channel(self, channel_map_key):
        """
        Retrieve channel object by key
        """
        if channel_map_key not in self.channel_map.keys():
            raise ValueError(f"Invalid channel map key: '{channel_map_key}'")

        return self.channel_data[self.channel_map[channel_map_key]]

    def remove_baseline_offset(self, single_channel_data, baseline_index_start=0, baseline_index_end=500) -> np.ndarray:
        """
        Remove baseline offset from a single channel array using the start and end to define location of baseline
        measure.
        @return: array of same size with baseline subtracted
        """

        if (not isinstance(baseline_index_start, int)) or (not isinstance(baseline_index_end, int)):
            raise ValueError("baseline_index_start and baseline_index_end values must be integers")

        if baseline_index_end < baseline_index_start:
            raise ValueError("baseline_index_end value must be greater than baseline_index_start")

        return single_channel_data - np.mean(single_channel_data[baseline_index_start:baseline_index_end])

    def export(self, export_path, window_anchor: str = 'rise_start'):
        """
        Export windowed data and summaries.
        'window_anchor' string can be 'peak' or 'rise_start' and determines how data window
        is centered. By default, data window in centered on peak for viewing in dataviewer.
        """

        if (window_anchor != 'peak') and (window_anchor != 'rise_start'):
            raise ValueError("window_anchor must be 'peak' or 'rise_start'")

        export_window_start = self.data_window_start
        export_window_end = self.data_window_end
        if window_anchor == 'rise_start':
            pre_peak_samples = int((self.window_samples / 4)/2)
            post_peak_sample = int(((self.window_samples / 4) * 3) + (self.window_samples / 4)/2)

            if self.machine_summary.rise_start_index == 0:
                if self.head_summary.rise_start_index == 0:
                    export_window_start = 0
                    export_window_end = self.window_samples
                else:
                    export_window_start = self.head_summary.rise_start_index - pre_peak_samples - 1
                    export_window_end = self.head_summary.rise_start_index + post_peak_sample - 1
            else:
                export_window_start = self.machine_summary.rise_start_index - pre_peak_samples - 1
                export_window_end = self.machine_summary.rise_start_index + post_peak_sample - 1

        # export raw scaled data
        np.savetxt(
            os.path.join(export_path, "_".join([self.get_label(), 'export', 'raw.csv'])),
            np.array(list(map(lambda x: self.remove_baseline_offset(x.scaled_data[export_window_start:export_window_end]), self.channel_data))).transpose(),
            fmt='%.11f',
            delimiter=',',
            header=",".join(self.channel_map.keys())
        )

        # export filtered data
        np.savetxt(
            os.path.join(export_path, "_".join([self.get_label(), 'export', 'filtered.csv'])),
            np.array(list(map(lambda x: self.remove_baseline_offset(x.get_filtered_data(start=export_window_start, stop=export_window_end)), self.channel_data))).transpose(),
            fmt='%.11f',
            delimiter=',',
            header=",".join(self.channel_map.keys())
        )

        # export three summaries
        with open(os.path.join(export_path, "_".join([self.get_label(), 'export', 'summary.csv'])), "w") as summary_file:
            summary_file.write("summary,peak_index,rise_start_index,rise_end_index,peak_vel,time_to_peak,decel_time,fwhm,delta_t,rise_to_peak_slope,is_peak_user_selected\n")

            summary_file.write(",".join(['head_rot_cor',
                                         str(self.get_channel('head_rot_cor').summary_data.peak_index),
                                         str(self.get_channel('head_rot_cor').summary_data.rise_start_index),
                                         str(self.get_channel('head_rot_cor').summary_data.rise_end_index),
                                         str(self.get_channel('head_rot_cor').summary_data.peak_vel.value),
                                         str(self.get_channel('head_rot_cor').summary_data.time_to_peak.value),
                                         str(self.get_channel('head_rot_cor').summary_data.decel_time.value),
                                         str(self.get_channel('head_rot_cor').summary_data.fwhm.value),
                                         str(self.get_channel('head_rot_cor').summary_data.delta_t.value),
                                         str(self.get_channel('head_rot_cor').summary_data.rise_to_peak_slope),
                                         str(bool(self.get_channel('head_rot_cor').summary_data.is_peak_user_selected)),
                                         '\n'
                                        ])
                               )

            summary_file.write(",".join(['head_resultant',
                                         str(self.head_resultant_summary.peak_index),
                                         str(self.head_resultant_summary.rise_start_index),
                                         str(self.head_resultant_summary.rise_end_index),
                                         str(self.head_resultant_summary.peak_vel.value),
                                         str(self.head_resultant_summary.time_to_peak.value),
                                         str(self.head_resultant_summary.decel_time.value),
                                         str(self.head_resultant_summary.fwhm.value),
                                         str(self.head_resultant_summary.delta_t.value),
                                         str(self.head_resultant_summary.rise_to_peak_slope),
                                         str(bool(self.head_resultant_summary.is_peak_user_selected)),
                                         '\n'
                                        ])
                               )

            summary_file.write(",".join(['mach_rot_pri',
                                         str(self.machine_summary.peak_index),
                                         str(self.machine_summary.rise_start_index),
                                         str(self.machine_summary.rise_end_index),
                                         str(self.machine_summary.peak_vel.value),
                                         str(self.machine_summary.time_to_peak.value),
                                         str(self.machine_summary.decel_time.value),
                                         str(self.machine_summary.fwhm.value),
                                         str(self.machine_summary.delta_t.value),
                                         str(self.machine_summary.rise_to_peak_slope),
                                         str(bool(self.machine_summary.is_peak_user_selected)),
                                         '\n'
                                        ])
                               )

        self.lastExportPath = export_path
