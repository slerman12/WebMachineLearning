import math
import pandas as pd
import numpy as np
import sys
import MachineLearning as mL
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LogisticRegression
from sklearn.naive_bayes import GaussianNB, MultinomialNB, BernoulliNB
from sklearn.neighbors import KNeighborsClassifier
from sklearn.svm import SVC
from sklearn.ensemble import GradientBoostingClassifier


def main():
    # Set seed
    np.random.seed(0)

    # Create the data frames from files
    all_patients = pd.read_csv("data/all_pats.csv")
    all_visits = pd.read_csv("data/all_visits.csv")
    all_updrs = pd.read_csv("data/all_updrs.csv")

    # Enrolled PD / Control patients
    pd_control_patients = all_patients.loc[
        ((all_patients["DIAGNOSIS"] == "PD") | (all_patients["DIAGNOSIS"] == "Control")) & (
            all_patients["ENROLL_STATUS"] == "Enrolled"), "PATNO"].unique()

    # Data for these patients
    pd_control_data = all_visits[all_visits["PATNO"].isin(pd_control_patients)]

    # Merge with UPDRS scores
    pd_control_data = pd_control_data.merge(all_updrs[["PATNO", "EVENT_ID", "TOTAL"]], on=["PATNO", "EVENT_ID"],
                                            how="left")

    # Get rid of nulls for UPDRS
    pd_control_data = pd_control_data[pd_control_data["TOTAL"].notnull()]

    # Merge with patient info
    pd_control_data = pd_control_data.merge(all_patients, on="PATNO", how="left")

    # TODO: Figure out what do with SC
    # Only include baseline and subsequent visits
    pd_control_data = pd_control_data[
        (pd_control_data["EVENT_ID"] != "ST") & (
            pd_control_data["EVENT_ID"] != "U01") & (pd_control_data["EVENT_ID"] != "PW") & (
            pd_control_data["EVENT_ID"] != "SC")]

    # Encode to numeric
    mL.clean_data(data=pd_control_data, encode_auto=["GENDER.x", "DIAGNOSIS", "HANDED"], encode_man={
        "EVENT_ID": {"BL": 0, "V01": 1, "V02": 2, "V03": 3, "V04": 4, "V05": 5, "V06": 6, "V07": 7, "V08": 8,
                     "V09": 9, "V10": 10, "V11": 11, "V12": 12}})

    # TODO: Optimize flexibility with NAs
    # Eliminate features with more than 20% NAs
    for feature in pd_control_data.keys():
        if len(pd_control_data.loc[pd_control_data[feature].isnull(), feature]) / len(
                pd_control_data[feature]) > 0.2:
            pd_control_data = pd_control_data.drop(feature, 1)

    # TODO: Rethink this
    # Eliminate features with more than 30% NA at Baseline
    for feature in pd_control_data.keys():
        if len(pd_control_data.loc[
                           (pd_control_data["EVENT_ID"] == 0) & (pd_control_data[feature].isnull()), feature]) / len(
                pd_control_data[pd_control_data["EVENT_ID"] == 0]) > 0.3:
            pd_control_data = pd_control_data.drop(feature, 1)

    # TODO: Imputation
    # Drop rows with NAs
    pd_control_data = pd_control_data.dropna()

    # Drop duplicates (keep first, delete others)
    pd_control_data = pd_control_data.drop_duplicates(subset=["PATNO", "EVENT_ID"])

    # Select all features in the data set
    all_data_features = list(pd_control_data.columns.values)

    # Generate features
    train = generate_features(data=pd_control_data, features=all_data_features, file="data/PPMI_train.csv",
                              action=True)

    # Data diagnostics after feature generation
    mL.describe_data(data=train, describe=True, description="AFTER FEATURE GENERATION:")

    # Initialize predictors as all features
    predictors = list(all_data_features)

    # Add generated features to predictors
    predictors.extend(["SCORE_NOW", "VISIT_NEXT", "NP1", "NP2", "NP3"])

    # Initialize which features to drop from predictors
    drop_predictors = ["PATNO", "EVENT_ID", "INFODT.x", "ORIG_ENTRY", "LAST_UPDATE", "PAG_UPDRS3", "PRIMDIAG",
                       "COMPLT", "INITMDDT", "INITMDVS", "RECRUITMENT_CAT", "IMAGING_CAT", "ENROLL_DATE", "ENROLL_CAT",
                       "ENROLL_STATUS", "BIRTHDT.x", "GENDER.y", "APPRDX", "GENDER", "CNO", "NP1SLPN", "NP1SLPD",
                       "NP1PAIN", "NP1URIN", "NP1CNST", "NP1LTHD", "NP1FATG", "NP2SPCH", "NP2SALV", "NP2SWAL", "NP2EAT",
                       "NP2DRES", "NP2HYGN", "NP2HWRT", "NP2HOBB", "NP2TURN", "NP2TRMR", "NP2RISE", "NP2WALK",
                       "NP2FREZ", "NP3SPCH", "NP3FACXP", "NP3RIGN", "NP3RIGRU", "NP3RIGLU", "PN3RIGRL", "NP3RIGLL",
                       "NP3FTAPR", "NP3FTAPL", "NP3HMOVR", "NP3HMOVL", "NP3PRSPR", "NP3PRSPL", "NP3TTAPR", "NP3TTAPL",
                       "NP3LGAGR", "NP3LGAGL", "NP3RISNG", "NP3GAIT", "NP3FRZGT", "NP3PSTBL", "NP3POSTR", "NP3BRADY",
                       "NP3PTRMR", "NP3PTRML", "NP3KTRMR", "NP3KTRML", "NP3RTARU", "NP3RTALU", "NP3RTARL", "NP3RTALL",
                       "NP3RTALJ", "NP3RTCON", "TOTAL"]

    # Drop unwanted features from predictors list
    for feature in drop_predictors:
        if feature in predictors:
            predictors.remove(feature)

    # TODO: Play around with different targets i.e. UPDRS subsets or symptomatic milestones
    # Target for the model
    target = "SCORE_NEXT"

    # Univariate feature selection
    mL.describe_data(data=train, univariate_feature_selection=[predictors, target])

    # Algs for model
    # Grid search: n_estimators=50, min_samples_split=75, min_samples_leaf=50
    algs = [RandomForestRegressor(n_estimators=150, min_samples_split=100, min_samples_leaf=25, oob_score=True),
            LogisticRegression(),
            SVC(probability=True),
            GaussianNB(),
            MultinomialNB(),
            BernoulliNB(),
            KNeighborsClassifier(n_neighbors=25),
            GradientBoostingClassifier(n_estimators=10, max_depth=3)]

    # Alg names for model
    alg_names = ["Random Forest",
                 "Logistic Regression",
                 "SVM",
                 "Gaussian Naive Bayes",
                 "Multinomial Naive Bayes",
                 "Bernoulli Naive Bayes",
                 "kNN",
                 "Gradient Boosting"]

    # TODO: Configure ensemble
    # Ensemble
    ens = mL.ensemble(algs=algs, alg_names=alg_names,
                      ensemble_name="Weighted ensemble of RF, LR, SVM, GNB, KNN, and GB",
                      in_ensemble=[True, True, True, True, False, False, True, True], weights=[3, 2, 1, 3, 1, 3],
                      voting="soft")

    # Add ensemble to algs and alg_names
    # algs.append(ens["alg"])
    # alg_names.append(ens["name"])

    # Parameters for grid search
    grid_search_params = [{"n_estimators": [50, 150, 300, 500, 750, 1000],
                           "min_samples_split": [4, 8, 25, 50, 75, 100],
                           "min_samples_leaf": [2, 8, 15, 25, 50, 75, 100]}]

    # Display ensemble metrics
    mL.metrics(data=train, predictors=predictors, target=target, algs=algs, alg_names=alg_names,
               feature_importances=[True], base_score=[True], oob_score=[True],
               cross_val=[True], scoring="r2", split_accuracy=[True],
               grid_search_params=None)


def generate_features(data, features=None, file="generated_features.csv", action=True):
    # Initialize features if None
    if features is None:
        # Empty list
        features = []

    # Generate features or use pre-generated features
    if action:
        # Generate UPDRS subset sums
        generated_features = generate_updrs_subsets(data=data)

        # Add generated features to features list
        features = features + ["NP1", "NP2", "NP3"]

        # Generate new data set for predicting future visits
        generated_features = generate_future(data=generated_features, features=features, id_name="PATNO",
                                             score_name="TOTAL",
                                             visit_name="EVENT_ID")

        # Save generated features data
        generated_features.to_csv(file, index=False)
    else:
        # Retrieve generated features data
        generated_features = pd.read_csv(file)

    # Return generated features
    return generated_features


def generate_future(data, features, id_name, score_name, visit_name):
    # Set features
    features = features + ["SCORE_NOW", "VISIT_NEXT", "SCORE_NEXT"]

    # Set max visit
    max_visit = data[visit_name].max()

    # Generate SCORE_NOW and VISIT_NOW
    data["SCORE_NOW"] = data[score_name]
    data["VISIT_NOW"] = data[visit_name]

    # Create new dataframe
    new_data = pd.DataFrame(columns=features)

    # Initialize progress measures
    progress_complete = 0
    progress_total = len(data)

    # Build new data (generate SCORE_NEXT, VISIT_NEXT, and TIME_PASSED)
    for index, row in data.iterrows():
        # Update progress
        progress_complete += 1
        sys.stdout.write("\rProgress: {:.2%}".format(progress_complete / progress_total))
        sys.stdout.flush()

        # If now visit isn't the max
        if row["VISIT_NOW"] == 0:
            # TODO: Consider predicting a specific future visit instead of any future visit
            # For the range of all visits after this one
            for i in range(1, max_visit + 1):
                # If any future visit belongs to the same patient
                if any((data["VISIT_NOW"] == row["VISIT_NOW"] + i) & (data[id_name] == row[id_name])):
                    # Set next score
                    row["SCORE_NEXT"] = data.loc[(data["VISIT_NOW"] == row["VISIT_NOW"] + i) &
                                                 (data[id_name] == row[id_name]), "SCORE_NOW"].item()

                    # Set next visit
                    row["VISIT_NEXT"] = data.loc[(data["VISIT_NOW"] == row["VISIT_NOW"] + i) &
                                                 (data[id_name] == row[id_name]), "VISIT_NOW"].item()

                    # Set time passed
                    row["TIME_PASSED"] = i

                    # Add row to new_data
                    if not math.isnan(new_data.index.max()):
                        new_data.loc[new_data.index.max() + 1] = row[features]
                    else:
                        new_data.loc[0] = row[features]

    # Print new line
    print()

    # Return new data
    return new_data


def generate_updrs_subsets(data):
    # Sum UPDRS subsets
    data["NP1"] = data.filter(regex="NP1.*").sum(axis=1)
    data["NP2"] = data.filter(regex="NP2.*").sum(axis=1)
    data["NP3"] = data.filter(regex="NP3.*").sum(axis=1)

    # Return new data
    return data


if __name__ == "__main__":
    main()