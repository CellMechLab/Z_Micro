import sys
import numpy as np
from PySide6.QtWidgets import (
    QApplication, QWidget, QPushButton, QVBoxLayout, QHBoxLayout, QFileDialog,
    QLabel, QSpinBox, QSlider, QMessageBox, QDialog
)
from PySide6.QtCore import Qt

import pyqtgraph as pg

class RandomScatterPlotDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Random Scatter Plot')
        self.setGeometry(200, 200, 600, 400)

        layout = QVBoxLayout()

        self.plotWidget = pg.PlotWidget()
        layout.addWidget(self.plotWidget)

        self.setLayout(layout)

        self.generateRandomData()

    def generateRandomData(self):
        x = np.random.rand(1000)
        y = np.random.rand(1000)
        self.plotWidget.plot(x, y, pen=None, symbol='o', symbolSize=5)

class MyApp(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()
        self.data = None
        self.bruteforce = False
        self.loaded = False
        

    def initUI(self):
        self.setWindowTitle('PySide6 CSV Plotter')
        self.setGeometry(100, 100, 800, 600)

        layout = QVBoxLayout()

        controlLayout = QHBoxLayout()
        self.selectButton = QPushButton('Select CSV', self)
        self.selectButton.clicked.connect(self.openFileDialog)
        controlLayout.addWidget(self.selectButton)
        
        # Button to show plot
        self.showButton = QPushButton('Show', self)
        self.showButton.clicked.connect(self.showRandomScatterPlot)
        controlLayout.addWidget(self.showButton)

        self.messageLabel = QLabel('', self)
        controlLayout.addWidget(self.messageLabel)

        self.pointsLabel = QLabel('Points to Plot:', self)
        controlLayout.addWidget(self.pointsLabel)
        self.pointsSpinBox = QSpinBox(self)
        self.pointsSpinBox.setRange(1, 999999)
        self.pointsSpinBox.setValue(1000)
        self.pointsSpinBox.valueChanged.connect(self.sizeChanged)
        controlLayout.addWidget(self.pointsSpinBox)
        
        # Label and SpinBox for threshold
        self.thresholdLabel = QLabel('Threshold:', self)
        controlLayout.addWidget(self.thresholdLabel)
        self.thresholdSpinBox = QSpinBox(self)
        self.thresholdSpinBox.setRange(0, 65535)
        self.thresholdSpinBox.setValue(2000)
        controlLayout.addWidget(self.thresholdSpinBox)

        self.prevButton = QPushButton('Previous', self)
        self.prevButton.clicked.connect(self.prevWindow)
        controlLayout.addWidget(self.prevButton)

        self.nextButton = QPushButton('Next', self)
        self.nextButton.clicked.connect(self.nextWindow)
        controlLayout.addWidget(self.nextButton)

        layout.addLayout(controlLayout)
        
        self.sliding = QSlider(Qt.Orientation.Horizontal,self)
        self.sliding.setMinimum(0)
        self.sliding.setMaximum(100000)
        self.sliding.setPageStep(1000)
        self.sliding.valueChanged.connect(self.updatePlot)
        layout.addWidget(self.sliding)

        self.plotWidget1 = pg.PlotWidget(title="Intensity vs Time")
        self.plotWidget2 = pg.PlotWidget(title="PMT vs Time")

        layout.addWidget(self.plotWidget1)
        layout.addWidget(self.plotWidget2)

        self.setLayout(layout)

    def openFileDialog(self):
        filePath, _ = QFileDialog.getOpenFileName(self, 'Open CSV', '', 'CSV Files (*.csv);;All Files (*)')
        if filePath:
            self.filename= filePath
            self.loadAndPlotData()

    def loadAndPlotData(self):
        QApplication.setOverrideCursor(Qt.WaitCursor)
        self.line_offset = []
        f = open(self.filename)
        if self.bruteforce is True:
            data=[]
            f.readline()
            for riga in f:
                tmptime,tmpfluo,tmppmt=[float(number) for number in riga.strip().split(',')[:3]]
                data.append([tmptime/1000,tmpfluo,tmppmt])
            self.data = np.array(data)
            total = self.data.shape[0]
            endtime = self.data[-1,0]
            starttime = self.data[0,0]
        else:            
            offset = 0
            total=0
            for line in f:
                if total==1:
                    starttime,tmpfluo=[float(number) for number in line.strip().split(',')[:2]]
                total+=1
                self.line_offset.append(offset)
                offset += len(line)
            endtime,tmpfluo=[float(number) for number in line.strip().split(',')[:2]]
            endtime/=1000
            starttime/=1000
        f.close()
        self.acqtime = (endtime-starttime)/(total)
        self.number = total
        N = self.pointsSpinBox.value()
        self.pointsSpinBox.setMaximum(total-1)
        self.sliding.setMaximum(total-N-1)
        QApplication.restoreOverrideCursor()
        QMessageBox.information(self, 'File loaded', f'File {self.filename} opened.\nA total of {self.number} lines has been read.\nTotal acquisition time of the track: {int(endtime)}s\nAcquisition time {int(self.acqtime*1e8)/100}us')
        self.updatePlot()
        self.messageLabel.setText(f'Loaded file: {self.filename}')
        self.loaded = True

    def sizeChanged(self):
        if self.loaded is False:
            return
        self.sliding.setMaximum(self.number-self.pointsSpinBox.value()-1)   
        self.sliding.setPageStep(self.pointsSpinBox.value())     
        self.updatePlot()

    def updatePlot(self):
        if self.loaded is False:
            return
        N = self.pointsSpinBox.value()
        position = self.sliding.value() #change here for the starting position of the slice in ms
        if self.bruteforce is True:
            time = self.data[position:position+N,0]
            fluo = self.data[position:position+N,1]
            pmt = self.data[position:position+N,2]
        else:
            f = open(self.filename)
            f.seek(self.line_offset[position])
            f.readline()
            time=[]
            fluo=[]
            pmt=[]
            i=0
            for riga in f:
                i+=1
                if i>=N:
                    break
                tmptime,tmpfluo,tmppmt=[float(number) for number in riga.strip().split(',')[:3]]
                time.append(tmptime/1000)
                fluo.append(tmpfluo)
                pmt.append(tmppmt)
            f.close()

        self.plotWidget1.clear()
        self.plotWidget1.plot(time, fluo, pen='r',symbol='o',symbolSize=3)
        self.plotWidget1.autoRange()
        self.plotWidget2.clear()        
        self.plotWidget2.plot(time, pmt, pen='g',symbol='o',symbolSize=3)
        self.plotWidget2.autoRange()

        def sync_x_range_p1_to_p2(axis, range):
            self.plotWidget2.setXRange(*range, padding=0)

        # Function to synchronize the x-axis range of p2 with p1
        def sync_x_range_p2_to_p1(axis, range):
            self.plotWidget1.setXRange(*range, padding=0)

        # Connect the signals to the synchronization functions
        self.plotWidget1.getViewBox().sigXRangeChanged.connect(lambda vb, range: sync_x_range_p1_to_p2(self.plotWidget1.getAxis('bottom'), range))
        self.plotWidget2.getViewBox().sigXRangeChanged.connect(lambda vb, range: sync_x_range_p2_to_p1(self.plotWidget2.getAxis('bottom'), range))

    def showRandomScatterPlot(self):
        dialog = RandomScatterPlotDialog()
        dialog.exec_()

    def prevWindow(self):
        if self.sliding.value()>self.pointsSpinBox.value():
            self.sliding.setValue(self.sliding.value()-self.pointsSpinBox.value())
        else:
            self.sliding.setValue(0)

    def nextWindow(self):
        self.sliding.setValue(self.sliding.value()+self.pointsSpinBox.value())

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = MyApp()
    ex.show()
    sys.exit(app.exec())
