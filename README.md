# naparimovie

The goal of this package is to provide the possibility to create movies based on [napari](https://github.com/napari/napari) visualisations. Two solutions are offered: either manually select key-frames or define a set of commands in a script, similarly to what is done in [3Dscript]((https://www.nature.com/articles/s41592-019-0359-1)). This package allows to create movies based on a series of key-frames selected in an napari visualisation. At the moment this package only handles 3D to 5D data (3D, multi-channel, time-lapses) but not 2D views.

This is NOT an official part of napari. Hopefully such an approach can at some point be integrated in a clean way directly into napari. In the meantime this package provides a temporary solution for this common task. The package is very experimental and has not been widely tested.

## Installation

This package has only been tested on OSX. On top of matplotlib and numpy, the only unusual dependencies needed are [pyquaternion](http://kieranwynn.github.io/pyquaternion/) and [ffmpeg](http://www.ffmpeg.org/) which can both be installed via pip or conda.

In order to get the example notebook working you can create a conda environment installing all necessary dependencies using the [environment.yml](environment.yml) file:

```
conda env create -f environment.yml
```
Then activate the environment and start Jupyter:
```
conda activate napari_movie
jupyter notebook
```
Download this repository or just the [examples](examples) folder containing notebooks and start for example the [naparimovie_interactive](examples/naparimovie_interactive.ipynb) notebook:

If you already have a working environment, you can just install this package via pip:
```
pip install git+https://github.com/guiwitz/naparimovie.git@master#egg=naparimovie
```

## How to use

### Create a napari view and a movie object
You first have to creat a napari view containing one ore more 3D or 4D data. The viewer object can then be used to create the Movie object. Here's a minimal example using a random 3D array (instruction valid within a Jupyter notebook, check [napari](https://github.com/napari/napari) for instructions in other contexts):

```python
import numpy as np
import napari
from naparimovie import Movie
%gui qt5

#create data
image = np.random.randn(100,100,100)

#create napari viewer
viewer = napari.Viewer(ndisplay=3)
viewer.add_image(image, scale=(1,1,1))

#create naparimovie object
movie = Movie(myviewer=viewer)
```

At this point, when the napari window is in foreground, you want to create a set of key-frames. The final movie will then be interpolated between these key-frames to generate a smooth animation. At each key-frame you can adjust the following paramters:

- rotation
- displacement
- zoom
- time frame (if time-lapse)
- visibility of different layers

In order to select these key-frames you have two choices: you can either select them manually or specify them within a script.

### Interactive key-frames

The idea here is to create a successive set of ***views*** with specific properties (see above) and to define them as key-frames. In order to capture and modify these key-frames, a set of keyboard keys can be used when navigating in the napari window:

- ```f```: set current view as key-frame. The key-frame is added right after the current key-frame. If you move between key-frames using a,b (see below) this allows you to insert key-frames at specific positions
- ```r``` : replace current key-frame with adjusted view
- ```d``` : delete current key-frame
- ```a``` : go to next key-frame
- ```b``` : go to previous key-frame

Once you have defined a set of key-frames, you can check how the movie is going to look like, by going through the **interpolated** frames using:

- ```w``` : go through interpolated key-frames

If it's not smooth enough, you can modify the number of interpolated frames by adjusting:
```python
movie.inter_steps = 30
```
You can add/remove key-frames and use ```w``` at any time, as frames are re-interpolated at every added key-frame. You can test all this in the [naparimovie_interactive](examples/naparimovie_interactive.ipynb) notebook.

### Script based key-frames

If you want to be able to replicate your animation or specify it precisely you can also write a script for it. This follows the ideas of the Fiji plugin [3Dscript](https://www.nature.com/articles/s41592-019-0359-1) where commands describing modifications of the viewed volume are implemented in a natural language. Two script examples are provided [here](/examples/moviecommands.txt) and [here](examples/moviecommands2.txt). Please read the 3Dscript documentation to understand how such scripts are written. At the moment you can use:

- At frame ...
- From frame x to frame y ...

statements to specific the range of frames. The possible modifications (with example values) are:

- zoom by a factor of 0.2
- translate by (0,40,0)
- rotate by 180 degrees around (1,0,0)
- make layer 0 visible
- make layer 0 invisible
- shift time by 3
- shift time by -45

The "time" and "make" commands are specific to this implementation. Here is an example of a script:

```
At frame 10 make layer 0 invisible
From frame 0 to frame 20 shift time by 45
From frame 0 to frame 20
-rotate by 180 degrees around (1,0,0)
-zoom by a factor of 2
At frame 20 make layer 0 visible
From frame 21 to frame 30
-rotate by 180 degrees around (0,0,1)
-zoom by a factor of 0.5
-shift time by -45
```

Once the script is ready and saved as a .txt file, you can call it like this on your movie object:
```python
movie.create_state_dict_from_script('moviecommands.txt')
```
This will generate key-frames as well as interpolated states, exactly like in the interactive version. Once this is done you can again browse through your animation using the keyboard keys define above. You can test all this in the [naparimovie_script](examples/naparimovie_script.ipynb) notebook.

### Saving the movie

Finally you can save your movie in .mp4 format or as gifs. For movies you can adjust the resolution (dpi) and the frame rate (fps):
```python
movie.make_movie(name = 'movie.mp4', resolution = 300, fps = 20)
```

No options are offered for gifs:
```python
movie.make_gif('gifmovie.gif')
```

And here is the sort of result you can get:
![movie](/examples/gif_script.gif)
