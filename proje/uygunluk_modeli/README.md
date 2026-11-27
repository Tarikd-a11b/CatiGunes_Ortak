# Rooftop PV suitability model (stage 1: "Can panels be installed on this roof?")

Prepared by Yiğit Eren Yıldırım, 14 November 2026; updated 27 November 2026 (Extra Trees is the main model)

## Model choice

Advisor decision (27 November 2026): report the results of all models; use the best-performing model in the application. **Extra Trees** scored best on the hand-labelled test set and is the model used in the application (`uygun_et` in `model_verisi/uygunluk/cati_uygunluk.csv`). Random Forest and XGBoost, the two models named in the project proposal, are reported alongside, together with the rule baseline.

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
| `suitability_model.py` | Trains Extra Trees, Random Forest and XGBoost, evaluates them and the rule baseline on the test set |
| `uygunluk_veri_tablosu.csv`, `cati_uretim.csv`, `sekil_ozellikleri.csv` | Features of all 1,085 roofs (from the shared data pipeline; Turkish column names are renamed inside the script) |
| `egitim_etiket_v2.csv` | 200 hand-labelled training roofs (roof 1391 is not a roof and is not used) |
| `test_etiketli_birlesik.csv` | 111 hand-labelled test roofs (original labels) |
| `predict_all_roofs.py` | Applies the same models to all 1,085 roofs and writes `model_verisi/uygunluk/cati_uygunluk.csv` for the API, web map and LLM layer (does not change any score) |
| `make_figures.py` | Draws the confusion matrices, SHAP explanations and permutation importance (uses the same data, features and model settings) |
| `results/results.json` | All scores, including confusion matrices |
| `results/test_predictions.csv` | Per-roof labels (three versions) and predictions |
| `results/confusion_matrices.png` | Confusion matrix of each method (label version B, seed 42) |
| `results/shap_importance.png`, `results/shap_importance.csv` | Mean absolute SHAP value per feature for Random Forest, XGBoost and Extra Trees |
| `results/shap_beeswarm_*.png` | SHAP beeswarm plots: one dot per roof, right = pushes towards "suitable" |
| `results/permutation_importance.png`, `results/permutation_importance.csv` | Drop in macro F1 when one feature is shuffled (50 shuffles per feature) |

## Method in brief

- Roofs whose existing PV covers the whole roof are "not suitable" by a team rule and never reach the classifier.
- For all other roofs the classifier learns from 200 hand labels using 16 numeric features: 6 basic (net area, gross area, existing PV share, pitched flag, deviation from south, specific yield) and 10 footprint-shape features (width, length, aspect ratio, compactness, solidity, rectangularity, number of parts, number of holes, inscribed-circle radius, net-to-gross ratio).
- Hyper-parameters are fixed and simple (Extra Trees: 300 trees, at least 3 roofs per leaf; RF: 300 trees, depth 6; XGBoost: 150 trees, depth 3). Class weights give each "not suitable" roof about 6.4 times the weight of a "suitable" roof. The test set was not used to tune any model.
- Roofs within 5 m of a test roof were excluded from the training sample.

## Test-label versions

- **A:** original 111 labels.
- **B (main result):** two records flagged before modelling are corrected. Roof 1307 becomes "suitable" (measurement error); roof 1076 is excluded because it is a courtyard, not a roof. 110 roofs, 20 "not suitable".
- **C:** B plus roof 1004 re-labelled "suitable". This change was made after seeing the model's error, so it is reported separately.

## Results (version B; tree models averaged over 15 seeds)

Environment: scikit-learn 1.6.1, xgboost 3.1.2 (see `requirements.txt`).

| Method | F1 suitable | F1 not suitable | Macro F1 |
|---|---|---|---|
| **Extra Trees (main model)** | **0.961** | **0.829** (identical for all 15 seeds) | **0.895** |
| Random Forest | 0.953 | 0.756 (0.722–0.778) | 0.854 |
| XGBoost | 0.941 | 0.718 (0.684–0.757) | 0.830 |
| Rule baseline (full PV or net area < 100 m²) | 0.957 | 0.778 | 0.867 |

With the original labels (A): Extra Trees F1 suitable 0.950, F1 not suitable 0.791, macro F1 0.870; Random Forest 0.942 / 0.716 / 0.829.

Confusion matrices (seed 42, version B), "not suitable" roofs caught / missed / false alarms among 90 "suitable" roofs: Extra Trees 17 / 3 / 4; Random Forest 13 / 7 / 2; XGBoost 13 / 7 / 5; rule 14 / 6 / 2. ROC-AUC of Extra Trees on the roofs that reach the classifier: 0.938.

### Sensitivity to the library version

Random Forest results depend on the scikit-learn version, because different versions build different trees from the same seed. With scikit-learn 1.9.1 the same script gives F1 not suitable 0.791 and macro F1 0.872 for Random Forest (version B). The gap corresponds to three test roofs. The rule baseline and Extra Trees give identical results in both versions. XGBoost may differ in the third decimal between operating systems.

## Caveats

- Extra Trees is ahead of the rule baseline, but the difference is not statistically significant (95% bootstrap interval of the macro-F1 difference: -0.057 to 0.119); with 20 "not suitable" test roofs it corresponds to about three roofs.
- Random Forest and the rule baseline are statistically indistinguishable (95% bootstrap interval of the macro-F1 difference: -0.079 to 0.031). Depending on the library version, Random Forest is slightly below or slightly above the rule on the 'not suitable' class.
- A model trained on rule-based labels reproduces the rule exactly; its score equals the rule-baseline row.
- The test set holds only 20 "not suitable" roofs, so one roof moves that F1 by about 0.03.
- All labels come from a single labeller.
- The 100 m² area threshold is not a team decision yet; it is used here for comparison only.
- Shape features clearly helped the tree models. SAM quality fields, extra engineered features, probability-threshold tuning and a wide hyper-parameter search did not help.

## What SHAP shows

- Extra Trees relies mainly on the net-to-gross ratio, inscribed-circle radius, width, compactness and net area: it asks above all whether the roof is narrow and how much of it the edge setbacks remove.
- Random Forest and XGBoost rely mainly on net area, rectangularity, width and the other shape features. Small, narrow or irregular footprints push a roof towards "not suitable".
- In Extra Trees, specific yield and the pitched flag carry a small weight. This is not an irradiation effect: specific yield has one value per region (Atatürk OIZ and Çiğli), so the model uses it as a region marker, and all pitched roofs are Çiğli schools.
- In Random Forest and XGBoost, orientation, specific yield, the pitched flag and the existing-PV share contribute almost nothing. Specific yield is nearly constant within each region, and fully PV-covered roofs are handled by the rule before the classifier.
- SHAP explains what the model does, not what is true on the ground. With only 27 "not suitable" training roofs, the ranking of mid-level features is not stable.

## What permutation importance shows

- Extra Trees: shuffling the net-to-gross ratio (drop 0.10), inscribed-circle radius (0.08), width (0.07) or net area (0.04) lowers macro F1 most. Rectangularity has no importance of its own here; its information is carried by compactness and the net-to-gross ratio. Specific yield shows a small drop (0.03), for the region-marker reason given above.
- Random Forest: shuffling any one of eight features (rectangularity, net-to-gross ratio, net area, width, aspect ratio, inscribed-circle radius, compactness, solidity) lowers macro F1 by 0.05 to 0.11. The model genuinely needs the area and shape information.
- XGBoost: only net area clearly helps (drop of 0.085). Shuffling solidity, gross area or width slightly raises the score, which means XGBoost uses these features in a way that does not carry over to the test roofs. This fits its lower test score.
- Orientation and the existing-PV share have zero importance in all three models.
- The whiskers are wide because the test set holds few "not suitable" roofs; only the clear separation between the top group and the zero group should be interpreted.
