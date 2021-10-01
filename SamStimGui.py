# -*- coding: utf-8 -*-
"""
GUI for initiating camstim or samstim scripts

@author: SVC_CCG
"""

from __future__ import division
import os
import subprocess
from PyQt5 import QtCore, QtGui, QtWidgets


def start():
    app = QtWidgets.QApplication.instance()
    if app is None:
        app = QtWidgets.QApplication([])
    obj = SamStimGui(app)
    app.exec_()


class SamStimGui():
    
    def __init__(self,app):
        self.app = app
        self.baseDir = r"\\allen\programs\mindscope\workgroups\dynamicrouting\DynamicRoutingTask"
        
        # main window
        winHeight = 600
        winWidth = 400
        self.mainWin = QtWidgets.QMainWindow()
        self.mainWin.setWindowTitle('SamStimGui')
        self.mainWin.resize(winWidth,winHeight)
        screenCenter = QtWidgets.QDesktopWidget().availableGeometry().center()
        mainWinRect = self.mainWin.frameGeometry()
        mainWinRect.moveCenter(screenCenter)
        self.mainWin.move(mainWinRect.topLeft())

        # rig layouts
        self.rigGroupBox = []
        self.rigLayout = []
        self.camstimButton = []
        self.samstimButton = []
        self.stimModeLayout = []
        self.stimModeGroupBox = []
        self.lightButton = []
        self.solenoidButton = []
        self.luminanceTestButton = []
        self.waterTestButton = []
        self.mouseIDLabel = []
        self.mouseIDEdit = []
        self.taskScriptLabel = []
        self.taskScriptEdit = []
        self.taskVersionLabel = []
        self.taskVersionEdit = []
        self.startTaskButton = []
        for n in range(6):
            self.rigLayout.append(QtWidgets.QGridLayout())
            self.setLayoutGridSpacing(self.rigLayout[-1],winHeight/3,winWidth/2,7,3)

            self.camstimButton.append(QtWidgets.QRadioButton('camstim'))
            self.samstimButton.append(QtWidgets.QRadioButton('samstim'))
            self.samstimButton[-1].setChecked(True)
            self.stimModeLayout.append(QtWidgets.QHBoxLayout())
            for button in (self.camstimButton[-1],self.samstimButton[-1]):
                button.clicked.connect(self.setStimMode)
                self.stimModeLayout[-1].addWidget(button)
            self.stimModeGroupBox.append(QtWidgets.QGroupBox())
            self.stimModeGroupBox[-1].setLayout(self.stimModeLayout[-1])

            self.lightButton.append(QtWidgets.QPushButton('Light',checkable=True))
            self.lightButton[-1].clicked.connect(self.setLight)
            
            self.solenoidButton.append(QtWidgets.QPushButton('Solenoid',checkable=True))
            self.solenoidButton[-1].setEnabled(False)
            self.solenoidButton[-1].clicked.connect(self.setSolenoid)
            
            self.luminanceTestButton.append(QtWidgets.QPushButton('Luminance Test'))
            self.luminanceTestButton[-1].clicked.connect(self.startLuminanceTest)
            
            self.waterTestButton.append(QtWidgets.QPushButton('Water Test'))
            self.waterTestButton[-1].clicked.connect(self.startWaterTest)

            self.mouseIDLabel.append(QtWidgets.QLabel('Mouse ID:'))
            self.mouseIDLabel[-1].setAlignment(QtCore.Qt.AlignVCenter)
            self.mouseIDEdit.append(QtWidgets.QLineEdit())
            self.mouseIDEdit[-1].setAlignment(QtCore.Qt.AlignHCenter)

            self.taskScriptLabel.append(QtWidgets.QLabel('Task Script:'))
            self.taskScriptLabel[-1].setAlignment(QtCore.Qt.AlignVCenter)
            self.taskScriptEdit.append(QtWidgets.QLineEdit('DynamicRouting1'))
            self.taskScriptEdit[-1].setAlignment(QtCore.Qt.AlignHCenter)

            self.taskVersionLabel.append(QtWidgets.QLabel('Task Version:'))
            self.taskVersionLabel[-1].setAlignment(QtCore.Qt.AlignVCenter)
            self.taskVersionEdit.append(QtWidgets.QLineEdit('vis detect'))
            self.taskVersionEdit[-1].setAlignment(QtCore.Qt.AlignHCenter)

            self.startTaskButton.append(QtWidgets.QPushButton('Start Task'))
            self.startTaskButton[-1].clicked.connect(self.startTask)
            
            self.rigLayout[-1].addWidget(self.stimModeGroupBox[-1],0,1,1,1)
            self.rigLayout[-1].addWidget(self.lightButton[-1],1,1,1,1)
            self.rigLayout[-1].addWidget(self.solenoidButton[-1],2,1,1,1)
            self.rigLayout[-1].addWidget(self.luminanceTestButton[-1],2,0,1,1)
            self.rigLayout[-1].addWidget(self.waterTestButton[-1],2,2,1,1)
            self.rigLayout[-1].addWidget(self.mouseIDLabel[-1],3,0,1,1)
            self.rigLayout[-1].addWidget(self.mouseIDEdit[-1],3,1,1,2)
            self.rigLayout[-1].addWidget(self.taskScriptLabel[-1],4,0,1,1)
            self.rigLayout[-1].addWidget(self.taskScriptEdit[-1],4,1,1,2)
            self.rigLayout[-1].addWidget(self.taskVersionLabel[-1],5,0,1,1)
            self.rigLayout[-1].addWidget(self.taskVersionEdit[-1],5,1,1,2)
            self.rigLayout[-1].addWidget(self.startTaskButton[-1],6,1,1,1)
            
            self.rigGroupBox.append(QtWidgets.QGroupBox('E'+str(n+1)))
            self.rigGroupBox[-1].setLayout(self.rigLayout[-1])

        # main layout
        self.mainWidget = QtWidgets.QWidget()
        self.mainWin.setCentralWidget(self.mainWidget)
        self.mainLayout = QtWidgets.QGridLayout()
        self.setLayoutGridSpacing(self.mainLayout,winHeight,winWidth,3,2)
        self.mainWidget.setLayout(self.mainLayout)
        
        for n,rigBox in enumerate(self.rigGroupBox):
            i,j = (n,0) if n<3 else (n-3,1)
            self.mainLayout.addWidget(rigBox,i,j,1,1)
        
        self.mainWin.show()

    def setLayoutGridSpacing(self,layout,height,width,rows,cols):
        for row in range(rows):
            layout.setRowMinimumHeight(row,height/rows)
            layout.setRowStretch(row,1)
        for col in range(cols):
            layout.setColumnMinimumWidth(col,width/cols)
            layout.setColumnStretch(col,1)

    def setStimMode(self):
        sender = self.mainWin.sender()
        useSamstim = sender in self.samstimButton
        rig = self.samstimButton.index(sender) if useSamstim else self.camstimButton.index(sender)
        self.solenoidButton[rig].setEnabled(not useSamstim)
        self.waterTestButton[rig].setEnabled(useSamstim)
        self.luminanceTestButton[rig].setEnabled(useSamstim)
        self.taskScriptEdit[rig].setEnabled(useSamstim)
        self.taskVersionEdit[rig].setEnabled(useSamstim)
        if useSamstim and self.lightButton[rig].isChecked():
            self.setLight(lightOn=False,rig=rig,camstim=True)
            self.lightButton[rig].setChecked(False)

    def setLight(self,lightOn,rig=None,camstim=None):
        if rig is None:
            sender = self.mainWin.sender()
            rig = self.lightButton.index(sender)
        if camstim is None:
            camstim = self.camstimButton[rig].isChecked()
        if camstim:
            scriptPath = os.path.join(self.baseDir,'camstimControl.py')
            batString = ('python ' + '"' + scriptPath + '"' +
                         ' --rigName ' + '"E' + str(rig+1) + '"' +
                         ' --lightOn ' + str(lightOn))
        else:
            self.lightButton[rig].setChecked(False)
            scriptPath = os.path.join(self.baseDir,'startTask.py')
            taskScript = os.path.join(self.baseDir,'TaskControl.py')
            batString = ('python ' + '"' + scriptPath +'"' + 
                         ' --rigName ' + '"E' + str(rig+1) + '"' + 
                         ' --taskScript ' + '"' + taskScript + '"')
        self.runBatFile(batString)
        
    def setSolenoid(self,openSolenoid):
        sender = self.mainWin.sender()
        rig = self.solenoidButton.index(sender)
        if self.camstimButton[rig].isChecked():
            scriptPath = os.path.join(self.baseDir,'camstimControl.py')
            batString = ('python ' + '"' + scriptPath + '"' +
                         ' --rigName ' + '"E' + str(rig+1) + '"' +
                         ' --solenoidOpen ' + str(openSolenoid))
            self.runBatFile(batString)
    
    def startLuminanceTest(self):
        pass
    
    def startWaterTest(self):
        pass

    def startTask(self):
        sender = self.mainWin.sender()
        rig = self.startTaskButton.index(sender)
        mouseID = self.mouseIDEdit[rig].text()
        if len(mouseID) != 6:
            print('mouseID must be 6 digits')
            return
        if self.camstimButton[rig].isChecked():
            scriptPath = os.path.join(self.baseDir,'camstimControl.py')
            batString = ('python ' + '"' + scriptPath +'"' + 
                         ' --rigName ' + '"E' + str(rig+1) + '"' + 
                         ' --mouseID ' + '"' + mouseID + '"')
        else:
            scriptPath = os.path.join(self.baseDir,'startTask.py')
            taskScript = self.taskScriptEdit[rig].text()
            taskVersion = self.taskVersionEdit[rig].text()
            batString = ('python ' + '"' + scriptPath +'"' + 
                         ' --rigName ' + '"E' + str(rig+1) + '"' + 
                         ' --subjectName ' + '"' + mouseID + '"' + 
                         ' --taskScript ' + '"' + taskScript + '"' + 
                         ' --taskVersion ' + '"' + taskVersion + '"')
        self.runBatFile(batString)

    def runBatFile(self,batString):
        anacondaActivatePath = r"C:\Users\svc_ncbehavior\Anaconda3\Scripts\activate.bat"
        anacondaPath = r"C:\Users\svc_ncbehavior\Anaconda3"

        toRun = ('call ' + '"' + anacondaActivatePath + '" ' + '"' + anacondaPath + '"' + '\n' +
                 'call activate zro27' + '\n' +
                 batString)

        batFile = os.path.join(self.baseDir,'samstimRun.bat')

        with open(batFile,'w') as f:
            f.write(toRun)
            
#        p = subprocess.Popen([batFile])
#        p.wait()

if __name__=="__main__":
    start()