#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
'''
@time    :   2022/02/09 17:33:27
@author  :   rosagross
@contact :   grossmann.rc@gmail.com
'''

from psychopy import event
import numpy as np
from exptools2.core.trial import Trial
from psychopy.hardware import keyboard
import os
import re
opj = os.path.join


class RSTrial(Trial):
    """ 
    This class implements the construction of the trials in the experiment. 
    There are different trial types:
    - unambiguous (left or right wards moving)
    - ambiguous (not clear which direction), in this trial, nothing changes over the whole duration of the trial

    Every trial begins with a 10s break.
    """

    def __init__(self, session, trial_nr, block_ID, block_type, trial_type, phase_duration, timing, last_frame_previous, *args, **kwargs):
        
        super().__init__(session, trial_nr, phase_duration,
                         parameters={'block_type': block_type,
                                     'trial_type': trial_type,
                                     'trial_nr': trial_nr, 
                                     'block_ID' : block_ID,
                                     'phase_length' : len(phase_duration),
                                     'last_frame' : last_frame_previous}, 
                         timing=timing,
                         verbose=False, *args, **kwargs)
        
        # store if it is a ambiguous trial or unambiguous trial 
        self.ID = trial_nr
        self.block_ID = block_ID
        self.block_type = block_type
        self.trial_type = trial_type # this can be either house_face, house or face
        self.last_frame_previous = last_frame_previous
        
            
    def draw(self):
        ''' This tells what happens in the trial, and this is defined in the session itself. '''
        self.session.draw_stimulus(self.phase)


    def get_events(self):
        """ Logs responses/triggers """

        keys = self.session.kb.getKeys(waitRelease=True)
        for thisKey in keys:

            if thisKey==self.session.exit_key:  # it is equivalent to the string 'q'
                print("End experiment!")
                self.session.save_output()

                if self.session.settings['Task settings']['Screenshot']==True:
                    print('\nSCREENSHOT\n')
                    self.session.win.saveMovieFrames(opj(self.session.screen_dir, self.session.output_str+'_Screenshot.png'))
                self.session.close()
                self.session.quit()

            elif (thisKey=='s') & (self.session.settings['Task settings']['Screenshot']==True):
                self.session.win.getMovieFrame()
                self.session.win.saveMovieFrames(opj(self.session.screen_dir, self.session.output_str+f'_Screenshot_{self.trial_type}.png'))
            else: 
                # the button press onset in the global experiment time
                t = thisKey.rt
                # to check if the responses have valid timing and correct button was used (only used for unambiguous trials)
                onset_delay_timing = np.NaN
                offset_delay_timing = np.NaN
                onset_delay = np.NaN
                offset_delay = np.NaN
                button_response = np.NaN

                event_type = self.trial_type
                idx = self.session.global_log.shape[0]     
                if self.block_type == 'unambiguous':

                    # check if the response was still within the same trial
                    if t <  self.session.current_trial_start_time:
                        # now I know that the response offset was in the next trial already
                        # for the reaction time it means we need the onset from previous trial to find the rt
                        previous_trial = self.session.global_log[self.session.global_log['trial_nr'] == self.trial_nr-1]
                        previous_trial_onset = previous_trial['onset'].iloc[0]
                        onset_delay = t - previous_trial_onset

                        # that also means the offset can be tetermined with trial start
                        offset_delay = self.session.clock.getTime() - self.session.current_trial_start_time
                    else:
                        
                        current_trial = self.session.global_log[self.session.global_log['trial_nr'] == self.trial_nr].iloc[0]
                        current_trial_onset = current_trial['onset']
                        onset_delay = t - current_trial_onset

                        trial_duration = (current_trial['phase_length']*self.session.screenticks_per_frame/self.session.monitor_refreshrate)
                        offset_delay = t - (current_trial_onset + trial_duration)
                    
                    # check if the onset delay is in time
                    if (onset_delay >= self.session.response_interval[0]) and (onset_delay <= self.session.response_interval[1]):
                        onset_delay_timing = 'in_time'
                    else:
                        print("respone took too long or was too quick!")
                        onset_delay_timing = 'invalid'

                    # check if offset delay is in time 
                    if (offset_delay >= self.session.response_interval[0]) and (offset_delay <= self.session.response_interval[1]) : 
                        offset_delay_timing = 'in_time'
                    else:
                        offset_delay_timing = 'invalid'

                    # based on the offset delay (if the response lasted until the beginning of the
                    # following trial) we can check if the response button was correct
                    # TODO: This has to be implemented in the analysis script, since we never know for sure which buttons were used!
                    #button_response = self.get_button_validity(thisKey.name, offset_delay, event_type)
    
                self.session.global_log.loc[idx, 'event_type'] = event_type
                self.session.global_log.loc[idx, 'trial_nr'] = self.trial_nr   
                self.session.global_log.loc[idx, 'onset'] = t
                self.session.global_log.loc[idx, 'reaction_time'] = onset_delay
                self.session.global_log.loc[idx, 'key_duration'] = thisKey.duration
                self.session.global_log.loc[idx, 'offset_delay'] = offset_delay
                self.session.global_log.loc[idx, 'onset_delay_timing'] =  onset_delay_timing
                self.session.global_log.loc[idx, 'offset_delay_timing'] =  offset_delay_timing
                self.session.global_log.loc[idx, 'response_button'] = self.session.response_button
                self.session.global_log.loc[idx, 'phase'] = self.phase
                self.session.global_log.loc[idx, 'response'] = thisKey.name
                self.session.global_log.loc[idx, 'nr_frames'] = 0

                for param, val in self.parameters.items():
                    self.session.global_log.loc[idx, param] = val

                if self.eyetracker_on:  # send message to eyetracker
                    msg = f'start_type-{event_type}_trial-{self.trial_nr}_phase-{self.phase}_key-{thisKey.name}_time-{t}_duration-{thisKey.duration}'
                    self.session.tracker.sendMessage(msg)

                if thisKey.name in self.session.break_buttons:
                    print('NEXT PHASE')
                    self.exit_phase = True

                if thisKey.name == 'p':
                    input('PAUSE. Press enter to continue.')


    def get_button_validity(self, keyName, offset_delay, event_type):
        
        response_key = np.NaN
        if keyName == self.session.button_right: 
            response_key = 'right'
        elif keyName == self.session.button_left:
            response_key = 'left'
    
        if offset_delay < 0:
            if event_type == response_key:
                button_response = 'correct'
            else:
                button_response = 'incorrect'
        # if the key was released in the following trial, then the event type is not corresponding but opposite!
        elif offset_delay >= 0:
            if (event_type != response_key) and ((response_key == 'left') or (response_key == 'right')):
                button_response = 'correct'
            else:
                button_response = 'incorrect'

        return button_response

        
                    


 

    



    
        
