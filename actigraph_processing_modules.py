# modules for processing the actigraph data

# ---------------
# import packages
import pandas as pd
import numpy as np
import os.path
from pygt3x.reader import FileReader
from agcounts.extract import get_counts


# ----------------- #
# Import .gt3x data #
# ----------------- #
# stolen from pygt3x (Actigraph GitHub)
# outputs .csv file

def actigraph_import(fname, out_fname):

    if os.path.isfile(out_fname): #if the file already exists
        print('\n --> SKIPPING: Already Exists')
    else: #if it doesn't exist
        # Read raw data and calibrate, then export to pandas data frame
        with FileReader(fname) as reader:
            was_idle_sleep_mode_used = reader.idle_sleep_mode_activated
            df = reader.to_pandas()
            # print(df.head(5))

        df.to_csv(out_fname)

# --------------------------------- #
# Get Activity Counts from raw data #
# --------------------------------- #
# stolen from agcounts GitHub

def get_counts_csv(
    file,
    freq: int,
    epoch: int,
    fast: bool = True,
    verbose: bool = False,
    time_column: str = None,
):
    if verbose:
        print("Reading in CSV", flush=True)
    raw = pd.read_csv(file, skiprows=0)

    if time_column is not None:
        ts = raw[time_column]
        ts = pd.to_datetime(ts)
        time_freq = str(epoch) + "S"
        ts = ts.dt.round(time_freq)
        ts = ts.unique()
        ts = pd.DataFrame(ts, columns=[time_column])
    raw = raw[["X", "Y", "Z"]]

    if verbose:
        print("Converting to array", flush=True)
    raw = np.array(raw)

    if verbose:
        print("Getting Counts", flush=True)
    counts = get_counts(raw, freq=freq, epoch=epoch, fast=fast)
    del raw
    counts = pd.DataFrame(counts, columns=["Axis1", "Axis2", "Axis3"])
    counts["AC"] = (
        counts["Axis1"] ** 2 + counts["Axis2"] ** 2 + counts["Axis3"] ** 2
    ) ** 0.5
    ts = ts[0 : counts.shape[0]]

    if time_column is not None:
        counts = pd.concat([ts, counts], axis=1)


    return counts


# ------------------ #
# Validate Wear Time #
# ------------------ #
# Using Toriani (2007) specs
# --
# non-wear time: >=60min of 0 CPM (vertical axis),
#  spike tolerance of 2 consecutive mins,
#  spike level >= 100 CPM (vertical axis) breaks nonwear cycle
# --

def validate_wear_time(
        df, inactive_count_threshold, active_spike_threshold,
        valid_day_count_threshold, valid_day_threshold
):

    # ------------------------------------
    # start with determining if being worn
    # ------------------------------------
    df['wearing'] = np.nan #added column to track (NaNs)

    total_secs = len(df['AC'])

    # -----------------------------------------------
    # cycle through each input, determine if inactive
    # -----------------------------------------------
    inactive_count = 0
    inactive_start_idx = 0
    active_spike_count = 0
    for sec_i in range(0, total_secs):
        count_i = df['Axis2'][sec_i]

        # --------------------------
        # if inactive, update counts
        if count_i < 100:
            inactive_count += 1
            active_spike_count = 0

            # if first inactive, get index
            if inactive_count == 1:
                inactive_start_idx = sec_i

        else:
            active_spike_count += 1

        # --------------------------------
        # if we reach the count thresholds
        if inactive_count == inactive_count_threshold:
            df['wearing'][inactive_start_idx:(sec_i + 1)] = 0 #need to add 1 to make sure current column accounted for
            inactive_count = 0

        if active_spike_count == active_spike_threshold:
            # check if continuation of inactivity
            if df['wearing'][inactive_start_idx - 1] == 0:
                # if a continuation, set active markers to start with activity,
                # fill in the cells between the end of previously marked inactivity and
                # the start of the new activity
                active_start = sec_i - 2
                df['wearing'][inactive_start_idx:active_start] = 0
            else:
                active_start = inactive_start_idx
            df['wearing'][active_start:(sec_i + 1)] = 1 # subtract 2 because want 3 but current is third
            inactive_count = 0

        elif active_spike_count > active_spike_threshold:
            df['wearing'][sec_i] = 1

    # mark the last hour as not wearing (I might have jostled them..)
    df['wearing'][total_secs - 60:total_secs + 1] = 0


    # ----------------------
    # determine if valid day
    # ----------------------
    # need 600 mins for day to be valid
    df['valid_day'] = np.nan
    df['day_count'] = np.nan

    # ------------------
    # cycle through days
    # turns on at 4am
    # split into days from 4am-4am
    secs_day = 24 * 60
    total_days = total_secs // secs_day #divides and rounds down (int)
    valid_day_count = 0
    day_i = 1

    day_counts_df = pd.DataFrame(columns = ['day', 'counts']) #init df for subj x day output

    day_loop = True
    while day_loop:
        day_end = secs_day * day_i
        if day_end > total_secs:
            end_discrepancy = day_end - total_secs
            day_end = (secs_day * day_i) - end_discrepancy + 1
            day_start = day_end - (secs_day - end_discrepancy)
        else:
            day_start = day_end - secs_day

        # ----------------------
        # determine if valid day
        day_count = len(df['wearing'][day_start:day_end] == 1)
        if day_count >= valid_day_count_threshold:
            day_valid = list( np.ones(len( df['valid_day'][day_start:day_end] )) )
            valid_day_count += 1
        else:
            day_valid = list( np.ones(len( df['valid_day'][day_start:day_end] )) * 0 )
        df['valid_day'][day_start:day_end] = day_valid

        # update day
        df['day_count'][day_start:day_end] = day_i

        # -------------
        # update counts
        day_i += 1 #update to next day
        # break loop if after last day
        if day_i > (total_days + 1):
            day_loop = False


    # -----------------------
    # determine if valid subj
    # -----------------------
    # need 3 or 4 days of data
    if valid_day_count >= valid_day_threshold:
        df['valid_subj'] = 1
    else:
        df['valid_subj'] = 0


    return df


# -------------- #
# Calculate METs #
# -------------- #
# Santos-Lozano et al. (2013)
# Actigraph GT3X: Validation and Determination of Physical Activity Intensity Cut Points
# METs = 2.8323 + 0.00054 · VMactivitycounts(counts · min− 1) – 0.059123 · bodymass(kg) + 1.4410 · gender(women=1, men=2)

def calculate_METs_MVPA(df, protocol_data, subj_i, ctrl_weight):
    # add METs row
    df['METs'] = 0  # init at zero (going to sum it)

    # -------------------
    # calculate body mass
    df_bw = protocol_data[['snum', 'weight', 'weightscale_baseline']].dropna().reset_index(drop = True)
    df_bw = df_bw.iloc[2:,:]
    df_bw = df_bw[df_bw['snum'].astype(int) == int(subj_i)]

    weight = float(df_bw['weight'])
    weightscale_baseline = float(df_bw['weightscale_baseline'])

    # calculate calibrated and corrected weight
    calibrated_weight_kg = ( weight + ( weightscale_baseline - ctrl_weight ) ) * .453592

    # ---------------------------------------
    # convert gender (they actually mean sex)
    df_sex = protocol_data[['snum', 'sex']].dropna().reset_index(drop = True)
    df_sex = df_sex.iloc[2:,:]
    df_sex = df_sex[df_sex['snum'].astype(int) == int(subj_i)]

    if str(df_sex['sex']) == 'Female':
        sex_num = 1
    elif str(df_sex['sex']) == 'Male':
        sex_num = 2
    else: #compromise
        sex_num = 1.5

    # --------------
    # calculate METs
    valid_rows = (df['subj'] == subj_i) & (df['valid_day'] == 1) & (df['wearing'] == 1)
    # VM = sqrt(x^2 + y^2 + z^2)
    VMx_counts = list(np.array(df.loc[valid_rows, 'Axis1'])**2)
    VMy_counts = list(np.array(df.loc[valid_rows, 'Axis2'])**2)
    VMz_counts = list(np.array(df.loc[valid_rows, 'Axis3'])**2)
    VM_counts = np.sqrt(np.sum(np.array([VMx_counts, VMy_counts, VMz_counts]), axis = 0))

    num_days = len(np.unique(df.loc[valid_rows, 'day_count']))
    mins = len(df[ valid_rows ])
    METs_min = 2.823 + ( 0.00054 * VM_counts ) - (0.059123 * calibrated_weight_kg) + (1.441 * sex_num)
    if mins == 0:
        METs = 0
        METs_daily_ave = 0
        mins_daily_ave = 0
    else:
        METs = sum(METs_min) / mins
        METs_daily_ave = sum(METs_min) / num_days
        mins_daily_ave = mins / num_days

    # --------------
    # calculate MVPA
    MVPA_rows = (df['AC'] >= 3208) & (df['subj'] == subj_i) & (df['wearing'] == 1) & (df['valid_day'] == 1)
    MVPA_VMx_counts = list(np.array(df.loc[MVPA_rows, 'Axis1'])**2)
    MVPA_VMy_counts = list(np.array(df.loc[MVPA_rows, 'Axis2'])**2)
    MVPA_VMz_counts = list(np.array(df.loc[MVPA_rows, 'Axis3'])**2)
    MVPA_VM_counts = np.sqrt(np.sum(np.array([MVPA_VMx_counts, MVPA_VMy_counts, MVPA_VMz_counts]), axis = 0))

    MVPA_mins = len(df[ MVPA_rows ])
    MVPA_METs_min = 2.823 + ( 0.00054 * MVPA_VM_counts ) - (0.059123 * calibrated_weight_kg) + (1.441 * sex_num)
    if MVPA_mins == 0:
        MVPA_METs = 0
        MVPA_METs_daily_ave = 0
        MVPA_mins_daily_ave = 0
    else:
        MVPA_METs = sum(MVPA_METs_min) / MVPA_mins
        MVPA_METs_daily_ave = sum(MVPA_METs_min) / num_days
        MVPA_mins_daily_ave = MVPA_mins / num_days


    return METs, METs_daily_ave, mins_daily_ave, MVPA_mins, MVPA_METs, MVPA_METs_daily_ave, MVPA_mins_daily_ave
