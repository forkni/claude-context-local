---
category: PY
document_type: guide
difficulty: intermediate
time_estimate: 15-25 minutes
operators:
- Execute_DAT
- Text_DAT
concepts:
- python_environment_management
- package_management
- dependency_management
- third_party_library_integration
- conda_environments
prerequisites:
- PY_Python_in_Touchdesigner
- command_line_basics
workflows:
- machine_learning_integration
- 3d_data_processing
- advanced_scripting_setup
- external_library_usage
keywords:
- anaconda
- miniconda
- conda
- install python packages
- third-party libraries
- python environment
- package manager
- scikit-learn
- open3d
- sys.path
- dependency management
- pip
- conda env
tags:
- python
- anaconda
- conda
- pip
- environment
- windows
- macos
- dependencies
- libraries
- setup
relationships:
  PY_Python_in_Touchdesigner: strong
  CLASS_ExecuteDAT_Class: strong
related_docs:
- PY_Python_in_Touchdesigner
- CLASS_ExecuteDAT_Class
hierarchy:
  secondary: environment_setup
  tertiary: anaconda_integration
question_patterns:
- Python scripting in TouchDesigner?
- How to use Python API?
- Scripting best practices?
- Python integration examples?
common_use_cases:
- machine_learning_integration
- 3d_data_processing
- advanced_scripting_setup
- external_library_usage
---

# ANACONDA - MANAGING PYTHON ENVIRONMENTS AND 3RD-PARTY LIBRARIES IN TOUCHDESIGNER

<!-- TD-META
category: PY
document_type: guide
operators: [Execute_DAT, Text_DAT]
concepts: [python_environment_management, package_management, dependency_management, third_party_library_integration, conda_environments]
prerequisites: [PY_Python_in_Touchdesigner, command_line_basics]
workflows: [machine_learning_integration, 3d_data_processing, advanced_scripting_setup, external_library_usage]
related: [PY_Python_in_Touchdesigner, CLASS_ExecuteDAT_Class]
relationships: {
  "PY_Python_in_Touchdesigner": "strong",
  "CLASS_ExecuteDAT_Class": "strong"
}
hierarchy:
  primary: scripting
  secondary: environment_setup
  tertiary: anaconda_integration
keywords: [anaconda, miniconda, conda, install python packages, third-party libraries, python environment, package manager, scikit-learn, open3d, sys.path, dependency management, pip, conda env]
tags: [python, anaconda, conda, pip, environment, windows, macos, dependencies, libraries, setup]
TD-META -->

## 🎯 Quick Reference

**Purpose**: Python scripting guide for TouchDesigner automation
**Difficulty**: Intermediate
**Time to read**: 15-25 minutes
**Use for**: machine_learning_integration, 3d_data_processing, advanced_scripting_setup

**Common Questions Answered**:

- "Python scripting in TouchDesigner?" → [See relevant section]
- "How to use Python API?" → [See relevant section]
- "Scripting best practices?" → [See relevant section]
- "Python integration examples?" → [See relevant section]

## 🔗 Learning Path

**Prerequisites**: [Py Python In Touchdesigner] → [Command Line Basics]
**This document**: PY reference/guide
**Next steps**: [PY Python in Touchdesigner] → [CLASS ExecuteDAT Class]

**Related Topics**: machine learning integration, 3d data processing, advanced scripting setup

## Summary

Guide for managing Python environments and third-party libraries in TouchDesigner using Anaconda, including environment creation, package installation, and integration with TouchDesigner.

## Relationship Justification

Strong connection to Python environment management as the primary topic. Links to related articles for specific OPs that utilize Python environments.

## Content

- [Overview](#overview)
- [What is Conda / Anaconda?](#what-is-conda--anaconda)
- [Setup](#setup)
- [Install Additional Packages](#install-additional-packages)
- [Link Environment to TouchDesigner](#link-environment-to-touchdesigner)
- [A note for MacOS users](#a-note-for-macos-users)
- [Conclusion](#conclusion)

## Overview

It has been quite a few times that I see on the Derivative forum or on social networks, cases
where users are struggling with third party Python libraries / packages integration in
TouchDesigner. While you should not consider the following example the ultimate solution, it
saved me quite a few times and Anaconda is a nice tool to use even outside of the
TouchDesigner context.

Important note: When adding your own version for a package that is already shipped with
TouchDesigner, you might encounter unexpected behaviors.Many of our internal tools and
palette components rely on NumPy and/or OpenCV. Loading different versions of Numpy
and/or OpenCV is at your own risk. Some other issue could be with the following:
considering a Package A with a dependency B, if updating your sys.path cause a different
version of dependency B to load first, it could cause issues with Package A.

## WHAT IS CONDA / ANACONDA?

Conda is a cross-platform, language-agnostic binary package manager. It is the package
manager used by Anaconda installations, but it may be used for other systems as well.
Conda makes environments first-class citizens, making it easy to create independent
environments even for C libraries. Conda is written entirely in Python, and is BSD licensed
open source.
As per
WHAT IS THE DIFFERENCE BETWEEN ANACONDA AND MINICONDA?
Miniconda is a free minimal installer for conda. It is a small, bootstrap version of
Anaconda that includes only conda, Python, the packages they depend on, and a small
number of other useful packages, including pip, zlib and a few others.

## SETUP

For the sake of this tutorial, at the time of writing (06 16 2021), the version used are:
<https://github.com/conda/conda> (<https://github.com/conda/conda>)
<https://docs.conda.io/en/latest/miniconda.html>
(<https://docs.conda.io/en/latest/miniconda.html>)
TouchDesigner 2021.13610, the latest stable release
Anaconda install is Anaconda3-2021.05-Windows-x86_64 Python 3.8 Win 10 64-bit
Windows 10 64-bit

INSTALL ANACONDA
The install is fairly straightforward. For the sake of that example, we will do a vanilla install of
the latest version of Anaconda (Windows64-bit) in a fairly vanilla environment, meaning: no
local Python installation, no changes, no previous installation of Anaconda or other things. It’s a
pretty clean environment.
First, head to the Miniconda documentation
or the Anaconda (full installer)
.
What you’ll want is to download the installer for Windows / Mac, preferably in 64-bit and
(important) w/ Python 3.x. The latest builds of either Anaconda or Miniconda 3 should all be
coming with Python 3.8 by default.
page
(<https://docs.conda.io/en/latest/miniconda.html>) page
(<https://www.anaconda.com/products/individual>)
(<https://derivative.ca/sites/default/files/styles/content_colorbox/public/field/body-images/condaDownload..png>)

Once the installer is downloaded, start the installation, and go through the install steps. You can
keep all the default recommended choices.
You are done with the installation, let’s check that everything is installed and running correctly.
CONFIRM INSTALLATION
The screenshot above is showing the Miniconda download page, where Python 3.8, Windows 64 Bits installer would be
selected.
(<https://derivative.ca/sites/default/files/styles/content_colorbox/public/field/body->
images/condaDownloadBis.png)

In Windows, launch the app Anaconda Prompt (anaconda3).
If the installation went through properly, it will be here and ready to be used. Launch it. And
you’ll see the following window (or similar).
Let’s go over this screenshot and a basic conda command.
In the terminal, you see (base) which is here to remind you which environment of conda is
currently the active environment. Followed by your user path.
(<https://derivative.ca/sites/default/files/styles/content_colorbox/public/field/body->
images/Screenshot%202021-01-29%20165211.png)

The first command we’ll learn is conda env list which is pretty self-explanatory, it will list
your environments.
(<https://derivative.ca/sites/default/files/styles/content_colorbox/public/field/body->
images/Screenshot%202021-01-29%20165442.png)

You should get a result similar to the screenshot above, where the star * before the path is the
currently active environment.
If you get a similar result, we are good to go.
CREATE AN ENVIRONMENT
Alright, our first big step! Congrats for making it here!
We will now create an environment that will be TouchDesigner friendly. You’ll see, it’s pretty
easy.
First, launch TouchDesigner.
(<https://derivative.ca/sites/default/files/styles/content_colorbox/public/field/body->
images/Screenshot%202021-01-29%20165722.png)

You want to know which version of Python TouchDesigner is currently using so that you can
match this version in your conda environment.
To do so, use Alt+T in TouchDesigner, which will open your textport.
You’ll see the following window.
You can read on the second line that the Python version currently used by TouchDesigner is
Python 3.7.2.
We will match this version.
Now, go back to the conda command prompt and type:
(<https://derivative.ca/sites/default/files/styles/content_colorbox/public/field/body->
images/Screenshot%202021-01-29%20170559.png)

conda create -n td-demo python=3.7.2
Where:
conda - the shortcut/context for Anaconda
create - self-explanatory, to create an environment
-n - for the name of the environment followed by your new environment name, with no space,
here “td-demo”
python= - to force a python install in the version matching TouchDesigner, 3.7.2 in our case
I like to name my TouchDesigner environments with “td-” since I work a lot with Anaconda,
sometimes outside of the TouchDesigner context. It helps me avoid using an environment for,
let’s say, Tensorflow, and using that same environment in the td- context w/ a bunch of other
packages that might cause issues with a side project or just be confusing.
This is quite important because environments/environment management is one of the great
features of Anaconda. And you want to avoid messing with your TouchDesigner local python
installation or using a conda environment with a Python version that doesn’t match
TouchDesigner.
Once you type the command, press enter, it might take a little while.
You’ll see the following lines (or similar) printing in the command prompt.

It is the default wheels and binaries for the conda environment to run in Python 3.7.2. You can
press y to proceed.
Conda will download and install all the packages in your new environment.
Once the downloads and installation are done, you’ll see the following (or similar).
(<https://derivative.ca/sites/default/files/styles/content_colorbox/public/field/body->
images/Screenshot%202021-01-29%20171922.png)

ACTIVATE (MOVE TO) AN ENVIRONMENT
As it is stated in the screenshot above, you can now use the command conda activate td-
demo to move to this newly created environment.
Where activate is the action and td-demo the environment we want to move to. You should
now see at the front of the line (td-demo) which means you are in your new environment.
Congrats!

## INSTALL ADDITIONAL PACKAGES

For the sake of this tutorial, we are going to install 2 main packages.
(<https://derivative.ca/sites/default/files/styles/content_colorbox/public/field/body->
images/CondaActivate.png)

The first one is sckikit-learn. A recent question in the forum made me go through these exact
same steps to debug a user issue, and it was extremely easy to get scikit up and running in
TouchDesigner with conda. The second one is open3d, which was introduced by Darien Brito
recently, in his Kinect Azure Point Cloud merger.
Let’s go through the steps on how to install those packages.
Most of the time, typing conda install packagename will work. But a good source to find
packages, package names and versions is to go to the central repository on
Note: pip does come with Anaconda, if a package is missing from the Anaconda package
repository, you can still use pip with the more traditional pip install packagename . It will still
install the package, using pip this time, but as part of your Anaconda environment.
Let’s look for Scikit, and we can easily find out that the command we are looking for is conda
install scikit-learn
You can now type the following in your conda command prompt, and conda will look for all the
required wheels and binaries for scikit-learn to run properly, in your current environment and on
Python 3.7.2.
You should see the following
<https://anaconda.org/> (<https://anaconda.org/>)

You can press y to install the extra packages.
Now, let’s do the same with open3d. On anaconda.org, we can find that the command to use is
conda install -c open3d-admin open3d
Let’s type that and press enter in our conda command prompt.
You should see quite the list of additional packages and dependencies. If you don’t need
open3d, you can press n , else, process with the install and press y .
(<https://derivative.ca/sites/default/files/styles/content_colorbox/public/field/body->
images/Screenshot%202021-01-29%20174231.png)

Additionally, you can use the command conda list within your environment to list all the
packages installed.

## LINK ENVIRONMENT TO TOUCHDESIGNER

Welcome to the TouchDesigner side, it might sound tricky, but it’s actually fairly straightforward
here.
Open your TouchDesigner project.
In this project, you will create an Execute DAT and toggle on the “Start” toggle parameter.
What we want to do next, on startup, ensure that the site-packages of our conda environment
are added to the path of TD and packages binaries / libs / dlls.
First, let’s type in the Anaconda command prompt the command we used earlier
conda env list
Remember? It’s listing the environments and paths of each environment.

Look for your newly created environment, or the active (the one with a star *) environment you
want to add to TouchDesigner.
Write down the path, if your install is using default settings, it should be something like
C:/Users/YOUR_USERNAME/miniconda3/envs/YOUR_ENVIRONMENT_NAME
In our case, if you are following this tutorial, the environment name should be td-demo
Back to TouchDesigner, at the top of the Execute DAT, replace the onStart() method with the
following code
(<https://derivative.ca/sites/default/files/styles/content_colorbox/public/field/body->
images/Screenshot%202021-01-31%20135525.png)

Note: Double check all the paths used in the code snippet, it could be that your anaconda 'envs'
folder is not in your User folder depending on your conda install settings and conda version, as
well as your OS.
import sys
import os
import platform
def onStart():
user = 'YOUR_USERNAME' # Update accordingly
condaEnv = 'YOUR_ENVIRONMENT_NAME' # Update accordingly
if platform.system() == 'Windows':
if sys.version_info.major >= 3 and sys.version_info.minor >= 8:
"""
Double check all the following paths, it could be that your anaconda 'envs' fol
"""
os.add_dll_directory('C:/Users/'+user+'/miniconda3/envs/'+condaEnv+'/DLLs')
os.add_dll_directory('C:/Users/'+user+'/miniconda3/envs/'+condaEnv+'/Library/bi
else:
"""
Double check all the following paths, it could be that your anaconda 'envs' fol
"""

# Not the most elegant solution, but we need to control load order

os.environ['PATH'] = 'C:/Users/'+user+'/miniconda3/envs/'+condaEnv+'/DLLs' + os
os.environ['PATH'] = 'C:/Users/'+user+'/miniconda3/envs/'+condaEnv+'/Library/bi
sys.path = ['C:/Users/'+user+'/miniconda3/envs/'+condaEnv+'/Lib/site-packages'] + sys.p
else:
"""
MacOS users should include path to .dlybs / MacOS binaries, site-packages
"""
os.environ['PATH'] = '/Users/'+user+'/opt/miniconda3/envs/'+condaEnv+'/lib' + os.pathse
os.environ['PATH'] = '/Users/'+user+'/opt/miniconda3/envs/'+condaEnv+'/bin' + os.pathse

# The following path might need editing (python3.9) based on the python version used wi

sys.path = ['/Users/'+user+'/opt/miniconda3/envs/'+condaEnv+'/lib/python3.9/site-packag
return

Where:
You can now either save your project and restart or simply pulse the pulse button of the Start
parameter of the Execute DAT.
YOUR_WINDOWS_USERNAME should be the name of your user folder, found in C:/Users/
YOUR_ENVIRONMENT_NAME should be td-demo if you are following this tutorial.
(<https://derivative.ca/sites/default/files/styles/content_colorbox/public/field/body-images/Screenshot%202021->
01-31%20142033.png)

Important: Some of the code pictured above takes into account a future version of
TouchDesigner which will be shipped with Python 3.9+. For Windows user, Python 3.8 brought
os.add_dll_directory() which is quite handy in our use case, but not yet available in Python
3.7.2 at the time of writing of this article.

## A note for MacOS users

To know where is your Anaconda environment, as per Anaconda’s official doc:

1. Open a terminal window.
2. If you want the location of a Python interpreter for a conda environment other than the root
conda environment, run conda activate environment-name .
3. Run which python .
In the same terminal, you can type python , and import a package such as import numpy if you
installed numpy in that environment. Typing numpy , it will print out where was numpy imported
from and show the site-packages folder location, within your Anaconda environment folder.
IMPORTANT: You might encounter issues if you are on an M1 Mac, and run different
architectures. If you are running the native ARM build of TouchDesigner, your Anaconda install,
Anaconda environment and libraries should all be the native ARM versions as well. More details
are available with documentation for Homebrew here:
USE YOUR PACKAGES (AND ENVIRONMENT) IN TOUCHDESIGNER
You should now be able to import the packages you installed using conda. Let’s make sure of it.
In TouchDesigner, press Alt+t to open the textport.
Starting with scikit-learn, type import sklearn and press enter. If the command goes through
without error, it means sklearn was imported with success.
You can make sure by typing sklearn.**file** which should point to the **init**.py of
sklearn or sklearn.**version** which should print the same version that the Anaconda
command prompt was listing.
Category:Python - Derivative
(<https://docs.derivative.ca/Category:Python#Installing_Custom_Python_Packages>)

If you installed open3d as well, you can proceed with the same command import open3d . If the
command goes through without error.
You can now use those packages in TouchDesigner, congratulations!
If an issue occurs, it can be due to a large number of factors. I would recommend first to go
back to your environment in the conda command prompt and type python -c “import
sklearn” , if the command is working without issues, then an issue occurred while linking your
conda environment to TouchDesigner.

## CONCLUSION

You now have a basic introduction to Anaconda and a simple integration in TouchDesigner. It
should help unlock access to a few interesting projects with all the great libraries that come out
from the Python community. I hope that this tutorial helped and that you were able to go
through it without issues. If you have any questions, comments, points to add, please leave a
comment and I will try to answer accurately and update this tutorial if necessary!
