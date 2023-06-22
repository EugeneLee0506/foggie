'''
Filename: my_first_foggie_script.py
Author: Cassi, modified by Ayan
Description: This basic script demonstrates how to load in a FOGGIE simulation output and make some
simple plots to visualize the data.
Date created: 6/8/21
Last modified: 6/5/23
Dependencies:
yt
foggie
'''

# First, import all python packages needed for simulation analysis and visualization
import numpy as np              # numpy is a general-purpose math package
import yt                       # yt is the data vizualization package
from yt.units import *          # this lets you get things like speed of light in proper units just by typing 'c'
from astropy.table import Table # this is needed for reading in various foggie data byproducts
from astropy.io import ascii    # this too
import matplotlib.pyplot as plt # this is the standard python plotting package, very useful!

# These imports are FOGGIE-specific files
from foggie.utils.consistency import *
from foggie.utils.foggie_load import *


### NEED TO CHANGE THESE BEFORE THIS SCRIPT WILL RUN!!!! ###
# Specify the paths to the code and the simulation output. I've left in my own paths, change them to yours!
# foggie_dir should be the path to the directory where you've placed the simulation output, the DD2427 folder.
foggie_dir = "/Users/hylee/foggie/foggie_sims/halo_008508/nref11c_nref9f/"
# code_path should be the path to the directory where you've cloned the github repo.
code_path = "/Users/hylee/coding/foggie/foggie/"
# Finally, this is the name of the simulation output.
snap = 'RD0030'

foggie_dir_output = "/Users/hylee/foggie/foggie_output/halo_008508/nref11c_nref9f/"


### END OF THINGS YOU NEED TO CHANGE ###




# These next two point to a specific place within the codebase. Leave these for now.
track_dir = code_path + 'halo_infos/008508/nref11c_nref9f/'
track_name = code_path + 'halo_tracks/008508/nref11n_selfshield_15/halo_track_200kpc_nref9'
# This puts together all the paths to get the full path to the simulation output that the code needs
snap_name = foggie_dir + snap + '/' + snap

# Now load in the simulation output. If you've looked at the yt documentation, you'll notice this looks
# very similar to the 'ds = yt.load(..)' step there. We wrote our own version of the load function
# designed just for FOGGIE, so you'll want to use this instead.
ds, refine_box = foggie_load(snap_name, track_name, halo_c_v_name=track_dir + 'halo_c_v',
                             disk_relative=False, do_filter_particles=False, masses_dir=track_dir)
# Now you have the full simulation dataset loaded into 'ds', and a small region of the dataset near
# the galaxy loaded into 'refine_box'.

# We can plot the gas density in the simulation using yt's ProjectionPlot function:
proj = yt.ProjectionPlot(ds, "x", "density", center=ds.halo_center_kpc, width=(200., 'kpc'), data_source=refine_box)
# This tells yt to make a projection of the field "density" in the x-direction, using the dataset 'ds',
# centered on 'ds.halo_center_kpc', with a width of the view window of 200 kiloparsecs, and to restrict
# what's plotted to only the subset of the dataset in 'refine_box'. 'ds.halo_center_kpc' is a variable
# that gives the location of the center of the galaxy. The whole simulation dataset is enormous,
# so you'll need that to find where the galaxy is to plot it! Try changing "x" to "y" or "z"
# instead to see the galaxy from different angles. Try changing the width from 200 to 100 or 50 to zoom in.

# With the projection plot made, we can now modify some things that will be useful to know.
proj.set_unit('density', 'Msun/pc**2')           # change the units of the density to solar masses per square parsec
proj.set_cmap('density', density_color_map)      # change the color map used
proj.set_zlim('density', density_proj_min, density_proj_max)  # change the minimum and maximum on the density scale
# In the above, 'density_color_map', 'density_proj_min', and 'density_proj_max' are all variables
# defined in foggie/utils/consistency.py. You can use them here because you imported it up above.

# Now let's save the plot so that we can look at it!
proj.save(foggie_dir_output + snap + '/' + snap+ '_density_projection.png')

# You can put any filename you want, and even save as a .pdf or .jpg instead of .png.

# Now let's try a temperature projection:
proj = yt.ProjectionPlot(ds, "x", "temperature", center=ds.halo_center_kpc, width=(200., 'kpc'), data_source=refine_box,
                         weight_field="density")
# Notice the additional argument "weight_field". This will make a projection of gas temperature weighted
# by gas density.
proj.set_cmap('temperature', temperature_color_map)
proj.set_zlim('temperature', temperature_min, temperature_max)
proj.save(foggie_dir_output + snap +'/' + snap+'_temperature_projection.png')

# One more: metallicity! The "metallicity" field will be very important for your project:
proj = yt.ProjectionPlot(ds, "x", "metallicity", center=ds.halo_center_kpc, width=(200., 'kpc'), data_source=refine_box,
                         weight_field="density")
# Notice the additional argument "weight_field". This will make a projection of gas temperature weighted
# by gas density.
proj.set_cmap('metallicity', metal_color_map)
proj.set_zlim('metallicity', metal_min, metal_max)
proj.save(foggie_dir_output + snap + '/' +snap +'_metallicity_projection.png')

# Try some of your own simple plots using the yt cookbook and play around with it!
# (Skip the parts of the yt documentation where they use yt.load(), and use our own custom-made
# foggie_load() like at the beginning of this script)
# https://yt-project.org/doc/cookbook/simple_plots.html
