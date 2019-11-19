# naparimovie

This package allows to create movies based on a series of key-frames selected in an napari visualisation. At the moment this package only handles multi-channel 3D time-lapse data. 2D stack views are not supported.

This little package has been developed for a specific application to bridge the gap until such a feature is available directly in napari, and is just provided "as is" for people who would like to use it or adapt it to their own use-case. 

## Installation

This package has only been tested on OSX. On top of matplotlib and numpy, the only unusual dependencies needed are [pyquaternion](http://kieranwynn.github.io/pyquaternion/) and [ffmpeg](http://www.ffmpeg.org/) which can both be installed via pip or conda.

In order to get the example notebook working you can create a conda environment installing all necessary dependencies using the [environment.yml](environment.yml) file:

```bash
conda env create -f environment.yml
```
Then activate the environment, start Jupyter and run the [naparimovie_example](naparimovie_example.ipynb) notebook:
```
conda activate napari_movie
jupyter notebook
```
If you already have a working environment, you can just install this package via pip:
```bash
pip install git+https://github.com/guiwitz/naparimovie.git@master#egg=naparimovie
```

## How to use

You first have to creat a napari view containing one ore more 3D or 4D data. The viewer object can then be used to create the Movie object. Here's a minimal example using a random 3D array (instruction valid within a Jupyter notebook, check [napari](https://github.com/napari/napari) for instructions in other contexts):

```python
import numpy as np
import napari
from naparimovie.naparimovie import Movie
%gui qt5

#create data
image = np.random.randn(100,100,100)

#create napari viewer
viewer = napari.Viewer(ndisplay=3)
viewer.add_image(image, scale=(1,1,1))

#create naparimovie object
movie = Movie(myviewer=viewer)
```

At this point, when the napari window is in foreground, one can use a set of keys to create and modify key-frames. Those key-frames are then interpolated at the time of movie creation to generate a smooth movie. For each key-frame the following properties can be changed:

- object rotation
- object displacement
- time frame
- field of view
- visibility of different layers

The following keys can be used to handle key-frames:

- f : set current view as key-frame. The key-frame is added right after the current key-frame. If you move between key-frames using a,b (see below) this allows you to insert key-frames at specific positions
- r : replace current key-frame with adjusted view
- d : delete current key-frame
- a : go to next key-frame
- b : go to previous key-frame
- w : go through interpolated key-frames

Once you have selected a series of key-frames, you can adjust the number of frames you want to be interpolated between them:
```python
movie.inter_steps = 30
```
You can check if that number is ok by going through the interpolated frames usig the ```w``` key.

And finally you can save your movie in .mp4 format and adjust the resolution (dpi) and the frame rate (fps):
```python
movie.make_movie(name = 'movie.mp4', resolution = 300, fps = 20)
```
