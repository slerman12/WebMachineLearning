import math
import pandas as pd
from pandas.tseries.offsets import Day
import numpy as np


def main():
    # Set seed
    np.random.seed(0)

    # Create the dataframe from file
    data = pd.read_csv("data/all_bp.csv")

    # Set columns
    columns = ["ID", "DAY", "DATE_TIME_CENTRAL_SIT", "DATE_TIME_CENTRAL_STAND", "DATE_TIME_LOCAL_SIT",
               "DATE_TIME_LOCAL_STAND", "TIME_DIFF", "MORNINGNIGHT", "COMPLIANCE"]

    # Convert datetimes to pandas datetimes
    data["date_time_local"] = pd.to_datetime(data["date_time_local"])

    # Find previous dawn before a time, and next dawn after another time
    def find_first_last_dawn(first_date_time, last_date_time):
        # First day's dawn and last day's dawn
        first_dawn = pd.Timestamp(first_date_time.date() + pd.DateOffset(hours=4, minutes=24))
        last_dawn = pd.Timestamp(last_date_time.date() + pd.DateOffset(hours=4, minutes=24))

        # For testing, print patient's first dawn and last dawn
        print(first_dawn)
        print(last_dawn)

        # Previous dawn
        if first_date_time < first_dawn:
            first_dawn = first_dawn - Day(1)

        # Next dawn
        if last_date_time > last_dawn:
            last_dawn = last_dawn + Day(1)

        # Return first and last dawn
        return first_dawn, last_dawn

    # Dataframe for storing final result
    result = pd.DataFrame(columns=columns)

    # Function to set features and values to a row and append row to result
    def set_add_row(row_observations, row):
        # Find local and central times of first sit observation for row row
        first_sit_date_time_local = row_observations.loc[
            row_observations["state"] == "sit", "date_time_local"].min()
        first_sit_date_time_central = row_observations.loc[
            row_observations["state"] == "sit", "date_time_central"].min()

        # Find local and central times of next stand observation for row row
        next_stand_date_time_local = row_observations.loc[
            (row_observations["state"] == "stand") & (row_observations[
                                                          "date_time_local"] > first_sit_date_time_local), "date_time_local"].min()
        next_stand_date_time_central = row_observations.loc[
            (row_observations["state"] == "stand") & (row_observations[
                                                          "date_time_central"] > first_sit_date_time_central), "date_time_central"].min()

        # Set sit/stand times for row row
        row["DATE_TIME_LOCAL_SIT"] = first_sit_date_time_local
        row["DATE_TIME_LOCAL_STAND"] = next_stand_date_time_local
        row["DATE_TIME_CENTRAL_SIT"] = first_sit_date_time_central
        row["DATE_TIME_CENTRAL_STAND"] = next_stand_date_time_central

        # Set time difference
        row["TIME_DIFF"] = next_stand_date_time_local - first_sit_date_time_local

        # Add rows to new_data
        if not math.isnan(result.index.max()):
            result.loc[result.index.max() + 1] = row
        else:
            result.loc[0] = row

    # Iterate through each patient
    for patient in data["id"].unique():
        # For testing, print patient id
        print("PATIENT: {}".format(patient))

        # Initialize time as first dawn before earliest observation
        time, last_time = find_first_last_dawn(data.loc[data["id"] == patient, "date_time_local"].min(),
                                               data.loc[data["id"] == patient, "date_time_local"].max())

        # Initialize day count
        day_count = 0

        # Iterate by 24 hour periods from dawn to dawn
        while time != last_time:
            # Increment day count
            day_count += 1

            # Initialize morning and night rows to be appended to result
            morning_row = pd.DataFrame(columns=columns)[0]
            night_row = pd.DataFrame(columns=columns)[0]

            # Observations of this patient on this time interval
            observations = data[data["id"] == patient & data["date_time_local"].between(time, time + Day(1))]

            # Divide the observations into morning and night
            morning_observations = observations[observations["ampm"] == "M"]
            night_observations = observations[observations["ampm"] == "N"]

            # Set row IDs and morning/night
            morning_row["ID"] = patient
            morning_row["DAY"] = day_count
            morning_row["MORNINGNIGHT"] = "M"
            night_row["ID"] = patient
            night_row["DAY"] = day_count
            night_row["MORNINGNIGHT"] = "N"

            # Append morning and night rows
            set_add_row(morning_observations, morning_row)
            set_add_row(night_observations, night_row)

            # Iterate by a day
            time = time + Day(1)


if __name__ == "__main__":
    main()
