#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
'''
@time    :   2022/02/10 13:31:09
@author  :   rosagross
@contact :   grossmann.rc@gmail.com
'''

import numpy as np
import os
import re
from datetime import datetime
from psychopy import visual
from psychopy.hardware import keyboard
from exptools2.core import PylinkEyetrackerSession
from trial import RSTrial
import random

opj = os.path.join

class RotatingSphereSession(PylinkEyetrackerSession):

    def __init__(self, output_str, output_dir, settings_file, subject_ID, eyetracker_on):
        """
        Parameters
        ----------
        output_str : str
            Basename for all output-files (like logs)
        output_dir : str
            Path to desired output-directory (default: None, which results in $pwd/logs)
        settings_file : str
            Path to yaml-file with settings (default: None, which results in the package's
            default settings file (in data/default_settings.yml)
        subject_ID : int
            ID of the current participant
        eyetracker_on : bool 
            Determines if the cablibration process is getting started.
        """

        super().__init__(output_str, output_dir, settings_file, eyetracker_on=eyetracker_on)
    	
        self.subject_ID = subject_ID
        # load task setting from settings.yml file
        self.previous_percept_duration = self.settings['Task settings']['Previous percept duration']
        self.percept_jitter = self.settings['Task settings']['Percept duration jitter']
        self.stim_dur_ambiguous = self.settings['Task settings']['Stimulus duration ambiguous']
        self.n_blocks = self.settings['Task settings']['Blocks'] 
        self.n_practice_blocks = self.settings['Task settings']['Blocks practice']         
        self.response_interval = self.settings['Task settings']['Response interval']
        self.break_duration = self.settings['Task settings']['Break duration']
        self.getready_duration = self.settings['Task settings']['Get ready duration']
        self.stim_size = self.settings['Task settings']['Stimulus size']
        self.fixation_dot_size = self.settings['Task settings']['Fixation dot size']
        self.exit_key = self.settings['Task settings']['Exit key']
        self.break_buttons = self.settings['Task settings']['Break buttons']
        self.monitor_refreshrate = self.settings['Task settings']['Monitor refreshrate']
        self.screentick_conversion = self.settings['Task settings']['Screentick conversion']
        self.test_eyetracker = self.settings['Task settings']['Test eyetracker']

        if self.settings['Task settings']['Screenshot']==True:
            self.screen_dir=output_dir+'/'+output_str+'_Screenshots'
            if not os.path.exists(self.screen_dir):
                os.mkdir(self.screen_dir)

        # setting for loading the correct stimulus
        self.path_to_stim = self.settings['Stimulus settings']['Stimulus path']
        self.stimulus_resolution = self.settings['Stimulus settings']['Stimulus resolution']
        self.dot_size = self.settings['Stimulus settings']['Dot size']
        self.nr_of_frames = self.settings['Stimulus settings']['Number frames'] 
        self.nr_of_dots = self.settings['Stimulus settings']['Number dots'] 
        self.sphere_number_ambiguous = self.settings['Stimulus settings']['Sphere number ambiguous'] 
        self.sphere_number_unambiguous = self.settings['Stimulus settings']['Sphere number unambiguous'] 
        self.black_at_back = self.settings['Stimulus settings']['Black at back'] 
        self.white_at_back = self.settings['Stimulus settings']['White at back'] 
        self.black_at_front = self.settings['Stimulus settings']['Black at front'] 
        self.white_at_front = self.settings['Stimulus settings']['White at front'] 
        self.dot_size_min = self.settings['Stimulus settings']['Dot size min'] 
        self.dot_size_max = self.settings['Stimulus settings']['Dot size max'] 


        # this determines how fast our stimulus images change, so the speed of the rotation 
        self.screenticks_per_frame = int(self.monitor_refreshrate/self.screentick_conversion)

        # randomly choose if the participant responds with the right BUTTON to house or face
        if random.uniform(1,100) < 50:
            self.response_button = 'upper_right'
        else:
            self.response_button = 'upper_left'

        # initialize the keyboard for the button presses
        self.kb = keyboard.Keyboard()

        # count the subjects responses for each condition
        self.switch_times_mean = 0
        self.switch_times_std = 0 
        self.nr_unambiguous_trials = 0       
        self.phase_names = ["fixation", "stimulus", "response_window"]

        self.create_trials()
        self.create_stimuli()


    def create_trials(self):
        """
        Creates the trials with its phase durations and randomization. 
        One trial looks like the following, depending on the block type
        """
        self.trial_list = []
        self.practice_blocks = []
        block_ID_ambiguous = 0 
        block_ID_unambig = 0
        self.trial_nr = 0

        # define which condition starts (equal subjects are 0, unequal 1)
        # either start with ambiguous or unambiguous 
        self.start_condition = 0 if self.subject_ID % 2 == 0 else 1

        # create the phase array for the ambiguous condition (same in all ambiguous blocks)
        nr_phases_ambig = int(self.stim_dur_ambiguous*self.monitor_refreshrate/self.screenticks_per_frame)
        phase_durations_ambiguous = [self.screenticks_per_frame]*nr_phases_ambig
        ambig_last_frame_previous = nr_phases_ambig%self.nr_of_frames

        # add practice blocks beforehand 
        for i in range(self.n_practice_blocks):
            # one ambiguous first
            self.practice_blocks.append([RSTrial(self, 0, 0, 'ambiguous_practice', 'ambiguous_practice', phase_durations_ambiguous, 'frames', 0)])
            # then one unambiguous

            unambiguous_practice_durations = self.create_duration_array()
            unambiguous_practice_block = self.create_unambiguous_block(unambiguous_practice_durations, i, 'unambiguous_practice')
            self.practice_blocks.append(unambiguous_practice_block)
        
        block_ID = 0
        # trial to test the eye tracker and the data analysis (e.g. if positions are measured correctly)
        if self.test_eyetracker:
            self.trial_list.append(RSTrial(self, 0, block_ID, 'tracking_test', '0', [5*self.monitor_refreshrate], 'frames', 0))
            self.trial_list.append(RSTrial(self, 0, block_ID, 'tracking_test', '1', [5*self.monitor_refreshrate], 'frames', 0))
            self.trial_list.append(RSTrial(self, 0, block_ID, 'tracking_test', '2', [5*self.monitor_refreshrate], 'frames', 0))
            self.trial_list.append(RSTrial(self, 0, block_ID, 'tracking_test', '3', [5*self.monitor_refreshrate], 'frames', 0))

        # start off with a break
        self.trial_list.append(RSTrial(self, 0, block_ID, 'break', 'break', [0, self.getready_duration*self.monitor_refreshrate], 'frames', 0))
            
        # now start adding the real blocks 
        for i in range(self.n_blocks):
            # we start counting with 1 because the blocks with ID 0 are breaks!

            block_ID = i + 1

            # even subjects start with rivarly, odd with unambiguous
            if (block_ID + self.start_condition) % 2 == 0:
                block_ID_ambiguous += 1
                block_type = 'ambiguous'
                trial_type = 'ambiguous'
                self.trial_nr += 1
                self.trial_list.append(RSTrial(self, self.trial_nr, block_ID_ambiguous, block_type, trial_type, phase_durations_ambiguous, 'frames', ambig_last_frame_previous))
                self.trial_nr += 1
                self.trial_list.append(RSTrial(self, self.trial_nr, block_ID_ambiguous, block_type, 'break', [self.break_duration*self.monitor_refreshrate, self.getready_duration*self.monitor_refreshrate], 'frames', 0))
                

            else:
                block_type = 'unambiguous'
                block_ID_unambig += 1
                # create the phase duration array 
                # total duration should add up to 120s for all unambiguous blocks
                stim_dur_unambiguous = self.create_duration_array()
                self.nr_unambiguous_trials = self.nr_unambiguous_trials + len(stim_dur_unambiguous)
                unambiguous_block = self.create_unambiguous_block(stim_dur_unambiguous, block_ID_unambig, block_type)
                
                # append it to the trial list
                self.trial_list = [*self.trial_list, *unambiguous_block]
                self.trial_nr += 1
                self.trial_list.append(RSTrial(self, self.trial_nr, block_ID_unambig, block_type, 'break', [self.break_duration*self.monitor_refreshrate, self.getready_duration*self.monitor_refreshrate], 'frames', 0))
                
                     


    def create_stimuli(self):

        # here we load the images that were produced in the MATLAB code 
        self.fixation_dot = visual.ImageStim(self.win, image=self.path_to_stim+'FixDot.bmp',  units='deg', size=self.fixation_dot_size)

        # load a stimulus that can test the eye tracking data 
        dots = [visual.Circle(self.win, lineColor='red', units='pix', size=70, pos=[-250,-250]),
                visual.Circle(self.win, lineColor='red', units='pix', size=70, pos=[250,-250]),
                visual.Circle(self.win, lineColor='red', units='pix', size=70, pos=[250,250]),
                visual.Circle(self.win, lineColor='red', units='pix', size=70, pos=[-250,250])]

        self.eye_tracking_test = dots

        # Stimulus text for the break
        self.break_stim = visual.TextStim(self.win, text="Break")
        
        # save the globe stimuli in different lists, since one rotation consists out of 190 images
        self.ambiguous_stim_list = []
        self.unambiguous_stim_list_right = []
        self.unambiguous_stim_list_left = []

        # we have a certain number of frames that make up one rotation of the sphere
        for i in range(self.nr_of_frames):
            filename_amb = f'Amb_{self.stimulus_resolution}x{self.stimulus_resolution}-{self.nr_of_frames}frames-{self.nr_of_dots}dots(size={self.dot_size})_{self.sphere_number_ambiguous}.{i+1}.bmp'
            filename_unamb_right = f'Contr_Unamb_{self.black_at_back}BB_{self.white_at_back}WB_{self.black_at_front}BF_{self.white_at_front}WF_{self.dot_size_min}-{self.dot_size_max}DS_{self.stimulus_resolution}x{self.stimulus_resolution}-{self.nr_of_frames}frames-{self.nr_of_dots}dots(size={self.dot_size})_{self.sphere_number_unambiguous}.{i+1}.bmp'
            filename_unamb_left = f'Contr_Unamb_{self.black_at_back}BB_{self.white_at_back}WB_{self.black_at_front}BF_{self.white_at_front}WF_{self.dot_size_min}-{self.dot_size_max}DS_{self.stimulus_resolution}x{self.stimulus_resolution}-{self.nr_of_frames}frames-{self.nr_of_dots}dots(size={self.dot_size})_{self.sphere_number_unambiguous}.{self.nr_of_frames-i}.bmp'
            
            self.ambiguous_stim_list.append(visual.ImageStim(self.win, image=self.path_to_stim+filename_amb, units='deg', size=self.stim_size))
            self.unambiguous_stim_list_right.append(visual.ImageStim(self.win, image=self.path_to_stim+filename_unamb_right, units='deg', size=self.stim_size))
            # create the left rotation list separately since it takes longer if we do the indices counting backwards later on!
            self.unambiguous_stim_list_left.append(visual.ImageStim(self.win, image=self.path_to_stim+filename_unamb_left, units='deg', size=self.stim_size))

    def create_duration_array(self):
            """
            Function that takes the duration entries from the setting file and constructs the 
            phase duration (duration of trial and ISI) for all trials. 
            The jitter is added to the mean percept duration from previous studies. If the jitter is
            0.1s, a random nr between -0.1 and 0.1 is added. 
            """

            if isinstance(self.previous_percept_duration, list):
                print('Use predefined phase durations')
                phase_durations = [elem*self.screenticks_per_frame for elem in self.previous_percept_duration]
                np.random.shuffle(phase_durations)
            else:
                # while the number is not above the trial duration, generate more trial durations
                max_duration = self.stim_dur_ambiguous
                nr_frames_total = max_duration*self.monitor_refreshrate
                frames_percept_duration = self.previous_percept_duration*self.monitor_refreshrate
                jitter_in_frames = int(self.percept_jitter*self.monitor_refreshrate)
                current_duration = 0 
                phase_durations = []
                while True:
                    percept_duration = frames_percept_duration + random.randrange(-jitter_in_frames, jitter_in_frames)
                    current_duration = np.array(phase_durations).sum() + percept_duration
                    if current_duration > nr_frames_total:
                        break
                    
                    phase_durations.append(percept_duration)
                    
                current_duration = np.array(phase_durations).sum()
                duration_difference = nr_frames_total - current_duration
                # append whats missing to the last trial
                phase_durations.append(duration_difference)
            
            print("durations unambiguous block:", np.array(phase_durations).sum(), "and length:", len(phase_durations))
            print(phase_durations)
            return phase_durations
        
    def create_unambiguous_block(self, stim_duration_list, block_ID_unambig, block_type):
        '''
        This function creates a list full of left and right rotation unambiguous trials.
        It is used for creating practice and actual experiment blocks.
        '''
        # the block will start at the beginning of the total frames of the stimulus
        last_frame_previous = 0 
        dummy = 0 # need this to add the previous last frame from the trial before
        block_list = [] # this is where we store the trials prior to concatenating them to the suitable trial list

        # the durations should determine the switch between left and right rotation
        for i, stim_duration in enumerate(stim_duration_list):
            # determine if next trial shows house or face
            trial_type = 'right' if self.trial_nr % 2 == 0 else 'left'

            # create the phase durations depending on the duration of the stimulus
            nr_phases_unambig = int(stim_duration/self.screenticks_per_frame)
            phase_durations_unambiguous = [self.screenticks_per_frame]*nr_phases_unambig
            
            # the number of phases also tell us which image was the last one, so that
            # the next rotation can start from there
            last_frame_previous = (last_frame_previous+dummy)%self.nr_of_frames
            if trial_type == 'right':
                last_frame_previous = self.nr_of_frames - last_frame_previous 
            elif trial_type == 'left':
                last_frame_previous = abs(last_frame_previous - self.nr_of_frames)
            self.trial_nr += 1 
            block_list.append(RSTrial(self, self.trial_nr, block_ID_unambig, block_type, trial_type, phase_durations_unambiguous,'frames', last_frame_previous))
            # save old value and update new one
            dummy = last_frame_previous
            last_frame_previous = nr_phases_unambig

        return block_list

    def draw_stimulus(self, phase):
        """
        Depending on what phase we are in, this function draws the apropriate stimulus.
        """
        # we want to start there where we ended in the previous rotation
        frame_index = (self.current_trial.phase+self.current_trial.last_frame_previous+1)%self.nr_of_frames
        if self.current_trial.trial_type == 'break':
            # in the break phase there is only the "break" text or fixation dot on a blank screen
            if phase == 0:
                self.break_stim.draw()
            elif phase == 1:
                self.fixation_dot.draw()
        elif re.match(r"(ambiguous)(.*)", self.current_trial.block_type):
            self.ambiguous_stim_list[frame_index].draw()
        
        elif re.match(r"(unambiguous)(.*)", self.current_trial.block_type):
            if self.current_trial.trial_type=='left':
                # makes the index count backwards and starts from the end when finished
                self.unambiguous_stim_list_left[frame_index].draw()
            else:
                self.unambiguous_stim_list_right[frame_index].draw()
        elif self.current_trial.block_type == 'tracking_test':
            self.eye_tracking_test[int(self.current_trial.trial_type)].draw()

    def  wait_for_yesno(self, text):
        '''
        This function is used to implement a yes or no response. 
        If the key pressed 'y' it returns True, if 'n' it returns false. 
        '''

        stim = visual.TextStim(self.win, text=text)
        stim.draw()
        self.win.flip()
        wait_for_key = True
        while wait_for_key:
            keys = self.kb.getKeys(keyList=['y', 'n'])  
            for key in keys:
                if key.name == 'y':
                    answer = True
                    wait_for_key = False
                elif key.name == 'n':
                    answer = False
                    wait_for_key = False
        return answer

    def run(self):
        print("-------------RUN SESSION---------------")
        
        if self.eyetracker_on:
            self.calibrate_eyetracker()
            self.start_recording_eyetracker()

        if self.response_button == 'upper_right':
            button_instructions = 'Upper - Right\n Lower - Left'
        else:
            button_instructions = 'Upper - Left\n Lower - Right'
        
        self.display_text(button_instructions, keys='space')
        
        # ask if practice block is needed
        start_practice = self. wait_for_yesno('Practice block\n Please wait')

        # this method actually starts the timer which keeps track of trial onsets
        self.start_experiment()
        self.kb.clock.reset()

        if start_practice:

            for block in self.practice_blocks:
                for trial in block:
                    self.current_trial = trial
                    self.current_trial.run()
                
                end_practice_text = 'End of practice block!\n' # press 'y' to start real experiment
                stop_practicing = self.wait_for_yesno(end_practice_text)
            
                if stop_practicing:
                    break
            
            self.display_text('End of practice block. \n Please wait', keys='t')
        else:
            self.display_text('Please wait', keys='t')
            
        # self.kb.clock.reset()
        for trial in self.trial_list:
            self.current_trial = trial 
            self.current_trial_start_time = self.kb.clock.getTime()
            # the run function is implemented in the parent Trial class, so our Trial inherited it
            self.current_trial.run()

        self.display_text('End. \n Well done!:)', keys='space')
        self.close()






        
