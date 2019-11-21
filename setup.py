from setuptools import setup

setup(name='naparimovie',
      version='0.1',
      description='Generating movies from napari views',
      url='https://github.com/guiwitz/naparimovie',
      author='Guillaume Witz',
      author_email='',
      license='BSD3',
      packages=['naparimovie'],
      zip_safe=False,
      install_requires=['pyquaternion', 'imageio'],
      )