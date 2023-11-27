# actigraph_gt3x_processing
Scripts to process Actigraph GT3X data in Python. 

There are two main scripts: `_main` and `_modules`. These were programmed on a Mac using Python 3.9. There are two ways I can see these used:

(1) Code is copied from the `_modules` as needed.

(2) The `_main` script is updated for personal use and run. This will output a .csv file with the processed data. This will require some minor customization of parameters in the `_main` script (no updates should be required to the `_modules`, unless further customization is desired):

 - `actigraph_folder` should be updated to the complete path to the folder that contains all of the raw `.gt3x` and `.agd` data.
 - `out_folder` should be updated to the complete path to the folder where you desire the output .csv to be saved.
 - `protocol_dfile` should be updated to the complete path to a .csv file containing the subject information necessary for calculating the METs values. The following columns should be in the .csv file:
   - `snum`: Subject number
   - `weight`: Weight of the participant (in lbs)
   - `weightscale_baseline`: My study used an unreliable scale to measure the weight of participants. To account for this, the weight of an object was measured using a trustworthy/reliable scale, then prior to every weigh-in of the participants, the object was wieghed again. This value was subtracted from the original measurement to account for variability in the scale. If you do not have this data, make `weightscale_baseline` = 0.
   - `sex`: Biological sex of the participant ("Male" or "Female").
 - I believe the settings provided are generally standard, but can be updated as necessary.
 - `ctrl_weight`: This is the weight measurement of the object used to calibrate the scale. If you have the `weightscale_baseline` == 0, `ctrl_weight` should also be set to 0.

**Output**:
The output .csv file will contain the following measures:

 - METs: Total METs calculated for entire collection period.
 - METs_daily_ave: Daily average of the METs calculation (only valid days included).
 - mins_daily_ave: Average number of mins the device recorded valid data each day (only valid days included).
 - MVPA_mins: Total number of minutes the participant spent at moderate-to-vigorous levels of activity.
 - MVPA_METs: Total METs burned while the participant was engaged in moderate-to-vigorous levels of activity.
 - MVPA_METs_daily_ave: Daily average of the METs burned while the participant was engaged in mmoderate-to-vigorous levels of activity (only valid days included).
 - MVPA_mins_daily_ave: Daily average number of minutes the participant spent engaged in moderate-to-vigorous levels of activity (only valid days included).

## Notes

All outcome measures are calculated from data points included as _valid_. _Valid_ means we are determining that this data was collected while the device was being worn by the participant. Logs are sometimes used to determine which data is valid (or in addition to the algorithmic approach), but for these scripts, the following criteria were used (some of these parameters can be updated under `settings` in the `_main_script`:

 - 60 mins of consecutive inactive data is required for the the counts to be considered _invalid_
 - 3 consecutive minutes of data were required for the data to be considered _valid_ (minimum activity count == 100, this setting is embedded in the `validate_wear_time` module)
 - 600 minutes are required in one day for the day to be considered valid (days are determined in 24 hour chunks starting when the devices is initiated - for my study, this was 4am of of the day the participant received the device).
 - 4 valid days were required for participants to be considered _valid_
 - Counts must be greater than 3208 to be considered moderate-to-vigorous activity (this setting is embedded in the `calculate_METs_MVPA` module

## Credit

Code for this project was borrowed from the following public repositories:
 - [agcounts](https://github.com/actigraph/agcounts)
 - [pygt3x](https://github.com/actigraph/pygt3x)
