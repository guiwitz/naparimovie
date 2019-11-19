"""
This module implements a Python class that allows to create movies based
on key frames selected within interactive napari visualisations.
"""
# Author: Guillaume Witz, Science IT Support, Bern University, 2019
# License: BSD3 License


import numpy as np
import matplotlib.pyplot as plt
import napari
from pyquaternion import Quaternion
from matplotlib.animation import FuncAnimation
import copy

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
        states : list
            list of napari camera states
        state_visible: list
            list of length n where n is number of layers. Each element is 
            a list of booleans indicating visibility
        state_time: list
            list of time points of the key frames
        all_states: list
            list of interpolated quaternion rotation states
        all_scales: numpy array
            interpolated zooming factors
        all_vis : list of numpy array
            list of length n where n is number of layers. Each element is a 
            list of interpolated booleans indicating visibility
        all_time : numpy array
            interpolated time points 
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
        
        
        self.inter_steps = inter_steps

        self.states = []
        self.state_visible = []
        self.state_time = []
        
        self.all_states = []
        self.all_scales = []
        self.all_vis = []
        self.all_time = []
        self.current_frame = 0
        self.current_interpolframe = 0
          
        
        self.add_callback()
        
        self.test = []
        
        
    def add_callback(self):
        """Bind p key to add key-frame"""
                
        self.myviewer.bind_key('f', self.capture_keyframe_callback)
        self.myviewer.bind_key('r', self.replace_keyframe_callback)
        self.myviewer.bind_key('d', self.delete_keyframe_callback)
        
        self.myviewer.bind_key('a', self.key_adv_frame)
        self.myviewer.bind_key('b', self.key_back_frame)

        self.myviewer.bind_key('w', self.key_interpolframe)
      
    
    def capture_keyframe_callback(self, viewer):
        """Record current key-frame"""

        current_state = copy.deepcopy(self.myviewer.window.qt_viewer.view.camera.get_state())
        self.states.insert(self.current_frame+1, current_state)
            
        self.state_visible.insert(self.current_frame+1,[x.visible for x in self.myviewer.layers])
        
        #if time-lapse, capture time frame
        if len(self.myviewer.dims.point)==4:
            self.state_time.insert(self.current_frame+1, self.myviewer.dims.point[0])
        
        self.current_frame += 1
        
        
    def replace_keyframe_callback(self, viewer):
        """Replace current key-frame with new view"""
        
        current_state = copy.deepcopy(self.myviewer.window.qt_viewer.view.camera.get_state())
        self.states[self.current_frame] = current_state
        self.state_visible[self.current_frame] = [x.visible for x in self.myviewer.layers]
        
        #if time-lapse, capture time frame
        if len(self.myviewer.dims.point)==4:
            self.state_time[self.current_frame] = self.myviewer.dims.point[0]
        self.create_steps()
        
            
    def delete_keyframe_callback(self, viewer):
        """Delete current key-frame"""
        
        self.states.pop(self.current_frame)
        self.state_visible.pop(self.current_frame)
        
        #if time-lapse, capture time frame
        if len(self.myviewer.dims.point)==4:
            self.state_time.pop(self.current_frame)
            
        self.current_frame = (self.current_frame -1)%len(self.states)
        self.set_to_keyframe(self.current_frame)
        self.create_steps()
            
    def key_adv_frame(self,viewer):
        """Go forwards in key-frame list"""
        new_frame = (self.current_frame + 1)%len(self.states)
        self.set_to_keyframe(new_frame)
        
    def key_back_frame(self,viewer):
        """Go backwards in key-frame list"""
        new_frame = (self.current_frame -1)%len(self.states)
        self.set_to_keyframe(new_frame)
            
    def set_to_keyframe(self, frame):
        """Set the napari viewer to a given key-frame
        
        Parameters
        -------
        frame : int
            frame to visualize
        """
        
        self.current_frame = frame
        
        if len(self.myviewer.dims.point)==4:
            self.myviewer.dims.set_point(0,self.state_time[frame])
        
        for j in range(len(self.state_visible[0])):
            self.myviewer.layers[j].visible = self.state_visible[frame][j]
                
        self.myviewer.window.qt_viewer.view.camera.set_state(self.states[frame])
        self.myviewer.window.qt_viewer.view.camera.view_changed()

     
    def key_interpolframe(self, viewer):
        """Progress through interpolated frames"""
        
        self.create_steps()
            
        new_frame = (self.current_interpolframe +1)%len(self.all_states)
        self.update_napari_state(new_frame)
        self.current_interpolframe = new_frame
       
        
        '''t1 = time.time()
        for f in range(len(self.all_states)):
            self.update_napari_state(f)
            self.current_interpolframe = f
            t2 = time.time()
            while t2-t1<1:
                t2 = time.time()
            t1 = t2
            self.myviewer.window.qt_viewer.canvas.update()'''

            
    def create_steps(self):
        """Create interpolated states between key-frames"""
        
        #gather rotation states and interpolate them as quaternions
        state_list = self.states.copy()
        all_states = []
        for i in range(len(state_list)-1):
            q0 = Quaternion(state_list[i]['_quaternion'].w, state_list[i]['_quaternion'].x,
                  state_list[i]['_quaternion'].y,state_list[i]['_quaternion'].z)
            q1 = Quaternion(state_list[i+1]['_quaternion'].w, state_list[i+1]['_quaternion'].x,
                  state_list[i+1]['_quaternion'].y,state_list[i+1]['_quaternion'].z)
            
            for q in Quaternion.intermediates(q0, q1, self.inter_steps, include_endpoints=True):
                all_states.append(q)
        
        #recover zooming steps and interpolate them
        all_scales = [x['scale_factor'] for x in state_list]
        scales_interp = np.interp(x=np.arange(len(all_states)),xp = np.linspace(0,len(all_states)-1,len(all_scales)), fp = all_scales)
        #yconv = np.convolve(scales_interp, np.ones(10)/10,mode = 'valid')
        #yfinal = np.array(4*[yconv[0]]+list(yconv)+5*[yconv[-1]])
        
        #recover fov steps and interpolate them
        all_fov = [x['fov'] for x in state_list]
        fov_interp = np.interp(x=np.arange(len(all_states)),xp = np.linspace(0,len(all_states)-1,len(all_fov)), fp = all_fov)
        
        #recover view center steps and interpolate them
        all_center = np.array([x['center'] for x in state_list])
        center_interp = [np.interp(x=np.arange(len(all_states)),xp = np.linspace(0,len(all_states)-1,len(all_center)), 
                                   fp = all_center[:,c]) for c in range(3)]
        center_interp = np.stack(center_interp,axis = 1)
        center_interp = [tuple(x) for x in center_interp]
        
        #recover visibility states for all layers and "interpolate" them
        all_vis = []
        for i in range(len(self.state_visible[0])):
            vis_to_interp = np.array(self.state_visible)[:,i].astype(int)
            vis_interp = np.interp(x=np.arange(len(all_states)),xp = np.linspace(0,len(all_states)-1,len(all_scales)), 
                          fp = vis_to_interp)
            all_vis.append(vis_interp>0)
            
            
        #if time-lapse, interpolate time points
        if len(self.myviewer.dims.point)==4:
            all_time = []
            for x in range(len(self.state_time)-1):
                t_step = (self.state_time[x+1]-self.state_time[x])/(self.inter_steps+2)
                all_time.append(self.state_time[x]+t_step*np.arange(0,self.inter_steps+2))

            self.all_time = np.concatenate(all_time).astype(int)
        
        
        
        self.all_states = all_states
        self.all_scales = scales_interp
        self.all_fov = fov_interp
        self.all_center = center_interp
        self.all_vis = all_vis
        
                
    def collect_images(self):
        """Collect images corresponding to all interpolated states
        
        Returns
        -------
        image_stack : 3D numpy
            stack of all snapshots
        """
        
        images = []
        new_state = copy.deepcopy(self.myviewer.window.qt_viewer.view.camera.get_state())
        self.create_steps()
        for i in range(len(self.all_states)):
            new_state['_quaternion'].x = self.all_states[i].x
            new_state['_quaternion'].y = self.all_states[i].y
            new_state['_quaternion'].z = self.all_states[i].z
            new_state['_quaternion'].w = self.all_states[i].w
            new_state['scale_factor'] = self.all_scales[i]
            new_state['fov'] = self.all_fov[i]
            new_state['center'] = self.all_center[i]
            
            if len(self.myviewer.dims.point)==4:
                self.myviewer.dims.set_point(0,self.all_time[i])
            self.myviewer.window.qt_viewer.view.camera.set_state(new_state)
            self.myviewer.window.qt_viewer.view.camera.view_changed()
            
            for j in range(len(self.all_vis)):
                self.myviewer.layers[j].visible = self.all_vis[j][i]
            images.append(self.myviewer.screenshot())
          
        image_stack = np.stack(images,axis = 0)
        return image_stack
    
    def create_interaction(self):
        
        frame = ipw.IntSlider(value = 0, min=0, 
                                      max = len(self.all_states),step = 1,
                                                                 continuous_update = False)
        out = ipw.interactive_output(self.update_napari_state, {'frame' : frame})
        ui = ipw.VBox([frame])
        
        return ui, out
        
        
    def update_napari_state(self, frame):
        """Set the napari viewer to a given interpolated frame
        
        Parameters
        -------
        frame : int
            frame to visualize
        """

        new_state = copy.deepcopy(self.myviewer.window.qt_viewer.view.camera.get_state())
        
        new_state['_quaternion'].x = self.all_states[frame].x
        new_state['_quaternion'].y = self.all_states[frame].y
        new_state['_quaternion'].z = self.all_states[frame].z
        new_state['_quaternion'].w = self.all_states[frame].w
        new_state['scale_factor'] = self.all_scales[frame]
        new_state['fov'] = self.all_fov[frame]
        new_state['center'] = self.all_center[frame]
        
        if len(self.myviewer.dims.point)==4:
                self.myviewer.dims.set_point(0,self.all_time[frame])
        
        for j in range(len(self.all_vis)):
                self.myviewer.layers[j].visible = self.all_vis[j][frame]
                
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
        self.anim = FuncAnimation(self.fig, self.update, frames=np.arange(len(self.all_states)),
                        init_func=self.movie_init, blit=False)
        plt.show()
        
        self.anim.save(name,dpi=resolution,fps = fps)
        



        
        
        
        
        
        
        
        
        
        
        
        
        
