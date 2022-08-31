#!/usr/bin/env python3

"""

    Title :      plot_Zevolution
    Notes :      Plot evolution of metallicity distribution for a given FOGGIE galaxy
    Output :     Various Z statistics vs time plots as png files
    Author :     Ayan Acharyya
    Started :    Aug 2022
    Examples :   run plot_Zevolution.py --system ayan_local --halo 8508,5036,5016,4123 --upto_re 3 --keep --weight mass --res 0.1 --zhighlight --use_gasre --overplot_smoothed
                 run plot_Zevolution.py --system ayan_local --halo 8508 --upto_kpc 10 --keep --weight mass --res 0.1 --zhighlight --docomoving --fit_multiple
"""
from header import *
from util import *
from matplotlib.collections import LineCollection
from plot_MZscatter import *
start_time = time.time()

# -----------------------------------
def plot_all_stats(df, args):
    '''
    Function to plot the time evolution of Z distribution statistics, based on an input dataframe
    '''
    fig, axes = plt.subplots(6 + 1, figsize=(14, 10), sharex=True)
    fig.subplots_adjust(top=0.98, bottom=0.07, left=0.07, right=0.92, hspace=0.05)

    df = df.sort_values(by='time')
    col_arr = ['darkolivegreen', 'brown', 'black', 'cornflowerblue', 'salmon', 'gold', 'saddlebrown', 'crimson',
               'black', 'darkturquoise', 'lawngreen']
    sfr_col_arr = ['cornflowerblue', 'salmon']  # ['black', 'brown']

    groups = pd.DataFrame({'quantities': [['Z25', 'Z50', 'Z75'], ['Zskew', 'Zmean', 'Zvar'],
                                          ['gauss_mean', 'gauss_sigma'], ['Ztotal', 'Ztotal_fixedr'],
                                          ['Zgrad', 'Zgrad_binned'], ['Zcen', 'Zcen_binned']], \
                           'label': np.hstack([np.tile([r'$\log{(\mathrm{Z}/\mathrm{Z}_\odot)}$'], 4),
                                               [r'$\Delta Z$ (dex/kpc)', r'$\log{(\mathrm{Z}/\mathrm{Z}_\odot)}$']]), \
                           'limits': [(-3, 1), (-3, 1), (-3, 1), (-1, 1), (-0.6, 0), (-3, 1)], \
                           'isalreadylog': np.hstack([np.tile([True], 4), [False, True]])})

    # -----------for first few panels: Z distribution statistics-------------------
    for j in range(len(groups)):
        thisgroup = groups.iloc[j]
        ax = axes[j]
        log_text = 'log_' if thisgroup.isalreadylog else ''
        for i, ycol in enumerate(thisgroup.quantities):
            ax.plot(df['time'], df[log_text + ycol], c=col_arr[i], lw=0.5 if args.overplot_smoothed else 1,
                    alpha=0.3 if args.overplot_smoothed or ycol == 'Zskew' else 1,
                    label=None if args.overplot_smoothed else ycol)

            if args.overplot_smoothed:
                npoints = int(len(df) / 8)
                if npoints % 2 == 0: npoints += 1
                box = np.ones(npoints) / npoints
                df[log_text + ycol + '_smoothed'] = np.convolve(df[log_text + ycol], box, mode='same')
                ax.plot(df['time'], df[log_text + ycol + '_smoothed'], c=col_arr[i], lw=2, label=ycol)

        ax.legend(loc='upper left', fontsize=args.fontsize / 1.5)
        ax.set_ylabel(thisgroup.label, fontsize=args.fontsize)
        ax.set_ylim(thisgroup.limits)
        ax.tick_params(axis='y', labelsize=args.fontsize)

        ax2 = ax.twinx()
        ax2.plot(df['time'], df['sfr'], c=sfr_col_arr[0], lw=1, alpha=0.2)
        ax2.set_ylim(0, 50)
        ax2.set_yticks([])

        ax3 = ax.twinx()
        ax3.plot(df['time'], df['log_ssfr'], c=sfr_col_arr[1], lw=1, alpha=0.2)
        ax3.set_ylim(-12, -7)
        ax3.set_yticks([])

    # -----------for last panel first part: SFR-------------------
    axes[-1].plot(df['time'], df['sfr'], c=sfr_col_arr[0], lw=1)

    axes[-1].set_ylabel(label_dict['sfr'], fontsize=args.fontsize, color=sfr_col_arr[0])
    axes[-1].set_ylim(0, 50)
    axes[-1].tick_params(axis='y', colors=sfr_col_arr[0], labelsize=args.fontsize)

    axes[-1].set_xlabel('Time (Gyr)', fontsize=args.fontsize)
    axes[-1].set_xlim(0, 14)
    axes[-1].tick_params(axis='x', labelsize=args.fontsize)

    # -----------for last panel second part: sSFR-------------------
    ax2 = axes[-1].twinx()
    ax2.plot(df['time'], df['log_ssfr'], c=sfr_col_arr[1], lw=1)

    ax2.set_ylabel(label_dict['log_ssfr'], fontsize=args.fontsize, color=sfr_col_arr[1])
    ax2.set_ylim(-12, -7)
    ax2.tick_params(axis='y', colors=sfr_col_arr[1], labelsize=args.fontsize)

    if args.upto_kpc is not None:
        upto_text = '_upto%.1Fckpchinv' % args.upto_kpc if args.docomoving else '_upto%.1Fkpc' % args.upto_kpc
    else:
        upto_text = '_upto%.1FRe' % args.upto_re

    figname = args.output_dir + 'figs/' + ','.join(args.halo_arr) + '_allstats_vs_time_res%.2Fkpc%s%s.png' % (
    float(args.res), upto_text, args.weightby_text)
    fig.savefig(figname)
    print('Saved', figname)
    plt.show(block=False)

    return fig

# -----main code-----------------
if __name__ == '__main__':
    args_tuple = parse_args('8508', 'RD0042')  # default simulation to work upon when comand line args not provided
    if type(args_tuple) is tuple: args = args_tuple[0] # if the sim has already been loaded in, in order to compute the box center (via utils.pull_halo_center()), then no need to do it again
    else: args = args_tuple
    if not args.keep: plt.close('all')

    # ---------reading in existing MZgrad txt file------------------
    args.weightby_text = '' if args.weight is None else '_wtby_' + args.weight
    args.fitmultiple_text = '_fitmultiple' if args.fit_multiple else ''

    # -----------loading in dataframe------------------------
    df_master = pd.DataFrame()
    cmap_arr = ['Purples', 'Oranges', 'Greens', 'Blues', 'PuRd', 'YlOrBr']
    things_that_reduce_with_time = ['redshift', 're'] # whenever this quantities are used as colorcol, the cmap is inverted, so that the darkest color is towards later times

    df = load_df(args)

    # -------- reading in and merging dataframe with SFR info-------
    sfr_df = pd.read_table(args.code_path + 'halo_infos/00' + args.halo + '/' + args.run + '/sfr', names=('output', 'redshift', 'sfr'), comment='#', delim_whitespace=True)
    df = df.merge(sfr_df[['output', 'sfr']], on='output')
    df['ssfr'] = df['sfr'] / 10**df['log_mass']
    df = df.replace([np.inf, -np.inf], np.nan).dropna(axis=0)
    df['log_ssfr'] = np.log10(df['ssfr'])
    df['log_sfr'] = np.log10(df['sfr'])

    # -------- reading in and merging dataframe with merger info-------
    m_df = pd.read_table(args.code_path + 'halo_infos/00' + args.halo + '/' + args.run + '/sfr', names=('output', 'redshift', 'sfr'), comment='#', delim_whitespace=True)
    #df = df.merge(m_df[['output', 'sfr']], on='output')

    df = df.sort_values('time')

    fig = plot_all_stats(df, args)

    print('Completed in %s' % (datetime.timedelta(minutes=(time.time() - start_time) / 60)))