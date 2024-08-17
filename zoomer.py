import sys
import numpy as np
from PySide6.QtWidgets import (
    QApplication, QWidget, QPushButton, QVBoxLayout, QHBoxLayout, QFileDialog,
    QLabel, QSpinBox, QSlider, QMessageBox, QDialog, QSizePolicy
)
from PySide6.QtCore import Qt
from scipy.signal import savgol_filter as savgol
import pyqtgraph as pg
import csv

class RandomScatterPlotDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Random Scatter Plot')
        self.setGeometry(200, 200, 600, 400)

        layout = QVBoxLayout()
        
        innerlayout = QHBoxLayout()
        self.plotWidget = pg.PlotWidget()
        self.plotWidget.getViewBox().setMouseMode(pg.ViewBox.RectMode)        
        self.plotWidget.setLabel('left','Intensity [a.u.]')
        self.plotWidget.setLabel('bottom','Duration [us]')
        self.graphWidget = pg.PlotWidget()
        self.graphWidget.setLabel('left','Intensity [a.u.]')
        self.graphWidget.setLabel('bottom','Time [us]')        
        innerlayout.addWidget(self.plotWidget)
        innerlayout.addWidget(self.graphWidget)
        
        lowelayout = QHBoxLayout()
        self.selectedpeak = QSlider(Qt.Orientation.Horizontal)
        self.selectedpeak.setMinimum(0)
        self.selectedpeak.setMaximum(100)
        self.selectedpeak.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        lowelayout.addWidget(self.selectedpeak)
        lowelayout.addWidget(QLabel('Duration [us]:'))
        self.Lduration = QLabel('n/a')
        lowelayout.addWidget(self.Lduration)
        lowelayout.addWidget(QLabel('Intensity [a.u.]:'))
        self.Lpeak = QLabel('n/a')
        lowelayout.addWidget(self.Lpeak) 
        
        layout.addLayout(innerlayout)
        layout.addLayout(lowelayout)       
        
        self.setLayout(layout)
        self.peaks=[]
        self.generateRandomData()

    def generateRandomData(self,x=None,y=None,data=None):
        self.plotWidget.clear()
        self.graphWidget.clear()        
        if x is None:
            x = np.random.rand(1000)
            y = np.random.rand(1000)
        self.selectedpeak.setMaximum(len(x)-1)
        self.x,self.y=x,y
        self.peaks=data
        self.plotWidget.plot(x, y, pen=None, symbol='o', symbolSize=5)
        self.point = self.plotWidget.plot([x[0]],[y[0]],pen=None, symbol='o', symbolSize=5, symbolBrush='orange')
        self.selectedpeak.setValue(0)
        self.selectedpeak.valueChanged.connect(self.updatePoint)
        self.updatePoint()
        
    def updatePoint(self,value=0):
        # Update the point based on the selected peak value
        if self.peaks is not None:
            peak = self.peaks[value]
            self.graphWidget.clear()
            self.graphWidget.plot(peak[:,0],peak[:,1], pen='y',symbol='o',symbolSize=3)    
        self.point.setData([self.x[value]], [self.y[value]])  # Assuming peaks is a list of (x, y) tuples    
        self.Lpeak.setText(f'{int(self.y[value])}')
        self.Lduration.setText(f'{int(self.x[value])}')

class MyApp(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()
        self.loaded = False
        self.finished=False
        self.inmemory = False
        self.duration,self.intensity = [],[]
        self.safepeaks = []
        
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

        self.isolateButton = QPushButton('Isolate', self)
        self.isolateButton.clicked.connect(self.isolatePeaks)
        controlLayout.addWidget(self.isolateButton)
        
        self.saveButton = QPushButton('Save CSV', self)
        self.saveButton.clicked.connect(self.saveData)
        controlLayout.addWidget(self.saveButton)
        

        layout.addLayout(controlLayout)
        
        self.sliding = QSlider(Qt.Orientation.Horizontal,self)
        self.sliding.setMinimum(0)
        self.sliding.setMaximum(100000)
        self.sliding.setPageStep(1000)
        self.sliding.valueChanged.connect(self.updatePlot)
        layout.addWidget(self.sliding)

        self.plotWidget1 = pg.PlotWidget(title="Intensity vs Time")
        self.plotWidget2 = pg.PlotWidget(title="PMT vs Time")
        self.plotWidget1.getViewBox().setMouseMode(pg.ViewBox.RectMode)
        self.plotWidget2.getViewBox().setMouseMode(pg.ViewBox.RectMode)
        
        self.plotWidget1.getViewBox().sigXRangeChanged.connect(lambda vb, range: self.on_xrange_changed(self.plotWidget1.getAxis('bottom'), range))
        self.plotWidget2.getViewBox().sigXRangeChanged.connect(lambda vb, range: self.on_xrange_changed(self.plotWidget2.getAxis('bottom'), range))

        layout.addWidget(self.plotWidget1)
        layout.addWidget(self.plotWidget2)

        self.setLayout(layout)

    def openFileDialog(self):
        filePath, _ = QFileDialog.getOpenFileName(self, 'Open CSV', '', 'CSV Files (*.csv);;All Files (*)')
        if filePath:
            self.filename= filePath
            self.loaded = False
            self.finished=False
            self.inmemory = False
            self.loadAndPlotData()
            
    def saveData(self):        
        defaultName = self.filename.rsplit('.', 1)[0] + '_processed.csv'
        filePath, _ = QFileDialog.getSaveFileName(self, 'Save CSV', defaultName, 'CSV Files (*.csv);;All Files (*)')
        QApplication.setOverrideCursor(Qt.WaitCursor)
        if not filePath:
            return
        if self.finished is False: 
            QMessageBox.warning(self, 'Warning', 'Please do isolate the peaks first.')
            return
        if len(self.duration) == 0:
            self.calculateFeatures()
        with open(filePath, 'w', newline='') as csvfile:
            csvwriter = csv.writer(csvfile)
            for duration, intensity in zip(self.duration, self.intensity):
                csvwriter.writerow([duration, intensity])
        QApplication.restoreOverrideCursor()
        QMessageBox.information(self, 'Data Saved', f'Data successfully saved to {filePath}.')

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
        
        self.messageLabel.setText(f'Loaded file: {self.filename}')        
        
        
        self.plotWidget1.clear()
        self.line1 = self.plotWidget1.plot([], [], pen='y',symbol='o',symbolSize=3)
        self.fit1  = self.plotWidget1.plot([], [], pen='r')
        self.threshline = self.plotWidget1.plot([], [], pen='b')
        self.plotWidget2.clear()        
        self.line2 = self.plotWidget2.plot([], [], pen='y',symbol='o',symbolSize=3)
        self.fit2 = self.plotWidget2.plot([], [], pen='r')
        
        self.loaded = True
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
        
    def calculateFeatures(self):
        win = self.winSpinBox.value()
        if win%2 == 0:
            win+=1
        peaks=[]
        prevtime=0
        tmp=[]
        for i in range(1,len(self.xtime)):
            time = self.xtime[i]
            fluo = self.xfluo[i]
            if int((time-prevtime)*1000) > int(self.acqtime*1000):
                if len(tmp)>win:
                    peaks.append(np.array(tmp))
                tmp=[]                    
            else:                
                tmp.append([time,fluo])        
            prevtime = time
        intensity= []
        duration = []
        for p in peaks:
            intensity.append(np.max(savgol(p[:,1],win,1)))
            duration.append((p[-1,0]-p[0,0])*1000)            
        self.duration,self.intensity = duration,intensity
        self.safepeaks = peaks

    def showRandomScatterPlot(self):
        dialog = RandomScatterPlotDialog()        
            
        if self.finished is True:        
            self.calculateFeatures()
            dialog.generateRandomData(self.duration,self.intensity,self.safepeaks)
            
        dialog.exec_()

    def prevWindow(self):
        self.range=[1,self.number]
        self.updatePlot()
        self.plotWidget1.autoRange()
        self.plotWidget2.autoRange()

    def isolatePeaks(self):
        win = self.winSpinBox.value()
        if win%2 == 0:
            win+=1
        QApplication.setOverrideCursor(Qt.WaitCursor)     
        self.loaded=False        
        self.finished=True
        if self.inmemory is False:
            f = open(self.filename)
            self.memfluo=[]
            self.mempmt=[]
            self.memtime=[]
            f.readline()
            for riga in f:
                tmptime,tmpfluo,tmppmt=[float(number) for number in riga.strip().split(',')[:3]]
                self.memtime.append(tmptime)
                self.memfluo.append(tmpfluo)
                self.mempmt.append(tmppmt)
            f.close()   
            self.inmemory = True    
             
        filtered = savgol(self.memfluo,win,1)
        threshold = self.thresholdSpinBox.value()
    
        block = np.where(filtered>threshold)
        
        self.xtime = np.array(self.memtime)[block]
        self.xfluo = np.array(self.memfluo)[block]
        self.xpmt = np.array(self.mempmt)[block]
        
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
