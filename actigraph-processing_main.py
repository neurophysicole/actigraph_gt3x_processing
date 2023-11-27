# main file for processing the actigraph data

# --------------
# import modules
from actigraph_processing_modules import *

# ---------------
# import packages
import glob #extracting files
import pandas as pd


# --------- #
# init vars #
# --------- #
# folders
actigraph_folder = '/Volumes/Freya/PAIR_data/_pa/data-actigraph' #folder containing raw actigraph data files
out_folder = '/Volumes/Odin/HARP_data/processing-pa'

protocol_dfile = '/Volumes/Freya/PAIR_data/PAIR_protocol_data-clean.csv' #data file containing participdant info (snum, weight, weightscale_baseline, sex)
protocol_df = pd.read_csv(protocol_dfile)

# settings
frequency = 30 #Hz - counts
epoch = 60 #seconds - counts
inactive_count_threshold = 60 #need 60mins of zeros to be inactive (not wearing) - valid_wear_time
active_spike_threshold = 3 #need 3 mins consecutive to be active (wearing) - valid_wear_time
valid_day_count_threshold = 600 #need 600 mins of recorded activity for it to be valid - valid_wear_time
valid_day_threshold = 4 #need 4 days of recorded activity for it to be a valid subject - valid_wear_time

ctrl_weight = 42.3

# ----------------- #
# Import .gt3x file #
# ----------------- #
# cycle through each file, save the csv counts
print('\n\nImporting GT3X files . . .\n\n')

actigraph_ftype = '*.gt3x'
actigraph_file_list = glob.glob( '%s/%s' % (actigraph_folder, actigraph_ftype))

for file_i in actigraph_file_list:
    subj_id = file_i.split('/')[-1]
    subj_id = subj_id.split('_')[1] #subj_id
    print('\n --> Participant %s' % subj_id)

    subj_id = '%s/counts/%s_counts.csv' % (out_folder, subj_id)
    actigraph_import(file_i, subj_id)


# ---------- #
# Get counts #
# ---------- #
# cycle through and
print('\n\nGetting Activity Counts . . .\n\n')

counts_ftype = '*.csv'
counts_file_list = glob.glob( '%s/counts/%s' % (out_folder, counts_ftype))

counts_dfs = []
for file_i in  counts_file_list:
    subj_id = file_i.split('/')[-1]
    subj_id = subj_id.split('_')[0]
    print('\n --> Participant %s' % subj_id)

    counts = get_counts_csv(file_i, frequency, epoch, True, True, 'Timestamp')
    counts['subj'] = subj_id #add subj_id to df
    counts_dfs.append(counts)


# ------------------ #
# Validate Wear Time #
# ------------------ #
# need to make sure actually wearing
# also validating if enough minutes to count the day
print('\n\nValidating the Wear Time and Days . . .\n\n')

# create empty data frame to append to..
# validated_df = pd.DataFrame(columns = ['Timestamp', 'Axis1', 'Axis2', 'Axis3', 'AC', 'subj', 'wearing', 'valid_day', 'valid_subj', 'METs'])
validated_df = pd.DataFrame(columns=['snum', 'METs', 'METs_daily_ave', 'mins_daily_ave', 'MVPA_mins', 'MVPA_METs', 'MVPA_METs_daily_ave', 'MVPA_mins_daily_ave'])
for counts_i in range(0, len(counts_dfs)):

    print('\n --> Validating %i of %i' % (counts_i, len(counts_dfs)))

    df_i = validate_wear_time(
        counts_dfs[counts_i], inactive_count_threshold, active_spike_threshold,
        valid_day_count_threshold, valid_day_threshold
    )


    # -------------- #
    # Calculate METs #
    # -------------- #
    print('\n - Calculating METs')

    # calculating [estimated] METs so can accurately categorize activity levels
    subj_i = df_i['subj'][0]
    METs, METs_daily_ave, mins_daily_ave, MVPA_mins, MVPA_METs, MVPA_METs_daily_ave, MVPA_mins_daily_ave = calculate_METs_MVPA(df_i, protocol_df, subj_i, ctrl_weight)

    validated_df_new_row = {
        'snum': subj_i,
        'METs': METs, 'METs_daily_ave': METs_daily_ave, 'mins_daily_ave': mins_daily_ave,
        'MVPA_mins': MVPA_mins, 'MVPA_METs': MVPA_METs, 'MVPA_METs_daily_ave': MVPA_METs_daily_ave,
        'MVPA_mins_daily_ave': MVPA_mins_daily_ave
    }
    validated_df.loc[len(validated_df)] = validated_df_new_row


# ------------- #
# Save the Data #
# ------------- #
# need to save the categorized and validated dfs as .csv files
print('\n\nSaving data files . . .\n\n')

validated_df.to_csv('%s/pa_data.csv' % out_folder, index = False)
