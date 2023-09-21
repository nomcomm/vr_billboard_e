#################################################
### Carismalab@MSU 2023                       ###
### Ralf Schmaelzle, Hee Jung Cho 			  ###
### VR-Billboard Driving E Study              ###  
#################################################

import viz, vizact, vizconnect, vizfx, vizinfo, vizshape, viztask, time, vizinput, os, json, vizdlg, random
from os import path
import pandas as pd
from utils import common_utils
from utils import eye_tracker_utils
from utils import hud
from datetime import datetime
#import SightLab_VR_driving

viz.setMultiSample(8)
viz.fov(80)
#Dictionary of Vizconnect Files
vizconnect_dict = {	'Omnicept Driving':'vizconnect_config_omnicept_driving.py',
                    'Driving Desktop': 'vizconnect_config_desktop_driving.py',
                    'Oculus No Eyetracker':'vizconnect_config_oculus_driving.py',
                    #'HP Omnicept':'vizconnect_config_omnicept.py',
                    }

vizconnect_configs = [  'Omnicept Driving',
                        'Driving Desktop', 
                        'Oculus No ET',
                        ]
                        
configuration = vizinput.choose('Select a Vizconnect configuration', vizconnect_configs)
vizconnect_path = 'vizconnect_configs/{}'.format(vizconnect_dict[vizconnect_configs[configuration]])

vizconnect.go(vizconnect_path)
viz.window.setSize(800, 720)
use_vive_pro = True if vizconnect_configs[configuration] in ['Omnicept', 'Omnicept Driving'] else False
gazeTime = None
eyeTracker = vizconnect.getTracker('eye_tracker').getRaw()
transportNode = None
rightHand = None
leftHand = None
env = None
point = None
envItems = []
newItems = []
objectCount = None
configureFlag = None
firstWrite = True
writeToggle = True

#Options for Video recording
viz.setOption('viz.AVIRecorder.maxWidth','800')
viz.setOption('viz.AVIRecorder.maxHeight','720')

# Keep track of order that objects were viewed and time to fixation
# startTime is initialized when the recording of eye tracker data starts
timeLine = []
startTime = None

indicatorWindow = viz.addWindow(size=(1,1), pos=(0,1))
indicatorWindow.fov(79)

# Add window for rendering GUI objects in mirrored desktop window
overlayWindow = viz.addWindow(size=(1,1), pos=(0,1), clearMask = 0, scene=viz.addScene())
configureWindow = viz.addWindow(size=(1,1), pos=(0,1), clearMask = 0, scene=viz.addScene())
hudMirror = hud.HUD(overlayWindow)
hudMirror.visible(viz.OFF)

# Add quad to hide and show the scene
fadeQuad = common_utils.FadeQuad()

# Store all eye tracking data in a list
trackingData = []
#ballTracker = None
trialNumber = 0
trackingFile = None

# Variable for triggering flags
flag = '-'

count = 1
record = None
replayFile = None
dateString = None
fileName = None
participant = None
participant_info = viz.Data()
participant_info.id = datetime.now().strftime("%m-%d-%Y-%H-%M-%S")
#participant_info.firstName = ""
#participant_info.lastName = ""

console = viz.addText('', parent=viz.ORTHO, scene=overlayWindow, color=viz.RED, fontSize=30, pos=[20,60,0])

#Default scene configuration settings
sceneConfigDict = {
    "record" : 0,
    "grabObjects": 0,
    "avatarHead": 0,
    "avatarrhand": 0,
    "avatarlhand": 0,
    "environment": 0,
    "gazePoint": 0,
    "fixationTime": 0.5,
    "trials": -1}

defaultSceneConfig = sceneConfigDict

invisibleObjects = []
objects = []
resources = []
parent = ['-']
gazeObjectsDict = {}
grabObjectsDict = {}
initGrabObjectsPos = {}

is_GUI = 1

headLight = viz.MainView.getHeadLight()
headLight.disable()

#Add manual fixation objects here
'''
MANUALLY ADDED FIXATION OBJECTS
'''

class AvatarTracker:
    def __init__(self, participant,trialNumber):
        self.pos = None
        self.update_function = vizact.onupdate(vizconnect.PRIORITY_ANIMATOR+1,self.UpdatePosition)
        participant = str(participant)
        fileName = 'data/{p}_tracking_data_replay_trial_{t}.txt'.format(p=participant, t = trialNumber+1)  
        self.replayFile = open(fileName, "w")
        self.replayFile.write(vizconnect_dict[vizconnect_configs[configuration]] + '\n')
        global newItems
        print("new: ",newItems, len(newItems))
        self.replayFile.write("Object count: " + '\t' + str(objectCount) + ' ' + str(len(gazeObjectsDict.keys()) - len(newItems)) + '\n')
        resource_names = ''
        start_positions = ''
        for i in range(0, objectCount):
            resource_names += resources[i] + '\t'
        self.replayFile.write(str(resource_names) + '\n')
        self.replayFile.write(str('\t'.join(gazeObjectsDict.keys())) + '\n')
        self.replayFile.write(str('\t'.join(invisibleObjects)) + '\n')
        
        
    def UpdatePosition(self):
        objectData = []
        flag = 'Animation '
        vizconnect.getAvatar().getAttachmentPoint('r_hand').getNode3d()
        vizconnect.getTracker('r_hand_tracker').getNode3d()
 
        for item in objects:
            objectData.append(item.getPosition(mode=viz.ABS_GLOBAL))
            objectData.append(item.getEuler(viz.ABS_GLOBAL))
        #print(objectData)
        self.writeEvent(objectData)
        
    def writeEvent(self, objectData):
        writeString = str(viz.tick() - startTime) + '\t'
        for item in objectData:
            writeString = writeString + str(item) + '\t'
        writeString = writeString + '\n'
#        print(writeString)
        self.replayFile.write(writeString)
        self.replayFile.flush()
    
    def __del__(self):
        if self.replayFile.closed is False:
            self.replayFile.close()
            
#Sets scene configurations settings to default
def defaultSettings(optionsDict, fixationtime):
    global sceneConfigDict, defaultSceneConfig
    sceneConfigDict = defaultSceneConfig
    
    for opt in optionsDict:
        if type(optionsDict[opt]).__name__ == "VizDropList":
            optionsDict[opt].select(sceneConfigDict[opt])
        else:
            optionsDict[opt].set(sceneConfigDict[opt])
    
    fixationtime.message("0.50")

configurePanel = None

#Function for the Environment Configuration GUI
def configureEnvironment(environment):
    global sceneConfigDict, env, envItems, configureFlag
    envFile =  "resources/environment/" + environment.getItems()[environment.getSelection()]
    
    if env is not None:
        if not env.getFilename() == envFile:
            env.remove()
            env = vizfx.addChild(envFile)
            configureFlag = environment.getItems()[environment.getSelection()]
            for item in envItems:
                sceneConfigDict.pop(item)
                        
    else:
        startFlag = 1
        env = vizfx.addChild(envFile)  
        configureFlag = environment.getItems()[environment.getSelection()]
        
    envItems = []
    for i in env.getNodeNames(flags = viz.TYPE_GROUP):
        if not i in env.getNodeNames(flags = viz.TYPE_TRANSFORM) and i not in env.getNodeNames(flags = viz.TYPE_LIGHT) and not i == "__VIZARD_NODE__" and not i == env.getFilename()[22:] and not env.getChild(i) == viz.VizChild(-1):
            envItems.append(i)
        
    global configurePanel
    configurePanel = vizinfo.InfoPanel('Select fixation/grab objects and visibility.',title='Environment Configuration', window = configureWindow ,align=viz.ALIGN_CENTER_TOP, icon=False)
    configurePanel.addSeparator()
    
    textbox = configurePanel.addLabelItem('Child Name', viz.addTextbox())
    addChildButton = configurePanel.addItem(viz.addButtonLabel('Add Child Object'), align=viz.ALIGN_LEFT_CENTER)
    doneButton = configurePanel.addItem(viz.addButtonLabel('Done'),align=viz.ALIGN_LEFT_CENTER)
    
    configurePanel.addSection("Fixations | Visible | Grabbable")
           
    envConfig = []
    for item in envItems:
        row = vizdlg.Panel(layout=vizdlg.LAYOUT_HORZ_BOTTOM,background=False,border=False)
        
        fixation = row.addItem(viz.addCheckbox())
        visible = row.addItem(viz.addCheckbox())
        grabbable = row.addItem(viz.addCheckbox())
        configurePanel.addLabelItem(item, row)
        
        print("scene: ", item, envItems, sceneConfigDict)
        
        if item in sceneConfigDict:
            fixation.set(sceneConfigDict[item][0])
            visible.set(sceneConfigDict[item][1])
            grabbable.set(sceneConfigDict[item][2])
            print("scene: ", sceneConfigDict[item])
        else:
            fixation.set(1) 
            #Child ending with the name '_env' are set as the environment
            if item[-4:] == "_env":
                fixation.set(0)
            visible.set(1)
            grabbable.set(0)
        envConfig.append([item, fixation, visible, grabbable])
        
    
    def doneConfigure():
        for item in envConfig:
            sceneConfigDict[item[0]] = [item[1].get(), item[2].get(), item[3].get()]
        configurePanel.remove()
    
    def addChildFunction():
        
        childName = textbox.get()
   
        if not env.getChild(childName) == viz.VizChild(-1):
            envItems.append(childName)
            
            row = vizdlg.Panel(layout=vizdlg.LAYOUT_HORZ_BOTTOM,background=False,border=False)
        
            fixation = row.addItem(viz.addCheckbox())
            visible = row.addItem(viz.addCheckbox())
            grabbable = row.addItem(viz.addCheckbox())
            configurePanel.addLabelItem(childName, row)
            
            fixation.set(1)
            visible.set(1)
            grabbable.set(0)
            
            envConfig.append([childName, fixation, visible, grabbable])
        
        else:
            configurePanel.addLabelItem("Child Not Found", viz.addText(""))
        
    vizact.onbuttonup(addChildButton, addChildFunction)
    vizact.onbuttonup(doneButton, doneConfigure)
                

def progressBarMessage(sliderPOS, progressBar):
    message = str('%.2f'%(float(sliderPOS)))
    progressBar.message(message)
    
    
#Function that enables the Scene Setup GUI
def sceneSetup():
    global sceneConfigDict
    
    sceneInfo = vizinfo.InfoPanel('Configure your scene. Last saved configuration will be auto-filled on every run.',title='Scene Configuration',window=overlayWindow, align=viz.ALIGN_LEFT_TOP, icon=False)
    sceneInfo.addSeparator()
    screenrecord = sceneInfo.addLabelItem('Screen Record', viz.addCheckbox())
    numberOfTrials = sceneInfo.addLabelItem('Number of Trials', viz.addTextbox())
    fixationtime = sceneInfo.addLabelItem('Fixation Time', viz.addProgressBar("0.5"))
    fixationtime.set(0.5)
    vizact.onslider(fixationtime, progressBarMessage, fixationtime)
    sceneInfo.addSection('Avatar')
    
    filePath = os.path.join(os.path.dirname(__file__), 'resources/avatar/head')
    fileList = []
    for filename in os.listdir(filePath):
        fileList.append(filename)
    
    avatarhead = sceneInfo.addLabelItem('Head', viz.addDropList())
    avatarhead.addItems(fileList)
    
    filePath = os.path.join(os.path.dirname(__file__), 'resources/avatar/hands')
    fileList = []
    for filename in os.listdir(filePath):
        fileList.append(filename)
    
    avatarrhand = sceneInfo.addLabelItem('Right Hand', viz.addDropList())
    avatarrhand.addItems(fileList)    
    avatarlhand = sceneInfo.addLabelItem('Left Hand', viz.addDropList())
    avatarlhand.addItems(fileList)    
    
    sceneInfo.addSection('Environment')
    
    filePath = os.path.join(os.path.dirname(__file__), 'resources/environment')
    fileList = []
    for filename in os.listdir(filePath):
        fileList.append(filename)
    
    environment = sceneInfo.addLabelItem('Environment', viz.addDropList())
    environment.addItems(fileList)
    
    envConfigure = sceneInfo.addLabelItem('' , viz.addButtonLabel('Configure'))
    
    filePath = os.path.join(os.path.dirname(__file__), 'resources/gaze_point')
    fileList = []
    for filename in os.listdir(filePath):
        fileList.append(filename)
    
    gazepoint = sceneInfo.addLabelItem('Gaze Point', viz.addDropList())
    gazepoint.addItems(fileList)
    
    sceneInfo.addSeparator()
    defaultButton = sceneInfo.addLabelItem('' , viz.addButtonLabel('Revert to Default Settings'))
    sceneInfo.addSeparator()
    saveButton = sceneInfo.addItem(viz.addButtonLabel('Continue'),align=viz.ALIGN_LEFT_CENTER)
    
    if len(avatarhead.getItems()) == 0 or len(avatarrhand.getItems()) == 0 or len(environment.getItems()) == 0:
        sceneInfo.remove()
        error = vizinfo.InfoPanel('Please add appropriate resources into all the resource folders and run again',title='Error', align=viz.ALIGN_CENTER_CENTER, icon=False)
        okayButton = error.addItem(viz.addButtonLabel('Okay'),align=viz.ALIGN_CENTER_CENTER)
        yield viztask.waitButtonUp(okayButton)
        viz.quit()

    optionsDict = {   
    "record": screenrecord, 
    "avatarHead": avatarhead,
    "avatarrhand": avatarrhand,
    "avatarlhand": avatarlhand,
    "environment": environment,
    "gazePoint": gazepoint,
    "fixationTime": fixationtime
    }
    
    if path.exists("config.txt") and not os.path.getsize("config.txt") == 0:
        configFile = open("config.txt", "r")
        try:
            sceneConfigDict = json.load(configFile)
            print("Loaded Config File\n", sceneConfigDict)
            
        except:
            print("Failed to load settings")
        configFile.close()
        
    else:
        print("No config file found")
        
    for opt in optionsDict:
        if type(optionsDict[opt]).__name__ == "VizDropList":
            optionsDict[opt].select(sceneConfigDict[opt])
        else:
            optionsDict[opt].set(sceneConfigDict[opt])
            
    fixationtime.message(str('%.2f'%(sceneConfigDict["fixationTime"])))
    
    if sceneConfigDict is None:
        sceneConfigDict = {}
            
    envFile =  "resources/environment/" + environment.getItems()[environment.getSelection()]
    vizact.onbuttonup(envConfigure, configureEnvironment, environment)
    vizact.onbuttonup(defaultButton, defaultSettings, optionsDict, fixationtime)
    
    yield viztask.waitButtonUp(saveButton)
    
    #moved to here because of loading issues
    participant = yield participantInfo()
    
    global configuration, transportNode, rightHand, leftHand, objects, gazeTime, envItems, record, env, resources, objectCount
    
    if not configureFlag == environment.getItems()[environment.getSelection()]:
        startFlag = 1
        envItems = []
        envFile =  "resources/environment/" + environment.getItems()[environment.getSelection()]
        
        if env is not None:
            env.remove()
        env = vizfx.addChild(envFile)
        for i in env.getNodeNames(flags = viz.TYPE_GROUP):
            if not i in env.getNodeNames(flags = viz.TYPE_TRANSFORM) and i not in env.getNodeNames(flags = viz.TYPE_LIGHT) and not i == "__VIZARD_NODE__" and not i == "scene.gltf" and not i == env.getFilename()[22:] and not env.getChild(i) == viz.VizChild(-1):
                if i not in envItems:
                    envItems.append(i)
                sceneConfigDict[i] = [1,1,0]
                
    sceneConfigDict["fixationTime"] = fixationtime.get() 
    sceneConfigDict["record"] = screenrecord.get()
    if numberOfTrials.get()=="":
        sceneConfigDict["trials"]=-1
    else:
        sceneConfigDict["trials"]=int(numberOfTrials.get())
    sceneConfigDict["environment"] = environment.getSelection()
    sceneConfigDict["avatarHead"] = avatarhead.getSelection()
    sceneConfigDict["avatarrhand"] = avatarrhand.getSelection()
    sceneConfigDict["avatarlhand"] = avatarlhand.getSelection()
    sceneConfigDict["gazePoint"] = gazepoint.getSelection()

    objects.append(env)
    resources.append("resources/environment/" + environment.getItems()[environment.getSelection()])
    
    gaze = vizfx.addChild("resources/gaze_point/" + gazepoint.getItems()[gazepoint.getSelection()])
    objects.append(gaze)
    resources.append("resources/gaze_point/" + gazepoint.getItems()[gazepoint.getSelection()])
    
    gaze.disable(viz.INTERSECTION)
    gaze.renderToMain = False
    
    global point
    point = gaze
    
    objects.append(viz.MainView)
    resources.append("resources/avatar/head/" + avatarhead.getItems()[avatarhead.getSelection()])
    
    record = sceneConfigDict["record"]

    if vizconnect_configs[configuration] == "Desktop":
        headNode = vizconnect.getTracker('head_tracker').getNode3d()
        rightHand = vizconnect.getTracker('r_hand_tracker').getNode3d()
        rightHandModel = vizfx.addChild("resources/avatar/hands/" + avatarrhand.getItems()[avatarrhand.getSelection()])
        rightHandModel.setParent(headNode)
        link_tracker_right = viz.link(rightHand,rightHandModel)
        
    elif vizconnect_configs[configuration] == "Oculus No ET":
        print('this is it')
        headNode = vizconnect.getTracker('head_tracker').getNode3d()
        rightHand = vizconnect.getTracker('r_hand_tracker').getNode3d()
        rightHandModel = vizfx.addChild("resources/avatar/hands/" + avatarrhand.getItems()[avatarrhand.getSelection()])
        rightHandModel.setParent(headNode)
        link_tracker_right = viz.link(rightHand,rightHandModel)
        
    elif vizconnect_configs[configuration] == "Omnicept Driving":
        print('this is it')
        headNode = vizconnect.getTracker('head_tracker').getNode3d()
        rightHand = vizconnect.getTracker('r_hand_tracker').getNode3d()
        #rightHandModel = vizfx.addChild("resources/avatar/hands/" + avatarrhand.getItems()[avatarrhand.getSelection()])
        #rightHandModel.setParent(headNode)
        #link_tracker_right = viz.link(rightHand,rightHandModel)
        
    else:
        transportNode = vizconnect.getTransport('main_transport').getNode3d()
        rightHand = vizconnect.getTracker('r_hand_tracker').getNode3d()
        rightHandModel = vizfx.addChild("resources/avatar/hands/" + avatarrhand.getItems()[avatarrhand.getSelection()])
        rightHandModel.setParent(transportNode)
        link_tracker_right = viz.link(rightHand,rightHandModel) 

        
        leftHand = vizconnect.getTracker('l_hand_tracker').getNode3d()
        leftHandModel = vizfx.addChild("resources/avatar/hands/" + avatarlhand.getItems()[avatarlhand.getSelection()])
        leftHandModel.setParent(transportNode)
        link_tracker_left = viz.link(leftHand,leftHandModel)

        objects.append(leftHandModel)
        resources.append("resources/avatar/hands/" + avatarlhand.getItems()[avatarlhand.getSelection()])
    
    #objects.append(rightHandModel)
    resources.append("resources/avatar/hands/" + avatarrhand.getItems()[avatarrhand.getSelection()])
    
    global indicatorWindow
    
    # Add window for rendering indicator in mirrored desktop window
    gaze.renderOnlyToWindows([indicatorWindow])
        
    global gazeObjectsDict
    global invisibleObjects
    
    objectCount = len(objects)
    
    for i in gazeObjectsDict:
        objects.append(gazeObjectsDict[i])
    
    for i in envItems:
        if sceneConfigDict[i][0]:
            gazeObjectsDict[i] = env.getChild(i)
            objects.append(env.getChild(i))
        
        if not sceneConfigDict[i][1]:
            env.getChild(i).alpha(0)
            invisibleObjects.append(i)
            
        if sceneConfigDict[i][2]:
            grabObjectsDict[i] = env.getChild(i)
            
    try:
        gazeTime = eye_tracker_utils.GazeTime(gazeObjectsDict, threshold=float(fixationtime.get()))
    except:
        gazeTime = eye_tracker_utils.GazeTime(gazeObjectsDict, threshold=0.5)
        
    if not grabObjectsDict == {}:
        grabTool = vizconnect.getRawTool('grabber')
        grabTool.setItems(list(grabObjectsDict.values()))
        
        if not vizconnect_configs[configuration] == 'Desktop':
            grabTool2 = vizconnect.getRawTool('grabber2')
            grabTool2.setItems(list(grabObjectsDict.values()))
        
    sceneInfo.remove()
    configFile = open("config.txt", "w")
    json.dump(sceneConfigDict, configFile)
    configFile.close()
    
    #participant = yield participantInfo()
    viztask.returnValue(participant)


#Function to collect participant data
def participantInfo():
    #Add an InfoPanel with a title bar
    participantInfo = vizinfo.InfoPanel('',title='Participant Information', window=overlayWindow, align=viz.ALIGN_RIGHT_BOTTOM, icon=False)
    
    #Add name and ID fields
    #textbox_last = participantInfo.addLabelItem('Last Name',viz.addTextbox())
    #textbox_first = participantInfo.addLabelItem('First Name',viz.addTextbox())
    textbox_id = participantInfo.addLabelItem('ID',viz.addTextbox())
    participantInfo.addSeparator(padding=(20,20))
    
    #Add submit button aligned to the right and wait until it's pressed
    submitButton = participantInfo.addItem(viz.addButtonLabel('Submit'),align=viz.ALIGN_RIGHT_CENTER)
    
    def submitInfo():
        data = viz.Data()
        #data.lastName = textbox_last.get()
        #data.firstName = textbox_first.get()
        data.id = textbox_id.get()
        participantInfo.remove()
        global participant
        participant = data.id
        
        # Return participant data
        viztask.returnValue(data)
        
    yield viztask.waitButtonUp(submitButton)
    submitInfo()
    
def moduleSetup():
    global configuration, transportNode, rightHand, leftHand, objects, gazeTime, envItems, record, env, resources, gazeObjectsDict, newItems
    
    env = objects[0]
    
    for i in objects:
        resources.append(i.getFilename())
        
    for item in gazeObjectsDict:
        print(item)
        if env.isChild(gazeObjectsDict[item]):
            envItems.append(item)
        else:
            newItems.append(item)
            objects.append(gazeObjectsDict[item])
            resources.append(gazeObjectsDict[item].getFilename())
            
        if item not in sceneConfigDict:
            sceneConfigDict[item] = [1,1,0] #fixations, visible, grab

    if not sceneConfigDict["avatarHead"]:
        sceneConfigDict["avatarHead"] = "resources/avatar/head/Male1.osgb"
        
    if not sceneConfigDict["avatarrhand"]:
        sceneConfigDict["avatarrhand"] = "resources/avatar/hands/controller2.osgb"
        
    if not sceneConfigDict["avatarlhand"]:
        sceneConfigDict["avatarlhand"] = "resources/avatar/hands/controller2.osgb"
        
    if not sceneConfigDict["gazePoint"]:
        sceneConfigDict["gazePoint"] = "resources/gaze_point/gaze_point1.osgb"
    
    gaze = vizfx.addChild(sceneConfigDict["gazePoint"])
    objects.insert(1, gaze)
    resources.insert(1, sceneConfigDict["gazePoint"])
    
    gaze.disable(viz.INTERSECTION)
    gaze.renderToMain = False
    
    global point
    point = gaze

    objects.insert(2, viz.MainView)
    resources.insert(2, sceneConfigDict["avatarHead"])
    
    record = sceneConfigDict["record"]

    if vizconnect_configs[configuration] == "Desktop":
        headNode = vizconnect.getTracker('head_tracker').getNode3d()
        rightHand = vizconnect.getTracker('r_hand_tracker').getNode3d()
        rightHandModel = vizfx.addChild(sceneConfigDict["avatarrhand"])
        rightHandModel.setParent(headNode)
        link_tracker_right = viz.link(rightHand,rightHandModel)
        
    elif vizconnect_configs[configuration] == "Oculus No ET":
        headNode = vizconnect.getTracker('head_tracker').getNode3d()
        rightHand = vizconnect.getTracker('r_hand_tracker').getNode3d()
        rightHandModel = vizfx.addChild(sceneConfigDict["avatarrhand"])
        rightHandModel.setParent(headNode)
        link_tracker_right = viz.link(rightHand,rightHandModel) 
        
    elif vizconnect_configs[configuration] == "Omnicept Driving":
        headNode = vizconnect.getTracker('head_tracker').getNode3d()
        rightHand = vizconnect.getTracker('r_hand_tracker').getNode3d()
        rightHandModel = vizfx.addChild(sceneConfigDict["avatarrhand"])
        #rightHandModel.setParent(headNode)
        link_tracker_right = viz.link(rightHand,rightHandModel) 
        
    else:
        transportNode = vizconnect.getTransport('main_transport').getNode3d()
        rightHand = vizconnect.getTracker('r_hand_tracker').getNode3d()
        rightHandModel = vizfx.addChild(sceneConfigDict["avatarrhand"])
        rightHandModel.setParent(transportNode)
        link_tracker_right = viz.link(rightHand,rightHandModel) 

        leftHand = vizconnect.getTracker('l_hand_tracker').getNode3d()
        leftHandModel = vizfx.addChild(sceneConfigDict["avatarlhand"])
        leftHandModel.setParent(transportNode)
        link_tracker_left = viz.link(leftHand,leftHandModel)

        objects.insert(4, leftHandModel)
        resources.insert(4, sceneConfigDict["avatarlhand"])

    objects.insert(3, rightHandModel)
    resources.insert(3, sceneConfigDict["avatarrhand"])
    
    global indicatorWindow
    
    # Add window for rendering indicator in mirrored desktop window
    gaze.renderOnlyToWindows([indicatorWindow])
        
    global invisibleObjects, objectCount
    
    objectCount = len(objects)
    
    for i in envItems:
        if sceneConfigDict[i][0]:
            gazeObjectsDict[i] = env.getChild(i)
            objects.append(env.getChild(i))
        
        if not sceneConfigDict[i][1]:
            env.getChild(i).alpha(0)
            invisibleObjects.append(i)
            
        if sceneConfigDict[i][2]:
            grabObjectsDict[i] = env.getChild(i)
            
    try:
        gazeTime = eye_tracker_utils.GazeTime(gazeObjectsDict, threshold=float(fixationtime.get()))
    except:
        gazeTime = eye_tracker_utils.GazeTime(gazeObjectsDict, threshold=0.5)
        
    if not grabObjectsDict == {}:
        grabTool = vizconnect.getRawTool('grabber')
        grabTool.setItems(list(grabObjectsDict.values()))
        
        if not vizconnect_configs[configuration] == 'Desktop':
            grabTool2 = vizconnect.getRawTool('grabber2')
            grabTool2.setItems(list(grabObjectsDict.values()))
        
    
#Function to set custom flags to be printed in the data files
def set_flag(flag_text, count_flag = False):
    global flag, count
    
    flag = str(flag_text)
    
    if count_flag:
        flag = flag + str(count)
        count += 1

def updateGaze():
    gazeMat = eyeTracker.getMatrix()
    gazeMat.postMult(viz.MainView.getMatrix())
    line = gazeMat.getLineForward(1000)
    info = viz.intersect(line.begin, line.end)
    global flag, writeToggle

    gazeTime.updateGazeObject(info.object)
    currentTime = viz.tick() - startTime
    
    if info.valid:
        data = [currentTime, info.point, viz.MainView.getPosition(), flag]
        objects[1].setPosition(info.point)
    else:
        fake_info = [0.00, 0.00, 0.00]
        data = [currentTime, fake_info, viz.MainView.getPosition(), flag]
        
    set_flag('-')
    if use_vive_pro:
        data.append(eyeTracker.getPupilDiameter())
    trackingData.append(data)
    
    if writeToggle:
        writeEvent(data)
    
def writeEvent(data):
    global firstWrite, participant, trackingData, trialNumber, trackingFile
    
    if firstWrite:
        firstWrite = False
        fileNameTracking = 'data/{p.id}_tracking_data_trial_{t}.txt'.format(p=participant, t=trialNumber+1)
        trackingFile = open(fileNameTracking, "w")

        if use_vive_pro:
            headers = ['seconds', 'point x', 'point y', 'point z', 'position x', 'position y', 'position z','pupil diameter', 'flag']
            fmt = '{:<8s}\t' * 9 + '\n\n'
            fileHeaders = fmt.format(*headers)
            trackingFile.write(fileHeaders)
        else:
            headers = ['seconds', 'point x', 'point y','point z', 'position x', 'position y', 'position z', 'flag']
            fmt = '{:<8s}\t' * 8 + '\n\n'
            fileHeaders = fmt.format(*headers)
            trackingFile.write(fileHeaders)
        
    else:
        if use_vive_pro:
            tick, point, position, flag, pupilDiameter = data
            fmt = '{:<8.2f}\t' * 8 + '{:<8s}\t'+ '\n'
            writeString = fmt.format(tick, point[0], point[1], point[2], position[0], position[1], position[2], pupilDiameter, flag)
            trackingFile.write(writeString)
#            if not flag == '-':
#                timeLine.append([flag, viz.tick() - startTimestartTime]) 
        else:
            tick, point, position, flag = data
            fmt = '{:<8.2f}\t' * 7 + '{:<8s}\t' + '\n'
            writeString = fmt.format(tick, point[0], point[1], point[2], position[0], position[1], position[2], flag)
            trackingFile.write(writeString)
#            if not flag == '-':
#                timeLine.append([flag, viz.tick() - startTime]) 

        
def onGazeBegin(e):
    print('gaze started : {:<15s}'.format(e.name))
    console.message('gaze started : {:<15s}'.format(e.name))
    set_flag('gaze started: ' + e.name)

def onGazeEnd(e):
    print('gaze ended   : {:<15s} seconds: {:.2f}'.format(e.name, e.time))
    console.message('gaze ended   : {:<15s} seconds: {:.2f}'.format(e.name, e.time))
    set_flag('gaze ended: ' + e.name)

def onGazeTime(e):
    threshold = gazeTime.getThreshold()
    print('gaze fixed   : {:<15s} seconds: {}'.format(e.name, threshold))
    console.message('gaze fixed   : {:<15s} seconds: {:.2f}'.format(e.name, threshold))
    timeToFixation = viz.tick() - startTime
    timeLine.append([e.name, timeToFixation])
    hudMirror.increase_views()
    set_flag('gaze fixated: ' + e.name)
    #if biopac == True:
        #acqServer.insertGlobalEvent(e.name, '', '')

def togglePoint():
    if point.renderToMain:
        point.renderOnlyToWindows([indicatorWindow])
    else:
        point.renderOnlyToWindows([viz.MainWindow, indicatorWindow])
    point.renderToMain = not point.renderToMain
    
def experiment():
    global startTime, record, gazeTime, trackingData, ballTracker, trialNumber, firstWrite, participant, writeToggle
    
    if is_GUI:
        participant = yield sceneSetup()
    else:
        participant = participant_info
        yield moduleSetup()
    
    for item in grabObjectsDict:
        initGrabObjectsPos[item] = [grabObjectsDict[item].getPosition(), grabObjectsDict[item].getEuler()]
    print(initGrabObjectsPos)
    
    
    ###hack 2
    
    transportNode = vizconnect.getTransport('main_transport').getNode3d()
    #if SightLab_VR_driving.vizconnect_configs[SightLab_VR_driving.configuration] == 'Driving Desktop':
    #    transportNode.setPosition([0.21, -0.58, -1.0])  #x y z  x is left right, second (y) is up down, z is front back
    #else: 
    transportNode.setPosition([-3, 1.0, 0])   #[-0.18, -0.58, -0.47]

    #car = vizfx.addChild('resources/objects/fiat.osgb')  #or honda fiat2.osgb
    #transportCar = vizconnect.getTransport('driving')
    #viz.link(transportCar.getNode3d(), car)
    #SightLab_VR_driving.objects.append(car)
    
    #end hack 2
        
    trialNumber = 0
    
    
    while True:
        
    ## hack to get the billboad texture in
        print('applying the billboard texture')
        
        bb_extension = '.bmp.'
        bb_prefix = 'resources/billboards'
        
        
        df = pd.read_csv(sub_name)
        
        billboard_list2 = df['billboard_name']
        
        billboard_list = []
        for bb in billboard_list2:
            bb_path = bb_prefix + bb + bb_extension
            billboard_list.append(bb_path)
        
        
        #billboard_list = [ 'resources/billboards/binge_drinking.bmp',
        #                   'resources/billboards/brunch.bmp',
        #                   'resources/billboards/buckle_up.bmp',
        #                   'resources/billboards/burger.bmp',
        #                   'resources/billboards/disobey_vape.bmp',
        #                   'resources/billboards/salad.bmp',
        #                   'resources/billboards/stop_smoking.bmp',
        #                   'resources/billboards/education_donation.bmp',
        #                   'resources/billboards/distracted_driving.bmp',
        #                   'resources/billboards/hotel.bmp',
        #                   'resources/billboards/texting_driving.bmp',
        #                   'resources/billboards/furniture.bmp',
        #                   'resources/billboards/marijuana_driving.bmp',
        #                   'resources/billboards/smartphone.bmp',
        #                   'resources/billboards/drugged_driving.bmp',
        #                   'resources/billboards/pizza.bmp',
        #                   'resources/billboards/drunk_driving.bmp',
        #                   'resources/billboards/coffee.bmp',
        #                   'resources/billboards/underage_drinking.bmp',
        #                   'resources/billboards/lawyer.bmp']
        #random.shuffle(billboard_list)
        
        billboard_positions   =    [ '1','2','3','4','5','6','7','8','9','10','11','12','13','14','15','16','17','18','19','20']
        billboard_name_positions = [ 'billboard_image_1','billboard_image_2','billboard_image_3','billboard_image_4','billboard_image_5','billboard_image_6','billboard_image_7','billboard_image_8','billboard_image_9','billboard_image_10',
                                     'billboard_image_11','billboard_image_12','billboard_image_13','billboard_image_14','billboard_image_15','billboard_image_16','billboard_image_17','billboard_image_18','billboard_image_19','billboard_image_20']
        
        list_file_name = 'data/{p.id}_billboard_list_position_name_assignment.csv'.format(p=participant)
        bbs = pd.DataFrame({'position_index': billboard_positions, 'billboard_named_position': billboard_name_positions, 'billboard_image_at_position':billboard_list}) 
        bbs.to_csv(list_file_name, index_label = 'index')
                                    
        env.texture(viz.addTexture(billboard_list[0]), node = 'billboard_image_1')
        env.texture(viz.addTexture(billboard_list[1]), node = 'billboard_image_2')
        env.texture(viz.addTexture(billboard_list[2]), node = 'billboard_image_3')
        env.texture(viz.addTexture(billboard_list[3]), node = 'billboard_image_4')
        env.texture(viz.addTexture(billboard_list[4]), node = 'billboard_image_5')
        env.texture(viz.addTexture(billboard_list[5]), node = 'billboard_image_6')
        env.texture(viz.addTexture(billboard_list[6]), node = 'billboard_image_7')
        env.texture(viz.addTexture(billboard_list[7]), node = 'billboard_image_8')
        env.texture(viz.addTexture(billboard_list[8]), node = 'billboard_image_9')
        env.texture(viz.addTexture(billboard_list[9]), node = 'billboard_image_10')
        env.texture(viz.addTexture(billboard_list[10]), node = 'billboard_image_11')
        env.texture(viz.addTexture(billboard_list[11]), node = 'billboard_image_12')
        env.texture(viz.addTexture(billboard_list[12]), node = 'billboard_image_13')
        env.texture(viz.addTexture(billboard_list[13]), node = 'billboard_image_14')
        env.texture(viz.addTexture(billboard_list[14]), node = 'billboard_image_15')
        env.texture(viz.addTexture(billboard_list[15]), node = 'billboard_image_16')
        env.texture(viz.addTexture(billboard_list[16]), node = 'billboard_image_17')
        env.texture(viz.addTexture(billboard_list[17]), node = 'billboard_image_18')
        env.texture(viz.addTexture(billboard_list[18]), node = 'billboard_image_19')
        env.texture(viz.addTexture(billboard_list[19]), node = 'billboard_image_20')
        ## end of the hack           
        print('done applying the billboard texture')
    
        #Text for displaying record/playback status
        statusText = viz.addText('Press spacebar to record data', parent=viz.ORTHO, scene=overlayWindow, color=viz.RED, fontSize=30, pos=[20,20,0])
       
        # Display the HUD's left status bar
        hudMirror.status_bar_left.visible(viz.ON)
        
        for item in grabObjectsDict:
            print(grabObjectsDict[item].getPosition())
            grabObjectsDict[item].setPosition(initGrabObjectsPos[item][0])
            grabObjectsDict[item].setEuler(initGrabObjectsPos[item][1])
        
        #Press spacebar to start the experiment for the participant
        yield viztask.waitKeyDown(' ')
       
        #Press the key P to toggle the visibility of the user gaze point
        vizact.onkeydown('p', togglePoint)
        
        #Show the scene and start recording
        yield fadeQuad.fade_out()
        
        updateHandle.setEnabled(viz.ON)
        statusText.message('Recording')
        startTime = viz.tick()
        hudMirror.set_timer_enabled(viz.ON)
        
        #AVI Video Recording
        if record:
            viz.window.startRecording('recordings/{p.id}_video1_trial_{t}.avi'.format(p=participant, t = trialNumber)) 
        
        #Initiates the Avatar Tracker Class
        #ballTracker = AvatarTracker(participant.id, trialNumber)
        #ballTracker.update_function.setEnabled(True)
        
        
        #Press Spacebar again to end the experiment recording
        yield viztask.waitKeyDown(' ')

        hudMirror.set_timer_enabled(viz.OFF)
        
        #Displays a static scanpath visualisation of the eyetracking data
        visualization = eye_tracker_utils.DataVisualization3D()
        visualization.setList([data[1] for data in trackingData])
        visualization.show3DPts()
        statusText.message('Showing gaze points')
        
        if record:
            viz.window.stopRecording()
            
        
        yield viztask.waitKeyDown(' ')
        statusText.message('')
        console.message('')
        #hudMirror.resetScore()
        transportNode = vizconnect.getTransport('main_transport').getNode3d()
        #transportNode.setPosition(0,0,0)
        #transportNode.setPosition([0.21, -0.58, -1.0])
        transportNode.setEuler(0,0,0)
        yield fadeQuad.fade_in()
        visualization.remove3DPts()
        hudMirror.clear_instruction()
            #Statistics for the experiment data file
        viewsDict = gazeTime.getViews()
        timesDict = gazeTime.getTotalTimes()
        avgTimesDict = gazeTime.getAvgTimes()
        plotData = []
        fileName = 'data/{p.id}_experiment_data_trial_{t}.txt'.format(p=participant, t=trialNumber+1)
        
        with open(fileName,'w') as f:
            #write participantparticipant data to file
            print('filename')
            print(fileName)
            data = 'Participant ID: {p.id}\\n\n'.format(p=participant)
            f.write(data)

            for name, views in viewsDict.items():
                totalTime = round(timesDict[name],2)
                avgTime = round(avgTimesDict[name],2)
                fmt = '{:<14s} views: {:<5} total time: {:<8} avg time: {:<8}\n'
                data = fmt.format(name, views, totalTime, avgTime)
                f.write(data)
                #add data to list for plotting
                plotData.append([name, views, totalTime, avgTime])

            f.write('\nTime line:\n\n')
            for name, timeToFixation in timeLine:
                data = '{:<14s} {:.2f}\n'.format(name, timeToFixation)
                f.write(data)
            f.close()
            print('closing file')

#        fileName = 'data/{p.id}_experiment_data.pdf'.format(p=participant)
#        set_flag('new trial')
        gazeTime = eye_tracker_utils.GazeTime(gazeObjectsDict, threshold=sceneConfigDict["fixationTime"])
        trackingData = []
        #ballTracker.update_function.setEnabled(False)
        updateHandle.setEnabled(viz.OFF)
        
        writeToggle = False
        
        trialNumber += 1
        firstWrite = True
        
        writeToggle = True
        if not sceneConfigDict["trials"]==-1:
            if not trialNumber < sceneConfigDict["trials"]:
                break
                

        #Log results to experiment_data file and tracking data to tracking_data file
    updateHandle.remove()
    gazeTime.updateGazeObject(None)
    #ballTracker.update_function.setEnabled(False)
        
    yield viztask.waitTime(1)
    statusText.message('Saved')
    
    

#Update Functions
updateHandle = vizact.onupdate(0, updateGaze)
updateHandle.setEnabled(viz.OFF)
viz.callback(eye_tracker_utils.GAZE_BEGIN_EVENT,onGazeBegin)
viz.callback(eye_tracker_utils.GAZE_END_EVENT,onGazeEnd)
viz.callback(eye_tracker_utils.GAZE_TIME_EVENT,onGazeTime)

if __name__ == '__main__':
    viztask.schedule(experiment)

#vizconnect.getRawTracker("head_tracker").setEnabled(False)