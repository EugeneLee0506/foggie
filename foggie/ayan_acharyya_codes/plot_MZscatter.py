#!/usr/bin/env python3

"""

    Title :      plot_MZscatter
    Notes :      Plot mass - metallicity scatter relation for a given FOGGIE galaxy
    Output :     M-Z scatter plots as png files
    Author :     Ayan Acharyya
    Started :    Aug 2022
    Examples :   run plot_MZscatter.py --system ayan_local --halo 8508,5036,5016,4123 --upto_re 3 --keep --weight mass --res 0.1 --xcol log_mass --binby log_mass --nbins 200 --zhighlight --use_gasre --overplot_smoothed
                 run plot_MZscatter.py --system ayan_local --halo 8508 --upto_kpc 10 --keep --weight mass --res 0.1 --ycol log_Zvar --xcol log_mass --colorcol time --zhighlight --docomoving --fit_multiple
"""
from header import *
from util import *
from matplotlib.collections import LineCollection
from plot_MZgrad import *
start_time = time.time()

# ---------------------------------
def load_df(args):
    '''
    Function to load and return the dataframe containing MZGR
    '''
    args.foggie_dir, args.output_dir, args.run_loc, args.code_path, args.trackname, args.haloname, args.spectra_dir, args.infofile = get_run_loc_etc(args)
    if args.upto_kpc is not None:
        upto_text = '_upto%.1Fckpchinv' % args.upto_kpc if args.docomoving else '_upto%.1Fkpc' % args.upto_kpc
    else:
        upto_text = '_upto%.1FRe' % args.upto_re
    grad_filename = args.output_dir + 'txtfiles/' + args.halo + '_MZscat%s%s%s.txt' % (upto_text, args.weightby_text, args.fitmultiple_text)

    df = pd.read_table(grad_filename, delim_whitespace=True)
    df.drop_duplicates(subset='output', keep='last', ignore_index=True, inplace=True)

    Zgrad_den_text = 'rad' if args.upto_kpc is not None else 'rad_re'
    df2 = pd.read_table(args.output_dir + 'txtfiles/' + args.halo + '_MZR_xcol_%s%s%s.txt' % (Zgrad_den_text, upto_text, args.weightby_text), comment='#', delim_whitespace=True)
    df = df.merge(df2[['output', 'Zcen_fixedr', 'Zgrad_fixedr', 'Zcen_binned_fixedr', 'Zgrad_binned_fixedr', 'Ztotal_fixedr']], on='output')
    cols_to_rename = ['Zcen_fixedr', 'Zgrad_fixedr', 'Zcen_binned_fixedr', 'Zgrad_binned_fixedr']
    df = df.rename(columns=dict(zip(cols_to_rename, [item[:-7] for item in cols_to_rename])))

    df.sort_values(by='redshift', ascending=False, ignore_index=True, inplace=True)

    if 'res' in df: df = df[df['res'] == float(args.res)]

    cols_to_log = ['Zpeak', 'Z25', 'Z50', 'Z75', 'Zmean', 'Zvar', 'Zskew', 'mass', 'Zcen', 'Zcen_binned', 'Ztotal_fixedr']
    for thiscol in cols_to_log:
        df['log_' + thiscol] = np.log10(df[thiscol])
        df = df.drop(thiscol, axis=1)

    return df

# -----------------------------------
def plot_all_stats(df, args):
    '''
    Function to plot the time evolution of Z distribution statistics, based on an input dataframe
    '''
    fig, axes = plt.subplots(3, figsize=(12, 10), sharex=True)
    fig.subplots_adjust(top=0.95, bottom=0.1, left=0.07, right=0.92, hspace=0.05)
    df = df.sort_values(by='time')

    # -----------for first plot: Z distribution statistics-------------------
    col_arr = ['saddlebrown', 'crimson', 'darkolivegreen', 'salmon', 'cornflowerblue', 'burlywood', 'darkturquoise']
    for i, ycol in enumerate(['Zskew', 'Zpeak', 'Z25', 'Z50', 'Z75', 'Zmean', 'Zvar']):
        axes[0].plot(df['time'], df['log_' + ycol], c=col_arr[i], lw=0.5 if args.overplot_smoothed else 1, alpha = 0.3 if args.overplot_smoothed or ycol == 'Zskew' else 1, label=None if args.overplot_smoothed else ycol)

        if args.overplot_smoothed:
            npoints = int(len(df)/8)
            if npoints % 2 == 0: npoints += 1
            box = np.ones(npoints) / npoints
            df['log_' + ycol + '_smoothed'] = np.convolve(df['log_' + ycol], box, mode='same')
            axes[0].plot(df['time'], df['log_' + ycol + '_smoothed'], c=col_arr[i], lw=2, label=ycol)
    axes[0].legend(loc='upper left', fontsize=args.fontsize/1.5)
    axes[0].set_ylabel(r'$\log{(\mathrm{Z}/\mathrm{Z}_\odot)}$', fontsize=args.fontsize)
    axes[0].set_ylim(-2, 1)
    axes[0].tick_params(axis='y', labelsize=args.fontsize)

    # -----------for second plot: Z gradient fitting properties-------------------
    col_arr = ['saddlebrown', 'crimson', 'darkolivegreen', 'salmon', 'cornflowerblue', 'burlywood', 'darkturquoise']
    ax1 = axes[1].twinx()
    for i, ycol in enumerate(['Zgrad', 'Zgrad_binned', 'log_Zcen', 'log_Zcen_binned', 'log_Ztotal_fixedr']):
        ax_to_plot = axes[1] if i >= 2 else ax1
        ax_to_plot.plot(df['time'], df[ycol], c=col_arr[i], lw=0.5 if args.overplot_smoothed else 1, alpha = 0.3 if args.overplot_smoothed else 1, label=None if args.overplot_smoothed else ycol[4:] if i >= 2 else ycol)

        if args.overplot_smoothed:
            npoints = int(len(df)/8)
            if npoints % 2 == 0: npoints += 1
            box = np.ones(npoints) / npoints
            df[ycol + '_smoothed'] = np.convolve(df[ycol], box, mode='same')
            ax_to_plot.plot(df['time'], df[ycol + '_smoothed'], c=col_arr[i], lw=2, label=ycol)

    axes[1].legend(loc='upper left', fontsize=args.fontsize/1.5)
    axes[1].set_ylabel(r'$\log{(\mathrm{Z}/\mathrm{Z}_\odot)}$', fontsize=args.fontsize)
    axes[1].set_ylim(-2, 1)
    axes[1].tick_params(axis='y', labelsize=args.fontsize)

    ax1.legend(loc='lower right', fontsize=args.fontsize)
    ax1.set_ylabel(r'$\Delta Z$ (dex/kpc)', fontsize=args.fontsize)
    ax1.set_ylim(-0.6, 0)
    ax1.tick_params(axis='y', labelsize=args.fontsize)

    # -----------for third plot first part: SFR properties-------------------
    col_arr = ['black', 'brown']
    axes[2].plot(df['time'], df['sfr'], c=col_arr[0], lw=1)

    axes[2].set_ylabel(label_dict['sfr'], fontsize=args.fontsize, color=col_arr[0])
    axes[2].set_ylim(0, 50)
    axes[2].tick_params(axis='y', colors=col_arr[0], labelsize=args.fontsize)

    axes[2].set_xlabel('Time (Gyr)', fontsize=args.fontsize)
    axes[2].set_xlim(0, 14)
    axes[2].tick_params(axis='x', labelsize=args.fontsize)

    # -----------for third plot second part: SFR properties-------------------
    ax2 = axes[2].twinx()
    ax2.plot(df['time'], df['log_ssfr'], c=col_arr[1], lw=1)

    ax2.set_ylabel(label_dict['log_ssfr'], fontsize=args.fontsize, color=col_arr[1])
    ax2.set_ylim(-12, -7)
    ax2.tick_params(axis='y', colors=col_arr[1], labelsize=args.fontsize)

    if args.upto_kpc is not None:
        upto_text = '_upto%.1Fckpchinv' % args.upto_kpc if args.docomoving else '_upto%.1Fkpc' % args.upto_kpc
    else:
        upto_text = '_upto%.1FRe' % args.upto_re

    figname = args.output_dir + 'figs/' + ','.join(args.halo_arr) + '_allstats_vs_time_res%.2Fkpc%s%s.png' % (float(args.res), upto_text, args.weightby_text)
    fig.savefig(figname)
    print('Saved', figname)
    plt.show(block=False)

    return fig

# -----------------------------------
def plot_MZscatter(args):
    '''
    Function to plot the mass-metallicity scatter relation, based on an input dataframe
    '''

    df_master = pd.DataFrame()
    cmap_arr = ['Purples', 'Oranges', 'Greens', 'Blues', 'PuRd', 'YlOrBr']
    things_that_reduce_with_time = ['redshift', 're'] # whenever this quantities are used as colorcol, the cmap is inverted, so that the darkest color is towards later times

    if args.xmin is None: args.xmin = lim_dict[args.xcol][0]
    if args.xmax is None: args.xmax = lim_dict[args.xcol][1]
    if args.ymin is None: args.ymin = lim_dict[args.ycol][0]
    if args.ymax is None: args.ymax = lim_dict[args.ycol][1]
    if args.cmin is None: args.cmin = lim_dict[args.colorcol][0]
    if args.cmax is None: args.cmax = lim_dict[args.colorcol][1]
    if args.zmin is None: args.zmin = lim_dict[args.zcol][0]
    if args.zmax is None: args.zmax = lim_dict[args.zcol][1]

    # -------declare figure object-------------
    fig, ax = plt.subplots(1, figsize=(12, 6))
    fig.subplots_adjust(top=0.95, bottom=0.15, left=0.1, right=1.05)

    if args.plot_deviation:
        fig2, ax2 = plt.subplots(1, figsize=(12, 6))
        fig2.subplots_adjust(top=0.95, bottom=0.15, left=0.1, right=1.05)
        args.overplot_smoothed = True

    # --------loop over different FOGGIE halos-------------
    for index, args.halo in enumerate(args.halo_arr[::-1]):
        thisindex = len(args.halo_arr) - index - 1
        df = load_df(args)
        # -------- reading in additional dataframes-------
        addn_df = pd.read_table(args.code_path + 'halo_infos/00' + args.halo + '/' + args.run + '/sfr', names=('output', 'redshift', 'sfr'), comment='#', delim_whitespace=True)
        df = df.merge(addn_df[['output', 'sfr']], on='output')
        df['ssfr'] = df['sfr'] / 10**df['log_mass']
        df = df.replace([np.inf, -np.inf], np.nan).dropna(axis=0)
        df['log_ssfr'] = np.log10(df['ssfr'])
        df['log_sfr'] = np.log10(df['sfr'])
        df = df.sort_values(args.xcol)

        fig3 = plot_all_stats(df, args)

        #df = df[(df[args.xcol] >= args.xmin) & (df[args.xcol] <= args.xmax)]
        #df = df[(df[args.ycol] >= args.ymin) & (df[args.ycol] <= args.ymax)]
        df = df[(df[args.colorcol] >= args.cmin) & (df[args.colorcol] <= args.cmax)]
        df = df.dropna(subset=[args.xcol, args.ycol, args.colorcol], axis=0)

        # ------- plot only the binned plot------------
        if args.binby is not None:
            df[args.binby + '_bins'] = pd.cut(df[args.binby], bins=np.linspace(np.min(df[args.binby]), np.max(df[args.binby]), args.nbins))
            cols_to_bin = [args.colorcol, args.xcol, args.ycol, args.binby + '_bins']
            if args.plot_deviation: cols_to_bin += [args.zcol]
            if 'redshift' not in cols_to_bin: cols_to_bin += ['redshift']
            df = df[cols_to_bin].groupby(args.binby + '_bins', as_index=False).agg(np.mean)
            df.dropna(axis=0, inplace=True)
            df = df.sort_values(args.xcol)

        # -----plot line with color gradient--------
        this_cmap = cmap_arr[thisindex] + '_r' if args.colorcol in things_that_reduce_with_time else cmap_arr[thisindex] # reverse colromap for redshift
        reversed_thiscmap = this_cmap + '_r' if '_r' not in this_cmap else this_cmap[:-2]
        thistextcolor = mpl_cm.get_cmap(this_cmap)(0.2 if args.colorcol == 'redshift' else 0.2 if args.colorcol == 're' else 0.8)
        line = get_multicolored_line(df[args.xcol], df[args.ycol], df[args.colorcol], this_cmap, args.cmin, args.cmax, lw=1 if args.overplot_smoothed else 2)
        plot = ax.add_collection(line)

        # ------- overplotting specific snapshot highlights------------
        if args.snaphighlight is not None:
            snaps_to_highlight = [item for item in args.snaphighlight.split(',')]
            df_snaps = df[df['output'].isin(snaps_to_highlight)]
            dummy = ax.scatter(df_snaps[args.xcol], df_snaps[args.ycol], c=df_snaps[args.colorcol], cmap=this_cmap, vmin=args.cmin, vmax=args.cmax, lw=1, edgecolor='k', s=200, alpha=0.2 if args.overplot_smoothed else 1, marker='*', zorder=10)
            print('For halo', args.halo, 'highlighted snapshots =', df_snaps['output'].values, 'with stars')

        # ------- overplotting redshift-binned scatter plot------------
        if args.zhighlight:
            df['redshift_int'] = np.floor(df['redshift'])
            df_zbin = df.drop_duplicates(subset='redshift_int', keep='last', ignore_index=True)
            dummy = ax.scatter(df_zbin[args.xcol], df_zbin[args.ycol], c=df_zbin[args.colorcol], cmap=this_cmap, vmin=args.cmin, vmax=args.cmax, lw=1, edgecolor='k', s=100, alpha=0.2 if args.overplot_smoothed else 1, zorder=20)
            print('For halo', args.halo, 'highlighted z =', [float('%.1F'%item) for item in df_zbin['redshift'].values], 'with circles')

        # ------- overplotting a boxcar smoothed version of the MZGR------------
        if args.overplot_smoothed:
            npoints = int(len(df)/8)
            if npoints % 2 == 0: npoints += 1
            box = np.ones(npoints) / npoints
            df[args.ycol + '_smoothed'] = np.convolve(df[args.ycol], box, mode='same')

            line.set_alpha(0.2) # make the actual wiggly line fainter
            smoothline = get_multicolored_line(df[args.xcol], df[args.ycol + '_smoothed'], df[args.colorcol], this_cmap, args.cmin, args.cmax, lw=2)
            plot = ax.add_collection(smoothline)
            print('Boxcar-smoothed plot for halo', args.halo, 'with', npoints, 'points')

        # ------- making additional plot of deviation in gradient vs other quantities, like SFR------------
        if args.plot_deviation:
            print('Plotting deviation vs', args.colorcol, 'halo', args.halo)
            df[args.ycol + '_deviation'] = df[args.ycol] - df[args.ycol + '_smoothed']
            df = df.sort_values(args.zcol)

            # --------- scatter plot------------
            #ax2.scatter(df[args.zcol], df[args.ycol + '_deviation'], c=thistextcolor, edgecolor='k', lw=0.5, s=50)

            # --------- colored line plot------------
            line2 = get_multicolored_line(df[args.zcol], np.abs(df[args.ycol + '_deviation']), df[args.colorcol], reversed_thiscmap, args.cmin, args.cmax, lw=1)
            plot2 = ax2.add_collection(line2)

            # --------- smoothed colored line plot------------
            line2.set_alpha(0.2) # make the actual wiggly line fainter

            df[args.ycol + '_deviation_smoothed'] = np.convolve(np.abs(df[args.ycol + '_deviation']), box, mode='same')
            smoothline2 = get_multicolored_line(df[args.zcol], df[args.ycol + '_deviation_smoothed'], df[args.colorcol], reversed_thiscmap, args.cmin, args.cmax, lw=2)
            plot2 = ax2.add_collection(smoothline2)


        fig.text(0.15, 0.9 - thisindex * 0.05, halo_dict[args.halo], ha='left', va='top', color=thistextcolor, fontsize=args.fontsize)
        if args.plot_deviation: fig2.text(0.15, 0.9 - thisindex * 0.05, halo_dict[args.halo], ha='left', va='top', color=thistextcolor, fontsize=args.fontsize)
        df['halo'] = args.halo
        df_master = pd.concat([df_master, df])

    # ------- tidying up fig1------------
    cax = fig.colorbar(plot)
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
    if args.upto_kpc is not None:
        upto_text = '_upto%.1Fckpchinv' % args.upto_kpc if args.docomoving else '_upto%.1Fkpc' % args.upto_kpc
    else:
        upto_text = '_upto%.1FRe' % args.upto_re

    figname = args.output_dir + 'figs/' + ','.join(args.halo_arr) + '_%s_vs_%s_colorby_%s_res%.2Fkpc%s%s%s.png' % (args.ycol, args.xcol, args.colorcol, float(args.res), upto_text, args.weightby_text, binby_text)
    fig.savefig(figname)
    print('Saved plot as', figname)

    # ------- tidying up fig2 if any------------
    if args.plot_deviation:
        cax = fig2.colorbar(plot2)
        cax.ax.tick_params(labelsize=args.fontsize)
        cax.set_label(label_dict[args.colorcol], fontsize=args.fontsize)

        ax2.set_xlim(args.zmin, args.zmax)
        ax2.set_ylim(-0.01, 0.15)

        ax2.set_xticklabels(['%.1F' % item for item in ax2.get_xticks()], fontsize=args.fontsize)
        ax2.set_yticklabels(['%.2F' % item for item in ax2.get_yticks()], fontsize=args.fontsize)

        ax2.set_xlabel(label_dict[args.zcol], fontsize=args.fontsize)
        ax2.set_ylabel('Deviation in ' + label_dict[args.ycol], fontsize=args.fontsize)

        figname = args.output_dir + 'figs/' + ','.join(args.halo_arr) + '_dev_in_%s_vs_%s_colorby_%s_res%.2Fkpc%s%s%s.png' % (args.ycol, args.zcol, args.colorcol, float(args.res), upto_text, args.weightby_text, binby_text)
        fig2.savefig(figname)
        print('Saved plot as', figname)
    else:
        fig2 = None

    plt.show(block=False)
    return fig, fig2, fig3, df_master


# -------------get plot limits-----------------
lim_dict = {'log_Zpeak': (-2, 0.1), 'log_Z50': (-2, 0.1), 'log_Zmean': (-2, 0.1), 'log_Zvar': (-2, 0.1),
            'Zskew': (-2, 0.1), 're': (0, 30), 'log_mass': (8.5, 11.5), 'redshift': (0, 6), 'time': (0, 14),
            'sfr': (0, 60), 'log_ssfr': (-11, -8), 'Ztotal': (8, 9), 'log_sfr': (-1, 3)}
label_dict = MyDefaultDict(re='Scale length (kpc)', log_mass=r'$\log{(\mathrm{M}_*/\mathrm{M}_\odot)}$', redshift='Redshift', time='Time (Gyr)', sfr=r'SFR (M$_{\odot}$/yr)', \
    log_ssfr=r'$\log{\, \mathrm{sSFR} (\mathrm{yr}^{-1})}$', Ztotal=r'$\log{(\mathrm{O/H})}$ + 12', log_sfr=r'$\log{(\mathrm{SFR} (\mathrm{M}_{\odot}/yr))}$')

# -----main code-----------------
if __name__ == '__main__':
    args_tuple = parse_args('8508', 'RD0042')  # default simulation to work upon when comand line args not provided
    if type(args_tuple) is tuple: args = args_tuple[0] # if the sim has already been loaded in, in order to compute the box center (via utils.pull_halo_center()), then no need to do it again
    else: args = args_tuple
    if not args.keep: plt.close('all')

    # ---------reading in existing MZgrad txt file------------------
    args.weightby_text = '' if args.weight is None else '_wtby_' + args.weight
    args.fitmultiple_text = '_fitmultiple' if args.fit_multiple else ''
    if args.ycol == 'metal': args.ycol = 'log_Zvar' # changing the default ycol to metallicity gradient
    if args.xcol == 'rad': args.xcol = 'log_mass' # changing the default xcol to mass, to make a MZGR plot by default when xcol and ycol aren't specified
    if args.colorcol == ['vrad']: args.colorcol = 'time'
    else: args.colorcol = args.colorcol[0]

    fig, fig2, fig3, df_binned = plot_MZscatter(args)

    print('Completed in %s' % (datetime.timedelta(minutes=(time.time() - start_time) / 60)))



