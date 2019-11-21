"""
This module implements a Python class that allows to handle scripts
containing intstructions for creating key-frames programmatically
"""
# Author: Guillaume Witz, Science IT Support, Bern University, 2019
# License: BSD3 License

import copy, re
import numpy as np
from pyquaternion import Quaternion as pyQuaternion
from vispy.util.quaternion import Quaternion

class Script:
    
    def __init__(self, path_to_script = None):

        """Standard __init__ method.
        
        Parameters
        ----------
        path_to_script : str
            path to script
        
        
        Attributes
        ----------
        command_series : list
            list of script commands
        end: int
            max frame
        command_list: list
            list of dictionaries with each element reprenting one operation. Keys are:
            'start': int
                start from of operation
            'end':  int
                start from of operation
            'operation': str
                type of operation, e.g. 'zoom', 'rotate'
            'params': list
                list of parameters needed for operation e.g [2] for 'zoom'
        states_dict : list
            list of dictionaries defining napari viewer states for each frame. Dictionaries have keys:
                'frame': int, frame
                'rotate': vispy quaternion, camera rotation
                'translate': tuple, camera center
                'zoom': float, camera zooming factor
                'vis': list of booleans, visibility of layers
                'time': int, time-point
        key_frames: list
            same as states_dict but only elements containing a change are conserved
            
        """        
        
        if path_to_script is None:
            raise TypeError('You need to pass a string with a path to a script')
        else:
            self.path_to_script = path_to_script
            
        #instantiate Quaternion object
        self.q = Quaternion()

        
        
        
    def read_script(self):
        """Read the script and create a list with groups of 
        commands belonging to a given unit"""
        
        #read all lines
        commands = []
        with open(self.path_to_script) as f:
            commands = f.readlines()

        #group commands belonging together e.g. those belonging to 
        #and From frame ... statement
        command_series = []
        line = 0
        while line<len(commands):
            main_line = commands[line]
            line+=1
            if main_line[0]=='#':
                continue
            if len(re.findall('.*to frame \d+(\n)', main_line))==1:
                temp_lines = []
                while (commands[line][0]=='-'):
                    temp_lines.append(commands[line])
                    line+=1
                    if line == len(commands):
                        break
                command_series.append([main_line,temp_lines])
            else:
                command_series.append([main_line,[main_line]])

        end = [re.findall('(At frame |to frame )(\d+).*',x) for x in commands]
        end = np.max([int(x[0][1]) for x in end if x])
        
        self.command_series = command_series
        self.end = end
        
        
    def create_commandlist(self):    
        """create a dictionary list of each operation. Each operation becomes
        one dictionary. Operations belonging to groups have same start/end frames"""
        
        #go through all commands and parse the information
        command_list = []
        for c in self.command_series:
            
            #get start and end frames. For "At frame..." statements end == start
            if c[0].split()[0] == 'From':
                start = int(re.findall('From frame (\d+) to*', c[0])[0])
                end = int(re.findall('to frame (\d+) *', c[0])[0])
            else:
                start = int(re.findall('At frame (\d+).*', c[0])[0])
                end = int(re.findall('At frame (\d+).*', c[0])[0])
            
            #For each group of statements parse the commands
            for c2 in c[1]:
                parsed = self.parse_command(c2)
                #if parsing returns a list, it means that the operation has been split into parts
                #mainly to handle large rotations
                if type(parsed) is list:
                    interm_steps = np.linspace(start,end,len(parsed)+1).astype(int)
                    for i in range(len(interm_steps)-1):
                        command_list.append([interm_steps[i], interm_steps[i+1], parsed[i]])
                else:
                    command_list.append([start, end, parsed])                        
        
        #sort commands by time
        command_list = np.array(command_list)
        command_list = command_list[np.argsort(command_list[:,0]),:]
        
        #create list of dictionaries
        command_list = [{'start': x[0], 'end': x[1], 'operation': x[2][0], 'params': x[2][1:]} for x in command_list]
        self.command_list = command_list
        
    def parse_command(self, command):
        """given a command line, parse the content
        
        Returns
        -------
        result : tuple
            tuple with the type of operation and the corresponding parameters
            e.g. ('zoom', 2)
        """
        
        #chcek operation type
        mod_type = re.findall('.*(rotate|translate|zoom|make|time).*',command)[0]
        
        #for each operation type recover necessary parameters
        if mod_type == 'rotate':
            angle = int(re.findall('.*rotate by (\d+).*', command)[0])
            axis = list(map(int,re.findall('.*around \((\d+)\,(\d+)\,(\d+).*', command)[0]))

            #if the rotation angle is large split it into 3 to ensure the rotation is accomplished fully
            if angle >= 180:
                new_q = self.q.create_from_axis_angle(angle/3*2*np.pi/360, axis[0], axis[1], axis[2], degrees=False)
                result = [(mod_type, new_q),(mod_type, new_q),(mod_type, new_q)]
            else:
                new_q = self.q.create_from_axis_angle(angle*2*np.pi/360, axis[0], axis[1], axis[2], degrees=False)
                result = (mod_type, new_q)

        elif mod_type == 'zoom':
            factor = float(re.findall('.*factor of (\d*\.*\d+).*', command)[0])
            result = (mod_type, factor)

        elif mod_type == 'translate':
            translate = np.array(list(map(int,re.findall('.*by \((\-*\d+)\,(\-*\d+)\,(\-*\d+).*', command)[0])))
            result = (mod_type, translate)

        elif mod_type == 'make':
            layer = int(re.findall('.*make layer (\d+).*', command)[0])
            vis_status = command.split()[-1]
            if vis_status == 'invisible':
                result = ('vis', layer, False)
            else:
                result = ('vis', layer, True)
                
        elif mod_type == 'time':
            time_shift = int(re.findall('.*by (\-*\d+).*', command)[0])
            result = (mod_type, time_shift)
        return result
    
    def create_frame_commandlist(self, movie):
        """Go through the list of operations and create for each frame a dictionary
        with modifications to be operated. Only frames with an operation are filled,
        the others are interpolated later"""
        
        states_dict = [dict(zip(('frame','rotate','translate','zoom', 'vis','time'), (a, [],[],[],[],[]))) for a in np.arange(self.end+1)]

        #initialize state with current view. This first point can be adjusted by using 
        #a series of "At frame 0... " commands
        current_state = copy.deepcopy(movie.myviewer.window.qt_viewer.view.camera.get_state())
        states_dict[0]['rotate'] = current_state['_quaternion']
        states_dict[0]['zoom'] = current_state['scale_factor']
        states_dict[0]['translate'] = current_state['center']
        states_dict[0]['vis'] = [x.visible for x in movie.myviewer.layers]
        if len(movie.myviewer.dims.point)==4:
            states_dict[0]['time'] = movie.myviewer.dims.point[0]

            
        #fille the states_dict at the start/end positions by compounding operations over frame containing changes
        old_state = copy.deepcopy(states_dict[0])
        for c in self.command_list:

            if c['operation'] == 'rotate':
                states_dict[c['start']]['rotate'] = copy.deepcopy(old_state['rotate'])
                states_dict[c['end']]['rotate'] = copy.deepcopy(old_state['rotate']*c['params'][0])
                old_state['rotate'] = copy.deepcopy(states_dict[c['end']]['rotate'])

            elif c['operation'] == 'translate':
                states_dict[c['start']]['translate'] = copy.deepcopy(old_state['translate'])
                states_dict[c['end']]['translate'] = copy.deepcopy(tuple(np.array(old_state['translate']) + c['params'][0]))
                old_state['translate'] = copy.deepcopy(states_dict[c['end']]['translate'])

            elif c['operation'] == 'zoom':
                states_dict[c['start']]['zoom'] = copy.deepcopy(old_state['zoom'])
                states_dict[c['end']]['zoom'] = copy.deepcopy(old_state['zoom'] * c['params'][0])
                old_state['zoom'] = copy.deepcopy(states_dict[c['end']]['zoom'])

            elif c['operation'] == 'vis':
                states_dict[c['start']]['vis'] = copy.deepcopy(old_state['vis'])
                states_dict[c['end']]['vis'] = copy.deepcopy(old_state['vis'])
                states_dict[c['end']]['vis'][c['params'][0]] = c['params'][1]
                old_state['vis'] = copy.deepcopy(states_dict[c['end']]['vis'])
                
            elif c['operation'] == 'time':
                states_dict[c['start']]['time'] = copy.deepcopy(old_state['time'])
                states_dict[c['end']]['time'] = copy.deepcopy(old_state['time'] + c['params'][0])
                old_state['time'] = copy.deepcopy(states_dict[c['end']]['time'])

        old_state['frame'] = states_dict[-1]['frame']
        states_dict[-1] = copy.deepcopy(old_state)
        
        self.states_dict = states_dict
        
        
    def make_keyframes(self):
        """In the states_dict list of dictionaries, conserve only elements 
        where change is happening
        """

        props = ['rotate', 'translate','zoom','vis','time']
        states_copy = copy.deepcopy(self.states_dict)
        key_frames = [y for y in states_copy if np.any([y[x] for x in props])]
        
        self.key_frames = key_frames

        
       