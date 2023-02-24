#!/usr/bin/env python3

"""

    Title :      datashader_singleplot
    Notes :      To make a single datashader plot of 3 given quantities from a given dataframe
    Output :     datashader plot as png file
    Author :     Ayan Acharyya
    Started :    Feb 2023
    Examples :   run datashader_singleplot.py --filename /Users/acharyya/Downloads/Tempest_RD0042_age_circ_rad.csv --galrad 20 --xcol vrad --xmin -400 --xmax 500 --ycol metal --ymin -4 --ymax 1 --colorcol phi_disk --cmin 0 --cmax 180 --cmap viridis --ncolbins 7

"""
from header import *
from util import *
yt_ver = yt.__version__
start_time = time.time()

# ---------------------------------------------------------------------------------
def plot_1D_histogram(data, data_min, data_max, ax, vertical=False):
    '''
    Function to plot marginalised histograms using seaborn
    '''
    sns.kdeplot(data, ax=ax, legend=False, lw=1, vertical=vertical, color='k')
    ax.tick_params(axis='x', which='both', top=False)
    if vertical: ax.set_ylim(data_min, data_max)
    else: ax.set_xlim(data_min, data_max)

    return ax

# ---------------------------------------------------------------------------------
def make_coordinate_axis(colname, data_min, data_max, ax, fontsize):
    '''
    Function to make the coordinate axis
    Uses globally defined islog_dict and unit_dict
    '''
    log_text = 'Log ' if islog_dict[colname]else ''
    unit_text = '' if unit_dict[colname] == '' else ' (' + unit_dict[colname] + ')'
    ax.set_label_text(log_text + labels_dict[colname] + unit_text, fontsize=fontsize)

    nticks = 5
    ticks = np.linspace(data_min, data_max, nticks)
    ax.set_ticks(ticks)

    nticklabels = 5
    ticklabels = np.array(['     '] * nticks)
    ticklabel_every = int(nticks/nticklabels)
    ticklabels[:: ticklabel_every] = ['%.1F' % item for item in ticks[:: ticklabel_every]]

    ax.set_ticklabels(ticklabels, fontsize=fontsize)

    return ax

# ---------------------------------------------------------------------------------
def make_colorbar_axis_mpl(colname, artist, fig, fontsize):
    '''
    Function to make the colorbar axis
    Uses globally defined islog_dict and unit_dict
    Different from make_colorbar_axis() because this function uses native matplotlib support of datashader
    '''
    cax_xpos, cax_ypos, cax_width, cax_height = 0.7, 0.835, 0.25, 0.035
    cax = fig.add_axes([cax_xpos, cax_ypos, cax_width, cax_height])
    plt.colorbar(artist, cax=cax, orientation='horizontal')

    cax.set_xticklabels(['%.0F' % index for index in cax.get_xticks()], fontsize=fontsize / 1.5)  # , weight='bold')

    log_text = 'Log ' if islog_dict[colname] else ''
    fig.text(cax_xpos + cax_width / 2, cax_ypos + cax_height + 0.005, log_text + labels_dict[colname] + ' (' + unit_dict[colname] + ')', fontsize=fontsize/1.5, ha='center', va='bottom')

    return fig, cax

# --------------------------------------------------------------------------------
def make_datashader_plot_mpl(df, outfilename, args):
    '''
    Function to make data shader plot of y_field vs x_field, colored in bins of color_field
    This function is based on foggie.render.shade_maps.render_image()
    This is different from make_datashader_plot() in that this function uses the newest version of datashader which has matplotlib support
    So this function essentially combines make_datashader_plot() and wrap_axes(), because the latter is not needed anymore
    :return dataframe, figure
    '''
    # ----------to filter and categorize the dataframe--------------
    df = df[(df[args.xcolname].between(args.xmin, args.xmax)) & (df[args.ycolname].between(args.ymin, args.ymax)) & (df[args.colorcolname].between(args.cmin, args.cmax))]

    # -----------------to initialise figure---------------------
    if args.plot_hist:
        axes = sns.JointGrid(args.xcolname, args.ycolname, df, height=8)
        plt.subplots_adjust(hspace=0.05, wspace=0.05, right=0.95, top=0.95, bottom=0.1, left=0.15)
        fig, ax1 = plt.gcf(), axes.ax_joint
    else:
        fig, ax1 = plt.subplots(1, figsize=(8, 8))
        fig.subplots_adjust(top=0.95, bottom=0.1, left=0.15, right=0.95)

    # --------to make the main datashader plot--------------------------
    color_key = [to_hex(item) for item in args.color_list]
    artist = dsshow(df, dsh.Point(args.xcolname, args.ycolname), dsh.mean(args.colorcolname), norm='linear', cmap=color_key, x_range=(args.xmin, args.xmax), y_range=(args.ymin, args.ymax), vmin=args.cmin, vmax=args.cmax, aspect = 'auto', ax=ax1) #, shade_hook=partial(dstf.spread, px=1, shape='square')) # the 40 in alpha_range and `square` in shade_hook are to reproduce original-looking plots as if made with make_datashader_plot()

    # ----------to plot 1D histogram on the top and right axes--------------
    if args.plot_hist:
        axes.ax_marg_x = plot_1D_histogram(df[args.xcolname], args.xmin, args.xmax, axes.ax_marg_x, vertical=False)
        axes.ax_marg_y = plot_1D_histogram(df[args.ycolname], args.ymin, args.ymax, axes.ax_marg_y, vertical=True)

    # ------to make the axes-------------
    ax1.xaxis = make_coordinate_axis(args.xcol, args.xmin, args.xmax, ax1.xaxis, args.fontsize)
    ax1.yaxis = make_coordinate_axis(args.ycol, args.ymin, args.ymax, ax1.yaxis, args.fontsize)

    # ------to make the colorbar axis-------------
    fig, ax2 = make_colorbar_axis_mpl(args.colorcol, artist, fig, args.fontsize)

    # ---------to annotate and save the figure----------------------
    filename = os.path.splitext(outfilename)[0] + '.png'
    plt.savefig(filename, transparent=False)
    myprint('Saved figure ' + filename, args)
    plt.show(block=False)

    return fig

# -------- set variables and dictionaries such that they are available to other scripts importing this script-----------
unit_dict = {'rad': 'kpc', 'radius': 'kpc', 'density': 'g/cm**3', 'metal': r'Zsun', 'temp': 'K', 'vrad': 'km/s', 'phi_L': 'deg',
             'theta_L': 'deg', 'PDF': '', 'mass': 'Msun', 'volume': 'pc**3', 'phi_disk': 'deg', 'theta_disk': 'deg', 'age':'Gyr', 'circularity':''}
labels_dict = {'rad': 'Radius', 'radius': 'Radius', 'density': 'Density', 'metal': 'Metallicity', 'temp': 'Temperature',
               'vrad': 'Radial velocity', 'phi_L': r'$\phi_L$', 'theta_L': r'$\theta_L$', 'PDF': 'PDF',
               'phi_disk': 'Azimuthal Angle', 'theta_disk': r'$\theta_{\mathrm{diskrel}}$', 'age':'Age', 'circularity': 'Circularity'}
islog_dict = defaultdict(lambda: False, metal=True, density=True, temp=True)
bin_size_dict = defaultdict(lambda: 1.0, metal=0.1, density=2, temp=1, rad=0.1, vrad=50)
colormap_dict = {'temp': temperature_discrete_cmap, 'metal': metal_discrete_cmap, 'density': density_discrete_cmap, 'vrad': outflow_inflow_discrete_cmap, \
                 'rad': radius_discrete_cmap, 'radius': radius_discrete_cmap, 'phi_L': angle_discrete_cmap_pi, 'circularity': 'viridis', \
                 'theta_L': angle_discrete_cmap_2pi, 'phi_disk': 'viridis', 'theta_disk': angle_discrete_cmap_2pi, 'age': tcool_discrete_cmap}
isfield_weighted_dict = defaultdict(lambda: False, metal=True, temp=True, vrad=True, phi_L=True, theta_L=True, phi_disk=True, theta_disk=True)
bounds_dict = defaultdict(lambda: None, density=(1e-31, 1e-21), temp=(1e1, 1e8), metal=(1e-3, 1e1), vrad=(-400, 400), phi_L=(0, 180), theta_L=(-180, 180), phi_disk=(0, 90), theta_disk=(-180, 180), age=(0, 14), circularity=(-1.6, 1.6))

# -----main code-----------------
if __name__ == '__main__':
    args_tuple = parse_args('8508', 'RD0042')  # default simulation to work upon when comand line args not provided
    # ------------------------------------------------------------------------------
    if type(args_tuple) is tuple:
        args, ds, refine_box = args_tuple  # if the sim has already been loaded in, in order to compute the box center (via utils.pull_halo_center()), then no need to do it again
        print_mpi('ds ' + str(ds) + ' for halo ' + str(args.output) + ' was already loaded at some point by utils; using that loaded ds henceforth', args)
    else:
        args = args_tuple
    args.colorcol = args.colorcol[0]

    args.xcolname = 'log_' + args.xcol if islog_dict[args.xcol] else args.xcol
    args.ycolname = 'log_' + args.ycol if islog_dict[args.ycol] else args.ycol
    args.colorcolname = 'log_' + args.colorcol if islog_dict[args.colorcol] else args.colorcol
    if isfield_weighted_dict[args.xcol] and args.weight: args.xcolname += '_wtby_' + args.weight
    if isfield_weighted_dict[args.ycol] and args.weight: args.ycolname += '_wtby_' + args.weight
    if isfield_weighted_dict[args.colorcol] and args.weight: args.colorcolname += '_wtby_' + args.weight

    # ----------to determine axes limits--------------
    bounds_dict.update(rad=(0, args.galrad), radius=(0, args.galrad))
    if args.xmin is None:
        args.xmin = np.log10(bounds_dict[args.xcol][0]) if islog_dict[args.xcol] else bounds_dict[args.xcol][0]
    if args.xmax is None:
        args.xmax = np.log10(bounds_dict[args.xcol][1]) if islog_dict[args.xcol] else bounds_dict[args.xcol][1]
    if args.ymin is None:
        args.ymin = np.log10(bounds_dict[args.ycol][0]) if islog_dict[args.ycol] else bounds_dict[args.ycol][0]
    if args.ymax is None:
        args.ymax = np.log10(bounds_dict[args.ycol][1]) if islog_dict[args.ycol] else bounds_dict[args.ycol][1]
    if args.cmin is None:
        args.cmin = np.log10(bounds_dict[args.colorcol][0]) if islog_dict[args.colorcol] else bounds_dict[args.colorcol][0]
    if args.cmax is None:
        args.cmax = np.log10(bounds_dict[args.colorcol][1]) if islog_dict[args.colorcol] else bounds_dict[args.colorcol][1]

    # ----------to determine colorbar parameters--------------
    if args.cmap is None:
        args.cmap = colormap_dict[args.colorcol]
    else:
        args.cmap = plt.get_cmap(args.cmap)
    color_list = args.cmap.colors
    ncol_bins = args.ncolbins if args.ncolbins is not None else len(color_list) if len(color_list) <= 10 else 7
    args.color_list = color_list[::int(len(color_list) / ncol_bins)]  # truncating color_list in to a length of rougly ncol_bins

    # ----------to labels and paths--------------
    outfile_rootname = 'datashader_boxrad_%.2Fkpc_%s_vs_%s_colby_%s.png' % (args.galrad, args.ycolname, args.xcolname, args.colorcolname)
    fig_dir = os.path.split(args.filename)[0] + '/'
    thisfilename = fig_dir + outfile_rootname

    # ----------to actually make the plot--------------
    if not args.keep: plt.close('all')

    df = pd.read_csv(args.filename, index_col=0)
    fig = make_datashader_plot_mpl(df, thisfilename, args)

    print_master('Completed in %s mins' % ((time.time() - start_time) / 60), args)
