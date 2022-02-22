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

    def __init__(self, session, trial_nr, block_ID, block_type, trial_type, response_hand, phase_duration, timing, last_frame_previous, *args, **kwargs):
        
        super().__init__(session, trial_nr, phase_duration,
                         parameters={'block_type': block_type,
                                     'trial_type': trial_type, 
                                     'block_ID' : block_ID,
                                     'response_hand': response_hand,
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
        self.session.draw_stimulus()


    def get_events(self):
        """ Logs responses/triggers """

        keys = self.session.kb.getKeys(waitRelease=True)
        for thisKey in keys:

            if thisKey=='q':  # it is equivalent to the string 'q'
                
                if re.match(r'(\w+)_(practice)', self.block_type):
                    print('End practice session')
                    # TODO: find out how to stop a trial in the middle without ending the experiment

                print("End experiment!")
                self.session.save_output()

                if self.session.settings['Task settings']['Screenshot']==True:
                    print('\nSCREENSHOT\n')
                    self.session.win.saveMovieFrames(opj(self.session.screen_dir, self.session.output_str+'_Screenshot.png'))
                self.session.close()
                self.session.quit()
                
            else: 
                print(thisKey.name, thisKey.tDown, thisKey.rt)
                t = thisKey.rt
                idx = self.session.global_log.shape[0]     
                if self.block_type == 'unambiguous':
                    self.session.unambiguous_responses += 1
                    self.session.total_responses += 1
                    # check if the button was pressed correctly for the shift
                    response_delay = t - self.session.global_log.loc[idx-1, 'onset']
                    print("\nresponse delay:", response_delay)
                    print("previous timing:", self.session.global_log.loc[idx-1, 'onset'])
                    if (response_delay >= self.session.response_interval[0]) and (response_delay <= self.session.response_interval[1]):
                        print("delay (within reponse interval!):", response_delay)
                        self.session.correct_responses += 1 
                    else:
                        print("respone took too long or was too quick!")
                
                if self.block_type == 'ambiguous':
                    self.session.ambiguous_responses += 1
                    self.session.total_responses += 1

                event_type = self.trial_type
                print("sessions clock", self.session.clock.getTime())
                       
                self.session.global_log.loc[idx, 'event_type'] = event_type
                self.session.global_log.loc[idx, 'trial_nr'] = self.trial_nr   
                self.session.global_log.loc[idx, 'onset'] = t
                self.session.global_log.loc[idx, 'key_duration'] = thisKey.duration
                self.session.global_log.loc[idx, 'phase'] = self.phase
                self.session.global_log.loc[idx, 'response'] = thisKey.name
                self.session.global_log.loc[idx, 'nr_frames'] = 0

                for param, val in self.parameters.items():
                    self.session.global_log.loc[idx, param] = val

        
                    


 

    



    
        
