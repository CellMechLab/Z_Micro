from PySide6 import QtWidgets, QtGui, QtCore
import pyqtgraph as pg
import numpy as np
from scipy.signal import savgol_filter as savgol
import sys
import os

def calculate(filename,outfile,threshold,win):
    f = open(filename)
    fluo=[]
    pmt=[]
    time=[]
    f.readline()
    for riga in f:
        tmptime,tmpfluo,tmppmt=[float(number) for number in riga.strip().split(',')[:3]]
        time.append(tmptime)
        fluo.append(tmpfluo)
        pmt.append(tmppmt)
    f.close()        

    print(f'{len(time)}+1 lines read')

    filtered = savgol(fluo,win,1)
    block = np.where(filtered>threshold)
    print(f'{len(block[0])} points isolated')

    acqtimeus = int((time[1]-time[0])*1000)

    time = np.array(time)[block]
    fluo = np.array(fluo)[block]
    pmt = np.array(pmt)[block]

    peaks=[]
    prevtime=0
    tmp=[]
    for i in range(1,len(time)):
        tmptime = time[i]
        tmpfluo = fluo[i]
        if int((tmptime-prevtime)*1000) > acqtimeus:
            if len(tmp)>win:
                peaks.append(np.array(tmp))
                tmp=[]                    
        else:                
            tmp.append([tmptime,tmpfluo])        
        prevtime = tmptime
    print(f'{len(peaks)} peaks identified')

    intensity= []
    duration = []
    for p in peaks:
        intensity.append(np.max(savgol(p[:,1],win,1)))
        duration.append(p[-1,0]-p[0,0])

    out = open(outfile,'w')
    out.write('Duration [us],Intensity []a.u]\n')
    for i in range(len(intensity)):
        out.write(f'{duration[i]},{intensity[i]}\n')
    out.close()
    return duration, intensity

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('PySide6 Application with pyqtgraph')

        # Create central widget and layout
        central_widget = QtWidgets.QWidget()
        self.setCentralWidget(central_widget)
        layout = QtWidgets.QVBoxLayout()
        central_widget.setLayout(layout)

        # Create input fields and button
        self.infile_edit = QtWidgets.QLineEdit()
        self.infile_button = QtWidgets.QPushButton('Select Input File')
        self.infile_button.clicked.connect(self.select_infile)

        self.outfile_edit = QtWidgets.QLineEdit()

        self.threshold_edit = QtWidgets.QLineEdit('4000')
        self.threshold_edit.setValidator(QtGui.QIntValidator(0, 65535))

        self.window_edit = QtWidgets.QLineEdit('31')
        self.window_edit.setValidator(QtGui.QIntValidator(1, 999))

        self.calculate_button = QtWidgets.QPushButton('Calculate')
        self.calculate_button.clicked.connect(self.calculate)

        # Add widgets to layout
        layout.addWidget(QtWidgets.QLabel('Input File:'))
        layout.addWidget(self.infile_edit)
        layout.addWidget(self.infile_button)

        layout.addWidget(QtWidgets.QLabel('Output File:'))
        layout.addWidget(self.outfile_edit)

        layout.addWidget(QtWidgets.QLabel('Threshold:'))
        layout.addWidget(self.threshold_edit)

        layout.addWidget(QtWidgets.QLabel('Window:'))
        layout.addWidget(self.window_edit)

        layout.addWidget(self.calculate_button)

        # Create a PlotWidget
        self.plot_widget = pg.PlotWidget()
        layout.addWidget(self.plot_widget)

    def select_infile(self):
        filename, _ = QtWidgets.QFileDialog.getOpenFileName(self, 'Select Input File', '', 'CSV Files (*.csv)')
        if filename:
            self.infile_edit.setText(filename)
            outfile = os.path.splitext(filename)[0] + '_out.csv'
            self.outfile_edit.setText(outfile)

    def calculate(self):
        infile = self.infile_edit.text()
        outfile = self.outfile_edit.text()
        threshold = int(self.threshold_edit.text())
        window = int(self.window_edit.text())

        # Ensure window is even
        if window % 2 == 0:
            QtWidgets.QMessageBox.warning(self, 'Invalid Window', 'Window size must be an even number.')
            return

        # Read data from infile
        x,y = calculate(infile,outfile,threshold,window)

        # Plot the data
        self.plot_widget.clear()
        self.plot_widget.plot(x, y, pen=None, symbol='o')

if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    main_window = MainWindow()
    main_window.show()
    sys.exit(app.exec())





