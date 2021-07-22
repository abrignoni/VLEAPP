# VLEAPP
Vehicle Logs Events And Properties Parser
Details in blog post here: https://abrignoni.blogspot.com/2021/07/vleapp-vehicle-logs-events-and.html

Select parsing directly from a compressed .tar/.zip file, or a directory.

## Pre-requisites:
This project requires you to have Python > 3.7.4 installed on your system. **Ideally use Python 3.9 (significantly faster processing!)**

## Installation

To install dependencies, run:

```
pip install -r requirements.txt
```

To run on **Linux**, you will also need to install `tkinter` separately like so:

```
sudo apt-get install python3-tk
```

## Compile to executable

To compile to an executable so you can run this on a system without python installed.

To create vleapp.exe, run:

```
pyinstaller --onefile vleapp.spec
````

To create ileappGUI.exe, run:

```
pyinstaller --onefile --noconsole vleappGUI.spec
```

## Usage

### CLI

```
$ python vleapp.py -t <zip | tar | fs | gz > -i <path_to_extraction> -o <path_for_report_output>
```

### GUI

```
$ python vleappGUI.py 
```

### Help

```
$ python vleapp.py --help
```

The GUI will open in another window.  <br><br>


## Acknowledgements

This tool is the result of a collaborative effort of many people in the DFIR community.
