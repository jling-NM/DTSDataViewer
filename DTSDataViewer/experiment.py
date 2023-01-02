import os
import datetime
from dts_file_reader import slice


class Experiment:
    """
    An instance of data collection either from the sensor or a data file.
    Settings specific to that instance and its data.
    """

    def __init__(self):

        # initiate container for data
        self.channel_data = None
        self._date = datetime.datetime.today().strftime("%Y%m%d")
        self._time = datetime.datetime.today().strftime("%H%M%S")
        self._subject_id = ""  # default subject id
        self.PsiLoad = ""  # default Load psi setting
        self.PsiSet = ""  # default Set psi setting
        self.lastDataPath = ''
        # self.file_name = self.subjectId + "_" + self.date + "_" + self.time + "_dual.hyg"

    @property
    def subjectId(self):
        return self._subject_id

    @subjectId.setter
    def subjectId(self, value):
        self._subject_id = value
        self.file_name = self._subject_id + "_" + self._date + "_" + self._time + "_dual.hyg"

    @property
    def date(self):
        return self._date

    @date.setter
    def date(self, value):
        self._date = value
        self.file_name = self.subjectId + "_" + self._date + "_" + self._time + "_dual.hyg"

    @property
    def time(self):
        return self._time

    @time.setter
    def time(self, value):
        self._time = value
        #self.file_name = self.subjectId + "_" + self._date + "_" + self._time + "_dual.hyg"

    def set_timestamp(self):
        import datetime
        self._date = datetime.datetime.today().strftime("%Y%m%d")
        self._time = datetime.datetime.today().strftime("%H%M%S")
        #self.file_name = self.subjectId + "_" + self._date + "_" + self._time + "_dual.hyg"

    def get_label(self):
        """
        name for experiment
        """
        # return self.subjectId + "_" + self.date + "_" + self.time
        # didn't do that incase someone change file name

        # remove file extension
        # and remove head
        return self.file_name.split('.')[0].replace('_head', '')

    @classmethod
    def load(cls, data_file_path):

        experiment = Experiment()
        experiment.lastDataPath = os.path.sep.join(str(data_file_path).split('/')[0:-1])
        experiment.file_name = str(data_file_path).split('/')[-1]
        experiment.channel_data = slice.Reader().parse(str(data_file_path))

        return experiment
