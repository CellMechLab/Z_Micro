import sys
import numpy as np
from PySide6.QtWidgets import (
    QApplication, QWidget, QPushButton, QVBoxLayout, QHBoxLayout, QFileDialog,
    QLabel, QSpinBox, QSlider, QMessageBox, QDialog
)
from PySide6.QtCore import Qt
from scipy.signal import savgol_filter as savgol
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
        self.loaded = False
        self.finished=False
        
    def initUI(self):
        self.setWindowTitle('AMK data analyser')
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
        
        self.winLabel = QLabel('Window:', self)
        controlLayout.addWidget(self.winLabel)
        self.winSpinBox = QSpinBox(self)
        self.winSpinBox.setRange(1, 999)
        self.winSpinBox.setValue(31)
        self.winSpinBox.valueChanged.connect(self.updatePlot)
        self.winSpinBox.setSingleStep(10)
        controlLayout.addWidget(self.winSpinBox)
        
        # Label and SpinBox for threshold
        self.thresholdLabel = QLabel('Threshold:', self)
        controlLayout.addWidget(self.thresholdLabel)
        self.thresholdSpinBox = QSpinBox(self)
        self.thresholdSpinBox.setRange(0, 65535)
        self.thresholdSpinBox.setValue(0)
        self.thresholdSpinBox.setSingleStep(1000)
        controlLayout.addWidget(self.thresholdSpinBox)
        self.thresholdSpinBox.valueChanged.connect(self.moveThreshold)

        self.prevButton = QPushButton('Reset', self)
        self.prevButton.clicked.connect(self.prevWindow)
        controlLayout.addWidget(self.prevButton)

        self.nextButton = QPushButton('Isolate', self)
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
        
        self.plotWidget1.getViewBox().sigXRangeChanged.connect(lambda vb, range: self.on_xrange_changed(self.plotWidget1.getAxis('bottom'), range))
        self.plotWidget2.getViewBox().sigXRangeChanged.connect(lambda vb, range: self.on_xrange_changed(self.plotWidget2.getAxis('bottom'), range))

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
        offset = 0
        for line in f:
            self.line_offset.append(offset)
            offset += len(line)+1
        endtime,tmpfluo=[float(number) for number in line.strip().split(',')[:2]]
        f.close()
        self.number = len(self.line_offset)-1
        self.acqtime = (endtime)/(self.number-1)        
        self.range=[1,self.number]
        N = self.pointsSpinBox.value()
        self.pointsSpinBox.setMaximum(self.number)
        self.pointsSpinBox.setMinimum(100)
        self.sliding.setMaximum(self.number-N-1)   
        QApplication.restoreOverrideCursor()
        QMessageBox.information(self, 'File loaded', f'File {self.filename} opened.\nA total of {self.number} lines has been read.\nTotal acquisition time of the track: {int(endtime/10)/100}s\nAcquisition time {int(self.acqtime*1e5)/100}us')
        self.updatePlot()
        self.messageLabel.setText(f'Loaded file: {self.filename}')        
        self.loaded = True
        
        self.plotWidget1.clear()
        self.line1 = self.plotWidget1.plot([], [], pen='w',symbol='o',symbolSize=3)
        self.fit1  = self.plotWidget1.plot([], [], pen='g')
        self.threshline = self.plotWidget1.plot([], [], pen='r')
        self.plotWidget2.clear()        
        self.line2 = self.plotWidget2.plot([], [], pen='w',symbol='o',symbolSize=3)
        self.fit2 = self.plotWidget2.plot([], [], pen='g')
        
        self.updatePlot()

    def sizeChanged(self):
        if self.loaded is False:
            return
        self.sliding.setMaximum(self.number-self.pointsSpinBox.value()-1)   
        self.sliding.setPageStep(self.pointsSpinBox.value())     
        self.updatePlot()
        
    def on_xrange_changed(self, axis, range):
        if self.loaded is False:
            if self.finished is True:
                self.plotWidget1.setXRange(*range, padding=0)
                self.plotWidget2.setXRange(*range, padding=0)
                self.range=[int(range[0]/self.acqtime),min(int(range[1]/self.acqtime),len(self.line_offset)-1)]
            return
        self.loaded = False
        self.plotWidget1.setXRange(*range, padding=0)
        self.plotWidget2.setXRange(*range, padding=0)
        self.range=[int(range[0]/self.acqtime),min(int(range[1]/self.acqtime),len(self.line_offset)-1)]
        self.loaded = True
        self.updatePlot()
        
    def moveThreshold(self):
        th=self.thresholdSpinBox.value()
        view_range = self.plotWidget1.viewRange()
        x_range = view_range[0]
        self.threshline.setData(x_range ,[th,th])

    def updatePlot(self):
        if self.loaded is False:
            return
        win = self.winSpinBox.value()
        if win%2 == 0:
            win+=1
        N = self.pointsSpinBox.value()
        #position = self.sliding.value() #change here for the starting position of the slice in ms
        f = open(self.filename)
        time=[]
        fluo=[]
        pmt=[]
        for position in np.linspace(self.range[0],self.range[1],N):
            f.seek(self.line_offset[int(position)])
            riga = f.readline()
            tmptime,tmpfluo,tmppmt=[float(number) for number in riga.strip().split(',')[:3]]
            time.append(tmptime)
            fluo.append(tmpfluo)
            pmt.append(tmppmt)
        f.close()

        self.loaded = False
        self.line1.setData(time, fluo)
        self.fit1.setData(time,savgol(fluo,win,1))
        th=self.thresholdSpinBox.value()
        self.threshline.setData([min(time),max(time)],[th,th])
        #self.plotWidget1.autoRange()
        self.line2.setData(time, pmt)
        self.fit2.setData(time, savgol(pmt,win,1), pen='y')
        #self.plotWidget2.autoRange()
        self.loaded=True
        

    def showRandomScatterPlot(self):
        dialog = RandomScatterPlotDialog()
        dialog.exec_()

    def prevWindow(self):
        self.range=[1,self.number]
        self.updatePlot()
        self.plotWidget1.autoRange()
        self.plotWidget2.autoRange()

    def nextWindow(self):
        win = self.winSpinBox.value()
        if win%2 == 0:
            win+=1
        QApplication.setOverrideCursor(Qt.WaitCursor)     
        self.loaded=False        
        self.finished=True
        f = open(self.filename)
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
        filtered = savgol(fluo,win,1)
        threshold = self.thresholdSpinBox.value()
        
        block = np.where(filtered>threshold)
        
        self.xtime = np.array(time)[block]
        self.xfluo = np.array(fluo)[block]
        self.xpmt = np.array(pmt)[block]
        
        
        self.line1.setData(self.xtime, self.xfluo)
        self.fit1.setData(self.xtime,savgol(self.xfluo,win,1))
        th=self.thresholdSpinBox.value()
        self.threshline.setData([min(self.xtime),max(self.xtime)],[th,th])
        self.plotWidget1.autoRange()
        self.line2.setData(self.xtime, self.xpmt)
        self.fit2.setData(self.xtime, savgol(self.xpmt,win,1), pen='y')
        self.plotWidget2.autoRange()
        
        QApplication.restoreOverrideCursor()        
        QMessageBox.information(self, 'File analysed', f'A total of {len(self.xtime)} points lay above the smoothed threshold, corresponding to {np.sum( (self.xtime[1:]-self.xtime[:-1])>self.acqtime )} events.')
        

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = MyApp()
    ex.show()
    sys.exit(app.exec())
