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
        self.path_to_stim = self.settings['Task settings']['Stimulus path']
        self.n_blocks = self.settings['Task settings']['Blocks'] 
        self.n_practice_blocks = self.settings['Task settings']['Blocks practice'] 
        self.break_duration = self.settings['Task settings']['Break duration']
        self.percept_jitter = self.settings['Task settings']['Percept duration jitter']
        self.previous_percept_duration = self.settings['Task settings']['Previous percept duration']
        self.stim_dur_ambiguous = self.settings['Task settings']['Stimulus duration ambiguous']
        self.response_interval = self.settings['Task settings']['Response interval']
        self.response_hand = self.settings['Task settings']['Response hand']
        self.phase_names = ["fixation", "stimulus", "response"]
        self.exit_key = self.settings['Task settings']['Exit key']
        self.monitor_framerate = self.settings['Task settings']['Monitor framerate']

        # this determines how fast our stimulus images change, so the speed of the rotation 
        self.refresh_stimulus_speed = int(self.monitor_framerate/30)

        # randomly choose if the participant responds with the right BUTTON to house or face
        self.response_button = 'upper_right' if random.uniform(1,100) < 50 else 'upper_left'

        # initialize the keyboard for the button presses
        self.kb = keyboard.Keyboard()

        # count the subjects responses for each condition
        self.unambiguous_responses = 0 
        self.ambiguous_responses = 0 
        self.total_responses = 0
        self.correct_responses = 0 
        self.switch_times_mean = 0
        self.switch_times_std = 0 
        self.nr_unambiguous_trials = 0

        self.create_trials()
        self.create_stimuli()


    def create_trials(self):
        """
        Creates the trials with its phase durations and randomization. 
        One trial looks like the following, depending on the block type:

        Unambiguous:
        1) 10s break, showing the fixation cross only
        2) ~ s right or left rotating sphere

        Ambiguous:
        1) 10s break, showing the fixation cross only
        2) 120s for the stimulus 
        """
        self.trial_list = []
        self.practice_blocks = []
        block_ID_ambiguous = 0 
        block_ID_unambig = 0
        trial_nr = 1

        # define which condition starts (equal subjects are 0, unequal 1)
        # either start with ambiguous or unambiguous 
        self.start_condition = 0 if self.subject_ID % 2 == 0 else 1

        # create the phase array for the ambiguous condition (same in all ambiguous blocks)
        nr_phases_ambig = int(self.stim_dur_ambiguous*self.monitor_framerate/self.refresh_stimulus_speed)
        phase_durations_ambiguous = [self.refresh_stimulus_speed]*nr_phases_ambig
        ambig_last_frame_previous = nr_phases_ambig%190

        # add practice blocks beforehand 
        for i in range(self.n_practice_blocks):
            print("Append practice blocks")
            # one ambiguous first
            self.practice_blocks.append([RSTrial(self, 0, 0, 'ambiguous_practice', 'ambiguous_practice', self.response_hand, phase_durations_ambiguous, 'frames', 0)])
            # then one unambiguous
            unambiguous_practice_durations = self.create_duration_array()
            unambiguous_practice_block = self.create_unambiguous_block(unambiguous_practice_durations, i, 'unambiguous_practice')
            self.practice_blocks.append(unambiguous_practice_block)

        print('length practice', self.practice_blocks)
        # now start adding the real blocks 
        for i in range(self.n_blocks):
            # we start counting with 1 because the blocks with ID 0 are breaks!
            block_ID = i + 1 
            print("\ncurrent block is", block_ID)
            print("start condition", self.start_condition)

            # we start with a break (which will have the block ID of the block that was previously running or 0 if first break)
            self.trial_list.append(RSTrial(self, 0, block_ID_ambiguous, 'break', 'break', self.response_hand, [self.break_duration*self.monitor_framerate], 'frames', 0))
            # equal subjects start with rivarly, unequal with unambiguous
            if (block_ID + self.start_condition) % 2 == 0:
                block_ID_ambiguous += 1
                block_type = 'ambiguous'
                trial_type = 'ambiguous'

                self.trial_list.append(RSTrial(self, trial_nr, block_ID_ambiguous, block_type, trial_type, self.response_hand, phase_durations_ambiguous, 'frames', ambig_last_frame_previous))
                print("appended trial nr", trial_nr)
                trial_nr += 1 

            else:
                block_type = 'unambiguous'
                block_ID_unambig += 1
                # create the phase duration array 
                # total duration should add up to 120s for all unambiguous blocks

                stim_dur_unambiguous = self.create_duration_array()
                print("durations unambiguous:", stim_dur_unambiguous)

                unambiguous_block = self.create_unambiguous_block(stim_dur_unambiguous, block_ID_unambig, block_type)
                # append it to the trial list
                self.trial_list = [*self.trial_list, *unambiguous_block]
                


    def create_stimuli(self):

        # here we load the images that were produced in the MATLAB code 
        self.fixation_dot = visual.ImageStim(self.win, image=self.path_to_stim+'FixDot.bmp')
        
        # save the globe stimuli in different lists, since one rotation consists out of 190 images
        self.ambiguous_stim = visual.ImageStim(self.win, image=self.path_to_stim+'Amb_190x190-190frames-350dots(size=0.02)_1.169.bmp')
        
        self.ambiguous_stim_list = []
        self.unambiguous_stim_list = []

        # we have 190 images for 
        for i in range(190):
            filename_amb = f'Amb_190x190-190frames-350dots(size=0.02)_1.{i+1}.bmp'
            filename_unamb = f'UnambContr_0.25BB_0.75WB_0BF_1WF_0.012-0.028DS_190x190-190frames-350dots(size=0.02)_1.{i+1}.bmp'
            self.ambiguous_stim_list.append(visual.ImageStim(self.win, image=self.path_to_stim+filename_amb))
            self.unambiguous_stim_list.append(visual.ImageStim(self.win, image=self.path_to_stim+filename_unamb))

        # technically, the unambiguous stimuli are the same, but the order in which the images are played is flipped
        self.unambiguous_stim_left = visual.ImageStim(self.win, image=self.path_to_stim+'UnambContr_0.25BB_0.75WB_0BF_1WF_0.012-0.028DS_190x190-190frames-350dots(size=0.02)_1.10.bmp')
        self.unambiguous_stim_right = visual.ImageStim(self.win, image=self.path_to_stim+'UnambContr_0.25BB_0.75WB_0BF_1WF_0.012-0.028DS_190x190-190frames-350dots(size=0.02)_1.1.bmp')


    def create_duration_array(self):
            """
            Function that takes the duration entries from the setting file and constructs the 
            phase duration (duration of trial and ISI) for all trials. 
            The jitter is added to the mean percept duration from previous studies. If the jitter is
            0.1s, a random nr between -0.1 and 0.1 is added. 
            """

            # while the number is not above the trial duration, generate more trial durations
            max_duration = self.stim_dur_ambiguous
            nr_frames_total = max_duration*self.monitor_framerate
            frames_percept_duration = self.previous_percept_duration*self.monitor_framerate
            jitter_in_frames = int(self.percept_jitter*self.monitor_framerate)
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
            print("duration unambiguous block:", np.array(phase_durations).sum(), "and length:", len(phase_durations))
            self.nr_unambiguous_trials = self.nr_unambiguous_trials + len(phase_durations)
            print(phase_durations)
            return phase_durations
       
    def create_unambiguous_block(self, stim_duration_list, block_ID_unambig, block_type):
        '''
        This function creates a list full of left and right rotation unambiguous trials.
        It is used for creating practice and actual experiment blocks.
        '''
        # the block will start at the beginning of the 190 frames of the stimulus
        last_frame_previous = 0 
        dummy = 0 # need this to add the previous last frame from the trial before
        trial_nr = 0
        block_list = [] # this is where we store the trials prior to concatenating them to the suitable trial list

        # the durations should determine the switch between left and right rotation
        for i, stim_duration in enumerate(stim_duration_list):
            # determine if next trial shows house or face
            trial_type = 'left' if trial_nr % 2 == 0 else 'right'

            print("appended trial nr", trial_nr)
            print("trial number in unabiguous:", i)
            print("stimulus duration (in frames!!)", stim_duration)

            # create the phase durations depending on the duration of the stimulus
            nr_phases_unambig = int(stim_duration/self.refresh_stimulus_speed)
            phase_durations_unambiguous = [self.refresh_stimulus_speed]*nr_phases_unambig
            print(len(phase_durations_unambiguous), nr_phases_unambig)
            
            # the numeber of phases also tell us which image was the last one, so that
            # the next rotation can start from there
            last_frame_previous = (last_frame_previous+dummy)%190
            block_list.append(RSTrial(self, trial_nr, block_ID_unambig, block_type, trial_type, self.response_hand, phase_durations_unambiguous,'frames', last_frame_previous))
            # save old value and update new one
            dummy = last_frame_previous
            last_frame_previous = nr_phases_unambig

            trial_nr += 1 
        
        return block_list

    def save_output(self):
        
        # calculate the mean duration of percepts in ambiguous blocks
        expected_responses = self.nr_unambiguous_trials - (self.n_blocks/2)
        np.savez(opj(self.output_dir, self.output_str+'_summary_response_data.npz'), ["Date & time", "Reponse hand", "Response button", "Monitor refreshrate (in Hz)", "Stimulus duration ambiguous", 
                                                                                      "Switch durations (mean)", "Switch durations jitter", "Expected number of responses (unambiguous)",
                                                                                      "Subject responses (unambiguous)", "Subject responses (ambiguous)"],
                                                                                       [datetime.now().strftime('%Y-%m-%d %H:%M:%S'), self.response_hand, self.response_button, self.monitor_framerate, 
                                                                                       self.stim_dur_ambiguous, self.previous_percept_duration, self.percept_jitter, expected_responses, 
                                                                                       self.unambiguous_responses, self.ambiguous_responses])
        

    def draw_stimulus(self):
        """
        Depending on what phase we are in, this function draws the apropriate stimulus.
        """
        # we want to start there where we ended in the previous rotation
        frame_index = (self.current_trial.phase+self.current_trial.last_frame_previous+1)%190

        if self.current_trial.block_type == 'break':
            # in the break phase there is only the fixation dot on a blank screen
            self.fixation_dot.draw()

        elif re.match(r"(ambiguous)(.*)", self.current_trial.block_type):
            self.ambiguous_stim_list[frame_index].draw()

        elif re.match(r"(unambiguous)(.*)", self.current_trial.block_type):
            if self.current_trial.trial_type=='left':
                # makes the index count backwards and starts from the end when finished
                self.unambiguous_stim_list[-(frame_index+1)].draw()
            else:
                self.unambiguous_stim_list[frame_index].draw()


    def run(self):
        print("-------------RUN SESSION---------------")
        
        if self.eyetracker_on:
            self.calibrate_eyetracker()
            self.start_recording_eyetracker()

        if self.response_button == 'upper_right':
            button_instructions = 'Press the upper button when you see the globe rotating to the right.\n Press the lower button when you see the globe rotating to the left.'
        else:
            button_instructions = 'Press the upper button when you see the globe rotating to the left.\n Press the lower button when you see the globe rotating to the right.'
        
        self.display_text(button_instructions, keys='space')
        
        # ask if practice block is neces
        end_practice_text = 'Start practice block? (press y/n)?'
        stim = visual.TextStim(self.win, text=end_practice_text)
        stim.draw()
        self.win.flip()

        while True:
            key = self.kb.getKeys(keyList=['y', 'n'])  
            if len(key)>0:
                start_practice = True if key == 'y' else False
                    
        # this method actually starts the timer which keeps track of trial onsets
        self.start_experiment()

        print('pracitce', self.practice_blocks)
        print(len(self.practice_blocks))
        for block in self.practice_blocks:

            print('BLOCK', block)
            for trial in block:
                print('trial', trial)
                self.current_trial = trial
                self.current_trial.run()
            
            end_practice_text = 'End of practice block!\n Would you like to continue practicing (press y/n)?'
            stim = visual.TextStim(self.win, text=end_practice_text)
            stim.draw()
            self.win.flip()

            while True:
                key = self.kb.getKeys(keyList=['y', 'n'])  
                if len(key)>0:
                    if key == 'n':
                        break        
        
        self.display_text('End of practice block. \nAre you ready to start the experiment?', keys='space')
        self.kb.clock.reset()
        
        for trial in self.trial_list:
            self.current_trial = trial 
            self.current_trial_start_time = self.clock.getTime()
            # the run function is implemented in the parent Trial class, so our Trial inherited it
            self.current_trial.run()

        self.save_output()
        self.display_text('End. \n Thank you for participating!', keys='space')
        self.close()






        