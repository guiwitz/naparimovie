"""
This module implements a Python class that allows to create movies based
on key frames selected within interactive napari visualisations or found in a 
script.
"""
# Author: Guillaume Witz, Science IT Support, Bern University, 2019
# License: BSD3 License


import numpy as np
import matplotlib.pyplot as plt
import napari
from pyquaternion import Quaternion
from matplotlib.animation import FuncAnimation
import imageio
import copy

from . import state_interpolations as si
from .scriptcommands import Script 

class Movie:
    
    def __init__(self, myviewer = None, inter_steps = 15):

        """Standard __init__ method.
        
        Parameters
        ----------
        myviewer : napari viewer
            napari viewer
        inter_steps: int
            number of steps to interpolate between key frames 
        
        Attributes
        ----------
        key_frames : list
            list of dictionary defining napari viewer states. Dictionaries have keys:
                'frame': int, frame
                'rotate': vispy quaternion, camera rotation
                'translate': tuple, camera center
                'zoom': float, camera zooming factor
                'vis': list of booleans, visibility of layers
                'time': int, time-point
        interpolated_states: dict
            dictionary defining interpolated states. Each element is a list of length N
            frames. Keys are:
                'rotate': list of pyquaternions
                'translate': list of tuple defining camera center
                'zoom': list of floats defining camera zoom
                'vis': list of boolean lists defining layer visibility
                'time': list of int defining time-point
        states_dict : list
            list of dictionary defining napari viewer states for each frame. Same keys as key_frames
        
        current_frame : int
            currently shown key frame
        implot : matplotlib Ax object
            reference to matplotlib image used for movie returned by imshow
        anim : matplotlib FuncAnimation object
            reference to animation object
            
        """        
        
        if myviewer is None:
            raise TypeError('You need to pass a napari viewer for the myviewer argument')
        else:
            self.myviewer = myviewer
        
        self.key_frames = []
        self.inter_steps = inter_steps

        self.current_frame = -1
        self.current_interpolframe = 0
          
        #establish key bindings
        self.add_callback()
                
        
    def add_callback(self):
        """Bind keys"""
                
        self.myviewer.bind_key('f', self.capture_keyframe_callback)
        self.myviewer.bind_key('r', self.replace_keyframe_callback)
        self.myviewer.bind_key('d', self.delete_keyframe_callback)
        
        self.myviewer.bind_key('a', self.key_adv_frame)
        self.myviewer.bind_key('b', self.key_back_frame)

        self.myviewer.bind_key('w', self.key_interpolframe)
      
    
    def get_new_state(self):
        """Capture current napari state
        
        Returns
        -------
        new_state : dict
            description of state
        """
        
        current_state = copy.deepcopy(self.myviewer.window.qt_viewer.view.camera.get_state())
        time = self.myviewer.dims.point[0] if len(self.myviewer.dims.point)==4 else []
        new_state = {'frame': self.current_frame,
                     'rotate': current_state['_quaternion'],
                     'translate': current_state['center'],
                     'zoom': current_state['scale_factor'],
                     'vis': [x.visible for x in self.myviewer.layers],
                    'time': time}
        
        return new_state
            
    def capture_keyframe_callback(self, viewer):
        """Record current key-frame"""

        new_state = self.get_new_state()
        new_state['frame']+=1
        self.key_frames.insert(self.current_frame+1, new_state)
        self.current_frame += 1
        
        
    def replace_keyframe_callback(self, viewer):
        """Replace current key-frame with new view"""
        
        new_state = self.get_new_state()
        self.key_frames[self.current_frame] = new_state
        
        self.create_steps()
        
            
    def delete_keyframe_callback(self, viewer):
        """Delete current key-frame"""
        
        self.key_frames.pop(self.current_frame)
            
        self.current_frame = (self.current_frame -1)%len(self.key_frames)
        self.set_to_keyframe(self.current_frame)
        self.create_steps()
            
    def key_adv_frame(self,viewer):
        """Go forwards in key-frame list"""
        
        new_frame = (self.current_frame + 1)%len(self.key_frames)
        self.set_to_keyframe(new_frame)
        
    def key_back_frame(self,viewer):
        """Go backwards in key-frame list"""
        
        new_frame = (self.current_frame -1)%len(self.key_frames)
        self.set_to_keyframe(new_frame)
        
            
    def set_to_keyframe(self, frame):
        """Set the napari viewer to a given key-frame
        
        Parameters
        -------
        frame : int
            key-frame to visualize
        """
        
        self.current_frame = frame
        
        #set camera state
        new_state = copy.deepcopy(self.myviewer.window.qt_viewer.view.camera.get_state())
        if self.key_frames[frame]['rotate']: 
            new_state['_quaternion'] = self.key_frames[frame]['rotate']
        if self.key_frames[frame]['translate']: new_state['center'] = self.key_frames[frame]['translate']
        if self.key_frames[frame]['zoom']: new_state['scale_factor'] = self.key_frames[frame]['zoom']
        
        #set time if 4D
        if len(self.myviewer.dims.point)==4:
            if type(self.key_frames[frame]['time']) is not list:
                self.myviewer.dims.set_point(0,self.key_frames[frame]['time'])
        
        #set visibility of layers
        for j in range(len(self.myviewer.layers)):
            if self.key_frames[frame]['vis']: self.myviewer.layers[j].visible = self.key_frames[frame]['vis'][j]
        
        #update state
        self.myviewer.window.qt_viewer.view.camera.set_state(new_state)
        self.myviewer.window.qt_viewer.view.camera.view_changed()
        
    def create_state_dict(self):
        """Create list of state dictionaries. For key-frames selected interactively,
        add self.inter_steps emtpy frames between key-frames. For key-frames from scripts,
        the number of empty frames ot add between each key-frame is already set in self.inter_steps.
        """
        
        if type(self.inter_steps) is not list:
            inter_steps = len(self.key_frames)*[self.inter_steps]
        else:
            inter_steps = self.inter_steps
        
        empty = {'frame': [],'rotate': [],'translate': [],'zoom': [],'vis': [], 'time': []}
        states_dict = []
        for ind, x in enumerate(self.key_frames):
            states_dict.append(x)
            if ind<len(self.key_frames)-1:
                for y in range(inter_steps[ind]):
                    states_dict.append(copy.deepcopy(empty))
        for ind, x in enumerate(states_dict):
            x['frame'] = ind
        self.states_dict = states_dict
        
    
    def create_state_dict_from_script(self, script_path):
        """Create key-frames and list of state dictionaries from a script.
        
        Parameters
        -------
        script_path : str
            path to script
        """
        
        script = Script(path_to_script=script_path)
        script.read_script()
        script.create_commandlist()
        script.create_frame_commandlist(self)
        self.states_dict = script.states_dict
        script.make_keyframes()
        self.key_frames = script.key_frames
        self.inter_steps = [self.key_frames[x+1]['frame']-self.key_frames[x]['frame']-1 for x in range(len(self.key_frames)-1)]

    def create_steps(self):
        """Interpolate states between key-frames"""
        
        self.create_state_dict()
        self.interpolated_states = si.interpolate(self.states_dict)
        
    def key_interpolframe(self, viewer):
        """Progress through interpolated frames"""
        
        self.create_steps()
            
        new_frame = (self.current_interpolframe+1)%len(self.states_dict)
        self.update_napari_state(new_frame)
        self.current_interpolframe = new_frame

               
    def collect_images(self):
        """Collect images corresponding to all interpolated states
        
        Returns
        -------
        image_stack : 3D numpy
            stack of all snapshots
        """
        
        images = []
        self.create_steps()
        for i in range(len(self.states_dict)):
            
            self.update_napari_state(i)
            images.append(self.myviewer.screenshot())
          
        image_stack = np.stack(images,axis = 0)
        return image_stack
    
    
    def update_napari_state(self, frame):
        """Set the napari viewer to a given interpolated frame
        
        Parameters
        -------
        frame : int
            frame to visualize
        """

        new_state = copy.deepcopy(self.myviewer.window.qt_viewer.view.camera.get_state())
        
        new_state['_quaternion'] = new_state['_quaternion'].create_from_axis_angle(
            self.interpolated_states['rotate'][frame].angle, *self.interpolated_states['rotate'][frame].axis)
        new_state['scale_factor'] = self.interpolated_states['zoom'][frame]
        #new_state['fov'] = self.all_fov[frame]
        new_state['center'] = self.interpolated_states['translate'][frame]
        
        if len(self.myviewer.dims.point)==4:
                self.myviewer.dims.set_point(0,self.interpolated_states['time'][frame])
        
        for j in range(len(self.myviewer.layers)):
                self.myviewer.layers[j].visible = self.interpolated_states['vis'][frame][j]
            
        self.myviewer.window.qt_viewer.view.camera.set_state(new_state)
        self.myviewer.window.qt_viewer.view.camera.view_changed()
        
    
    def create_movie_frame(self):
        """Create the matplotlib figure, and image object hosting all snapshots"""
        
        newim = self.myviewer.screenshot()
        sizes = newim.shape
        height = float(sizes[0])
        width = float(sizes[1])

        factor = 3
        fig = plt.figure()
        fig.set_size_inches(factor*width/height, factor, forward=False)
        ax = plt.Axes(fig, [0., 0., 1., 1.])
        ax.set_axis_off()
        fig.add_axes(ax)
        
        self.fig = fig
        self.ax = ax
                
        self.implot = plt.imshow(newim,animated=True)

    def movie_init(self):
        """init function for matplotlib FuncAnimation"""
        
        newim = self.myviewer.screenshot()
        self.implot.set_data(newim)
        return self.implot

    def update(self, frame):
        """Update function matplotlib FuncAnimation 
        
        Parameters
        -------
        frame : int
            frame to visualize
        """
        
        self.update_napari_state(frame)
        newim = self.myviewer.screenshot()
        self.implot.set_data(newim)
        return self.implot

    def make_movie(self, name = 'movie.mp4', resolution = 600, fps = 20):
        """Create a movie based on key-frames selected in napari
        
        Parameters
        -------
        name : str
            name to use for saving the movie (can also be a path)
        resolution: int
            resolution in dpi to save the movie
        fps : int
            frames per second
        """
        
        #creat all states
        self.create_steps()
        #create movie frame
        self.create_movie_frame()
        #animate
        self.anim = FuncAnimation(self.fig, self.update, frames=np.arange(len(self.states_dict)),
                        init_func=self.movie_init, blit=False)
        plt.show()
        
        self.anim.save(name,dpi=resolution,fps = fps)
        
        
    def make_gif(self, name = 'movie.gif'):
        """Create a gif based on key-frames selected in napari
        
        Parameters
        -------
        name : str
            name to use for saving the movie (can also be a path)
        """
        
        #create the image stack with all snapshots
        stack = self.collect_images()
        
        imageio.mimsave(name, [stack[i,:,:,:] for i in range(stack.shape[0])])


        
        