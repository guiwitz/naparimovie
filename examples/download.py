import os
import requests
from zipfile import ZipFile

if not os.path.isfile('Sample/mitosis.zip'):
    os.makedirs('Sample/',exist_ok=True)
    myfile = requests.get('http://mirror.imagej.net/images/Spindly-GFP.zip', allow_redirects=True)
    open('Sample/mitosis.zip', 'wb').write(myfile.content)
    with ZipFile('Sample/mitosis.zip', 'r') as zipObj:
        zipObj.extractall(path='Sample/')