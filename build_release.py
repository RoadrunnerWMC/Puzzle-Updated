
import json
import os, os.path
import shutil
import sys

import PyInstaller.__main__


########################################################################
############################### Constants ##############################
########################################################################

# Everything highly specific to Puzzle is in this section, to make it
# simpler to copypaste this script across all of the NSMBW-related
# projects that use the same technologies (Reggie, Puzzle, BRFNTify,
# etc)

PROJECT_NAME = 'Puzzle'
PROJECT_VERSION = '1.0'

WIN_ICON = os.path.join('reggiedata', 'win_icon.ico')
MAC_ICON = os.path.join('reggiedata', 'reggie.icns')
MAC_BUNDLE_IDENTIFIER = 'ca.chronometry.reggie'

SCRIPT_FILE = 'puzzle.py'
DATA_FOLDERS = ['Icons']
DATA_FILES = ['readme.txt', 'license.txt']


########################################################################
################################# Intro ################################
########################################################################

DIR = 'distrib'
WORKPATH = 'build_temp'
SPECFILE = SCRIPT_FILE[:-3] + '.spec'

def print_emphasis(s):
    print('>>')
    print('>> ' + '=' * (len(s) - 3))
    print(s)
    print('>> ' + '=' * (len(s) - 3))
    print('>>')

print('[[ Building ' + PROJECT_NAME + ' ]]')
print('>> Please note: extra command-line arguments passed to this script will be passed through to PyInstaller.')
print('>> Destination directory: ' + DIR)

if os.path.isdir(DIR): shutil.rmtree(DIR)
if os.path.isdir(WORKPATH): shutil.rmtree(WORKPATH)
if os.path.isdir(SPECFILE): os.remove(SPECFILE)

def run_pyinstaller(args):
    print('>>')
    printMessage = ['>> Running PyInstaller with the following arguments:']
    for a in args:
        if ' ' in a:
            printMessage.append('"' + a + '"')
        else:
            printMessage.append(a)
    print(' '.join(printMessage))
    print('>>')

    PyInstaller.__main__.run(args)


########################################################################
######################### Environment detection ########################
########################################################################
print('>>')
print('>> Detecting environment...')
print('>>')

# Python optimization level
if sys.flags.optimize == 2:
    print('>>   [X] Python optimization level is -OO')
else:
    print('>>   [ ] Python optimization level is -OO')

# NSMBLib being installed
try:
    import nsmblib
    print('>>   [X] NSMBLib is installed')
except ImportError:
    nsmblib = None
    print('>>   [ ] NSMBLib is installed')

# UPX being installed

# There seems to be no reliable way to determine in this script if
# PyInstaller will detect UPX or not. PyInstaller itself provides no
# public API for this, and doing horrible things with its private API
# didn't ultimately work well enough to be useful.
# So all we can do is show this generic message, unfortunately.
print('>>   [?] UPX is installed')


# Now show big warning messages if any of those failed
if sys.flags.optimize < 2:
    msg = 'without' if sys.flags.optimize == 0 else 'with only one level of'
    print_emphasis('>> WARNING: Python is being run ' + msg + ' optimizations enabled! Please consider building with -OO.')

if nsmblib is None:
    print_emphasis('>> WARNING: NSMBLib does not seem to be installed! Please consider installing it prior to building.')

print_emphasis('>> NOTE: If the PyInstaller output below says "INFO: UPX is not available.", you should install UPX!')


########################################################################
############################### Excludes ###############################
########################################################################
print('>>')
print('>> Populating excludes...')
print('>>')

# Static excludes
excludes = ['calendar', 'difflib', 'doctest', 'hashlib', 'inspect',
    'locale', 'multiprocessing', 'optpath', 'os2emxpath', 'pdb',
    'select', 'socket', 'ssl', 'threading', 'unittest']

if sys.platform == 'nt':
    excludes.append('posixpath')

# Add excludes for other Qt modules

unneededQtModules = ['Designer', 'Network', 'OpenGL', 'Qml', 'Script', 'Sql', 'Test', 'WebKit', 'Xml']
neededQtModules = ['Core', 'Gui', 'Widgets']

targetQt = 'PyQt' + str(4 if sys.version_info.major < 3 else 5)
print('>> Targeting ' + targetQt)

for qt in ['PySide2', 'PyQt4', 'PyQt5']:
    # Exclude all the stuff we don't use
    for m in unneededQtModules:
        excludes.append(qt + '.Qt' + m)

    if qt != targetQt:
        # Since we're not using this copy of Qt, exclude it
        excludes.append(qt)

        # As well as its QtCore/QtGui/etc
        for m in neededQtModules:
            excludes.append(qt + '.Qt' + m)

print('>> Will use the following excludes list: ' + ', '.join(excludes))


########################################################################
################### Running PyInstaller (first time) ###################
########################################################################

# Our only goal here is to create a specfile we can edit. Unfortunately,
# there's no good way to do that without doing a full PyInstaller
# build...

args = [
    '--windowed',
    '--onefile',
    '--distpath=' + DIR,
    '--workpath=' + WORKPATH,
]

if sys.platform == 'win32':
    args.append('--icon=' + os.path.abspath(WIN_ICON))
elif sys.platform == 'darwin':
    args.append('--icon=' + os.path.abspath(MAC_ICON))
    args.append('--osx-bundle-identifier=' + MAC_BUNDLE_IDENTIFIER)

for e in excludes:
    args.append('--exclude-module=' + e)
args.extend(sys.argv[1:])
args.append(SCRIPT_FILE)

run_pyinstaller(args)

shutil.rmtree(DIR)
shutil.rmtree(WORKPATH)


########################################################################
########################## Adjusting specfile ##########################
########################################################################
print('>> Adjusting specfile...')

# New plist file data (if on Mac)
info_plist = {
    'CFBundleName': PROJECT_NAME,
    'CFBundleShortVersionString': PROJECT_VERSION,
    'CFBundleGetInfoString': PROJECT_NAME + ' ' + PROJECT_VERSION,
    'CFBundleExecutable': SCRIPT_FILE.split('.')[0],
}

# Open original specfile
with open(SPECFILE, 'r', encoding='utf-8') as f:
    lines = f.read().splitlines()

# Iterate over its lines, and potentially add new ones
new_lines = []
for line in lines:
    new_lines.append(line)

    if sys.platform == 'darwin' and 'BUNDLE(' in line:
        new_lines.append('info_plist=' + json.dumps(info_plist) + ',')

# Save new specfile
with open(SPECFILE, 'w', encoding='utf-8') as f:
    f.write('\n'.join(new_lines))


########################################################################
################### Running PyInstaller (second time) ##################
########################################################################

# Most of the arguments are now contained in the specfile. Thus, we can
# run with minimal arguments this time.

args = [
    '--windowed',
    '--distpath=' + DIR,
    '--workpath=' + WORKPATH,
    SPECFILE,
]

run_pyinstaller(args)

shutil.rmtree(WORKPATH)
os.remove(SPECFILE)


########################################################################
######################## Copying required files ########################
########################################################################
print('>> Copying required files...')

if sys.platform == 'darwin':
    app_bundle_name = SCRIPT_FILE.split('.')[0] + '.app'
    dest_folder = os.path.join(DIR, app_bundle_name, 'Contents', 'Resources')
else:
    dest_folder = DIR

for f in DATA_FOLDERS:
    if os.path.isdir(os.path.join(dest_folder, f)):
        shutil.rmtree(os.path.join(dest_folder, f))
    shutil.copytree(f, os.path.join(dest_folder, f))

for f in DATA_FILES:
    shutil.copy(f, dest_folder)


########################################################################
################################ Cleanup ###############################
########################################################################
print('>> Cleaning up...')

# On macOS, there's a second "reggie" executable for some reason,
# separate from the app bundle. I don't know why it's there, but we
# delete it.

if sys.platform == 'darwin':
    leftover_executable = os.path.join(DIR, SCRIPT_FILE.split('.')[0])
    if os.path.isfile(leftover_executable):
        os.unlink(leftover_executable)


########################################################################
################################## End #################################
########################################################################
print('>> %s has been built to the %s folder!' % (PROJECT_NAME, DIR))