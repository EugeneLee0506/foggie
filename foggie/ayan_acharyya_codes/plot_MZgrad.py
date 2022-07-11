#!/usr/bin/env python3

"""

    Title :      plot_MZgrad
    Notes :      Plot mass - metallicity gradient relation for a given FOGGIE galaxy
    Output :     M-Z gradient plots as png files plus, optionally, MZR plot
    Author :     Ayan Acharyya
    Started :    Mar 2022
    Examples :   run plot_MZgrad.py --system ayan_local --halo 8508,5036,5016,4123 --upto_re 3 --Zgrad_den rad_re --keep --weight mass --overplot_manga --overplot_clear --binby log_mass --nbins 200 --zhighlight --use_gasre --overplot_smoothed
                 run plot_MZgrad.py --system ayan_local --halo 8508,5036,5016,4123 --upto_kpc 10 --Zgrad_den rad_re --keep --weight mass --overplot_manga --overplot_clear --binby log_mass --nbins 200 --zhighlight --use_gasre --overplot_smoothed
                 run plot_MZgrad.py --system ayan_local --halo 8508 --upto_re 3 --Zgrad_den rad_re --keep --weight mass --overplot_manga --overplot_clear --overplot_belfiore --overplot_mjngozzi --binby log_mass --nbins 200 --zhighlight --use_gasre --overplot_smoothed --manga_diag pyqz
                 run plot_MZgrad.py --system ayan_pleiades --halo 8508 --upto_re 3 --Zgrad_den rad_re --weight mass --binby log_mass --nbins 20 --cmap plasma --xmax 11 --ymin 0.3 --overplot_manga --manga_diag n2
                 run plot_MZgrad.py --system ayan_local --halo 8508 --Zgrad_den kpc --upto_kpc 10 --keep --weight mass --ycol Zgrad --xcol time --colorcol log_mass --overplot_smoothed --zhighlight
                 run plot_MZgrad.py --system ayan_local --halo 8508 --Zgrad_den kpc --upto_kpc 10 --keep --weight mass --ycol Zgrad --xcol time --colorcol re --cmax 3 --zhighlight
"""
from header import *
from util import *
from matplotlib.collections import LineCollection
start_time = time.time()

# ---------------------------------
def load_df(args):
    '''
    Function to load and return the dataframe containing MZGR
    '''
    args.foggie_dir, args.output_dir, args.run_loc, args.code_path, args.trackname, args.haloname, args.spectra_dir, args.infofile = get_run_loc_etc(args)
    upto_text = '_upto%.1Fkpc' % args.upto_kpc if args.upto_kpc is not None else '_upto%.1FRe' % args.upto_re
    Zgrad_den_text = 'rad' if args.Zgrad_den == 'kpc' else 'rad_re'
    grad_filename = args.output_dir + 'txtfiles/' + args.halo + '_MZR_xcol_%s%s%s.txt' % (Zgrad_den_text, upto_text, args.weightby_text)

    convert_Zgrad_from_dexkpc_to_dexre = False
    convert_Zgrad_from_dexre_to_dexkpc = False

    if os.path.exists(grad_filename):
        print('Trying to read in', grad_filename)
        df = pd.read_table(grad_filename, delim_whitespace=True)

    elif not os.path.exists(grad_filename) and args.Zgrad_den == 're':
        print('Could not find', grad_filename)
        grad_filename = grad_filename.replace('re', 'kpc')
        print('Trying to read in', grad_filename, 'instead')
        df = pd.read_table(grad_filename, delim_whitespace=True)
        convert_Zgrad_from_dexkpc_to_dexre = True

    elif not os.path.exists(grad_filename) and args.Zgrad_den == 'kpc':
        print('Could not find', grad_filename)
        grad_filename = grad_filename.replace('kpc', 're')
        print('Trying to read in', grad_filename, 'instead')
        df = pd.read_table(grad_filename, delim_whitespace=True)
        convert_Zgrad_from_dexre_to_dexkpc = True

    df.drop_duplicates(subset='output', keep='last', ignore_index=True, inplace=True)
    df.sort_values(by='redshift', ascending=False, ignore_index=True, inplace=True)

    binned_fit_text = '_binned' if args.use_binnedfit else ''
    which_re = 're_coldgas' if args.use_gasre else 're_stars'
    try:
        df = df[['output', 'redshift', 'time', which_re, 'mass_' + which_re] + [item + binned_fit_text + '_' + which_re for item in ['Zcen', 'Zcen_u', 'Zgrad', 'Zgrad']] + ['Ztotal_' + which_re]]
        df.columns = ['output', 'redshift', 'time', 're', 'mass', 'Zcen', 'Zcen_u', 'Zgrad', 'Zgrad_u', 'Ztotal']
    except:
        pass

    df['log_mass'] = np.log10(df['mass'])
    df = df.drop('mass', axis=1)

    if convert_Zgrad_from_dexkpc_to_dexre:
        print('Zgrad is in dex/kpc, converting it to dex/re')
        df['Zgrad'] *= df['re']
        df['Zgrad_u'] *= df['re']

    elif convert_Zgrad_from_dexre_to_dexkpc:
        print('Zgrad is in dex/re, converting it to dex/kpc')
        df['Zgrad'] /= df['re']
        df['Zgrad_u'] /= df['re']

    return df

# -----------------------------------
def overplot_mingozzi(ax, paper='M20', color='salmon', diag='PP04'):
    '''
    Function to overplot the observed MZGR from Mingozzi+20 OR Belfiore+17 and return the axis handle
    '''
    print('Overplotting Mingozzi+20 data..')

    input_filename = HOME + '/Desktop/bpt_contsub_contu_rms/newfit/lit_log_mass_Zgrad|r_e_bin.txt'
    df = pd.read_table(input_filename, delim_whitespace=True, comment='#') # grad is in dex/re, mass_bin is in log

    ax.scatter(df['log_mass'], df[diag + '_' + paper], c=color, s=50)
    ax.plot(df['log_mass'], df[diag + '_' + paper], c=color, lw=2)

    return ax

# -----------------------------------
def overplot_clear(ax):
    '''
    Function to overplot the observed MZGR from CLEAR (Simons+21) and return the axis handle
    '''
    print('Overplotting Simons+21 data..')

    input_filename = HOME + '/models/clear/clear_simons_2021.txt'
    df = pd.read_table(input_filename, delim_whitespace=True) # grad is in dex/re, mass_bin is in log
    col_arr = ['r', 'k']

    for index,survey in enumerate(pd.unique(df['survey'])):
        df_sub = df[df['survey'] == survey]

        ax.errorbar(df_sub['mass_bin'], df_sub['grad'], yerr=df_sub['egrad'], c=col_arr[index], ls='none')
        ax.scatter(df_sub['mass_bin'], df_sub['grad'], c=col_arr[index], s=50)
        ax.plot(df_sub['mass_bin'], df_sub['grad'], c=col_arr[index], lw=2)

    return ax

# -----------------------------------
def overplot_manga(ax, args):
    '''
    Function to overplot the observed MZGR from MaNGA and return the axis handle
    '''
    print('Overplotting MaNGA data..')

    # ---------read in the manga catalogue-------
    manga_input_filename = HOME + '/models/manga/manga.Pipe3D-v2_4_3_downloaded.fits'
    data = Table.read(manga_input_filename, format='fits')
    df_manga = data.to_pandas()

    # --------trim to required columns---------------
    # options for args.manga_diag are: n2, o3n2, ons, pyqz, t2, m08, t04
    df_manga = df_manga[['mangaid', 'redshift', 're_kpc', 'log_mass', 'alpha_oh_re_fit_' + args.manga_diag, 'e_alpha_oh_re_fit_' + args.manga_diag, 'oh_re_fit_' + args.manga_diag, 'e_oh_re_fit_' + args.manga_diag]]
    df_manga = df_manga.dropna(subset=['alpha_oh_re_fit_' + args.manga_diag])

    sns.kdeplot(df_manga['log_mass'], df_manga['alpha_oh_re_fit_' + args.manga_diag], ax=ax, shade=True, shade_lowest=False, alpha=0.7, n_levels=10, cmap='Greys')
    #ax.scatter(df_manga['log_mass'], df_manga['alpha_oh_re_fit_' + args.manga_diag], c=df_manga['redshift'], cmap='Greys_r', s=10, alpha=0.5)

    return ax, df_manga

# ---------------------------------------------
def get_multicolored_line(xdata, ydata, colordata, cmap, cmin, cmax, lw=2, ls='solid'):
    '''
    Function to take x,y and z (color) data as three 1D arrays and return a smoothly-multi-colored line object that can be added to an axis object
    '''
    points = np.array([xdata, ydata]).T.reshape(-1, 1, 2)
    segments = np.concatenate([points[:-1], points[1:]], axis=1)
    norm = plt.Normalize(cmin, cmax)
    lc = LineCollection(segments, cmap=cmap, norm=norm)
    lc.set_array(colordata)
    lc.set_linewidth(lw)
    lc.set_linestyle(ls)
    return lc

# ----------------------------------
class MyDefaultDict(dict):
    '''
    subclass to modify dict to return the missing key itself
    '''
    __missing__ = lambda self, key: key

# -----------------------------------
def plot_MZGR(args):
    '''
    Function to plot the mass-metallicity gradient relation, based on an input dataframe
    '''

    df_master = pd.DataFrame()
    cmap_arr = ['Purples', 'Oranges', 'Greens', 'Blues', 'PuRd', 'YlOrBr']
    things_that_reduce_with_time = ['redshift', 're'] # whenever this quantities are used as colorcol, the cmap is inverted, so that the darkest color is towards later times

    # -------------get plot limits-----------------
    lim_dict = {'Zgrad': (-0.5, 0.1)  if args.Zgrad_den == 'kpc' else (-2, 0.1), 're': (0, 30), 'log_mass': (8.5, 11.5), 'redshift': (0, 6), 'time': (0, 14)}
    label_dict = MyDefaultDict(Zgrad=r'$\nabla(\log{\mathrm{Z}}$) (dex/r$_{\mathrm{e}}$)' if args.Zgrad_den == 're' else r'$\Delta Z$ (dex/kpc)', \
        re='Scale length (kpc)', log_mass=r'$\log{(\mathrm{M}_*/\mathrm{M}_\odot)}$', redshift='Redshift', time='Time (Gyr)')

    if args.xmin is None: args.xmin = lim_dict[args.xcol][0]
    if args.xmax is None: args.xmax = lim_dict[args.xcol][1]
    if args.ymin is None: args.ymin = lim_dict[args.ycol][0]
    if args.ymax is None: args.ymax = lim_dict[args.ycol][1]
    if args.cmin is None: args.cmin = lim_dict[args.colorcol][0]
    if args.cmax is None: args.cmax = lim_dict[args.colorcol][1]

    # -------declare figure object-------------
    fig, ax = plt.subplots(1, figsize=(10, 5))
    fig.subplots_adjust(top=0.95, bottom=0.15, left=0.12, right=1.05)

    # ---------plot observations----------------
    obs_text = ''
    if args.overplot_manga and args.Zgrad_den == 're':
        ax, df_manga = overplot_manga(ax, args)
        obs_text += '_manga_' + args.manga_diag
        fig.text(0.15, 0.2, 'MaNGA: Pipe3D', ha='left', va='top', color='Grey', fontsize=args.fontsize)
    else:
        df_manga = -99 # bogus value

    if args.overplot_clear and args.Zgrad_den == 're':
        ax = overplot_clear(ax)
        obs_text += '_clear'
        fig.text(0.15, 0.25, 'CLEAR: Simons+21', ha='left', va='top', color='k', fontsize=args.fontsize)
        fig.text(0.15, 0.3, 'MaNGA: Belfiore+17', ha='left', va='top', color='r', fontsize=args.fontsize)

    if args.overplot_belfiore and args.Zgrad_den == 're':
        ax = overplot_mingozzi(ax, paper='B17', color='darkolivegreen', diag='M08')
        obs_text += '_belfiore_'
        fig.text(0.15, 0.35, 'MaNGA: Belfiore+17', ha='left', va='top', color='darkolivegreen', fontsize=args.fontsize)

    if args.overplot_mingozzi and args.Zgrad_den == 're':
        ax = overplot_mingozzi(ax, paper='M20', color='salmon', diag='M08')
        obs_text += '_mingozzi_'
        fig.text(0.15, 0.4, 'MaNGA: Mingozzi+20', ha='left', va='top', color='salmon', fontsize=args.fontsize)

    # --------loop over different FOGGIE halos-------------
    for index, args.halo in enumerate(args.halo_arr[::-1]):
        thisindex = len(args.halo_arr) - index - 1
        df = load_df(args)
        df = df[(df[args.xcol] >= args.xmin) & (df[args.xcol] <= args.xmax)]
        #df = df[(df[args.ycol] >= args.ymin) & (df[args.ycol] <= args.ymax)]

        if args.binby is not None:
            df[args.binby + '_bins'] = pd.cut(df[args.binby], bins=np.linspace(np.min(df[args.binby]), np.max(df[args.binby]), args.nbins))
            df = df[[args.colorcol, args.xcol, args.ycol, args.binby + '_bins']].groupby(args.binby + '_bins', as_index=False).agg(np.mean)
            df.dropna(inplace=True)

        # -----plot line with color gradient--------
        this_cmap = cmap_arr[thisindex] + '_r' if args.colorcol in things_that_reduce_with_time else cmap_arr[thisindex] # reverse colromap for redshift
        line = get_multicolored_line(df[args.xcol], df[args.ycol], df[args.colorcol], this_cmap, args.cmin, args.cmax, lw=1 if args.overplot_smoothed else 2)
        plot = ax.add_collection(line)

        # ------- overplotting redshift-binned scatter plot------------
        if args.zhighlight:
            df['redshift_int'] = np.floor(df['redshift'])
            df_zbin = df.drop_duplicates(subset='redshift_int', keep='last', ignore_index=True)
            dummy = ax.scatter(df_zbin[args.xcol], df_zbin[args.ycol], c=df_zbin[args.colorcol], cmap=this_cmap, lw=1, edgecolor='k', s=100, alpha=0.2 if args.overplot_smoothed else 1)
            print('For halo', args.halo, 'highlighted z =', [float('%.1F'%item) for item in df_zbin['redshift'].values])

        # ------- overplotting a boxcar smoothed version of the MZGR------------
        if args.overplot_smoothed:
            line.set_alpha(0.2) # make the actual wiggly line fainter
            npoints = int(len(df)/8)
            if npoints % 2 == 0: npoints += 1
            box = np.ones(npoints) / npoints
            df[args.ycol + '_smoothed'] = np.convolve(df[args.ycol], box, mode='same')
            smoothline = get_multicolored_line(df[args.xcol], df[args.ycol + '_smoothed'], df[args.colorcol], this_cmap, args.cmin, args.cmax, lw=2)
            plot = ax.add_collection(smoothline)
            print('Boxcar-smoothed plot for halo', args.halo, 'with', npoints, 'points')

        fig.text(0.15, 0.9 - thisindex * 0.05, halo_dict[args.halo], ha='left', va='top', color=mpl_cm.get_cmap(this_cmap)(0.2 if args.colorcol == 'redshift' else 0.8), fontsize=args.fontsize)
        df['halo'] = args.halo
        df_master = pd.concat([df_master, df])

    cax = plt.colorbar(plot)
    cax.ax.tick_params(labelsize=args.fontsize)
    cax.set_label(label_dict[args.colorcol], fontsize=args.fontsize)

    if args.xcol == 'redshift':  ax.set_xlim(args.xmax, args.xmin)
    else: ax.set_xlim(args.xmin, args.xmax)
    ax.set_ylim(args.ymin, args.ymax)

    ax.set_xticklabels(['%.1F' % item for item in ax.get_xticks()], fontsize=args.fontsize)
    ax.set_yticklabels(['%.2F' % item for item in ax.get_yticks()], fontsize=args.fontsize)

    ax.set_xlabel(label_dict[args.xcol], fontsize=args.fontsize)
    ax.set_ylabel(label_dict[args.ycol], fontsize=args.fontsize)

    binby_text = '' if args.binby is None else '_binby_' + args.binby
    upto_text = '_upto%.1Fkpc' % args.upto_kpc if args.upto_kpc is not None else '_upto%.1FRe' % args.upto_re
    figname = args.output_dir + 'figs/' + ','.join(args.halo_arr) + '_%s_vs%s_colorby_%s_Zgrad_den_%s%s%s%s%s.png' % (args.ycol, args.xcol, args.colorcol, args.Zgrad_den, upto_text, args.weightby_text, binby_text, obs_text)
    fig.savefig(figname)
    print('Saved plot as', figname)
    plt.show(block=False)

    return fig, df_master, df_manga


# -----main code-----------------
if __name__ == '__main__':
    args_tuple = parse_args('8508', 'RD0042')  # default simulation to work upon when comand line args not provided
    if type(args_tuple) is tuple: args = args_tuple[0] # if the sim has already been loaded in, in order to compute the box center (via utils.pull_halo_center()), then no need to do it again
    else: args = args_tuple
    if not args.keep: plt.close('all')

    # ---------reading in existing MZgrad txt file------------------
    args.weightby_text = '' if args.weight is None else '_wtby_' + args.weight
    if args.ycol == 'metal': args.ycol = 'Zgrad' # changing the default ycol to metallicity gradient
    if args.xcol == 'rad': args.xcol = 'log_mass' # changing the default xcol to mass, to make a MZGR plot by default when xcol and ycol aren't specified
    if args.colorcol == ['vrad']: args.colorcol = 'redshift'
    else: args.colorcol = args.colorcol[0]

    fig, df_binned, df_manga = plot_MZGR(args)

    print('Completed in %s' % (datetime.timedelta(minutes=(time.time() - start_time) / 60)))



