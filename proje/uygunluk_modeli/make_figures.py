"""
Figures for the suitability model: confusion matrices and SHAP explanations.

Run AFTER (or instead of) suitability_model.py; it reuses the same data loading,
features and model settings, so the figures match the reported scores.

Usage
    python make_figures.py results

Outputs (written to the given folder)
    confusion_matrices.png   2 x 2 confusion matrix of each method (test-label version B)
    shap_importance.png      mean |SHAP| per feature for Random Forest and XGBoost
    shap_beeswarm_random_forest.png
    shap_beeswarm_xgboost.png
    shap_importance.csv      the numbers behind shap_importance.png
    permutation_importance.png   drop in macro F1 when one feature is shuffled
    permutation_importance.csv   the numbers behind permutation_importance.png

How to read permutation importance here
    One feature column is shuffled across the test roofs, the model predicts again without
    retraining, and the drop in macro F1 is recorded. A large drop means the model needs the
    feature to predict correctly; a value near zero (or below) means it does not.
    Many shape features carry overlapping information, so shuffling a single one is partly
    compensated by the others and each of them looks less important than the group really is.

How to read SHAP here
    SHAP values are computed for the class "suitable". A positive value means the feature
    pushed that roof towards "suitable", a negative value towards "not suitable".
    Values are computed on the test roofs that actually reach the classifier
    (roofs fully covered by PV are decided by the rule and are left out).
"""
import os
import sys
import warnings

import matplotlib
matplotlib.use("Agg")                      # write image files without opening a window
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import shap
from sklearn.base import clone
from sklearn.inspection import permutation_importance
from sklearn.metrics import confusion_matrix

import suitability_model as sm

warnings.filterwarnings("ignore")

LABEL_VERSION = "B_preflagged_corrections"   # main result
N_PERMUTATION_REPEATS = 50                   # shuffles per feature for permutation importance
CLASS_NAMES = ["Not suitable", "Suitable"]
INK = "#1f2933"          # text colour
MUTED = "#6b7280"        # secondary text
BAR_COLOR = "#2f6fb0"    # single hue: the bars show magnitude, not categories

DISPLAY_NAMES = {
    "random_forest": "Random Forest",
    "xgboost": "XGBoost",
    "extra_trees_additional": "Extra Trees (additional)",
}


def prepare():
    """Load data, fit the models with the fixed seed and return everything the figures need."""
    roofs = sm.load_roofs()
    train = sm.load_training_set(roofs)
    test = sm.load_test_set(roofs)

    train_median = train[sm.FEATURES].median()
    X_train = train[sm.FEATURES].fillna(train_median)
    y_train = train["y"].to_numpy()
    X_test = test[sm.FEATURES].fillna(train_median)
    fully_covered_by_pv = (test["pv_status"] == sm.PV_FULL).to_numpy()

    y_true, keep = sm.build_label_versions(test)[LABEL_VERSION]

    fitted, predictions = {}, {}
    for name, model in sm.build_models(y_train).items():
        fitted[name] = clone(model).set_params(random_state=sm.SEED).fit(X_train.to_numpy(), y_train)
        predictions[name], _ = sm.predict_with_rule_override(fitted[name], X_test.to_numpy(), fully_covered_by_pv)
    predictions["rule"] = sm.rule_baseline(test, fully_covered_by_pv)

    return X_test, y_true, keep, fully_covered_by_pv, fitted, predictions


def plot_confusion_matrices(y_true, keep, predictions, out_dir):
    """One 2 x 2 matrix per method. Rows = true class, columns = predicted class."""
    titles = dict(DISPLAY_NAMES, rule=f"Rule baseline (full PV or net area < {int(sm.MIN_NET_AREA_M2)} m²)")
    order = ["random_forest", "xgboost", "extra_trees_additional", "rule"]
    fig, axes = plt.subplots(1, 4, figsize=(15, 4.2))
    for ax, name in zip(axes, order):
        matrix = confusion_matrix(y_true[keep], predictions[name][keep], labels=[0, 1])
        ax.imshow(matrix, cmap="Blues", vmin=0, vmax=matrix.max())
        for row in range(2):
            for col in range(2):
                # white text on dark cells, dark text on light cells
                colour = "white" if matrix[row, col] > 0.5 * matrix.max() else INK
                ax.text(col, row, str(matrix[row, col]), ha="center", va="center", fontsize=20, fontweight="bold", color=colour)
        ax.set_xticks([0, 1], CLASS_NAMES, fontsize=10, color=INK)
        ax.set_yticks([0, 1], CLASS_NAMES, fontsize=10, color=INK, rotation=90, va="center")
        ax.set_xlabel("Predicted", fontsize=10, color=MUTED)
        if name == order[0]:
            ax.set_ylabel("True (hand label)", fontsize=10, color=MUTED)
        ax.set_title(titles[name], fontsize=11, color=INK, pad=10, wrap=True)
        ax.tick_params(length=0)
        for spine in ax.spines.values():
            spine.set_visible(False)
    n_roofs, n_negative = int(keep.sum()), int((y_true[keep] == 0).sum())
    fig.suptitle(f"Confusion matrices on the test set ({n_roofs} roofs, {n_negative} not suitable; seed {sm.SEED})",
                 fontsize=13, color=INK, y=1.02)
    fig.tight_layout()
    fig.savefig(os.path.join(out_dir, "confusion_matrices.png"), dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def shap_values_for_suitable(model, X):
    """Return a (n_roofs, n_features) array of SHAP values for the class "suitable"."""
    values = shap.TreeExplainer(model).shap_values(X.to_numpy())
    if isinstance(values, list):          # older SHAP: one array per class
        values = values[1]
    values = np.asarray(values)
    if values.ndim == 3:                  # newer SHAP: (roofs, features, classes)
        values = values[:, :, 1]
    return values


def plot_shap(X_model, fitted, out_dir):
    """Mean |SHAP| bar chart for both proposal models, plus one beeswarm plot per model."""
    names = ["random_forest", "xgboost"]
    shap_values = {name: shap_values_for_suitable(fitted[name], X_model) for name in names}

    # 1) importance = mean absolute SHAP value per feature
    importance = pd.DataFrame({DISPLAY_NAMES[name]: np.abs(shap_values[name]).mean(axis=0) for name in names},
                              index=sm.FEATURES)
    importance.round(4).to_csv(os.path.join(out_dir, "shap_importance.csv"), index_label="feature")

    fig, axes = plt.subplots(1, 2, figsize=(13, 6))
    for ax, name in zip(axes, names):
        column = importance[DISPLAY_NAMES[name]].sort_values()
        ax.barh(column.index, column.values, color=BAR_COLOR, height=0.65)
        for y_position, value in enumerate(column.values):
            ax.text(value, y_position, f"  {value:.3f}", va="center", fontsize=9, color=INK)
        ax.set_title(DISPLAY_NAMES[name], fontsize=12, color=INK)
        # the two models use different output scales, so each panel has its own x-axis
        unit = "probability of suitable" if name == "random_forest" else "log-odds of suitable"
        ax.set_xlabel(f"Mean |SHAP value| ({unit})", fontsize=10, color=MUTED)
        ax.set_xlim(0, column.max() * 1.18)
        ax.tick_params(axis="y", length=0, labelsize=10, labelcolor=INK)
        ax.tick_params(axis="x", labelsize=9, labelcolor=MUTED)
        ax.grid(axis="x", color="#e5e7eb", linewidth=0.8)
        ax.set_axisbelow(True)
        for side in ("top", "right", "left"):
            ax.spines[side].set_visible(False)
        ax.spines["bottom"].set_color("#d1d5db")
    fig.suptitle(f"Feature importance by SHAP ({len(X_model)} test roofs that reach the classifier)", fontsize=13, color=INK)
    fig.tight_layout()
    fig.savefig(os.path.join(out_dir, "shap_importance.png"), dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)

    # 2) beeswarm: every dot is one roof; colour = feature value, position = effect on the prediction
    for name in names:
        plt.figure()
        shap.summary_plot(shap_values[name], X_model, feature_names=sm.FEATURES, show=False, plot_size=(9, 6.5))
        plt.title(f"{DISPLAY_NAMES[name]}: SHAP values for the class \"suitable\"", fontsize=12, color=INK)
        plt.xlabel("SHAP value (right = pushes towards suitable, left = towards not suitable)", fontsize=10)
        plt.savefig(os.path.join(out_dir, f"shap_beeswarm_{name}.png"), dpi=200, bbox_inches="tight", facecolor="white")
        plt.close()
    return importance


def plot_permutation_importance(X_model, y_model, fitted, out_dir):
    """Drop in macro F1 after shuffling one feature (mean and standard deviation over repeats)."""
    names = ["random_forest", "xgboost"]
    table = {}
    fig, axes = plt.subplots(1, 2, figsize=(13, 6), sharex=True)
    for ax, name in zip(axes, names):
        result = permutation_importance(fitted[name], X_model.to_numpy(), y_model, scoring="f1_macro",
                                        n_repeats=N_PERMUTATION_REPEATS, random_state=sm.SEED, n_jobs=2)
        table[DISPLAY_NAMES[name] + " mean"] = result.importances_mean
        table[DISPLAY_NAMES[name] + " std"] = result.importances_std
        order = np.argsort(result.importances_mean)
        labels = [sm.FEATURES[i] for i in order]
        ax.barh(labels, result.importances_mean[order], xerr=result.importances_std[order], color=BAR_COLOR,
                height=0.65, error_kw={"ecolor": MUTED, "elinewidth": 1, "capsize": 2})
        ax.axvline(0, color="#9ca3af", linewidth=1)
        ax.set_title(DISPLAY_NAMES[name], fontsize=12, color=INK)
        ax.set_xlabel("Drop in macro F1 when the feature is shuffled", fontsize=10, color=MUTED)
        ax.tick_params(axis="y", length=0, labelsize=10, labelcolor=INK)
        ax.tick_params(axis="x", labelsize=9, labelcolor=MUTED)
        ax.grid(axis="x", color="#e5e7eb", linewidth=0.8)
        ax.set_axisbelow(True)
        for side in ("top", "right", "left"):
            ax.spines[side].set_visible(False)
        ax.spines["bottom"].set_color("#d1d5db")
    fig.suptitle(f"Permutation importance ({len(X_model)} test roofs that reach the classifier, "
                 f"{N_PERMUTATION_REPEATS} shuffles per feature; bars = mean, whiskers = 1 std)", fontsize=13, color=INK)
    fig.tight_layout()
    fig.savefig(os.path.join(out_dir, "permutation_importance.png"), dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    table = pd.DataFrame(table, index=sm.FEATURES)
    table.round(4).to_csv(os.path.join(out_dir, "permutation_importance.csv"), index_label="feature")
    return table


def main():
    out_dir = sys.argv[1] if len(sys.argv) > 1 else "results"
    os.makedirs(out_dir, exist_ok=True)

    X_test, y_true, keep, fully_covered_by_pv, fitted, predictions = prepare()
    plot_confusion_matrices(y_true, keep, predictions, out_dir)

    # SHAP only for roofs the classifier actually decides (rule-decided roofs are excluded)
    reaches_classifier = keep & ~fully_covered_by_pv
    X_model = X_test[reaches_classifier]
    importance = plot_shap(X_model, fitted, out_dir)
    permutation = plot_permutation_importance(X_model, y_true[reaches_classifier], fitted, out_dir)

    print("Mean |SHAP| per feature (largest first, Random Forest order):")
    print(importance.sort_values("Random Forest", ascending=False).round(3).to_string())
    print("\nPermutation importance (drop in macro F1, largest first, Random Forest order):")
    print(permutation.sort_values("Random Forest mean", ascending=False).round(3).to_string())
    print(f"\nSaved figures to: {out_dir}/")


if __name__ == "__main__":
    main()
