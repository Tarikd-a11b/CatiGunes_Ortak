"""
Stage-1 rooftop PV suitability model: "Can PV panels be installed on this roof?"

Pipeline
    1. Roofs whose existing PV system already covers the whole roof are labelled
       "not suitable" by a team rule. They never reach the classifier.
    2. For every other roof, a classifier trained on 200 hand-labelled training roofs
       predicts suitable / not suitable from 16 numeric features
       (6 basic features + 10 footprint-shape features).
    3. The classifiers (Random Forest, XGBoost, plus Extra Trees as an additional
       comparison) are evaluated on the 111 independently hand-labelled test roofs and
       compared with a rule-only baseline.

Evaluation protocol
    - Hyper-parameters are fixed and deliberately simple. The test set was never used
      to choose a model, a feature set or a threshold.
    - Tree ensembles are random, so headline scores are averaged over 15 random seeds.
    - Three versions of the test labels are reported side by side (see build_label_versions).

Usage
    python suitability_model.py results

Note: the input CSV files keep their original Turkish column names because they are
produced by the shared data pipeline. They are renamed to English right after loading.
"""
import json
import os
import sys
import warnings

import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.ensemble import ExtraTreesClassifier, RandomForestClassifier
from sklearn.metrics import (accuracy_score, confusion_matrix, f1_score,
                             precision_score, recall_score, roc_auc_score)
from xgboost import XGBClassifier

warnings.filterwarnings("ignore")

# --------------------------------------------------------------------------- #
# Configuration
# --------------------------------------------------------------------------- #
SEED = 42                 # seed used for the single-run tables (confusion matrix, bootstrap)
N_SEEDS = 15              # number of seeds for the seed-averaged headline scores
N_BOOTSTRAP = 2000        # bootstrap resamples for the confidence interval
MIN_NET_AREA_M2 = 100.0   # area threshold of the rule baseline (comparison only, not a team decision)

# Input files (file names come from the shared data pipeline)
ROOF_TABLE_CSV = "uygunluk_veri_tablosu.csv"     # one row per roof: type, PV status, split, orientation
PRODUCTION_CSV = "cati_uretim.csv"               # net usable area and specific yield per roof
SHAPE_FEATURES_CSV = "sekil_ozellikleri.csv"     # footprint-shape features per roof
TRAIN_LABELS_CSV = "egitim_etiket_v2.csv"        # 200 hand-labelled training roofs
TEST_LABELS_CSV = "test_etiketli_birlesik.csv"   # 111 hand-labelled test roofs (original labels)

# Turkish -> English column names
RENAME_ROOF_TABLE = {
    "cati_id": "roof_id",
    "bolum": "split",                              # train / val / test_referans
    "panel_durumu": "pv_status",                   # panel_yok / kismi_panel_dusuldu / tam_dolu
    "cati_tipi": "roof_type",                      # duz (flat) / egimli (pitched)
    "cati_alan_m2": "gross_area_m2",
    "uygun_alan_m2": "pv_free_area_m2",            # gross area minus the area covered by existing PV
    "etkin_yon_sapma_guney_deg": "deviation_from_south_deg",
}
RENAME_PRODUCTION = {
    "cati_id": "roof_id",
    "net_alan_m2": "net_area_m2",                  # PV-free area after the edge setback
    "ozgul_kWh_kWp": "specific_yield_kwh_kwp",
}
RENAME_SHAPE = {
    "cati_id": "roof_id",
    "genislik_m": "width_m",                       # short side of the minimum rotated rectangle
    "uzunluk_m": "length_m",                       # long side of the minimum rotated rectangle
    "en_boy_orani": "aspect_ratio",
    "kompaktlik": "compactness",
    "doluluk": "solidity",                         # area / convex-hull area
    "dikdortgen_doluluk": "rectangularity",        # area / minimum-rotated-rectangle area
    "parca_sayisi": "n_parts",
    "delik_sayisi": "n_holes",
    "ic_cember_yaricap_m": "inscribed_circle_radius_m",
}

# Values used in the data files
SPLIT_TEST = "test_referans"
PV_FULL = "tam_dolu"            # existing PV covers the whole roof
ROOF_PITCHED = "egimli"
LABEL_SUITABLE = "uygun"
LABEL_NOT_SUITABLE = "uygun_degil"   # a third value, "cati_degil" (not a roof), is dropped

BASIC_FEATURES = [
    "net_area_m2",                 # usable area after edge setback
    "gross_area_m2",               # footprint area
    "existing_pv_share",           # share of the roof already covered by PV
    "is_pitched",                  # 1 = pitched roof, 0 = flat roof
    "deviation_from_south_deg",    # 0 for flat roofs (panels are tilted south on a frame)
    "specific_yield_kwh_kwp",      # annual yield per installed kWp (almost constant per region)
]
SHAPE_FEATURES = [
    "width_m", "length_m", "aspect_ratio", "compactness", "solidity", "rectangularity",
    "n_parts", "n_holes", "inscribed_circle_radius_m", "net_to_gross_ratio",
]
FEATURES = BASIC_FEATURES + SHAPE_FEATURES


# --------------------------------------------------------------------------- #
# Data
# --------------------------------------------------------------------------- #
def load_roofs():
    """Load the three roof tables, rename columns to English and build the model features."""
    table = pd.read_csv(ROOF_TABLE_CSV).rename(columns=RENAME_ROOF_TABLE)
    production = pd.read_csv(PRODUCTION_CSV)[list(RENAME_PRODUCTION)].rename(columns=RENAME_PRODUCTION)
    shape = pd.read_csv(SHAPE_FEATURES_CSV)[list(RENAME_SHAPE)].rename(columns=RENAME_SHAPE)
    roofs = table.merge(production, on="roof_id").merge(shape, on="roof_id")

    roofs["is_pitched"] = (roofs["roof_type"] == ROOF_PITCHED).astype(int)
    # Flat roofs have no orientation of their own; panels face south, so the deviation is 0.
    roofs["deviation_from_south_deg"] = roofs["deviation_from_south_deg"].fillna(0.0)
    roofs["existing_pv_share"] = (1 - roofs["pv_free_area_m2"] / roofs["gross_area_m2"]).clip(0, 1)
    roofs["net_to_gross_ratio"] = roofs["net_area_m2"] / roofs["gross_area_m2"]
    return roofs


def load_training_set(roofs):
    """Return the hand-labelled training roofs with target y (1 = suitable, 0 = not suitable)."""
    labels = pd.read_csv(TRAIN_LABELS_CSV)[["cati_id", "karar"]]
    labels = labels.rename(columns={"cati_id": "roof_id", "karar": "label"})
    # Records labelled "not a roof" are data errors, not a class of the model.
    labels = labels[labels["label"].isin([LABEL_SUITABLE, LABEL_NOT_SUITABLE])]
    train = roofs.merge(labels, on="roof_id")
    train["y"] = (train["label"] == LABEL_SUITABLE).astype(int)
    assert not (train["split"] == SPLIT_TEST).any(), "a test roof leaked into the training labels"
    return train


def load_test_set(roofs):
    """Return the 111 hand-labelled test roofs with their original labels."""
    labels = pd.read_csv(TEST_LABELS_CSV)[["cati_id", "y_uygun"]]
    labels = labels.rename(columns={"cati_id": "roof_id", "y_uygun": "y"})
    test = roofs[roofs["split"] == SPLIT_TEST].merge(labels, on="roof_id")
    assert len(test) == 111
    return test


def build_label_versions(test):
    """Build the three test-label versions. Each entry is (labels, mask of roofs kept).

    A  original labels, all 111 roofs.
    B  main result. Only records that had been flagged BEFORE any model was trained are
       corrected: roof 1307 becomes "suitable" (width was misjudged during labelling) and
       roof 1076 is excluded because it is a courtyard, not a roof.
    C  B plus roof 1004 re-labelled "suitable". This change was made after seeing that
       the model missed the roof, so it is reported separately and is not the main result.
    """
    roof_ids = test["roof_id"].to_numpy()
    everything = np.ones(len(test), dtype=bool)

    y_a = test["y"].to_numpy().copy()

    y_b = y_a.copy()
    y_b[roof_ids == 1307] = 1
    keep_b = roof_ids != 1076

    y_c = y_b.copy()
    y_c[roof_ids == 1004] = 1

    return {
        "A_original": (y_a, everything),
        "B_preflagged_corrections": (y_b, keep_b),
        "C_B_plus_1004": (y_c, keep_b),
    }


# --------------------------------------------------------------------------- #
# Models
# --------------------------------------------------------------------------- #
def build_models(y_train):
    """Return the classifiers with fixed, simple hyper-parameters.

    Class imbalance (few "not suitable" roofs) is handled with class weights.
    """
    negative_to_positive = (y_train == 0).sum() / (y_train == 1).sum()
    return {
        "random_forest": RandomForestClassifier(
            n_estimators=300, max_depth=6, class_weight="balanced", n_jobs=2),
        "xgboost": XGBClassifier(
            n_estimators=150, max_depth=3, learning_rate=0.05, subsample=0.9, colsample_bytree=0.9,
            scale_pos_weight=negative_to_positive, eval_metric="logloss", n_jobs=2),
        # Not named in the project proposal; kept as an additional comparison only.
        "extra_trees_additional": ExtraTreesClassifier(
            n_estimators=300, min_samples_leaf=3, class_weight="balanced", n_jobs=2),
    }


def predict_with_rule_override(model, X_test, fully_covered_by_pv, threshold=0.5):
    """Predict suitability, then force roofs fully covered by PV to "not suitable"."""
    probability_suitable = model.predict_proba(X_test)[:, 1]
    prediction = (probability_suitable >= threshold).astype(int)
    prediction = np.where(fully_covered_by_pv, 0, prediction)
    return prediction, probability_suitable


def rule_baseline(test, fully_covered_by_pv):
    """Rule-only baseline: not suitable if fully covered by PV or net area below the threshold."""
    too_small = (test["net_area_m2"] < MIN_NET_AREA_M2).to_numpy()
    return np.where(fully_covered_by_pv | too_small, 0, 1)


# --------------------------------------------------------------------------- #
# Metrics
# --------------------------------------------------------------------------- #
def classification_metrics(y_true, y_pred):
    """Scores for one set of predictions. Class 1 = suitable, class 0 = not suitable."""
    matrix = confusion_matrix(y_true, y_pred, labels=[0, 1])
    return {
        "n_roofs": int(len(y_true)),
        "n_not_suitable": int((y_true == 0).sum()),
        "f1_suitable": round(float(f1_score(y_true, y_pred, pos_label=1)), 3),
        "f1_not_suitable": round(float(f1_score(y_true, y_pred, pos_label=0)), 3),
        "f1_macro": round(float(f1_score(y_true, y_pred, average="macro")), 3),
        "accuracy": round(float(accuracy_score(y_true, y_pred)), 3),
        "precision_not_suitable": round(float(precision_score(y_true, y_pred, pos_label=0)), 3),
        "recall_not_suitable": round(float(recall_score(y_true, y_pred, pos_label=0)), 3),
        # rows = true class, columns = predicted class, order: [not suitable, suitable]
        "confusion_matrix": {
            "true_not_suitable": {"pred_not_suitable": int(matrix[0, 0]), "pred_suitable": int(matrix[0, 1])},
            "true_suitable": {"pred_not_suitable": int(matrix[1, 0]), "pred_suitable": int(matrix[1, 1])},
        },
    }


def bootstrap_macro_f1_difference(y_true, pred_model, pred_rule, rng):
    """95% bootstrap confidence interval of macro-F1(model) - macro-F1(rule baseline)."""
    differences = []
    for _ in range(N_BOOTSTRAP):
        sample = rng.randint(0, len(y_true), len(y_true))
        differences.append(
            f1_score(y_true[sample], pred_model[sample], average="macro")
            - f1_score(y_true[sample], pred_rule[sample], average="macro"))
    low, high = np.percentile(differences, [2.5, 97.5])
    return [round(float(low), 3), round(float(high), 3)]


def seed_averaged_scores(model, X_train, y_train, X_test, y_true, keep, fully_covered_by_pv):
    """Retrain with N_SEEDS different seeds and average the test scores."""
    f1_suitable, f1_not_suitable, f1_macro = [], [], []
    for seed in range(N_SEEDS):
        fitted = clone(model).set_params(random_state=seed).fit(X_train, y_train)
        prediction, _ = predict_with_rule_override(fitted, X_test, fully_covered_by_pv)
        f1_suitable.append(f1_score(y_true[keep], prediction[keep], pos_label=1))
        f1_not_suitable.append(f1_score(y_true[keep], prediction[keep], pos_label=0))
        f1_macro.append(f1_score(y_true[keep], prediction[keep], average="macro"))
    return {
        "f1_suitable_mean": round(float(np.mean(f1_suitable)), 3),
        "f1_not_suitable_mean": round(float(np.mean(f1_not_suitable)), 3),
        "f1_not_suitable_min_max": [round(float(min(f1_not_suitable)), 3), round(float(max(f1_not_suitable)), 3)],
        "f1_macro_mean": round(float(np.mean(f1_macro)), 3),
    }


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def main():
    out_dir = sys.argv[1] if len(sys.argv) > 1 else "results"
    os.makedirs(out_dir, exist_ok=True)

    roofs = load_roofs()
    train = load_training_set(roofs)
    test = load_test_set(roofs)

    # Missing feature values are filled with the TRAINING median (no information from the test set).
    train_median = train[FEATURES].median()
    X_train = train[FEATURES].fillna(train_median).to_numpy()
    y_train = train["y"].to_numpy()
    X_test = test[FEATURES].fillna(train_median).to_numpy()
    fully_covered_by_pv = (test["pv_status"] == PV_FULL).to_numpy()

    models = build_models(y_train)
    label_versions = build_label_versions(test)

    # Single run with a fixed seed: used for confusion matrices, ROC-AUC and the bootstrap.
    predictions, probabilities = {}, {}
    for name, model in models.items():
        fitted = clone(model).set_params(random_state=SEED).fit(X_train, y_train)
        predictions[name], probabilities[name] = predict_with_rule_override(fitted, X_test, fully_covered_by_pv)
    RULE = f"rule_baseline_full_pv_or_net_area_below_{int(MIN_NET_AREA_M2)}"
    predictions[RULE] = rule_baseline(test, fully_covered_by_pv)

    results = {"n_training_roofs": {"suitable": int((y_train == 1).sum()), "not_suitable": int((y_train == 0).sum())},
               "features": FEATURES}
    rng = np.random.RandomState(SEED)

    for version, (y_true, keep) in label_versions.items():
        # Subset without roofs fully covered by PV: shows what the classifier itself contributes,
        # because those roofs are decided by the rule, not by the classifier.
        keep_without_full_pv = keep & ~fully_covered_by_pv
        results[version] = {"single_run_seed_42": {}, f"mean_over_{N_SEEDS}_seeds": {}}
        print(f"\n== {version}: {int(keep.sum())} roofs, {int((y_true[keep] == 0).sum())} not suitable ==")

        for name, prediction in predictions.items():
            scores = classification_metrics(y_true[keep], prediction[keep])
            scores["f1_not_suitable_without_full_pv"] = round(float(
                f1_score(y_true[keep_without_full_pv], prediction[keep_without_full_pv], pos_label=0)), 3)
            if name in probabilities:
                scores["roc_auc_without_full_pv"] = round(float(
                    roc_auc_score(y_true[keep_without_full_pv], probabilities[name][keep_without_full_pv])), 3)
                scores["macro_f1_minus_rule_ci95"] = bootstrap_macro_f1_difference(
                    y_true[keep], prediction[keep], predictions[RULE][keep], rng)
            results[version]["single_run_seed_42"][name] = scores
            matrix = scores["confusion_matrix"]
            print(f"{name:45s} F1 suitable {scores['f1_suitable']:.3f} | F1 not suitable {scores['f1_not_suitable']:.3f} | "
                  f"macro F1 {scores['f1_macro']:.3f} | accuracy {scores['accuracy']:.3f} | "
                  f"confusion [[{matrix['true_not_suitable']['pred_not_suitable']}, {matrix['true_not_suitable']['pred_suitable']}], "
                  f"[{matrix['true_suitable']['pred_not_suitable']}, {matrix['true_suitable']['pred_suitable']}]]")

        for name, model in models.items():
            averaged = seed_averaged_scores(model, X_train, y_train, X_test, y_true, keep, fully_covered_by_pv)
            results[version][f"mean_over_{N_SEEDS}_seeds"][name] = averaged
            print(f"  {N_SEEDS}-seed mean  {name:30s} F1 suitable {averaged['f1_suitable_mean']:.3f} | "
                  f"F1 not suitable {averaged['f1_not_suitable_mean']:.3f} {averaged['f1_not_suitable_min_max']} | "
                  f"macro F1 {averaged['f1_macro_mean']:.3f}")

    with open(os.path.join(out_dir, "results.json"), "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    # Per-roof output: labels of the three versions (empty = excluded) and every prediction.
    per_roof = test[["roof_id", "pv_status", "net_area_m2", "width_m"]].copy()
    for version, (y_true, keep) in label_versions.items():
        per_roof["label_" + version] = np.where(keep, y_true, np.nan)
    for name, prediction in predictions.items():
        per_roof["pred_" + name] = prediction
    per_roof.to_csv(os.path.join(out_dir, "test_predictions.csv"), index=False)
    print(f"\nSaved: {out_dir}/results.json, {out_dir}/test_predictions.csv")


if __name__ == "__main__":
    main()
