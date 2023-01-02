#! /usr/bin/env python
# -*- coding: utf-8 -*-
#

import os
import sys

from PyQt5 import QtWidgets, QtGui, QtCore
from experiment import Experiment
from plotarea import PlotArea


__version__ = '1.0.2'


class GUI(QtWidgets.QMainWindow):

    def __init__(self):
        super().__init__()

        # init a default experiment
        self.plotAnnotationMenu = None
        self.settings = None
        self.plotCalculatorMenu = None
        self.plotFilterMenu = None
        self.plot_filter_data = None
        self.plot_calculator = None
        self.plot_annotate = None
        self.overlayMenu = None
        self.experiment = Experiment()

        # get app settings
        self.read_app_settings()

        self.main_frame = QtWidgets.QWidget(self)
        self.plot_area = None

        self.init_gui()

    def init_gui(self):
        """
        QT GUI
        """
        # create menus
        exitAction = QtWidgets.QAction(QtGui.QIcon('exit.png'), '&Exit', self)
        exitAction.setShortcut('Ctrl+Q')
        exitAction.setStatusTip('Exit application')
        exitAction.triggered.connect(QtWidgets.qApp.quit)

        clearTraceAction = QtWidgets.QAction('&Clear Traces', self)
        clearTraceAction.setStatusTip('Clear all traces from plot')
        clearTraceAction.triggered.connect(self.clear_trace)

        openFileAction = QtWidgets.QAction('&Open DTS File', self)
        openFileAction.setShortcut('Ctrl+O')
        openFileAction.setStatusTip('Load DTS Data File')
        openFileAction.triggered.connect(self.load_trace)

        menubar = self.menuBar()
        fileMenu = menubar.addMenu('&File')
        fileMenu.addAction(openFileAction)
        fileMenu.addAction(clearTraceAction)
        fileMenu.addAction(exitAction)

        # options menu
        optMenu = menubar.addMenu('&Options')

        # # overlay option s
        # # plot filter submenu
        # self.plotFilterMenu = optMenu.addMenu('Filter Trace Plot:')
        #
        # # group so options are exclusive
        # ag = QtWidgets.QActionGroup(self.plotFilterMenu)
        # # add menu items
        # a = ag.addAction(QtWidgets.QAction('Yes', self.plotFilterMenu, checkable=True))
        # a.setData(True)
        # if self.plot_filter_data:
        #     a.setChecked(True)
        # self.plotFilterMenu.addAction(a)
        #
        # a = ag.addAction(QtWidgets.QAction('No', self.plotFilterMenu, checkable=True))
        # a.setData(False)
        # if not self.plot_filter_data:
        #     a.setChecked(True)
        # self.plotFilterMenu.addAction(a)
        # self.plotFilterMenu.triggered.connect(self.plotFilterMenu_changed)
        #
        # # plot param calculator submenu
        # self.plotCalculatorMenu = optMenu.addMenu('Calculation Type:')
        #
        # # group so options are exclusive
        # ag = QtWidgets.QActionGroup(self.plotCalculatorMenu)
        #
        # # add menu items
        # a = ag.addAction(QtWidgets.QAction('Basic', self.plotCalculatorMenu, checkable=True))
        # a.setData('Basic')
        # if self.plot_calculator == 'Basic':
        #     a.setChecked(True)
        # self.plotCalculatorMenu.addAction(a)
        # self.plotCalculatorMenu.triggered.connect(self.plotCalculatorMenu_changed)
        #
        # a = ag.addAction(QtWidgets.QAction('Compatible', self.plotCalculatorMenu, checkable=True))
        # a.setData('Compatible')
        # if self.plot_calculator == 'Compatible':
        #     a.setChecked(True)
        # self.plotCalculatorMenu.addAction(a)
        # self.plotCalculatorMenu.triggered.connect(self.plotCalculatorMenu_changed)
        #
        # a = ag.addAction(QtWidgets.QAction('Historical', self.plotCalculatorMenu, checkable=True))
        # a.setData('Historical')
        # if self.plot_calculator == 'Historical':
        #     a.setChecked(True)
        # self.plotCalculatorMenu.addAction(a)
        # self.plotCalculatorMenu.triggered.connect(self.plotCalculatorMenu_changed)

        # plot filter submenu
        self.plotAnnotationMenu = optMenu.addMenu('Annotate Plot:')

        # group so options are exclusive
        ag = QtWidgets.QActionGroup(self.plotAnnotationMenu)
        # add menu items
        a = ag.addAction(QtWidgets.QAction('Yes', self.plotAnnotationMenu, checkable=True))
        a.setData(True)
        if self.plot_annotate:
            a.setChecked(True)
        self.plotAnnotationMenu.addAction(a)

        a = ag.addAction(QtWidgets.QAction('No', self.plotAnnotationMenu, checkable=True))
        a.setData(False)
        if not self.plot_annotate:
            a.setChecked(True)
        self.plotAnnotationMenu.addAction(a)
        self.plotAnnotationMenu.triggered.connect(self.plotAnnotationMenu_changed)

        # about menu
        abtMenu = menubar.addMenu('&About')
        appAction = QtWidgets.QAction('Application', self)
        appAction.triggered.connect(self.show_about_app_dlg)
        abtMenu.addAction(appAction)
        # expAction = QtWidgets.QAction('Current Experiment', self)
        # expAction.triggered.connect(self.show_about_experiment_dlg)
        # abtMenu.addAction(expAction)

        # create status bar
        self.statusBar()

        self.setWindowTitle('DTS Data Viewer')
        self.setWindowIcon(QtGui.QIcon('rc/appicon.png'))
        self.statusBar().showMessage('Ready')

        self.plot_area = PlotArea(self.main_frame)
        self.main_frame.setLayout(self.plot_area)
        self.setCentralWidget(self.main_frame)

    def show_about_app_dlg(self):
        """
        Show some version info
        """
        aboutDlg = QtWidgets.QMessageBox(self)
        aboutDlg.setIcon(QtWidgets.QMessageBox.Information)
        aboutDlg.setWindowTitle("About DTS Data Viewer")
        aboutDlg.setWindowModality(QtCore.Qt.ApplicationModal)
        aboutDlg.setText("Version: " + __version__)
        aboutDlg.setInformativeText("Click 'Show Details' for a list of changes.")
        aboutDlg.setDetailedText("""Changes:
=== 1.0.2 ===
 - Removed cleardepth level. All plot items cleared by default.
 - Rise start and end now identified by 3 stdev instead of CHOP 5% of peak velocity
 
=== 1.0.1 ===
 - Added summary to Head rotation resultant plot
 - Coordinate display now contains correct x and y units for all plots
 - Bottom right plot is now machine primary plotted with head resultant

=== 1.0.0 ===
 - Initial DTS Data Viewer
""")
        aboutDlg.exec_()

    def show_about_experiment_dlg(self):
        """
        Show some version info
        """
        aboutDlg = QtWidgets.QMessageBox(self)
        aboutDlg.setIcon(QtWidgets.QMessageBox.Information)
        aboutDlg.setWindowTitle("About Experiment")
        aboutDlg.setWindowModality(QtCore.Qt.ApplicationModal)
        aboutDlg.setText("Active Experiment Details:")

        if len(self.experiment.subjectId):
            aboutDlg.setInformativeText(self.experiment.get_header().replace(':', ' : '))

        aboutDlg.exec_()

    def get_experiment_params(self):
        """
        Query experiment variables from user; 
        update experiment instance;
        chain to wait for trigger
        """

        # prior to gettting experimental parameters, do a successful voltage check or stop
        current_excitation_voltage = self.get_current_excitation_voltage()
        if current_excitation_voltage is None:
            return

        def frmAccept():

            # make sure we have data
            if (len(inFldId.text()) != 0) and (len(inFldPsiLoad.text()) != 0) and (len(inFldPsiSet.text()) != 0):
                # start new experiment
                self.experiment = Experiment()
                self.experiment.subjectId = str(inFldId.text())
                self.experiment.PsiLoad = str(inFldPsiLoad.text())
                self.experiment.PsiSet = str(inFldPsiSet.text())
                self.experiment.excitation_volts = current_excitation_voltage

                # close user input dialog
                experimentDlg.close()

                # go to trigger wait
                self.wait_trigger_collection()

        def frmCancel():
            experimentDlg.close()

        # see if we can collect an experiment first; perhaps better place to put this?
        if 'PyDAQmx' not in sys.modules:
            self.display_msg("No NI Driver", "You cannot collect data.",
                             "Data collection requires niDAQmx driver and PyDAQmx wrapper.")

        experimentDlg = QtWidgets.QDialog(self)
        experimentDlg.setWindowTitle("Experiment Settings")
        experimentDlg.setWindowModality(QtCore.Qt.ApplicationModal)

        # input form
        inLblId = QtWidgets.QLabel("Subject ID:")
        inFldId = QtWidgets.QLineEdit()
        # inFldId.setInputMask('M99999999')   # input validation for MRN ids
        inFldId.setText(self.experiment.subjectId)
        # inFldId.setCursorPosition(len(self.experiment.subjectId)) # input validation, cursor position

        inLblPsiLoad = QtWidgets.QLabel("Load PSI:")
        inFldPsiLoad = QtWidgets.QLineEdit()
        inFldPsiLoad.setValidator(QtGui.QIntValidator())
        inFldPsiLoad.setMaxLength(4)
        inFldPsiLoad.setText(self.experiment.PsiLoad)

        inLblPsiSet = QtWidgets.QLabel("Set PSI:")
        inFldPsiSet = QtWidgets.QLineEdit()
        inFldPsiSet.setValidator(QtGui.QIntValidator())
        inFldPsiSet.setMaxLength(3)
        inFldPsiSet.setText(self.experiment.PsiSet)

        btnBox = QtWidgets.QDialogButtonBox()
        btnBox.addButton("Continue", QtWidgets.QDialogButtonBox.AcceptRole)
        btnBox.setStandardButtons(QtWidgets.QDialogButtonBox.Cancel)
        btnBox.accepted.connect(frmAccept)
        btnBox.rejected.connect(frmCancel)
        btnBox.centerButtons()

        dlgLayout = QtWidgets.QFormLayout()
        dlgLayout.addRow(inLblId, inFldId)
        dlgLayout.addRow(inLblPsiSet, inFldPsiSet)
        dlgLayout.addRow(inLblPsiLoad, inFldPsiLoad)
        dlgLayout.setSpacing(10.0)
        dlgLayout.addRow(btnBox)

        experimentDlg.setLayout(dlgLayout)
        experimentDlg.exec_()

    def display_msg(self, txt, iTxt, dTxt):
        msg = QtWidgets.QMessageBox()
        msg.setIcon(QtWidgets.QMessageBox.Information)
        msg.setText(txt)
        msg.setInformativeText(iTxt)
        msg.setWindowTitle('DTS Data Viewer')
        msg.setDetailedText(dTxt)
        msg.setStandardButtons(QtWidgets.QMessageBox.Ok)
        msg.exec_()

    def clear_trace(self, event):
        """
        Handle request to clear all traces and text from plot
        """
        # reply = QtWidgets.QMessageBox.question(self, 'Confirm', "Clear plot traces?",
        #                                        QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
        #                                        QtWidgets.QMessageBox.Yes)
        #
        # if reply == QtWidgets.QMessageBox.Yes:
        self.experiment = Experiment()
        self.plot_area.clear_plot()
        self.setWindowTitle('DTS Data Viewer')

    def plotFilterMenu_changed(self):
        """ 
        Connect to Option menu for sensor
        """
        for action in self.plotFilterMenu.actions():
            if action.isChecked():
                self.plot_filter_data = action.data()

    def plotCalculatorMenu_changed(self):
        """ 
        Connect to Option menu for sensor
        """
        for action in self.plotCalculatorMenu.actions():
            if action.isChecked():
                self.plot_calculator = action.data()

    def plotAnnotationMenu_changed(self):
        for action in self.plotAnnotationMenu.actions():
            if action.isChecked():
                self.plot_annotate = action.data()
                # refresh the plot
                self.plot_area.clear_plot()
                self.plot_area.plot(self.experiment, self.plot_annotate)
                self.statusBar().showMessage('Ready')

    def load_trace(self):
        """
        Read DTS data file and display in plot
        """
        try:

            fname, _ = QtWidgets.QFileDialog.getOpenFileName(self, 'Open file',
                                                             self.experiment.lastDataPath, "Sliceware Files (*.dts)")
            if fname:
                # update experiment parameters with header from file being loaded
                self.experiment = Experiment.load(fname)
                # clear the plot
                self.plot_area.clear_plot()

                # plot data
                self.plot_area.plot(self.experiment, self.plot_annotate)
                self.statusBar().showMessage('Ready')

                self.setWindowTitle('DTS Data Viewer - ' + self.experiment.get_label())

        except Exception as e:
            self.display_msg("Error:", "Loading Trace file", str(e))
            return

    def save_trace(self):
        """ 
        write out trace data in voltage 
        """
        self.experiment.save(os.path.join(os.getcwd(), "data", self.experiment.file_name))

    def read_app_settings(self):
        """
        read app session settings
        """
        self.settings = QtCore.QSettings()

        # plot settings
        # default plot filter
        self.plot_filter_data = self.settings.value('plot_filter_data', True, type=bool)
        # default plot calculator
        self.plot_calculator = self.settings.value('plot_calculator', 'Compatible', type=str)
        # default plot annotation
        self.plot_annotate = self.settings.value('plot_annotate', True, type=bool)
        # change to script directory
        script_home = os.path.dirname(os.path.abspath(__file__))
        os.chdir(script_home)
        # point experiment output to the data subdirectory
        self.experiment.lastDataPath = self.settings.value('lastDataPath', os.path.join(script_home, 'data'))

    def save_app_settings(self):
        """
        save app session settings
        """
        # update settings
        self.settings.setValue('plot_filter_data', self.plot_filter_data)
        self.settings.setValue('plot_calculator', self.plot_calculator)
        self.settings.setValue('plot_annotate', self.plot_annotate)
        self.settings.setValue('lastDataPath', self.experiment.lastDataPath)
        # this writes to native storage
        del self.settings

    @QtCore.pyqtSlot()
    def close(self):
        """
        Anything you want to do before we close gui?
        :return: 
        """
        self.save_app_settings()
        super().close()


def main():
    try:
        app = QtWidgets.QApplication(sys.argv)
        # set application values once here for QSettings
        app.setOrganizationName("MayerLab")
        app.setApplicationName("DTSDATAVIEWER")

        gui = GUI()
        # exit menu action calls app quit. Notify mainwindow gui that we are quiting.
        app.aboutToQuit.connect(gui.close)
        gui.showFullScreen()
        gui.showMaximized()

    except Exception as e:
        print(e)

    finally:
        sys.exit(app.exec_())


if __name__ == '__main__':
    main()
