# Rooftop PV suitability model (stage 1: "Can panels be installed on this roof?")

Prepared by Yiğit Eren Yıldırım, 14 November 2026

## How to run

```
pip install -r requirements.txt
python suitability_model.py results
python make_figures.py results
```

Outputs are written to `results/`. Input files are never modified.

## Files

| File | Content |
|---|---|
| `suitability_model.py` | Trains Random Forest, XGBoost and the rule baseline, evaluates them on the test set |
| `uygunluk_veri_tablosu.csv`, `cati_uretim.csv`, `sekil_ozellikleri.csv` | Features of all 1,085 roofs (from the shared data pipeline; Turkish column names are renamed inside the script) |
| `egitim_etiket_v2.csv` | 200 hand-labelled training roofs (roof 1391 is not a roof and is not used) |
| `test_etiketli_birlesik.csv` | 111 hand-labelled test roofs (original labels) |
| `make_figures.py` | Draws the confusion matrices, SHAP explanations and permutation importance (uses the same data, features and model settings) |
| `results/results.json` | All scores, including confusion matrices |
| `results/test_predictions.csv` | Per-roof labels (three versions) and predictions |
| `results/confusion_matrices.png` | Confusion matrix of each method (label version B, seed 42) |
| `results/shap_importance.png`, `results/shap_importance.csv` | Mean absolute SHAP value per feature for Random Forest and XGBoost |
| `results/shap_beeswarm_*.png` | SHAP beeswarm plots: one dot per roof, right = pushes towards "suitable" |
| `results/permutation_importance.png`, `results/permutation_importance.csv` | Drop in macro F1 when one feature is shuffled (50 shuffles per feature) |

## Method in brief

- Roofs whose existing PV covers the whole roof are "not suitable" by a team rule and never reach the classifier.
- For all other roofs the classifier learns from 200 hand labels using 16 numeric features: 6 basic (net area, gross area, existing PV share, pitched flag, deviation from south, specific yield) and 10 footprint-shape features (width, length, aspect ratio, compactness, solidity, rectangularity, number of parts, number of holes, inscribed-circle radius, net-to-gross ratio).
- Hyper-parameters are fixed and simple (RF: 300 trees, depth 6; XGBoost: 150 trees, depth 3). The test set was not used for any model choice.
- Roofs within 5 m of a test roof were excluded from the training sample.

## Test-label versions

- **A:** original 111 labels.
- **B (main result):** two records flagged before modelling are corrected. Roof 1307 becomes "suitable" (measurement error); roof 1076 is excluded because it is a courtyard, not a roof. 110 roofs, 20 "not suitable".
- **C:** B plus roof 1004 re-labelled "suitable". This change was made after seeing the model's error, so it is reported separately.

## Results (version B; tree models averaged over 15 seeds)

Environment: scikit-learn 1.6.1, xgboost 3.1.2 (see `requirements.txt`).

| Method | F1 suitable | F1 not suitable | Macro F1 |
|---|---|---|---|
| Random Forest | 0.953 | 0.756 (0.722–0.778) | 0.854 |
| XGBoost | 0.941 | 0.718 (0.684–0.757) | 0.830 |
| Rule baseline (full PV or net area < 100 m²) | 0.957 | 0.778 | 0.867 |
| Extra Trees (additional comparison) | 0.961 | 0.829 | 0.895 |

With the original labels (A), Random Forest scores F1 suitable 0.942, F1 not suitable 0.716, macro F1 0.829.

Confusion matrix of Random Forest (seed 42, version B): 13 of 20 "not suitable" roofs caught, 7 missed, 2 false alarms among 90 "suitable" roofs.

### Sensitivity to the library version

Random Forest results depend on the scikit-learn version, because different versions build different trees from the same seed. With scikit-learn 1.9.1 the same script gives F1 not suitable 0.791 and macro F1 0.872 for Random Forest (version B). The gap corresponds to three test roofs. The rule baseline and Extra Trees give identical results in both versions. XGBoost may differ in the third decimal between operating systems.

## Caveats

- Random Forest and the rule baseline are statistically indistinguishable (95% bootstrap interval of the macro-F1 difference: -0.079 to 0.031). Depending on the library version, Random Forest is slightly below or slightly above the rule on the 'not suitable' class.
- A model trained on rule-based labels reproduces the rule exactly; its score equals the rule-baseline row.
- The test set holds only 20 "not suitable" roofs, so one roof moves that F1 by about 0.03.
- All labels come from a single labeller.
- The 100 m² area threshold is not a team decision yet; it is used here for comparison only.
- Shape features clearly helped Random Forest. SAM quality fields, extra engineered features, probability-threshold tuning and a wide hyper-parameter search did not help.

## What SHAP shows

- Both models rely mainly on net area, rectangularity, width and the other shape features. Small, narrow or irregular footprints push a roof towards "not suitable".
- Orientation, specific yield, the pitched flag and the existing-PV share contribute almost nothing. Specific yield is nearly constant within each region, and fully PV-covered roofs are handled by the rule before the classifier.
- SHAP explains what the model does, not what is true on the ground. With only 27 "not suitable" training roofs, the ranking of mid-level features is not stable.

## What permutation importance shows

- Random Forest: shuffling any one of eight features (rectangularity, net-to-gross ratio, net area, width, aspect ratio, inscribed-circle radius, compactness, solidity) lowers macro F1 by 0.05 to 0.11. The model genuinely needs the area and shape information.
- XGBoost: only net area clearly helps (drop of 0.085). Shuffling solidity, gross area or width slightly raises the score, which means XGBoost uses these features in a way that does not carry over to the test roofs. This fits its lower test score.
- Orientation, specific yield, the pitched flag and existing-PV share have zero importance in both models.
- The whiskers are wide because the test set holds few "not suitable" roofs; only the clear separation between the top group and the zero group should be interpreted.
