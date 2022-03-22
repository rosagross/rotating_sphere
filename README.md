# rotating_sphere
This is the repository for an experiment that is used to investigate the ambiguity of the rotating sphere illusion.


**Requirements**

- python 3.6 (or 3.8)
- psychopy
- exptools2
- pylink

**Execution**

To execute the experiment run: ```python main.py sub-xxx ses-x False\True``` <br>
The boolean operator in the end indicates if we want to run it in connection with the eyetracking device.
<br>
Before the real experiment starts, the participant has the possibility to practice. Press 'y' to start a preactice session. It will always start with an ambiguous block. After that there will still be the option to do further test trials.
<br>
Please check the ```settings.yml``` file for experiment settings that can be changed. Change the button names in the file to the ones your subject is going to use! If you want to test if the eyetracker captures the gaze correctly, set ```Test eyetracker``` to ```True```. It is important to insert the correct refreshrate of the monitor, because it is used to calculate the rotation speed.

<br>

## Conditions and tiral procedure

**Unambiguous:**
1) 10s break, showing the red fixation dot only
2) Alternatingly right or left rotating sphere. The duration of each rotation depends on the durations that were entered in the ```settings.yml``` file.

**Ambiguous:**
1) 10s break, showing the red fixation dot only
2) 120s for the stimulus 

**Note**
- Subjects with even IDs start with the ambiguous, odd with the unambiguous condition
- Trial counting starts with 1
- The breaks have trialID and blockID of '0'
- The participant uses the preferred hand to respond. Which finger is used for which button is indicated in the instructions. Carefully check the instructions in the beginning.
<br>

## Code Structure
- ```main.py``` creates the session object.
- ```session.py``` creates the trials and blocks of the exeriment. Creates the stimuli, executes the trials end draws the stimuli.
- ```trial.py``` implements the trial object, which outlines how a trial should look like. Logs button presses and parameters for the trials. 
- ```settings.yml``` contains the experiment and task settings

 




## ToDos: 

- check dot colour in break vs in the trials, in the paper the dot is green (and has size 0.18)
- check the stimulus speed!
- improve naming of the previous frames indices (e.g. ambiguous_last_frame_previous is way too long and unclear)