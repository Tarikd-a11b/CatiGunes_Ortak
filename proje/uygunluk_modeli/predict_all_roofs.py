"""
Apply the stage-1 suitability models to all 1,085 roofs.

This script does NOT change the evaluation. It retrains the same models with the same
settings and the same training labels as suitability_model.py (seed 42, the run used for
the confusion matrices) and writes one row per roof, so that the API, the web map and the
LLM layer can read a suitability result for every roof.

Usage
    python predict_all_roofs.py ../../model_verisi/uygunluk

Output: cati_uygunluk.csv (one row per roof, joins to every other file on cati_id)
    cati_id
    p_uygun_rf, uygun_rf        Random Forest probability of "suitable" and decision (1/0)
    p_uygun_et, uygun_et        Extra Trees probability and decision
    uygun_kural                 rule baseline (full PV or net area < 100 m2), comparison only
    karar_kaynagi               "kural_tam_dolu_GES" if the roof is fully covered by PV
                                (decided by the team rule, probability left empty), else "model"
    etiket_kumesi               "egitim" (one of the 199 training roofs), "test" (one of the
                                111 test roofs) or "yok" (not hand-labelled)
    el_etiketi                  the hand label (1 suitable, 0 not suitable) where one exists;
                                test labels follow version B of the evaluation
    cati_degil                  True for records found during labelling not to be roofs

Notes
    - Predictions for training roofs are in-sample: the model has seen these roofs, so they
      say nothing about accuracy. Accuracy comes only from the test roofs (results.json).
    - Which model is the main one (Random Forest or Extra Trees) is not decided yet, so both
      are written. The decision threshold is 0.5 as in the evaluation.
"""
import os
import sys
import warnings

import numpy as np
import pandas as pd
from sklearn.base import clone

import suitability_model as sm

warnings.filterwarnings("ignore")

# Records that hand labelling showed are not roofs (1391: stacked sacks, 1076: courtyard).
NOT_A_ROOF = [1391, 1076]


def main():
    out_dir = sys.argv[1] if len(sys.argv) > 1 else "results"
    os.makedirs(out_dir, exist_ok=True)

    roofs = sm.load_roofs()
    train = sm.load_training_set(roofs)
    test = sm.load_test_set(roofs)
    assert len(roofs) == 1085, len(roofs)

    # Same feature preparation as the evaluation: fill gaps with the TRAINING median.
    train_median = train[sm.FEATURES].median()
    X_train = train[sm.FEATURES].fillna(train_median).to_numpy()
    y_train = train["y"].to_numpy()
    X_all = roofs[sm.FEATURES].fillna(train_median).to_numpy()
    fully_covered_by_pv = (roofs["pv_status"] == sm.PV_FULL).to_numpy()

    models = sm.build_models(y_train)
    out = pd.DataFrame({"cati_id": roofs["roof_id"].to_numpy()})
    for short, name in [("rf", "random_forest"), ("et", "extra_trees_additional")]:
        fitted = clone(models[name]).set_params(random_state=sm.SEED).fit(X_train, y_train)
        decision, probability = sm.predict_with_rule_override(fitted, X_all, fully_covered_by_pv)
        out[f"p_uygun_{short}"] = np.where(fully_covered_by_pv, np.nan, probability.round(3))
        out[f"uygun_{short}"] = decision

    out["uygun_kural"] = sm.rule_baseline(roofs, fully_covered_by_pv)
    out["karar_kaynagi"] = np.where(fully_covered_by_pv, "kural_tam_dolu_GES", "model")

    # Hand labels: training labels as used for training, test labels as in version B.
    out["etiket_kumesi"] = "yok"
    out["el_etiketi"] = np.nan
    train_labels = dict(zip(train["roof_id"], train["y"]))
    y_b, keep_b = sm.build_label_versions(test)["B_preflagged_corrections"]
    test_labels = {rid: lab for rid, lab, keep in zip(test["roof_id"], y_b, keep_b) if keep}
    for labels, set_name in [(train_labels, "egitim"), (test_labels, "test")]:
        mask = out["cati_id"].isin(labels)
        out.loc[mask, "etiket_kumesi"] = set_name
        out.loc[mask, "el_etiketi"] = out.loc[mask, "cati_id"].map(labels)
    out["cati_degil"] = out["cati_id"].isin(NOT_A_ROOF)
    out.loc[out["cati_id"].isin(NOT_A_ROOF), "etiket_kumesi"] = "cati_degil"

    path = os.path.join(out_dir, "cati_uygunluk.csv")
    out.to_csv(path, index=False)

    # Short summary for the console
    real = ~out["cati_degil"]
    print(f"Saved {path}: {len(out)} roofs")
    for col in ["uygun_rf", "uygun_et", "uygun_kural"]:
        print(f"  {col:12s} suitable {int(out.loc[real, col].sum())} / not suitable {int((out.loc[real, col] == 0).sum())}")
    print("  decided by full-PV rule:", int(fully_covered_by_pv.sum()))
    print("  hand-labelled roofs:", out["etiket_kumesi"].value_counts().to_dict())


if __name__ == "__main__":
    main()
