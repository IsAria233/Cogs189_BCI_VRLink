"""This script tries to access neurosky to record eeg data. Non-LSL version.
Based on: https://github.com/D1o0g9s/EEGFaceDetection/blob/master/mindwave_code/CollectRawData.py
Notes:
- requires mindwave.py
- M1 macs don't seem to work now
- change the line labeled "mac version" to run it on Windows
- to run it on Windows, set up COM port and copy the number over
- run by typing 'python neurosky.py' in the terminal or console
- configure your experimental settings under SETTINGS
- trial_permutations are randomly sampled from TARGETS by default
- the recorded data are saved under ./[SUBJECT_NUMBER]/[SESSION_NUMBER]/
"""

## IMPORTS
import mindwave
from psychopy import visual
from sklearn.linear_model import LinearRegression
import numpy as np
import json
import time
import pandas as pd
from random import choices
from tqdm import tqdm
import sys
import os
import pyautogui
from os.path import join as pjoin

##########################################################################
##########################################################################

## SETTINGS

def default_config():
    CONFIG = {
        'SUBJECT_NUMBER' : 0,
        'SESSION_NUMBER' : 0,
        'NUM_TRIALS' : 2, # number of trials in total
        'TRIAL_DURATION' : 2000, # ms
        'INTER_TRIAL_INTERVAL' : 1000, # ms, between trials
        'SAMPLING_FREQUENCY' : 128, # Hz
        # 'offline' for offline only
        # 'full' for offline, train, and online prediction
        # 'online' will skip offline/train if eeg/model exists
        'MODE' : 'full', 
        # classication labels, eg. {1:'task1', 2:'task2'}
        # NOTE: 0 is reserverd for 'rest'. Unless you just
        # want to record 'rest' for the entire session, you
        # should not include the key 0 in this dictionary
        'TARGETS' : {1:'task1', 
                     2:'task2'} 
    }
    with open('config.json', 'w') as json_file:
        json.dump(CONFIG, json_file, indent=4, sort_keys=True)

if not os.path.isfile('./config.json'):
    default_config()

with open('config.json', 'r') as json_file:
    CONFIG = json.load(json_file)

for key, val in CONFIG.items():
    exec(key + '=val')

SESSION_DURATION = NUM_TRIALS * (TRIAL_DURATION/1000 + INTER_TRIAL_INTERVAL/1000)
###############################################################
# if the trial permutation is generated by the GUI,           
# then you should load the permutation from the GUI instead
# (one way to do this is having the GUI save a config.json)
if 'TRIAL_PERMUTATION' not in globals():
    TRIAL_PERMUTATION = choices(list(TARGETS.keys()), k = NUM_TRIALS) # random trial generation
###############################################################

### PATHS
BASE_PATH = "./"
DATA_PATH = pjoin(pjoin(BASE_PATH, str(SUBJECT_NUMBER)),str(SESSION_NUMBER))
EEG_PATH = pjoin(DATA_PATH, 'eeg.csv')
if not os.path.isdir(DATA_PATH):
    os.makedirs(DATA_PATH)

SKIP_OFFLINE = False
SKIP_TRAINING = False
SKIP_ONLINE = False
if MODE == 'offline':
    SKIP_TRAINING = True
    SKIP_ONLINE = True
elif MODE == 'online':
    if os.path.isfile(EEG_PATH):
        SKIP_OFFLINE = True
    # model file exists
    SKIP_TRAINING = True

##########################################################################
##########################################################################

## FUNCTIONS
def on_raw(headset, rawvalue):
    '''
    Save values collected from the headset
    Inputs:
        headset (obj) : argument provided by the headset
        data (global dict) : where this function saves new datapoints
        label (global int) : where this function takes the current label marker status
    Output: 
        one data point to each item of data
    Examples:
        >>> data = {'timestamp': [], 'raw_value': [], 'attention': [], 'label':[]}
        >>> label = 0
        >>> headset.raw_value_handlers.append(on_raw) # Start Collecting EEG
    '''
    (eeg, attention, meditation, blink) = (headset.raw_value, headset.attention, headset.meditation, headset.blink)

    global label
    
    ts = time.time()
    data['timestamp'].append(ts)
    data['raw_value'].append(eeg)
    data['attention'].append(attention)
    data['meditation'].append(meditation)
    data['blink'].append(blink)
    data['label'].append(label)


def print_seconds_elapsed():
    '''
    Print "second elapsed" every second
    Inputs:
        START_TIME (global constant) : start time of the session
        SAMPLING_FREQUENCY (global constant) : sampling frequency of headset
    Output: 
        console logging of seconds elapsed every second
    '''
    global START_TIME
    timeDiff = time.time() - START_TIME
    if timeDiff % 1 < 1/SAMPLING_FREQUENCY: 
        print("seconds elapsed: " + str(int(timeDiff)))

def update_label(trial_permutation):
    '''
    Track trial time and update the current label
    Will print_trial the current trial if starting the next trial
    When current label is updated, update offline collection GUI
    Inputs:
        trial_permutation (list of int) : the sequence of trials
        label (global int) : where this function takes the current label marker status
        trial_stime (global float) : the starting time of the current trial
        trial_index (glonal int) : which trial in the trial permutation we are currently at
    Output: 
        - console logging of the current trial
        - offline collection GUI update
    '''
    global label
    global trial_stime
    global trial_index
    if time.time()-trial_stime < TRIAL_DURATION/1000:
        label = trial_permutation[trial_index]
    else:
        label = 0 # 0 means inter-trial interval or rest
    # if starting the next trial
    if time.time()-trial_stime >= TRIAL_DURATION/1000 + INTER_TRIAL_INTERVAL/1000:
        trial_stime = time.time()
        if trial_index < len(trial_permutation): # increment trial index to next trial
            trial_index += 1
            print_trial(trial_permutation, trial_index, TRIAL_DURATION/1000)
            update_offline_collection_gui(trial_permutation, trial_index, TRIAL_DURATION/1000)
            
def print_trial(trial_permutation, trial_index, duration):
    # print the current trial and how many seconds it lasts
    print(TARGETS[trial_permutation[trial_index]], duration)

def dummy_train():
    # change this function to a real model training function (if you need one)
    for i in tqdm(range(100), desc='Training...'):
        time.sleep(4/100)
    print('Training Complete!')

def dummy_predict(data):
    # change this function to a real online prediction function (if you need one)
    if data['attention'][-1] >55:
        #pyautogui.write("hello world", interval = 0.25)
        pyautogui.press('e')
    else:
        print('pause')

def update_offline_collection_gui(trial_permutation, trial_index, duration):
    '''
    Update offline collection GUI
    Inputs:
        trial_permutation (list of int) : the sequence of trials
        win (global visual.Window) : psychopy window object
        trial_index (int) : which trial in the trial permutation we are currently at
        duration (int) : how long the trial is in ms
    Output: 
        - offline collection GUI update
    Note: intended to be used when current label is updated
    '''
    global win
    trial_text = '(' + str(TARGETS[trial_permutation[trial_index]]) + ', ' + str(duration) + ')'
    msg = visual.TextStim(win, text=trial_text)
    msg.draw()
    win.flip()

##########################################################################
##########################################################################

# if this script is run as a script rather than imported
if __name__ == "__main__": 

    ###################### Headset Starting Sequence #####################
    currentTimestamp = None
    currentRawValue = None
    currentAttention = None
    label = 0 # 0 means inter-trial interval or rest
    trial_index = 0 # the first trial in the permutation

    data = {'timestamp': [],
            'raw_value': [],
            'attention': [],
            'meditation': [],
            'blink': [],
            'label':[]}

    print("Connecting...")
    # headset = mindwave.Headset('/dev/tty.MindWaveMobile-SerialPo') # mac version
    headset = mindwave.Headset('COM3') # windows version. set up COM port first (see video)
    print("Connected!")

    print("Starting...")
    # Wait for the headset to steady down
    while (headset.poor_signal > 5 or headset.attention == 0):
        time.sleep(0.1)
    headset.raw_value_handlers.append(on_raw) # Start Collecting EEG
    print('Started!')
    ######################################################################

    # Offline Recording Session
    if not SKIP_OFFLINE:
        win = visual.Window()
        try:
            print("Writing %d seconds output to %s" % (SESSION_DURATION,EEG_PATH))
            START_TIME = time.time() # session start time constant
            trial_stime = time.time() # trial start time
            
            # Print out the first trial
            print_trial(TRIAL_PERMUTATION, trial_index, TRIAL_DURATION/1000)
            update_offline_collection_gui(TRIAL_PERMUTATION, trial_index, TRIAL_DURATION/1000)

            # Recording Loop
            while (time.time()- START_TIME) < SESSION_DURATION:
                # Log to console if the headset is too noisy
                if headset.poor_signal > 5 :
                    print("Headset signal noisy %d. Adjust the headset and the earclip." % (headset.poor_signal))

                # Track trial time and change label
                update_label(TRIAL_PERMUTATION)

                # print_seconds_elapsed()

                time.sleep(1/SAMPLING_FREQUENCY) # wait till the start of next sample
        except:
            win.close()
            headset.stop()
            df = pd.DataFrame.from_dict(data)
            df.to_csv(EEG_PATH, index=False)
            print("Stopped!")
            sys.exit(0)
        finally:
            time.sleep(0.2)
            win.close()
            df = pd.DataFrame.from_dict(data)
            df.to_csv(EEG_PATH, index=False)

    # ML Modeling Training
    if not SKIP_TRAINING:
        dummy_train()

    # Online Prediction
    if not SKIP_ONLINE:
        try:
            print("Start Online Prediction:")
            time.sleep(0.1)
            while True:
                dummy_predict(data)
                time.sleep(0.5)
        finally:
            headset.stop()
            print("Stopped!")
            sys.exit(0)
        
    
    