import pandas as pd
import sys
import os
import stat
import columns
from columns import _columns_of_interest, _ions_of_interest
import util


# Number of times info is printed to stdout
_KINFO = 10


# Number of times GRIDDATA is saved
_KGRID = 50


# Number of times PARTICLEDATA is saved
_KPART = 50


# Number of times fluid data is saved
_KFLUID = 50


def get_domain_debye_lengths(df_row):
    p1 = 50
    return p1


def get_grid_points_per_debye_length(df_row):
    p2 = 1
    return p2


def get_time_steps_per_gyroperiod(df_row):
    p3 = 20
    return p3


def get_num_ion_transit_times(df_row):
    p4 = 1
    return p4


def get_num_particles_per_cell(df_row):
    p5 = 500
    return p5


def format_hPIC_command_line_args(df_row, output_dir):
    cla = ''

    SimID = get_simulation_id(df_row)
    cla += SimID + ' '

    p1 = get_domain_debye_lengths(df_row)
    p2 = get_grid_points_per_debye_length(df_row)
    p3 = get_time_steps_per_gyroperiod(df_row)
    p4 = get_num_ion_transit_times(df_row)
    p5 = get_num_particles_per_cell(df_row)
    cla += ' '.join((str(p) for p in (p1, p2, p3, p4, p5))) + ' '

    B0 = df_row['|B| (T)']
    psi = df_row['Bangle (deg)']

    Te = df_row['Te (eV)']
    Ti = df_row['Ti (eV)']
    cla += ' '.join(f'{x:.5f}' for x in (B0, psi, Te, Ti)) + ' '

    BC_LEFT_VALUE = 0.0
    BC_RIGHT_VALUE = 0.0
    cla += f'{BC_LEFT_VALUE:.5f} {BC_RIGHT_VALUE:.5f} '

    # RF wave Frequency [rad/s
    Omega = 0.0
    RF_VOLTAGE_RIGHT = 0.0
    RF_VOLTAGE_LEFT = 0.0
    cla += f'{Omega:.2f} {RF_VOLTAGE_RIGHT:.2f} {RF_VOLTAGE_LEFT:.2f} '

    # Global print and save options (defined at the top)
    cla += f'{_KINFO} {_KGRID} {_KPART} {_KFLUID} '

    for ion, mass_info in _ions_of_interest.items():
        Ai = mass_info['Ai']
        Zi = mass_info['Zi']
        ni = df_row[ion]

        cla += f'{Ai} {Zi} {ni:.5e} '


    """
    Pummi args
    """

    # Total number of submeshes in the domain
    N = 1
    cla += f'{N} '
    # active mesh type segment in the i-th mesh
    typeflag_i = 'uniform'

    # number of Debye Lengths in the i-th mesh. Using a dummy value since
    # we're using "uniform"
    p1_i = '50'

    # number of elements in the i-th submesh. Using dummy value since we're
    # using "uniform"
    Nel_i = '60'

    # For the leftBL/rightBL, Number of minimum size cells in a Debye Length
    # for the i-th submesh. Using dummy value since we're using "uniform"
    p2_min_i = '0'
    cla += '"' + '" "'.join((typeflag_i, p1_i, Nel_i, p2_min_i)) + '"'

    return cla, SimID


def get_data_set_label(datafile):
    data_set_label = datafile.split('/')[-1].split('.')[0]
    return data_set_label


def get_simulation_id(df_row):
    """
    One hPIC simulation per position relative to the Strike Point
    """
    separation = df_row['L-Lsep (m)']
    sign = 'plus_' if separation > 0 else 'minus_'
    simulation_id = f'{sign}{abs(separation):.3f}'+ 'm_separation'
    return simulation_id


def mkdir(dirname):
    if not os.path.exists(dirname):
        os.mkdir(dirname)


def main():
    if len(sys.argv) < 2:
        print('usage: $python run_simulations.py <SOLPS_CSV_DATAFILE>')
        return
    datafile = sys.argv[1]

    # Make a directory to hold the output of all simulations
    results_dir = 'hpic_results'
    mkdir(results_dir)

    data_set_label = get_data_set_label(datafile)

    # write commands to a bash script, to be executed in order to run
    # simulations
    simulation_script_filename = 'scripts/run-hpic-' + data_set_label + '.sh'
    simulation_script = open(simulation_script_filename, 'w+')
    simulation_script.write(
        '#!/usr/bin/env bash\n'
        + '\n'
        + '# Generated by configure_simulations.py\n'
        + '\n'
        + '# Runs one hPIC simulation per row of data from SOLPS output\n'
        + '# i.e one simulation per position from the strike point\n'
        + '\n'
        + '# Assumes compiled 1d3v hpic binary is in PATH\n\n\n',
    )

    df = util.load_solps_data(datafile, columns_subset = _columns_of_interest)

    # Make a directory to hold these results
    data_set_output_dir = results_dir + '/' + data_set_label
    util.mkdir(data_set_output_dir)

    for index, row in df.iterrows():
        hpic_args, SimID = format_hPIC_command_line_args(
            row, data_set_output_dir,
        )

        # Each simulation has its own directory
        simulation_dir = data_set_output_dir + '/' + SimID
        util.mkdir(data_set_output_dir + '/' + SimID)

        # Write the simulation command to the bash script
        simulation_script.write(
            f'# Run the simulation for {SimID}\n'
            + f'cd {simulation_dir}\n'
            + f'hpic -command_line {hpic_args}\n'
            + f' cd ../../..\n\n',
        )

    simulation_script.close()
    util.make_executable(simulation_script_filename)


if __name__ == '__main__':
    main()
