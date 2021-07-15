##!/usr/bin/env python3

"""

    Title :      plot_metallicity_evolution
    Notes :      To TRACK ambient gas metallicity around young (< 10Myr) stars as function of redshift, write to file, and plot
    Input :      txt file with all young star properties for each snapshot of each halo (generated by filter_star_properties.py)
    Output :     One pandas dataframe per halo as a txt file (Or fits file?)
    Author :     Ayan Acharyya
    Started :    July 2021
    Example :    run plot_metallicity_evolution.py --system ayan_hd --halo 8508 --saveplot

"""
from header import *
from util import *
from track_metallicity_evolution import *
from mpl_toolkits.axes_grid1 import make_axes_locatable

# ----------------------------------------------------------------------------------
def plot_median_metallicity(z_arr, Z_arr, ax, args, color=['salmon', 'brown']):
    '''
    Function to plot the metallicity evolution
    '''
    median_arr, low_arr, up_arr, len_arr = [], [], [], []
    for thisZ in Z_arr:
        median_arr.append(np.median(thisZ))
        low_arr.append(np.percentile(thisZ, 16))
        up_arr.append(np.percentile(thisZ, 84))
        len_arr.append(len(thisZ))

    ax.fill_between(z_arr, low_arr, up_arr, color=color[0], lw=0.5, alpha=0.7)
    ax.plot(z_arr, median_arr, color=color[1], lw=1)

    ax.set_xlabel('Redshift', fontsize=args.fontsize)
    ax.set_xticklabels(['%.1F'%item for item in ax.get_xticks()], fontsize=args.fontsize)
    ax.set_xlim(z_min, z_max)
    ax.set_xlim(ax.get_xlim()[::-1])

    ax.set_ylabel(r'Metallicity (Z/Z$_\odot$)', fontsize=args.fontsize)
    ax.set_yticks(np.linspace(Z_min, Z_max, 5))
    ax.set_yticklabels(['%.1F'%item for item in ax.get_yticks()], fontsize=args.fontsize)
    ax.set_ylim(Z_min, Z_max)

    # plotting number of star-particles as function of redshift
    ax2 = ax.twinx()
    ax2.plot(z_arr, np.log10(len_arr), color='k', lw=1, ls='dashed')
    ax2.set_ylabel('log (# of stars)', fontsize=args.fontsize/1.5)
    ax2.set_yticklabels(['%.1F'%item for item in ax2.get_yticks()], fontsize=args.fontsize/1.5)

    return ax

# ---------------------------------------------------------------------------------
def make_heatmap(heat_arr, z_arr, ax, cmap='viridis', nybins=40, clabel='Metallicity PDF', nzbins=10):
    '''
    Function to actually plot the heatmap and fine polish axes labels, etc.
    :return: ax of the plot
    '''
    global z_max, z_min
    if z_max is None: z_max = z_arr[0]
    if z_min is None: z_min = z_arr[-1]
    uniform_z_arr = np.linspace(z_max, z_min, nzbins)
    bin_index = np.digitize(z_arr, uniform_z_arr)

    heatmap = np.zeros((np.shape(heat_arr)[0], nzbins))
    for index in range(nzbins):
        heatmap[:, index] = np.mean(heat_arr[:, bin_index == index], axis=1)
        heatmap[:, index] /= np.sum(heatmap[:, index])

    im = ax.imshow(heatmap, cmap=cmap, aspect='auto', origin='lower', extent=(0, nzbins, 0, np.shape(heatmap)[0])) # extent = (left, right, bottom, top) in data coordinates

    ax.grid(False)
    nxticks = 5
    x_tick_arr = np.array([int(item) for item in np.linspace(0, nzbins - 1, nxticks)])
    ax.set_xticks(x_tick_arr + 0.5)

    ax.set_xticklabels(['%.1F'%uniform_z_arr[item] for item in x_tick_arr], fontsize=args.fontsize)
    ax.set_xlabel('Redshift', fontsize=args.fontsize)

    y_tick_arr = np.linspace(Z_min, Z_max, 5)
    ax.set_yticks(np.linspace(0, nybins, len(y_tick_arr)))
    ax.set_yticklabels(['%.1F'%item for item in y_tick_arr], fontsize=args.fontsize)

    fig = plt.gcf()
    divider = make_axes_locatable(ax)
    cax = divider.new_horizontal(size='5%', pad=0.05)
    fig.add_axes(cax)
    cb = plt.colorbar(im, cax=cax, orientation='vertical')
    cb.ax.set_ylabel(clabel, fontsize=args.fontsize/1.5)

    return ax

# ----------------------------------------------------------------------------------
def plot_metallicity_heatmap(z_arr, Z_arr, axes, args, weight_arr=None):
    '''
    Function to plot the metallicity evolution
    '''
    if args.weight is None: ax1 = axes[0]
    else: ax1, ax2, ax3 = axes

    Zhist_arr = []
    if weight_arr is not None: mhist_arr, mchist_arr = [], []

    for index, thisZ in enumerate(Z_arr):
        myprint('Preparing histogram/s ' + str(index + 1) + ' of ' + str(len(Z_arr)) + '..', args)
        thisweight = weight_arr[index] if args.weight is not None else None
        Zhist, bin_edges = np.histogram(thisZ, bins=40, range=(Z_min, Z_max), density=True, weights=thisweight)
        Zhist = Zhist / np.max(Zhist) # to make sure max = 1, so that all redshifts get equal weightage visually
        Zhist_arr.append(Zhist)

        if args.weight is not None:
            bin_index = np.digitize(thisZ, bin_edges)
            mhist = np.array([np.array(thisweight)[bin_index == ii].sum() for ii in range(1, len(bin_edges) + 1)])
            mhist /= np.sum(mhist)
            mchist = np.cumsum(mhist)
            mhist_arr.append(mhist)
            mchist_arr.append(mchist)

    Zhist_arr = np.transpose(np.array(Zhist_arr))
    ax1 = make_heatmap(Zhist_arr, z_arr, ax1, nybins=len(bin_edges) - 1, clabel='Metallicity PDF' if args.weight is None else args.weight + '-weighted metallicity PDF', nzbins=args.nzbins)
    if args.weight is not None:
        mhist_arr = np.transpose(np.array(mhist_arr))
        mchist_arr = np.transpose(np.array(mchist_arr))
        ax2 = make_heatmap(mhist_arr, z_arr, ax2, nybins=len(bin_edges) - 1, clabel='Fraction of ' + args.weight + ' entrained', nzbins=args.nzbins)
        ax3 = make_heatmap(mchist_arr, z_arr, ax3, nybins=len(bin_edges) - 1, clabel='Cumulative fraction of ' + args.weight + ' entrained', nzbins=args.nzbins)

    return axes

# -----------------------------------------------------------------------------------
if __name__ == '__main__':
    start_time = time.time()

    args = parse_args('8508', 'RD0042', fast=True)
    if type(args) is tuple: args = args[0] # if the sim has already been loaded in, in order to compute the box center (via utils.pull_halo_center()), then no need to do it again
    if not args.keep: plt.close('all')

    if args.do_all_halos: list_of_halos = get_all_halos(args)
    else: list_of_halos = [args.halo]

    z_min, z_max = None, None #0, 0.8
    Z_min, Z_max = 0, 4
    color_arr = [['salmon', 'brown'], ['lightgreen', 'darkgreen'], ['silver', 'black'], ['paleturquoise', 'lightseagreen'], ['pink', 'crimson'], ['wheat', 'orange']]

    # ----------looping over halos----------------------
    for index, this_halo in enumerate(list_of_halos):
        myprint('Plotting halo ' + this_halo + '; ' + str(index+1) + ' of ' + str(len(list_of_halos)), args)
        args.halo = this_halo
        foggie_dir, output_dir, run_loc, code_path, trackname, haloname, spectra_dir, infofile = get_run_loc_etc(args)

        infilename = output_dir + 'txtfiles/' + args.halo + '_Z_vs_z_allsnaps.txt'

        if not os.path.exists(infilename):
            myprint(infilename + ' does not exist; calling assimilate_this_halo()..', args)
            z_arr, Z_arr, m_arr = assimilate_this_halo(args)
        else:
            z_arr, Z_arr, m_arr = read_list_file(infilename, args)
        m_arr = [x for _, x in sorted(zip(z_arr, m_arr), key=lambda x: x[0], reverse=True)]
        Z_arr = [x for _, x in sorted(zip(z_arr, Z_arr), key=lambda x: x[0], reverse=True)]
        z_arr = sorted(z_arr, reverse=True)

        if args.weight is None:
            fig, axes = plt.subplots(1, 2, figsize=(10, 4))
            fig.subplots_adjust(top=0.95, left=0.1, right=0.9, bottom=0.15)
        else:
            fig, axes = plt.subplots(1, 4, figsize=(20, 4))
            fig.subplots_adjust(top=0.95, left=0.05, right=0.95, bottom=0.15, wspace=0.5)

        axes[0] = plot_median_metallicity(z_arr, Z_arr, axes[0], args, color=color_arr[index])
        axes[1:] = plot_metallicity_heatmap(z_arr, Z_arr, axes[1:], args, weight_arr=m_arr)
        fig.text(0.15 if args.weight is None else 0.1, 0.85, halo_dict[args.halo], color='black', ha='left', va='top', fontsize=args.fontsize)

        plt.show(block=False)

        if args.saveplot:
            fig_output_dir = output_dir + 'figs/'
            weight_text = '_weighted_by_' + args.weight if args.weight is not None else ''
            saveplot(fig, args, halo_dict[args.halo] + '_Z_vs_z' + weight_text, outputdir=fig_output_dir)

    myprint('All halos done in %s minutes' % ((time.time() - start_time) / 60), args)