#! /usr/bin/env python
# -*- coding: utf-8 -*-
#

import os
import sys

from PyQt5 import QtWidgets, QtGui, QtCore
from .experiment import Experiment
from .plotarea import PlotArea


__version__ = '2.0.0'


class GUI(QtWidgets.QMainWindow):

    def __init__(self):
        super().__init__()

        # init a default experiment
        self.settings = None
        self.experiment = Experiment()
        self.plot_annotate = None
        self.plotAnnotationMenu = None
        self.plot_cursor_tracks_data = None
        self.plotCursorTrackDataMenu = None

        # class member for runtime access
        self.exportFileAction = None

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

        self.exportFileAction = QtWidgets.QAction('&Export Data', self)
        self.exportFileAction.setShortcut('Ctrl+E')
        self.exportFileAction.setStatusTip('Export Trace and Summary Data')
        self.exportFileAction.triggered.connect(self.export)
        self.exportFileAction.setEnabled(False)

        menubar = self.menuBar()
        fileMenu = menubar.addMenu('&File')
        fileMenu.addAction(openFileAction)
        fileMenu.addAction(self.exportFileAction)
        fileMenu.addAction(clearTraceAction)
        fileMenu.addAction(exitAction)

        # options menu
        optMenu = menubar.addMenu('&Options')

        self.plotAnnotationMenu = optMenu.addMenu('Annotate Plot:')
        # group so options are exclusive
        ag = QtWidgets.QActionGroup(self.plotAnnotationMenu)
        # add menu items
        a = ag.addAction(QtWidgets.QAction('On', self.plotAnnotationMenu, checkable=True))
        a.setData(True)
        if self.plot_annotate:
            a.setChecked(True)
        self.plotAnnotationMenu.addAction(a)

        a = ag.addAction(QtWidgets.QAction('Off', self.plotAnnotationMenu, checkable=True))
        a.setData(False)
        if not self.plot_annotate:
            a.setChecked(True)
        self.plotAnnotationMenu.addAction(a)
        self.plotAnnotationMenu.triggered.connect(self.plotAnnotationMenu_changed)

        #
        self.plotCursorTrackDataMenu = optMenu.addMenu('Cursor Tracks Data:')
        # group so options are exclusive
        ag = QtWidgets.QActionGroup(self.plotCursorTrackDataMenu)
        # add menu items
        a = ag.addAction(QtWidgets.QAction('On', self.plotCursorTrackDataMenu, checkable=True))
        a.setData('x')
        if self.plot_cursor_tracks_data == 'x':
            a.setChecked(True)
        else:
            a.setChecked(False)
        self.plotCursorTrackDataMenu.addAction(a)

        a = ag.addAction(QtWidgets.QAction('Off', self.plotCursorTrackDataMenu, checkable=True))
        a.setData('off')
        if self.plot_cursor_tracks_data == 'off':
            a.setChecked(True)
        else:
            a.setChecked(False)
        self.plotCursorTrackDataMenu.addAction(a)
        self.plotCursorTrackDataMenu.triggered.connect(self.plotCursorTrackDataMenu_changed)


        # about menu
        abtMenu = menubar.addMenu('&About')
        appAction = QtWidgets.QAction('Application', self)
        appAction.triggered.connect(self.show_about_app_dlg)
        abtMenu.addAction(appAction)

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
=== 2.0.0 ===
 - Add feature to manually select peak
 - Add data export
 - Extend precision of crosshair coordinate display
 
=== 1.0.4 ===
 - Improve settings for Windows
 - Add menu to toggle cursor tracking on plots
 
=== 1.0.3 ===
 - High DPI support and better formatting for Windows
 - Add crosshair coordinate display to plots
 
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

    @staticmethod
    def display_msg(txt, iTxt, dTxt):
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
        # with data cleared, disable export of data menu item
        self.exportFileAction.setEnabled(False)
        self.setWindowTitle('DTS Data Viewer')

    def plotCursorTrackDataMenu_changed(self):
        """ 
        Connect to Option menu for sensor
        """
        for action in self.plotCursorTrackDataMenu.actions():
            if action.isChecked():
                self.plot_cursor_tracks_data = action.data()
                # refresh the plot
                self.plot_area.clear_plot()
                self.plot_area.plot(self.experiment, self.plot_annotate, self.plot_cursor_tracks_data)
                self.statusBar().showMessage('Ready')

    def plotAnnotationMenu_changed(self):
        for action in self.plotAnnotationMenu.actions():
            if action.isChecked():
                self.plot_annotate = action.data()
                # refresh the plot
                self.plot_area.clear_plot()
                self.plot_area.plot(self.experiment, self.plot_annotate, self.plot_cursor_tracks_data)
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
                self.plot_area.plot(self.experiment, self.plot_annotate, self.plot_cursor_tracks_data)
                self.statusBar().showMessage('Ready')

                self.setWindowTitle('DTS Data Viewer - ' + self.experiment.get_label())
                # with data loaded, enable export of data menu item
                self.exportFileAction.setEnabled(True)

        except Exception as e:
            self.display_msg("Error:", "Loading Trace file", str(e))
            return

    def export(self):
        """ 
        Export experiment data files
        """
        try:

            dname = QtWidgets.QFileDialog.getExistingDirectory(self,
                                                               'Select Export Directory',
                                                               self.experiment.lastExportPath,
                                                               options=QtWidgets.QFileDialog.ShowDirsOnly)
            if len(dname):
                self.experiment.export(dname)

        except Exception as e:
            self.display_msg("Error:", "Could not select export directory", str(e))
            return



    def read_app_settings(self):
        """
        read app session settings
        """
        self.settings = QtCore.QSettings()

        # plot settings
        # default plot annotation
        self.plot_annotate = self.settings.value('plot_annotate', True, type=bool)
        # default cursor data track
        self.plot_cursor_tracks_data = self.settings.value('plot_cursor_tracks_data', 'x', type=str)
        # change to script directory
        script_home = os.path.dirname(os.path.abspath(__file__))
        os.chdir(script_home)
        # point experiment output to the data subdirectory
        self.experiment.lastDataPath = self.settings.value('lastDataPath', os.path.join(script_home, 'data'))
        # point experiment export
        self.experiment.lastExportPath = self.settings.value('lastExportPath', os.path.join(script_home, 'data'))

    def save_app_settings(self):
        """
        save app session settings
        """
        # update settings
        self.settings.setValue('plot_annotate', self.plot_annotate)
        self.settings.setValue('plot_cursor_tracks_data', self.plot_cursor_tracks_data)
        self.settings.setValue('lastDataPath', self.experiment.lastDataPath)
        self.settings.setValue('lastExportPath', self.experiment.lastExportPath)
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
        # enable highdpi scaling
        QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)
        # use highdpi icons
        QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps, True)

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
