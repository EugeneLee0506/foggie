#!/usr/bin/env python3

"""

    Title :      flux_tracking_movie
    Notes :      Run Cassi's foggie/flux_tracking/flux_tracking.calculate_fluxes() code to track metal mass over time and make movies
    Output :     flux profile plots as png files (which can be later converted to a movie via animate_png.py)
    Author :     Ayan Acharyya
    Started :    August 2021
    Examples :   run flux_tracking_movie.py --system ayan_local --halo 8508 --galrad 20 --units_kpc --output RD0042 --clobber_plot --keep --nchunks 20 --overplot_source_sink --overplot_stars --colorcol log_Z_gas
                 run flux_tracking_movie.py --system ayan_pleiades --halo 8508 --galrad 20 --units_kpc --do_all_sims --makemovie --delay 0.05
"""
from header import *
from util import *
from make_ideal_datacube import shift_ref_frame
from datashader_movie import get_radial_velocity
from yt.utilities.physical_ratios import metallicity_sun

# -------------------------------------------------------------------
def new_stars(pfilter, data):
    '''
    Filter star particles with creation time < dt Myr ago, where dt is the time gap between two consecutive snapshots
    To use: yt.add_particle_filter("new_stars", function=new_stars, filtered_type='all', requires=["creation_time"])
    Based on: foggie.yt_fields._young_stars8()
    '''
    isstar = data[(pfilter.filtered_type, "particle_type")] == 2
    age = data.ds.current_time - data[pfilter.filtered_type, "creation_time"]
    filter = np.logical_and(isstar, age.in_units('Myr') <= args.dt, age >= 0)
    return filter

# ---------------------------------------------------------------------------------
def segment_region(radius, inner_radius, outer_radius, refine_width_kpc, Rvir=100., units_kpc=False, units_rvir=False):
    '''
    This function reads in arrays of x, y, z, theta_pos, phi_pos, and radius values and returns a
    boolean list of the same size that is True if a cell is contained within a shape in the list of
    shapes given by 'shapes' and is False otherwise. If disk-relative coordinates are needed for some
    shapes, they can be passed in with the optional x_disk, y_disk, z_disk.
    This function is abridged from Cassi's code foggie.utils.analysis_utils.segment_region()
    '''
    if (units_rvir):
        inner_radius = inner_radius * Rvir
        outer_radius = outer_radius * Rvir
    elif not units_kpc:
        inner_radius = inner_radius * refine_width_kpc
        outer_radius = outer_radius * refine_width_kpc
    bool_insphere = (radius > inner_radius) & (radius < outer_radius)

    return bool_insphere

# ---------------------------------------------------------------------------------
def set_table_units(table):
    '''
    Sets the units for the table. Note this needs to be updated whenever something is added to the table. Returns the table.
    This function is abridged from Cassi's code foggie.flux_tracking.flux_tracking.set_table_units()
    '''
    for key in table.keys():
        if (key=='redshift'):
            table[key].unit = None
        elif ('radius' in key):
            table[key].unit = 'kpc'
        elif ('gas' in key) or ('metal' in key):
            table[key].unit = 'Msun/yr'
    return table

# ---------------------------------------------------------------------------------
def make_table(flux_types, args):
    '''
    Makes the giant table that will be saved to file.
    This function is abridged from Cassi's code foggie.flux_tracking.flux_tracking.make_table()
    '''
    names_list = ['redshift', 'radius']
    types_list = ['f8', 'f8']

    dir_name = ['net_', '_in', '_out']
    if (args.temp_cut): temp_name = ['', 'cold_', 'cool_', 'warm_', 'hot_']
    else: temp_name = ['']
    for i in range(len(flux_types)):
        for k in range(len(temp_name)):
            for j in range(len(dir_name)):
                if (j==0): name = dir_name[j]
                else: name = ''
                name += temp_name[k]
                name += flux_types[i]
                if (j>0): name += dir_name[j]
                names_list += [name]
                types_list += ['f8']

    table = Table(names=names_list, dtype=types_list)

    return table

# ---------------------------------------------------------------------------------
def calc_fluxes(ds, snap, zsnap, dt, refine_width_kpc, tablename, args):
    '''
    This function calculates the gas and metal mass fluxes into and out of a spherical surface. It
    uses the dataset stored in 'ds', which is from time snapshot 'snap', has redshift
    'zsnap', and has width of the refine box in kpc 'refine_width_kpc', the time step between outputs
    'dt', and stores the fluxes in 'tablename'.

    This function calculates the flux as the sum
    of all cells whose velocity and distance from the surface of interest indicate that the gas
    contained in that cell will be displaced across the surface of interest by the next timestep.
    That is, the properties of a cell contribute to the flux if it is no further from the surface of
    interest than v*dt where v is the cell's velocity normal to the surface and dt is the time
    between snapshots, which is dt = 5.38e6 yrs for the DD outputs. It is necessary to compute the
    flux this way if satellites are to be removed because they become 'holes' in the dataset
    and fluxes into/out of those holes need to be accounted for.
    This function is abridged from Cassi's code foggie.flux_tracking.flux_tracking.calc_fluxes()
    '''
    # Set up table of everything we want
    fluxes = ['gas_flux', 'metal_flux']

    # Define list of ways to chunk up the shape over radius or height
    inner_radius = 0.3 # kpc; because yt can't take sphere smaller than 0.3 kpc; so this makes flux tracking bin-wise consistent with source sink calculation
    outer_radius = args.galrad
    num_steps = args.nchunks
    table = make_table(fluxes, args)
    if (args.units_kpc):
        dr = (outer_radius-inner_radius)/num_steps
        chunks = ds.arr(np.arange(inner_radius,outer_radius+dr,dr), 'kpc')
    elif (args.units_rvir):
        # Load the mass enclosed profile
        masses_dir = args.code_path + 'halo_infos/00' + args.halo + '/' + args.run + '/'
        rvir_masses = Table.read(masses_dir + 'rvir_masses.hdf5', path='all_data')
        Rvir = rvir_masses['radius'][rvir_masses['snapshot'] == snap]
        dr = (outer_radius-inner_radius)/num_steps*Rvir
        chunks = ds.arr(np.arange(inner_radius*Rvir,outer_radius*Rvir+dr,dr), 'kpc')
    else:
        dr = (outer_radius-inner_radius)/num_steps*refine_width_kpc
        chunks = np.arange(inner_radius*refine_width_kpc,outer_radius*refine_width_kpc+dr,dr)

    # Load arrays of all fields we need
    print('Loading field arrays')
    sphere = ds.sphere(ds.halo_center_kpc, chunks[-1])

    radius = sphere['gas','radius_corrected'].in_units('kpc').v
    x = sphere['gas','x'].in_units('kpc').v - ds.halo_center_kpc[0].v
    y = sphere['gas','y'].in_units('kpc').v - ds.halo_center_kpc[1].v
    z = sphere['gas','z'].in_units('kpc').v - ds.halo_center_kpc[2].v

    vx = sphere['gas','vx_corrected'].in_units('km/s').v
    vy = sphere['gas','vy_corrected'].in_units('km/s').v
    vz = sphere['gas','vz_corrected'].in_units('km/s').v

    new_x = x + vx*dt*(100./cmtopc*stoyr)
    new_y = y + vy*dt*(100./cmtopc*stoyr)
    new_z = z + vz*dt*(100./cmtopc*stoyr)
    new_radius = np.sqrt(new_x**2. + new_y**2. + new_z**2.)
    temperature = np.log10(sphere['gas','temperature'].in_units('K').v)

    mass = sphere['gas','cell_mass'].in_units('Msun').v
    metal_mass = sphere['gas','metal_mass'].in_units('Msun').v
    fields = [mass, metal_mass]

    # Cut to just the shapes specified
    bool_inshapes = segment_region(radius, inner_radius, outer_radius, refine_width_kpc, Rvir=Rvir if args.units_rvir else 0, units_kpc=args.units_kpc, units_rvir=args.units_rvir)
    bool_inshapes_new = segment_region(new_radius, inner_radius, outer_radius, refine_width_kpc, Rvir=Rvir if args.units_rvir else 0, units_kpc=args.units_kpc, units_rvir=args.units_rvir)
    bool_inshapes_entire = (bool_inshapes) & (bool_inshapes_new)

    bool_nosat = np.ones(len(x), dtype=bool)

    # Cut to within shapes, entering/leaving shapes, and entering/leaving satellites
    fields_shapes = []
    radius_shapes = radius[(bool_inshapes_entire) & (bool_nosat)]
    new_radius_shapes = new_radius[(bool_inshapes_entire) & (bool_nosat)]
    temperature_shapes = temperature[(bool_inshapes_entire) & (bool_nosat)]
    for i in range(len(fields)):
        field = fields[i]
        fields_shapes.append(field[(bool_inshapes_entire) & (bool_nosat)])

    if (args.temp_cut): temps = [0.,4.,5.,6.,12.]
    else: temps = [0.]

    # Loop over chunks and compute fluxes to add to tables
    for r in range(len(chunks)-1):
        if (r%10==0): print("Computing chunk " + str(r) + "/" + str(len(chunks)) + " for snapshot " + snap)

        inner = chunks[r]
        row = [zsnap, inner]

        temp_up = temperature_shapes[(radius_shapes < inner) & (new_radius_shapes > inner)]
        temp_down = temperature_shapes[(radius_shapes > inner) & (new_radius_shapes < inner)]

        for i in range(len(fields)):
            iter = [0,1,2]
            field_up = fields_shapes[i][(radius_shapes < inner) & (new_radius_shapes > inner)]
            field_down = fields_shapes[i][(radius_shapes > inner) & (new_radius_shapes < inner)]

            for k in range(len(temps)):
                if (k==0):
                    field_up_t = field_up
                    field_down_t = field_down
                else:
                    field_up_t = field_up[(temp_up > temps[k-1]) & (temp_up < temps[k])]
                    field_down_t = field_down[(temp_down > temps[k-1]) & (temp_down < temps[k])]
                for j in iter:
                    if (j==0): row.append(np.sum(field_up_t)/dt - np.sum(field_down_t)/dt)
                    if (j==1): row.append(-np.sum(field_down_t)/dt)
                    if (j==2): row.append(np.sum(field_up_t)/dt)

        table.add_row(row)

    table = set_table_units(table)
    table.write(tablename, path='all_data', serialize_meta=True, overwrite=True)
    myprint('Saved table ' + tablename, args)

    return table

# ---------------------------------------------------------------------------------
def calc_source_sink(ds, refine_width_kpc, args):
    '''
    This function calculates the gas and metal mass sink and source, respectively, i.e.
    how much gas is being consumed by SF and how much metal is being produced, in a given
    spherical shell.
    '''
    StarMassEjectionFraction = 0.25 # from tempest RD0042 config file
    StarMetalYield = 0.025 # from tempest RD0042 config file

    # ------to ready the dataframe in which source sink will eventually be stored--------------
    df_columns = ['radius', 'gas_produced', 'metal_produced', 'nstars', 'current_gas', 'current_metal']
    df = pd.DataFrame(columns=df_columns)

    # ------to ready the dataframe in which source sink will eventually be stored--------------
    newstars_df_columns = ['radial_pos', 'mass', 'Z_star', 'vrad', 'age', 'Z_gas']
    newstars_df = pd.DataFrame(columns=newstars_df_columns)

    # ---------to add new particle filter to get stars that only just formed in this snapshot--------
    yt.add_particle_filter('new_stars', function=new_stars, filtered_type='all', requires=['particle_type', 'creation_time'])
    ds.add_particle_filter('new_stars')

    # ----------to define list of ways to chunk up the shape over radius or height----------
    inner_radius = 0.3 # kpc; because yt can't take sphere smaller than 0.3 kpc
    outer_radius = args.galrad # kpc
    num_steps = args.nchunks

    if args.units_kpc:
        dr = (outer_radius-inner_radius)/num_steps
        bin_edges = ds.arr(np.arange(inner_radius, outer_radius + dr, dr), 'kpc')
    elif args.units_rvir:
        # ----- to load the mass enclosed profile--------
        masses_dir = args.code_path + 'halo_infos/00' + args.halo + '/' + args.run + '/'
        rvir_masses = Table.read(masses_dir + 'rvir_masses.hdf5', path='all_data')
        Rvir = rvir_masses['radius'][rvir_masses['snapshot'] == args.output]
        dr = (outer_radius - inner_radius)/num_steps * Rvir
        bin_edges = ds.arr(np.arange(inner_radius * Rvir, outer_radius * Rvir + dr, dr), 'kpc')
    else:
        dr = (outer_radius-inner_radius)/num_steps * refine_width_kpc
        bin_edges = np.arange(inner_radius * refine_width_kpc, outer_radius * refine_width_kpc + dr, dr)

    # ------looping over bins and compute source and sink terms to add to table-------------
    for index in range(len(bin_edges)-1):
        this_rad = bin_edges[index] # right bin edge
        start_time_this_shell = time.time()

        if index: # all but the first bin are shells
            myprint('Computing for shell #' + str(index + 1) + ' out of ' + str(len(bin_edges) - 1) + ' shells, which extends from ' + str(bin_edges[index - 1]) + ' to ' + str(bin_edges[index]), args)
            smaller_sphere = ds.sphere(ds.halo_center_kpc, bin_edges[index - 1])
            larger_sphere = ds.sphere(ds.halo_center_kpc, bin_edges[index])
            shell = larger_sphere - smaller_sphere
        else: # the first radial bin is a small sphere
            myprint('Computing for shell #' + str(index + 1) + ' out of ' + str(len(bin_edges) - 1) + ' shells, which is a sphere up to ' + str(bin_edges[index]), args)
            shell = ds.sphere(ds.halo_center_kpc, bin_edges[index])

        # ------to get age, mass & metallicity of new stars in the shell---------
        age_star = shell['new_stars', 'age'].in_units('Myr')
        mass_star = shell['new_stars', 'particle_mass'].in_units('Msun')
        Z_star = shell['new_stars', 'metallicity_fraction'].in_units('Zsun')
        nstars = len(mass_star)

        # ------to get radial pos & vel of new stars in the shell, relative to halo---------
        xgrid = shell['new_stars', 'particle_position_x'].in_units('kpc')
        zgrid = shell['new_stars', 'particle_position_z'].in_units('kpc')
        ygrid = shell['new_stars', 'particle_position_y'].in_units('kpc')

        vxgrid = shell['new_stars', 'particle_velocity_x'].in_units('km/s')
        vygrid = shell['new_stars', 'particle_velocity_y'].in_units('km/s')
        vzgrid = shell['new_stars', 'particle_velocity_z'].in_units('km/s')

        temp_df = pd.DataFrame({'pos_x': xgrid, 'pos_y': ygrid, 'pos_z': zgrid, 'vel_x': vxgrid, 'vel_y': vygrid, 'vel_z': vzgrid}) # the function shift_ref_frame() requires exactly these column names
        temp_df = shift_ref_frame(temp_df, args) # to get coordinates relative to halo center
        temp_df = get_radial_velocity(temp_df) # to get radial pos & vel
        pos_star = temp_df['rad']
        vrad_star = temp_df['vrad']

        # ------to get AMBIENT metallicity of gas around new stars in the shell---------
        coord = ds.arr(np.vstack([xgrid, ygrid, zgrid]).transpose().value, 'kpc').in_units('code_length') # coord has to be in code_lengths for find_field_values_at_points() to work
        Z_gas = shell.ds.find_field_values_at_points([('gas', 'metallicity')], coord).in_units('Zsun')

        # ------to get overall gas quantities in the shell---------
        current_gas_mass = np.sum(shell[('gas', 'mass')].in_units('Msun'))
        current_metal_mass = np.sum(shell[('gas', 'metal_mass')].in_units('Msun'))

        # --- From from https://enzo.readthedocs.io/en/latest/physics/star_particles.html#star-particles: -----------------------
        # --- M_ej = M_form * StarMassEjectionFraction of gas are returned to the grid and removed from the particle. -----------
        # --- M_form * ((1 - Z_star) * StarMetalYield + StarMassEjectionFraction * Z_star) of metals are added to the cell, -----
        # --- where Z_star is the star particle metallicity. This formulation accounts for gas recycling back into the stars. ---

        total_new_mass = np.sum(mass_star)
        total_gas_used = (1 - StarMassEjectionFraction) * total_new_mass # net gas mass that gets converted into stellar mass
        metal_sources = mass_star * ((1 - Z_star) * StarMetalYield + StarMassEjectionFraction * Z_star) # factor 0.25 from
        # metal_sources = 0.025 * m_star * (1 - Z_star) + 0.25 * Z_star # from Peeples+2019, but this is probably wrong, based on dimensional analysis
        total_metal_produced = np.sum(metal_sources)

        # --------to store the gas/metal mass source sink terms in df-----------
        row = [this_rad.value, -1. * total_gas_used.value, total_metal_produced.value, nstars, current_gas_mass.value, current_metal_mass.value] # the -1 factor to denote sink, i.e., -ve gain in gas mass
        df.loc[len(df)] = row

        # --------to store the star particle properties in newstars_df------------
        quant_arr = [pos_star, mass_star, Z_star, vrad_star, age_star, Z_gas]
        thisbin_df = pd.DataFrame({newstars_df_columns[i]: quant_arr[i] for i in range(len(newstars_df_columns))})
        newstars_df = newstars_df.append(thisbin_df, ignore_index=True)
        print_mpi('This shell with ' + str(nstars) + ' stars completed in %s' % (datetime.timedelta(seconds=time.time() - start_time_this_shell)), args)

    # ------define new columns and store table--------
    df['current_Z'] = (df['current_metal'] / df['current_gas']) / metallicity_sun # to convert to Zsun
    df.to_csv(args.source_table_name, sep='\t', index=None)
    myprint('Saved source sink table as ' + args.source_table_name, args)

    # ------define new columns and store table--------
    newstars_df['metal_mass'] = newstars_df['mass'] * newstars_df['Z_star'] * metallicity_sun # because metallicity is in Zsun units
    newstars_df.to_csv(args.starlistfile, sep='\t', index=None)
    myprint('Saved new stars table as ' + args.starlistfile, args)

    return df

# ---------------------------------------------------------------------------------
def overplot_stars(axes, args, colorcol='log_Z_gas'):
    '''
    Function to overplot new stars on existing plot
    '''
    # -------------to read in simulation data------------
    paramlist = pd.read_table(args.starlistfile, delim_whitespace=True, comment='#') # has columns ['radial_pos', 'mass', 'Z_star', 'vrad', 'age', 'Z_gas', 'metal_mass']
    paramlist['log_Z_star'] = np.log10(paramlist['Z_star'])
    paramlist['log_Z_gas'] = np.log10(paramlist['Z_gas'])

    clabel_dict = {'log_Z_star':r'Log Stellar metallicity (Z/Z$_{\odot}$)', 'Z_star':r'Stellar metallicity (Z/Z$_{\odot}$)', 'log_Z_gas':r'Log Gas metallicity (Z/Z$_{\odot}$)', 'Z_gas':r'Gas metallicity (Z/Z$_{\odot}$)', 'vrad': 'Radial velocity (km/s)', 'age': 'Age (Myr)', 'radius': 'Star particle radius (pc)'}
    clim_dict = {'log_Z_star': (-1.0, 0.4), 'Z_star': (-0.5, 0.3), 'log_Z_gas': (-1.0, 0.4), 'Z_gas': (-0.5, 0.3), 'vrad': (-100, 100), 'age': (0, 5), 'radius': (0, 200)}
    cmap_dict = {'log_Z_star': metal_discrete_cmap, 'Z_star': metal_discrete_cmap, 'log_Z_gas': metal_discrete_cmap, 'Z_gas': metal_discrete_cmap, 'vrad': outflow_inflow_discrete_cmap, 'age': 'viridis', 'radius': 'viridis'}

    # -------------to actually plot the simulation data------------
    ycol_arr = ['mass', 'metal_mass', 'log_Z_star']
    
    for index, ax in enumerate(axes):
        im = ax.scatter(paramlist['radial_pos'], paramlist[ycol_arr[index]], c=paramlist[colorcol], edgecolors='black', lw=0.2, s=15, cmap=cmap_dict[colorcol], vmin=clim_dict[colorcol][0], vmax=clim_dict[colorcol][1])
    print_mpi('Overplotted ' + str(len(paramlist)) + ' new star particles', args)

    ax_xpos, ax_ypos, ax_width, ax_height = 0.92, 0.1, 0.01, 0.8
    cax = ax.figure.add_axes([ax_xpos, ax_ypos, ax_width, ax_height])
    ax.figure.colorbar(im, cax=cax, orientation='vertical')
    cax.set_ylabel(clabel_dict[colorcol], fontsize=args.fontsize)
    cax.set_yticklabels(['%.1F'%item for item in cax.get_yticks()], fontsize=args.fontsize * 0.75)

    return axes

# -----------------------------------------------------
def make_flux_plot(table_name, fig_name, args):
    '''
    Function to read in hdf5 files created by Cassi's flux_tracking.py and plot the 'metallicity flux' vs radius,
    where 'metallicity flux' is the metal_mass/gas_mass of the inflowing OR outflowing material
    '''
    df = pd.read_hdf(table_name, key='all_data') # read in table
    df['radius'] = np.round(df['radius'], 3)

    # ------create new columns for 'metallicity'--------
    df['net_Z_flux'] = (df['net_metal_flux'] / df['net_gas_flux']) / metallicity_sun # to convert to Zsun
    df['Z_flux_in'] = (df['metal_flux_in'] / df['gas_flux_in']) / metallicity_sun # to convert to Zsun
    df['Z_flux_out'] = (df['metal_flux_out'] / df['gas_flux_out']) / metallicity_sun # to convert to Zsun

    quant_arr = ['gas', 'metal', 'Z']
    ylabel_arr = [r'Gas mass (M$_{\odot}$/yr)', r'Metal mass (M$_{\odot}$/yr)', r'log Metallicity (Z/Zsun)']
    if args.overplot_source_sink: ylim_arr = [(-1e6, 1e10), (-10, 1e8), (-1.0, 0.4)]
    else: ylim_arr = [(-100, 1000), (-10, 100), (-1.3, 0.5)]

    # -------read in source sink dataframe----------------
    if args.overplot_source_sink:
        df_ss = pd.read_table(args.source_table_name, delim_whitespace=True, comment='#')
        df_ss['radius'] = np.round(df_ss['radius'], 3)
        df = pd.merge(df, df_ss)
        df['previous_gas'] = df['current_gas'] - df['gas_produced'] - df['net_gas_flux']
        df['previous_metal'] = df['current_metal'] - df['metal_produced'] - df['net_metal_flux']
        df['previous_Z'] = (df['previous_metal'] / df['previous_gas']) / metallicity_sun # to convert to Zsun

        df['net_gas_appear'] = df['net_gas_flux'] + df['gas_produced'] # net gas mass that appears (net amount moved in + net amount produced)
        df['net_metal_appear'] = df['net_metal_flux'] + df['metal_produced'] # net metal mass that appears (net amount moved in + net amount produced)
        df['net_Z_appear'] = df['current_Z'] - df['previous_Z']

    # -------to convert all Z related quantities to log-----------
    df = df.dropna() # usually the first row (innrermost shell)  has 0/0 = NaNs
    Z_cols = [item for item in df.columns if 'Z' in item]
    for thiscol in Z_cols:
        df[thiscol] = np.log10(df[thiscol])
        df = df.rename(columns={thiscol : 'log_' + thiscol})

    if args.overplot_source_sink: df['log_Z_produced'] = np.ones(len(df)) * np.nan  # dummy column just for sake of continuity of the code, lengds, etc.

    # --------plot radial profiles----------------
    fig, axes = plt.subplots(1, 3, figsize=(14,5))
    extra_space = 0.07 if not args.overplot_stars else 0
    plt.subplots_adjust(wspace=0.3, right=0.9 + extra_space, top=0.95, bottom=0.12, left=0.08)

    for index, ax in enumerate(axes):
        prefix = 'log_' if quant_arr[index] == 'Z' else ''
        ax.axhline(0, c='k', ls='--', lw=0.5)
        ax.plot(df['radius'], df[prefix + quant_arr[index] + '_flux_in'], c='cornflowerblue', label='Incoming')
        ax.plot(df['radius'], df[prefix + quant_arr[index] + '_flux_out'], c='sienna', label='Outgoing')
        ax.plot(df['radius'], df[prefix + 'net_' + quant_arr[index] + '_flux'], c='gray', alpha=0.5, label='Net flux')
        if args.overplot_source_sink:
            ax.plot(df['radius'], df[prefix + quant_arr[index] + '_produced'], c='salmon', label='Net_produced')
            #ax.plot(df['radius'], df[prefix + 'net_' + quant_arr[index] + '_appear'], c='darkgreen', label='Net appeared')

            ax.plot(df['radius'], df[prefix + 'previous_' + quant_arr[index]], c='cyan', label='Previous')
            ax.plot(df['radius'], df[prefix + 'current_' + quant_arr[index]], c='blue', ls='dashed', label='Current')

        if index == 2: ax.legend(fontsize=args.fontsize * 0.75, loc='lower right')
        ax.set_xlim(0, args.galrad)
        ax.set_xlabel('Radius (kpc)', fontsize=args.fontsize)
        ax.set_xticks(np.linspace(0, args.galrad, 5))
        ax.set_xticklabels(['%.1F'%item for item in ax.get_xticks()], fontsize=args.fontsize * 0.75)

        if quant_arr[index] != 'Z': ax.set_yscale('symlog') # metallicity panel is not on log-scale, but the metallicity values themselves are in log
        ax.set_ylim(ylim_arr[index])
        ax.set_ylabel(ylabel_arr[index], fontsize=args.fontsize)
        ax.set_yticklabels(['%.2F'%item if quant_arr[index] == 'Z' else '%.0E'%item for item in ax.get_yticks()], fontsize=args.fontsize * 0.75)

    # ----------to overplot young stars----------------
    if args.overplot_stars: axes = overplot_stars(axes, args, colorcol=args.colorcol[0])

    ax.text(0.95, 0.97, 'z = %.4F' % args.current_redshift, transform=ax.transAxes, fontsize=args.fontsize, ha='right', va='top')
    ax.text(0.95, 0.9, 't = %.3F Gyr' % args.current_time, transform=ax.transAxes, fontsize=args.fontsize, ha='right', va='top')

    plt.savefig(fig_name, transparent=False)
    myprint('Saved figure ' + fig_name, args)
    if not args.do_all_sims: plt.show(block=False)

    return df, fig

# -----main code-----------------
if __name__ == '__main__':
    start_time = time.time()
    dummy_args_tuple = parse_args('8508', 'RD0042')  # default simulation to work upon when comand line args not provided
    if type(dummy_args_tuple) is tuple: dummy_args = dummy_args_tuple[0] # if the sim has already been loaded in, in order to compute the box center (via utils.pull_halo_center()), then no need to do it again
    else: dummy_args = dummy_args_tuple
    if not dummy_args.keep: plt.close('all')

    if dummy_args.do_all_sims:
        list_of_sims = get_all_sims(dummy_args) # all snapshots of this particular halo
    else:
        if dummy_args.do_all_halos: halos = get_all_halos(dummy_args)
        else: halos = dummy_args.halo_arr
        list_of_sims = list(itertools.product(halos, dummy_args.output_arr))
    total_snaps = len(list_of_sims)

    cmtopc = 3.086e18
    stoyr = 3.155e7
    dt = 5.38e6 # yr

    # --------domain decomposition; for mpi parallelisation-------------
    comm = MPI.COMM_WORLD
    ncores = comm.size
    rank = comm.rank
    print_master('Total number of MPI ranks = ' + str(ncores) + '. Starting at: {:%Y-%m-%d %H:%M:%S}'.format(datetime.datetime.now()), dummy_args)
    comm.Barrier() # wait till all cores reached here and then resume

    split_at_cpu = total_snaps - ncores * int(total_snaps/ncores)
    nper_cpu1 = int(total_snaps / ncores)
    nper_cpu2 = nper_cpu1 + 1
    if rank < split_at_cpu:
        core_start = rank * nper_cpu2
        core_end = (rank+1) * nper_cpu2 - 1
    else:
        core_start = split_at_cpu * nper_cpu2 + (rank - split_at_cpu) * nper_cpu1
        core_end = split_at_cpu * nper_cpu2 + (rank - split_at_cpu + 1) * nper_cpu1 - 1

    # --------------------------------------------------------------
    print_mpi('Operating on snapshots ' + str(core_start + 1) + ' to ' + str(core_end + 1) + ', i.e., ' + str(core_end - core_start + 1) + ' out of ' + str(total_snaps) + ' snapshots', dummy_args)

    for index in range(core_start + dummy_args.start_index, core_end + 1):
        start_time_this_snapshot = time.time()
        this_sim = list_of_sims[index]
        print_mpi('Doing snapshot ' + this_sim[1] + ' of halo ' + this_sim[0] + ' which is ' + str(index + 1 - core_start) + ' out of the total ' + str(core_end - core_start + 1) + ' snapshots...', dummy_args)
        try:
            if len(list_of_sims) == 1 and not dummy_args.do_all_sims: args = dummy_args_tuple # since parse_args() has already been called and evaluated once, no need to repeat it
            else: args = parse_args(this_sim[0], this_sim[1])

            if type(args) is tuple:
                args, ds, refine_box = args  # if the sim has already been loaded in, in order to compute the box center (via utils.pull_halo_center()), then no need to do it again
                print_mpi('ds ' + str(ds) + ' for halo ' + str(this_sim[0]) + ' was already loaded at some point by utils; using that loaded ds henceforth', args)
            else:
                ds, refine_box = load_sim(args, region='refine_box', do_filter_particles=False)

        except (FileNotFoundError, PermissionError) as e:
            print_mpi('Skipping ' + this_sim[1] + ' because ' + str(e), dummy_args)
            continue

        # parse paths and filenames
        fig_dir = args.output_dir + 'figs/' if args.do_all_sims else args.output_dir + 'figs/' + args.output + '/'
        Path(fig_dir).mkdir(parents=True, exist_ok=True)
        table_dir = args.output_dir + 'txtfiles/'
        Path(table_dir).mkdir(parents=True, exist_ok=True)

        refine_width_kpc = ds.arr(ds.refine_width, 'kpc')
        args.current_redshift = ds.current_redshift
        args.current_time = ds.current_time.in_units('Gyr')
        args.dt = dt / 1e6 # Myr

        # ----------generating the flux tracking tables----------
        table_name = table_dir + args.output + '_rad' + str(args.galrad) + 'kpc_nchunks' + str(args.nchunks) + '_fluxes_mass.hdf5'
        if not os.path.exists(table_name) or args.clobber:
            if not os.path.exists(table_name):
                print_mpi(table_name + ' does not exist. Creating afresh..', args)
            elif args.clobber:
                print_mpi(table_name + ' exists but over-writing..', args)

            table = calc_fluxes(ds, args.output, args.current_redshift, dt, refine_width_kpc, table_name, args)
            # inner and outer radii of sphere are by default as a fraction of refine_box_width, unless --units_kpc is specified in user args, in whic case they are in kpc
        else:
            print_mpi('Skipping ' + table_name + ' because file already exists (use --clobber to over-write)', args)

        # ----------generating the sink-source tables----------
        args.source_table_name = table_dir + args.output + '_rad' + str(args.galrad) + 'kpc_nchunks' + str(args.nchunks) + '_metal_sink_source.txt'
        args.starlistfile = table_dir + args.output + '_rad' + str(args.galrad) + 'kpc_new_stars_properties.txt'

        if args.overplot_source_sink:
            if not os.path.exists(args.source_table_name) or args.clobber:
                if not os.path.exists(args.source_table_name):
                    print_mpi(args.source_table_name + ' does not exist. Creating afresh..', args)
                elif args.clobber:
                    print_mpi(args.source_table_name + ' exists but over-writing..', args)

                source_sink_table = calc_source_sink(ds, refine_width_kpc, args)
                # inner and outer radii of sphere are by default as a fraction of refine_box_width, unless --units_kpc is specified in user args, in whic case they are in kpc
            else:
                print_mpi('Skipping ' + args.source_table_name + ' because file already exists (use --clobber to over-write)', args)

        # ----------generating the new stars table----------
        if args.overplot_stars:
            if not os.path.exists(args.starlistfile) or args.clobber:
                if not os.path.exists(args.starlistfile):
                    print_mpi(args.starlistfile + ' does not exist. Creating afresh..', args)
                elif args.clobber:
                    print_mpi(args.starlistfile + ' exists but over-writing..', args)

                source_sink_table = calc_source_sink(ds, refine_width_kpc, args)
                # inner and outer radii of sphere are by default as a fraction of refine_box_width, unless --units_kpc is specified in user args, in whic case they are in kpc
            else:
                print_mpi('Skipping ' + args.starlistfile + ' because file already exists (use --clobber to over-write)', args)

        # ----------plotting the tracked flux----------
        outfile_rootname = 'metal_flux_profile_boxrad_%.2Fkpc.png' % (args.galrad)
        if args.do_all_sims: outfile_rootname = 'z=*_' + outfile_rootname
        fig_name = fig_dir + outfile_rootname.replace('*', '%.5F' % (args.current_redshift))

        if not os.path.exists(fig_name) or args.clobber_plot:
            if not os.path.exists(fig_name):
                print_mpi(fig_name + ' plot does not exist. Creating afresh..', args)
            elif args.clobber_plot:
                print_mpi(fig_name + ' plot exists but over-writing..', args)

            df, fig = make_flux_plot(table_name, fig_name, args)
        else:
            print_mpi('Skipping ' + fig_name + ' because plot already exists (use --clobber_plot to over-write)', args)

        print_mpi('This snapshot ' + this_sim[1] + ' completed in %s' % (datetime.timedelta(seconds=time.time() - start_time_this_snapshot)), args)
    comm.Barrier() # wait till all cores reached here and then resume

    if args.makemovie and args.do_all_sims:
        print_master('Finished creating snapshots, calling animate_png.py to create movie..', args)
        if args.do_all_halos: halos = get_all_halos(args)
        else: halos = dummy_args.halo_arr
        for thishalo in halos:
            args = parse_args(thishalo, 'RD0020') # RD0020 is inconsequential here, just a place-holder
            fig_dir = args.output_dir + 'figs/'
            subprocess.call(['python ' + HOME + '/Work/astro/ayan_codes/animate_png.py --inpath ' + fig_dir + ' --rootname ' + outfile_rootname + ' --delay ' + str(args.delay_frame) + ' --reverse'], shell=True)

    if ncores > 1: print_master('Parallely: %d snapshots completed in %s using %d cores' % (total_snaps, datetime.timedelta(seconds=time.time() - start_time), ncores), dummy_args)
    else: print_master('Serially: %d snapshots completed in %s using %d core' % (total_snaps, datetime.timedelta(seconds=time.time() - start_time), ncores), dummy_args)
