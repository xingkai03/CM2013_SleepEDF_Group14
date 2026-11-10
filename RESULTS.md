# Results log — `Sleep EDF`, `Group 14`

For a guide to the saved files and comparisons, see [the results index](results/README.md). For your first experiment, see [getting started](docs/GETTING_STARTED.md). Script paths below reflect the current folder structure, including the shared baseline runner in `scripts/internal/`; historical metrics and result directories are retained.

> It exists because Chapter 16 §16.3 defines an iteration as *done* only when it 
>
> (1) runs end to end to a result
>
> (2) reports the primary metric **with its spread**
>
> (3) is committed with a note saying what changed and why
>
> (4) is at least as good as the previous iteration **or** says in writing why the change was kept anyway. 
>
> This table is where (2), (3) and (4) land; `git log` is where (1) becomes checkable. It also makes writing the report an assembly job rather than an archaeology project.
>
> **This file is graded.** `CAPSTONE_REPORT_RUBRIC.md` **Criterion 9 — Iteration & revision history (3 pts)** takes `RESULTS.md` as its evidence, and it asks for one specific thing that a forward-only log cannot show: **at least one earlier decision you went back and changed because of a downstream result**, with the symptom that sent you back named. A row that *lowered* the headline metric and was kept for a stated reason is full-marks evidence, not a weakness. Rows here are also direct evidence for "Reproducibility & engineering" and "Report quality & defence".

**Track:** `sleep_edf` ·
**Split unit:** `subject` · **Primary metric:** Cohen's kappa ·
**Evaluation mode:** subject-wise LOSO for early experiments (3 real subjects); fixed five-fold subject-wise GroupKFold for large-scale development experiments (68 subjects). Final holdout excluded from development.

## Iteration log

Paste the metric straight from the harness — `rep["summary"]` prints the required shape, e.g.
`mean cohens_kappa 0.61 (sd 0.12, range 0.34-0.73 across 8 subjects)`. A pooled number with no
spread is half a result.

| # | Date | What changed & why (one line) | Primary metric **with spread** | Better than previous? | If not — why it was kept | Commit |
|---|---|---|---|---|---|---|
| ~~1 (smoke only)~~ | ~~2026-09-30~~ | ~~Supplied baseline on synthetic medium-difficulty data~~ | ~~mean kappa 0.682 (sd 0.318, range 0.155-0.933 across 5 subjects)~~ | ~~Baseline~~ | ~~Functional check only~~ | ~~`0a48f51`~~ |
| ~~1a (real baseline)~~ | ~~2026-10-01~~ | ~~Same supplied model and features on SC4001, SC4011, SC4021; establish a real-data reference~~ | ~~mean kappa 0.618 (sd 0.202, range 0.386-0.760 across 3 subjects)~~ | ~~Baseline on real data~~ | - | ~~`dde6e44`~~ |
| ~~1b (real baseline)~~ | ~~2026-10-02~~ | ~~Supplied baseline run end-to-end on real Sleep-EDF data to establish the reference performance before DSP/feature changes~~ | ~~mean cohens_kappa 0.720 (sd 0.119, range 0.589-0.822 across 3 subjects)~~ | ~~Baseline on real data~~ | - | ~~`69d392f`~~ |
| 1c (course environment, smoke) | 2026-10-08 | Align Python and dependencies with the course guide; repeat the P0 synthetic smoke check (5 subjects × 80 epochs, seed 0) | mean cohens_kappa 0.614 (sd 0.314, range 0.137-0.933 across 5 subjects) | Baseline on smoke data | Kept to match the course pins; scores from the earlier environment remain historical | `e470502` |
| 1d (course environment, real baseline) | 2026-10-08 | Repeat P0 on subjects 0, 1, 2, both nights, under the course environment; unchanged features and classifier, seed 0 | mean cohens_kappa 0.723 (sd 0.115, range 0.596-0.822 across 3 subjects) | Baseline on real data | Kept to match the course pins; rerun preprocessing/model candidates under this environment before comparing them | `e470502` |
| 2a | 2026-10-06 | P0: current baseline on 3 subjects × 2 nights, no preprocessing, to establish the development reference | mean cohens_kappa 0.704 (sd 0.087, range 0.627-0.799 across 3 subjects) | Baseline for Iteration 2 development experiments | - | `e6cada5` |
| 2b | 2026-10-06 | P1: EEG 0.5–40 Hz zero-phase Butterworth band-pass; tested as a controlled preprocessing candidate | mean cohens_kappa 0.737 (sd 0.074, range 0.666-0.813 across 3 subjects) | Yes — pooled κ 0.710→0.742; macro-F1 0.648→0.683 | - | `e6cada5` |
| 2c | 2026-10-06 | P2: EEG wavelet denoising using db4, automatic decomposition level (max 5), soft thresholding and automatic per-epoch VisuShrink threshold; EOG and EMG unchanged | mean Cohen's kappa 0.743 (sd 0.065, range 0.669–0.781 across 3 subjects) | Yes vs P0; only marginally higher kappa than P1, with lower macro-F1 and balanced accuracy | P1 retained as the current preprocessing candidate because it provides more balanced stage-wise performance |`97447e2` |
| 2d | 2026-10-06 | P3: objective broken-segment handling; epochs with simultaneous full-epoch near-flat EEG and EOG were excluded using thresholds fixed from QC before evaluation; 3/16,688 epochs were removed | mean Cohen's kappa 0.694 (sd 0.109, range 0.582–0.800 across 3 subjects) | No — mean kappa decreased from 0.704 to 0.694 vs P0; macro-F1 0.648→0.644 | Retained as a data-quality safeguard rather than a performance improvement: the rule removes objectively unreliable epochs and provides predefined handling if similar sustained flatlines occur in additional recordings |`7c34ebf` |
| 2e | 2026-10-08 | P5: EEG suspected-clipping detection using recording-specific extrema and plateaus of at least 3 consecutive samples (30 ms); 57/16,688 epochs flagged, with no signal modification or exclusion | mean cohens_kappa 0.704 (sd 0.087, range 0.627-0.799 across 3 subjects) | No improvement vs P0; all 16,688 predictions identical (0 differences) | Retained as a label-independent signal-quality safeguard: suspected clipping is documented without reconstructing potentially lost EEG information or altering classification | `c8410dc` |
| 2ca                                  | 2026-10-08 | Model: XGBoost | mean cohens_kappa 0.754 (sd 0.011, range 0.742-0.765 across 3 subjects) | Yes vs 2c | - | `c85cb4` |
|                                     |                |                                                              |                                                              |                                                              |                                                              |               |
| 2f (spindle preservation) | 2026-10-16 | Physiological validation of P1 vs P2 on eight automatically detected spindle candidates in two N2 epochs from SC400; compared sigma power, Hilbert envelope, independent re-detection and temporal matching | N/A — diagnostic analysis only; no new LOSO classification run. P2 sigma-power retention: 27.63% (SD 17.98 pp); P1 re-detection: 8/8; P2: 5/8 at IoU ≥ 0.30 | P1 better preserved the selected spindle candidates; classification performance not reassessed | Retain P1 as the preferred preprocessing candidate; reconsider P2 thresholding before further use, subject to larger-scale validation | `217763e` |
| 2g (mother wavelet comparison) | 2026-10-19 | Compared db4, sym4, coif1 and coif3 under identical 3-fold subject-wise LOSO conditions (16,688 epochs); verified exact reproduction of the original db4 P2 features | db4: mean κ 0.736 (sd 0.102, range 0.620–0.811); sym4: 0.730 (sd 0.104, range 0.611–0.806); coif1: 0.727 (sd 0.090, range 0.625–0.798); coif3: 0.738 (sd 0.103, range 0.621–0.813), across 3 subjects | No clear improvement — coif3 gained only +0.002 mean κ over db4 | Retain db4 as the P2 reference; reconsider coif3 on a larger development cohort. P1 remains the preferred preprocessing candidate | 510d041 |
| 2h (P6 clock cropping) | 2026-10-21 | Fixed 20:30–11:00 clock-based selection for training epochs, combined with P1 band-pass; full held-out nights retained for testing | mean κ 0.735 (sd 0.102, range 0.620–0.816 across 3 subjects); P1: 0.743 (sd 0.114) | No, pooled κ 0.752→0.742; balanced accuracy 0.619→0.625, but better classification for some sleep stages | Retained as a reproducible, label-independent training-selection experiment; P1 remains preferred | `f8bbda7` |
| 2i (large-scale P0) | 2026-10-29 | Re-evaluated the unprocessed baseline on 68 development subjects (133 recordings, 360,621 epochs), using fixed five-fold subject-wise GroupKFold to establish a larger-cohort reference | mean κ 0.726 (sd 0.118, range 0.231–0.895 across 68 subjects) | New large-cohort baseline; not directly comparable with three-subject LOSO results | Retained as the reference for controlled large-scale preprocessing comparisons | `4ccdbbc` |
| 2j (large-scale P1) | 2026-10-29 | Re-evaluated EEG 0.5–40 Hz band-pass filtering on the same 68 subjects and fixed folds | mean κ 0.728 (sd 0.120, range 0.217–0.906 across 68 subjects) | Marginal improvement vs P0: pooled κ 0.728→0.731, macro-F1 0.651→0.655 | P1 remains preferred provisionally; improvement is small relative to subject variability | `4ccdbbc` |
| 2k (large-scale P2) | 2026-10-30 | Re-evaluated EEG wavelet denoising using the current P2 configuration on the same 68 subjects and fixed folds | mean κ 0.687 (sd 0.129, range 0.216–0.886 across 68 subjects) | No: pooled κ 0.728→0.692 and macro-F1 0.651→0.624 vs P0 | Retained as a documented negative result; wavelet settings and physiological preservation require further investigation | `4ccdbbc` |
| 2l (integrated preprocessing QC) | 2026-10-31 | Integrated P3 near-flat and P5 suspected-clipping flags with P1 band-pass in the SleepEDFTrack pipeline; verified that QC metadata is preserved without changing signals, labels, epochs or extracted features | N/A — integration validation, no new classifier evaluation; P1 reference: mean subject κ 0.728 (SD 0.120, range 0.217–0.906 across 68 subjects) | No classification change expected: QC flags are metadata only | Retained to provide reproducible signal-quality monitoring without excluding potentially valid epochs | `66aa8ae` |
| 2m (68-subject QC and error analysis) | 2026-11-01 | Applied P3/P5 flag-only QC to 133 recordings and aligned flagged epochs with P1 out-of-fold predictions across 68 development subjects | P1 reference: mean subject κ 0.728 (SD 0.120, range 0.217–0.906); 3,630/360,621 epochs flagged (1.007%); flagged error 3.609% vs unflagged 12.719% | No new classifier evaluation; 94.1% of flagged epochs were Wake, explaining much of the aggregate difference | Retained QC as diagnostic metadata; stage-specific analysis showed higher error among flagged N2/REM epochs, but flagged counts were small | `66aa8ae` |
| 2n (combined P1+P2, 68 subjects) | 2026-11-01 | Evaluated sequential EEG 0.5–40 Hz band-pass filtering followed by db4 wavelet denoising on the same 68 development subjects and fixed five-fold subject-wise GroupKFold splits | mean subject κ 0.696 (SD 0.137, range 0.169–0.914 across 68 subjects) | No — pooled κ decreased from 0.731 (P1) to 0.702 (P1+P2); 53/68 subjects deteriorated | Retained as a documented negative experiment; the combined preprocessing is not selected for the current 11-feature Random Forest pipeline | `66aa8ae` |

| 2o (P1b, cutoff sensitivity) | 2026-11-02 | Reduced the EEG Butterworth upper cutoff from 40 to 35 Hz while keeping order 4 and zero-phase epoch-wise filtering; evaluated on the same 68 development subjects and five GroupKFold splits | mean subject κ 0.727 (SD 0.121 across 68 subjects); pooled κ 0.730; macro-F1 0.654 | No clear improvement vs P1 (pooled κ 0.731) | Retained as a controlled sensitivity experiment; P1 remains the preferred configuration | `bca3a38` |
| 2p (P1c, filter-order sensitivity) | 2026-11-02 | Increased the EEG Butterworth order from 4 to 5 at 0.5–35 Hz, keeping all other pipeline settings unchanged | mean subject κ 0.727 (SD 0.121, range 0.223–0.911 across 68 subjects); pooled κ 0.730; macro-F1 0.654 | No measurable improvement vs P1b at three-decimal precision | Retained as a documented neutral experiment; P1 remains preferred | `bca3a38` |

| 2q (P1d, continuous EEG filtering) | 2026-11-02 | Applied the P1 Butterworth 0.5–40 Hz order-4 filter to continuous EEG before epoch segmentation, rather than filtering each 30-second epoch independently; evaluated on the same 68 development subjects and five subject-wise folds | mean subject κ 0.728 (SD 0.121, range 0.223–0.909 across 68 subjects); pooled κ 0.731; macro-F1 0.655 | No meaningful improvement over P1 (pooled κ 0.731) | Retained as a controlled comparison of filter placement; P1 remains preferred | pending |
| 2r (EEG clipping and EDF limits) | 2026-11-06 | Investigated repeated EEG extrema, validated clipping candidates against EDF physical limits, and quantified sustained boundary plateaus across 133 recordings | N/A — diagnostic QC; 1,227/360,621 epochs flagged (0.340%) using plateaus of at least 10 samples at recording extrema | No new classification evaluation | Retained as objective signal-quality documentation without signal reconstruction or epoch exclusion | pending |
| 2s (EOG/EMG quality audit) | 2026-11-06 | Audited original EOG and EMG channels for EDF-boundary samples, examined sampling rates and inspected epochs with extreme signal variability | N/A — diagnostic QC; EOG: 1 EDF-boundary sample across 133 recordings; EMG: 0 | No new classification evaluation | No additional automatic correction justified; original EOG/EMG preserved | pending |
| 2t (multichannel inspection) | 2026-11-06 | Visually compared aligned EEG, EOG and EMG signals in suspicious epochs from SC4372F0 to investigate possible shared disturbances | N/A — visual diagnostic only; no classifier evaluation | No new classification evaluation | Large-amplitude fluctuations were not sufficient to confirm acquisition artifacts; retain flag-only QC | pending |

| 4 |  |  |  | yes / no |  |  |
| 4 |  |  |  | yes / no |  |  |
| 4 |  |  |  | yes / no |  |  |
| 4 |  |  |  | yes / no |  |  |
| 4 |  |  |  | yes / no |  |  |
| 4 |  |  |  | yes / no |  |  |

*"Better" means better under the same honest harness — same split unit, same evaluation mode, same seed. A change that lowers the metric can still be the right call (simpler, faster, more robust across subjects, removes a leak). Say so in the column instead of quietly reverting it: "kept — κ fell 0.02 but the worst-subject κ rose from 0.18 to 0.31" is a stronger result than a silent higher mean.*

## Detailed log

### Feature summary on 2 subjects (SC4001, SC4011, SC4002, SC4022) - Lucas 10-11-2026

============================================================
COMBINED RESULTS (4 recordings, 11129 epochs)
============================================================

Mean feature value per sleep stage (all recordings pooled):
       eeg_rel_delta  eeg_rel_sigma  eeg_sef_95  eeg_zcr  eeg_dwt_d2_energy    emg_wl
stage                                                                                
N1             0.699        0.02515       15.36   0.1322            0.04902 9.268e-06
N2            0.7929        0.03478       10.01  0.09603            0.03234  8.92e-06
N3            0.9135       0.009202       5.072  0.05565           0.008532 7.937e-06
REM           0.6695        0.02406       13.18   0.1251            0.04296 8.204e-06
W             0.8248        0.01515       10.66   0.1281            0.03203 3.909e-06

Std per sleep stage (all recordings pooled):
       eeg_rel_delta  eeg_rel_sigma  eeg_sef_95  eeg_zcr  eeg_dwt_d2_energy    emg_wl
stage                                                                                
N1            0.1232         0.0125       5.489  0.02281            0.02321 4.662e-06
N2            0.0706        0.02204       2.958  0.01764            0.01713 3.729e-06
N3           0.03417       0.005647       1.454   0.0125           0.005872 2.799e-06
REM           0.1047        0.01217       4.184  0.02244             0.0237 5.432e-06
W             0.1049        0.01431       6.864  0.05719             0.0322 5.433e-06

Mean per stage, per subject (rows = stage, columns = subject):

eeg_rel_delta
subject  SC4001  SC4002  SC4011  SC4012
stage                                  
N1       0.6137  0.6169  0.7662  0.7258
N2        0.802  0.7657  0.8001  0.7988
N3       0.9149  0.9076  0.9217  0.9197
REM      0.6178  0.5877  0.7391   0.739
W        0.8085  0.7097  0.9001  0.8851

eeg_rel_sigma
subject   SC4001  SC4002   SC4011   SC4012
stage                                     
N1       0.02605 0.03428  0.02101  0.02363
N2       0.03055 0.04155   0.0335  0.03364
N3      0.008124 0.01064 0.007864 0.008693
REM      0.02515 0.03527  0.01661  0.01678
W        0.01535 0.03423 0.004771 0.005759

eeg_sef_95
subject  SC4001  SC4002  SC4011  SC4012
stage                                  
N1        13.87   15.21   15.22   16.57
N2        9.034   10.89   9.915   9.952
N3        4.909   5.444   4.648   4.755
REM       12.41   16.14   11.44   11.81
W         11.15   20.33   5.255    5.63

eeg_zcr
subject  SC4001  SC4002  SC4011  SC4012
stage                                  
N1        0.133  0.1421  0.1245  0.1344
N2      0.08837  0.1065 0.09407 0.09466
N3      0.05387 0.05967 0.05147 0.05186
REM      0.1224  0.1475    0.11  0.1142
W         0.145  0.2006 0.08167 0.08174

eeg_dwt_d2_energy
subject   SC4001  SC4002   SC4011   SC4012
stage                                     
N1       0.05083 0.05919   0.0433  0.04815
N2       0.02551 0.03734  0.03215  0.03227
N3      0.007323 0.01015 0.007005 0.007956
REM      0.04283 0.06356  0.02982  0.03058
W        0.03304 0.07527 0.008583  0.01008

emg_wl
subject    SC4001    SC4002    SC4011    SC4012
stage                                          
N1      7.824e-06 1.102e-05 7.327e-06 1.135e-05
N2      8.042e-06 8.701e-06 7.219e-06 1.082e-05
N3      7.389e-06 8.246e-06 6.821e-06 9.454e-06
REM     6.805e-06 8.418e-06 6.169e-06  1.09e-05
W       2.588e-06 7.253e-06 2.355e-06 3.481e-06


### EEG clipping investigation and EDF-limit validation — Lili, 2026-11-06

**Motivation.**

Earlier P5 quality-control experiments identified repeated EEG extrema, but the original heuristic detector did not establish whether these values corresponded to EDF acquisition limits. A more specific investigation was conducted to distinguish sustained boundary plateaus from ordinary repeated quantised samples.

**Dataset and methods.**

The analysis covered 68 development subjects, 133 PSG recordings and 360,621 labelled 30-second epochs. The final holdout was excluded.

For each EEG recording, the minimum and maximum amplitudes were determined. Consecutive exactly identical samples were grouped into plateaus. A stricter clipping candidate was defined as a plateau of at least 10 samples (100 ms at 100 Hz) whose amplitude equalled the recording minimum or maximum.

EDF physical and digital limits were independently extracted from the original recording headers and compared with the detected plateaus.

This stricter analysis is distinct from the earlier P5 heuristic using at least three repeated samples.

**Results.**

- 1,227 of 360,621 epochs were flagged (0.340%).
- All 1,227 flagged epochs contained a qualifying plateau at an EDF physical boundary.
- All 35,305 samples counted by the strict detector corresponded to EDF physical limits.
- 92 of 133 recordings reached their EEG physical minimum.
- 77 of 133 recordings reached their EEG physical maximum.
- 76 recordings reached both limits.
- None of the 40 recordings reaching neither limit contained a strict clipping flag.

The 1,227 flagged epochs were distributed across sleep stages as follows:

| Stage | Flagged epochs |
|---|---:|
| W | 1,195 |
| N1 | 10 |
| N2 | 9 |
| N3 | 5 |
| REM | 8 |
| **Total** | **1,227** |

**Clipping severity.**

Severity was defined using the percentage of samples belonging to qualifying boundary plateaus within each 30-second epoch.

| Severity | Clipped-sample percentage | Epochs |
|---|---|---:|
| None | 0% | 359,394 |
| Low | >0–1% | 961 |
| Moderate | >1–5% | 239 |
| High | >5–10% | 15 |
| Very high | >10% | 12 |

The severity categories are exploratory engineering thresholds, not clinically validated artifact categories.

**Interpretation and decision.**

The agreement with EDF physical limits strongly supports interpreting the detected plateaus as boundary saturation or clipping candidates. However, the detector does not establish the underlying hardware mechanism or capture every possible acquisition artifact.

The original signals, labels and epochs were preserved. No interpolation, reconstruction or automatic exclusion was introduced.

This analysis refines the earlier P5 investigation: the previous 2,882 flagged epochs and the present 1,227 strict flags use different detection criteria and must not be treated as interchangeable.

**Reproducibility.**

Scripts:
- `scripts/internal/quantify_eeg_clipping.py`
- `scripts/internal/check_edf_limits.py`
- `scripts/internal/build_eeg_quality_flags.py`
- `scripts/internal/inspect_suspicious_signals.py`

Outputs:
- `results/eeg_clipping_68/clipping_epochs.csv`
- `results/eeg_clipping_68/eeg_quality_flags.csv`
- `results/multichannel_audit_68/signal_inspection/`

Commit: pending.


### EOG and EMG quality assessment — Lili, 2026-11-06

**Motivation.**

After identifying EEG boundary plateaus, the investigation was extended to EOG and EMG to assess whether similar acquisition-limit anomalies were present in other channels.

**Methods.**

The original EOG and EMG channels were inspected independently of the mixed-channel loader to preserve their native sampling rates.

EDF physical limits were compared with observed sample extrema across all 133 development recordings. Epoch-wise standard deviations and representative extreme epochs were also examined.

**Sampling-rate findings.**

- EEG Fpz-Cz: 100 Hz.
- EOG horizontal: 100 Hz.
- EMG submental: 1 Hz in the inspected original EDF recordings.

The mixed-channel MNE loader provides EMG samples at 100 Hz through resampling. This does not restore high-frequency EMG information absent from the original 1 Hz channel.

**EDF-limit audit.**

| Channel | Recordings reaching an EDF physical limit | Samples at EDF physical limits |
|---|---:|---:|
| EOG | 1/133 | 1 |
| EMG | 0/133 | 0 |

The only EOG boundary sample was observed in recording SC4771G0 at its lower physical limit. No sustained EOG or EMG boundary plateau was identified.

**Visual variability analysis.**

Representative epochs with low and high standard deviation were inspected for three recordings: SC4201E0, SC4372F0 and SC4592G0.

Low-variability epochs were not necessarily flat or defective. High-variability EOG epochs displayed large slow oscillations, potentially compatible with physiological eye movements or other disturbances.

The original 1 Hz EMG samples were compared with the resampled 100 Hz curves. The large EMG variations observed in selected epochs were already present in the original samples, although the interpolated waveform between samples should not be interpreted as newly measured high-frequency activity.

**Decision.**

No additional EOG/EMG correction or automatic epoch exclusion was justified by these observations. Standard deviation alone was not adopted as an artifact detector.

**Reproducibility.**

Scripts:
- `scripts/internal/audit_eog_emg_limits.py`
- `scripts/internal/inspect_eog_emg_extremes.py`

Outputs:
- `results/eeg_clipping_68/eog_emg_recording_audit.csv`
- `results/multichannel_audit_68/eog_emg_inspection/`

Commit: pending.


### Final multichannel inspection and preprocessing decision, Lili, 2026-11-06

**Objective.**

To investigate whether large EOG and EMG variations coincided with changes in EEG, aligned 30-second epochs from recording SC4372F0 were inspected simultaneously.

**Results.**

| Epoch | Stage | EEG SD (µV) | EOG SD (µV) | EMG SD (µV) |
|---|---|---:|---:|---:|
| 35 | W | 42.587 | 268.638 | 2.374 |
| 2599 | W | 75.872 | 231.445 | 3.664 |

Epoch 35 showed large EOG fluctuations accompanied by EEG variations and a slower EMG change. Some disturbances occurred at similar times, but the observations did not establish a shared cause.

Epoch 2599 showed substantial variability across all three channels. The EEG also displayed flattened extrema visually compatible with clipping. Confirmation of EDF-boundary clipping requires the numerical detector rather than visual inspection alone.

The multichannel inspection did not establish whether the large-amplitude fluctuations were physiological, acquisition-related or a mixture of both.

**Final preprocessing decision.**

P1 (0.5–40 Hz, fourth-order, zero-phase Butterworth filtering applied epoch-wise) remains the preferred EEG preprocessing configuration for the current baseline pipeline.

P1d did not demonstrate a meaningful classification improvement. EEG clipping is documented using strict EDF-boundary quality flags. EOG and EMG remain unchanged, and no additional automatic artifact correction or epoch exclusion is introduced.

All conclusions are based on development recordings. The final holdout remains untouched.

**Reproducibility.**

Script:
- `scripts/internal/inspect_final_multichannel.py`

Outputs:
- `results/multichannel_audit_68/final_inspection/SC4372F0_epoch_35.png`
- `results/multichannel_audit_68/final_inspection/SC4372F0_epoch_2599.png`

Commit: pending.


### P1d, Continuous EEG filtering before epoch segmentation

**Hypothesis:** Applying the Butterworth band-pass filter to the continuous EEG signal before segmentation may reduce epoch-boundary artifacts and improve sleep-stage classification compared with epoch-wise filtering.

**Method:** Fourth-order Butterworth band-pass filter (0.5–40 Hz), applied using zero-phase `scipy.signal.filtfilt` to the continuous EEG recording before 30-second epoch extraction. EOG, EMG, labels, features, classifier, and subject-wise cross-validation protocol were unchanged.

**Dataset:** 68 development subjects, 133 PSG/Hypnogram pairs, 360,621 epochs. The final holdout was not used.

**Results:**
- Accuracy: 0.873
- Cohen's κ: 0.731
- Macro-F1: 0.655
- Balanced accuracy: 0.633
- Mean subject κ: 0.728 (SD 0.121; range 0.223–0.909)

**Comparison with P1:** Performance was nearly identical to epoch-wise filtering. No meaningful improvement was observed at the reported precision.

**Decision:** Retain P1 as the provisional reference preprocessing method. P1d is documented as a controlled comparison of filter placement, with no demonstrated classification benefit.

**Limitations:** No paired statistical comparison or direct quantification of boundary artifacts has yet been performed. The results do not establish that continuous filtering has no effect on the underlying EEG signal.


**Reproducibility.**

Runner: `scripts/internal/run_baseline_large.py`

Command:
```powershell
uv run --locked python -B scripts/internal/run_baseline_large.py --preprocess p1d --cache-dir "G:\My Drive\CM2013\data_cache\sleep_edf\physionet-sleep-data"
```

Saved results:
- `results/real__P1d_20261102T163844876492Z/`

Commit: pending.


### EEG Butterworth cutoff and filter-order sensitivity: P1b and P1c, Lili, 2026-11-02

**Motivation.**

Following the large-scale P0/P1/P2 comparison, P1 (0.5–40 Hz, fourth-order zero-phase Butterworth filtering) remained the preferred preprocessing configuration. Two controlled experiments investigated whether reducing the upper cutoff frequency or increasing the filter order could improve downstream sleep-stage classification.

**Experimental protocol.**

The experiments used the same 68 development subjects, 133 PSG/hypnogram recordings, 360,621 labelled 30-second epochs and five subject-wise GroupKFold splits as the previous large-scale evaluations. The final holdout subjects remained excluded.

Four configurations were compared:

- P0: no preprocessing.
- P1: EEG Butterworth band-pass, 0.5–40 Hz, order 4.
- P1b: EEG Butterworth band-pass, 0.5–35 Hz, order 4.
- P1c: EEG Butterworth band-pass, 0.5–35 Hz, order 5.

Filtering was zero-phase and applied independently to 30-second EEG epochs. EOG and EMG remained unchanged. All experiments used the same 11 baseline features, Welch spectral estimation, Random Forest classifier (200 trees, balanced class weights, seed 0), and subject-wise evaluation protocol.

P1 versus P1b isolates the effect of the upper cutoff frequency. P1b versus P1c isolates the effect of the filter order.

**Classification results.**

| Metric | P0 | P1 | P1b | P1c |
|---|---:|---:|---:|---:|
| Mean subject-wise Cohen's κ | 0.726 | 0.728 | 0.727 | 0.727 |
| SD of subject-wise κ | 0.118 | 0.120 | 0.121 | 0.121 |
| Pooled accuracy | 0.873 | 0.874 | 0.873 | 0.873 |
| Pooled Cohen's κ | 0.728 | 0.731 | 0.730 | 0.730 |
| Pooled macro-F1 | 0.651 | 0.655 | 0.654 | 0.654 |
| Pooled balanced accuracy | 0.628 | 0.634 | 0.633 | 0.633 |

All metrics are rounded to three decimal places.

**Sleep-stage recall.**

| Stage | P0 | P1 | P1b | P1c |
|---|---:|---:|---:|---:|
| Wake | 97.97% | 97.83% | 97.80% | 97.80% |
| N1 | 13.08% | 13.78% | 13.40% | 13.52% |
| N2 | 80.93% | 81.24% | 81.12% | 80.91% |
| N3 | 66.67% | 66.75% | 66.86% | 66.93% |
| REM | 55.35% | 57.25% | 57.24% | 57.26% |

**Interpretation.**

Reducing the upper cutoff frequency from 40 to 35 Hz did not improve the overall classification metrics. Increasing the Butterworth filter order from four to five also produced no measurable improvement in the rounded pooled metrics.

Small changes were observed in stage-specific recall, but these changes were mixed and did not establish a consistent advantage for either alternative.

The results do not demonstrate that the 35–40 Hz frequency range is physiologically irrelevant or that fourth- and fifth-order filters produce identical signals. They indicate only that the tested changes did not yield a meaningful classification improvement under the current feature representation and classifier.

N1 recall remained particularly low across all configurations. Subject-wise performance also showed substantial variability (SD approximately 0.12), much larger than the differences between the reported mean scores.

**Decision.**

Retain P1 (0.5–40 Hz, order 4) as the provisional preprocessing reference. Document P1b and P1c as controlled sensitivity experiments without demonstrated classification benefit.

**Limitations and next steps.**

- Reported metrics are rounded; exact differences require the saved `report.json` files.
- Paired subject-level differences and confidence intervals have not yet been calculated.
- The same development folds have been used for multiple preprocessing comparisons, creating potential model-selection bias.
- The conclusions apply to the current 11-feature Random Forest pipeline.
- Next evaluate P1d: continuous EEG filtering before 30-second segmentation, using P1 filter parameters to isolate epoch-boundary effects.
- Keep the final holdout untouched until pipeline selection is complete.

**Reproducibility.**

Runner: `scripts/internal/run_baseline_large.py`

- P0: `results/real__P0_20261029T140444314080Z/`
- P1: `results/real__P1_20261029T161038916244Z/`
- P1b: insert exact saved results directory.
- P1c: `results/real__P1c_20261102T124921338377Z/`

Commit: `bca3a38`.

### Combined P1 + P2 preprocessing: large-scale evaluation and paired subject analysis, Lili, 2026-11-01

**Motivation.**

The previous 68-subject experiments showed that P1 band-pass filtering marginally outperformed the unprocessed baseline, whereas P2 db4 wavelet denoising reduced classification performance. A combined P1 + P2 configuration was evaluated to investigate whether applying band-pass filtering before wavelet denoising could improve downstream sleep-stage classification.

**Experimental protocol.**

The experiment used 68 development subjects, 133 PSG/hypnogram recordings and 360,621 labelled 30-second epochs. The final holdout subjects were excluded.

The combined preprocessing applied EEG 0.5–40 Hz zero-phase Butterworth band-pass filtering followed by db4 wavelet denoising with the existing P2 settings. EOG and EMG remained unchanged.

All configurations used the same 11 baseline features, Welch spectral estimation, Random Forest classifier (200 trees, balanced class weights, seed 0), and five-fold subject-wise GroupKFold evaluation.

**Classification results.**

| Metric | P1 | P2 db4 | P1 + P2 db4 |
|---|---:|---:|---:|
| Mean subject-wise Cohen's κ | 0.728 | 0.687 | 0.696 |
| SD of subject-wise κ | 0.120 | 0.129 | 0.137 |
| Pooled accuracy | 0.874 | 0.856 | 0.860 |
| Pooled Cohen's κ | 0.731 | 0.692 | 0.702 |
| Pooled macro-F1 | 0.655 | 0.624 | 0.635 |
| Pooled balanced accuracy | 0.634 | 0.605 | 0.614 |

**Stage-wise recall.**

| Stage | P1 | P2 db4 | P1 + P2 db4 |
|---|---:|---:|---:|
| W | 97.83% | 97.00% | 97.10% |
| N1 | 13.78% | 11.02% | 12.20% |
| N2 | 81.24% | 76.60% | 77.80% |
| N3 | 66.75% | 65.75% | 66.17% |
| REM | 57.25% | 52.33% | 53.94% |

P1 achieved the highest recall for all five sleep stages. Compared with P1, the combined preprocessing reduced N2 recall by approximately 3.44 percentage points and REM recall by 3.31 percentage points.

**Paired subject-level analysis.**

The saved out-of-fold predictions from P1 and P1 + P2 were aligned using original test-epoch indices. Exact equality of epoch indices, ground-truth labels and subject assignments was verified across all five folds.

The comparison included 360,621 epochs and 68 subjects.

- Improved subjects: 15/68.
- Degraded subjects: 53/68.
- Unchanged subjects: 0.
- Mean paired difference in subject-wise κ (P1+P2 minus P1): −0.0321.
- Median paired difference: −0.0193.
- SD of paired differences: 0.0553.

The largest decreases were observed for SC419 (−0.250), SC436 (−0.220) and SC434 (−0.177). The largest improvement was observed for SC477 (+0.069).

The degradation affected 53 of 68 subjects, indicating that the lower pooled performance was not caused solely by a few unusually difficult recordings. No formal confidence interval or hypothesis test was calculated for the paired differences.

**Interpretation and revision.**

The combined P1 + P2 configuration performed better than P2 alone but worse than P1 alone on all reported pooled classification metrics and all five stage-specific recall values.

The earlier spindle-candidate preservation analysis found substantial sigma-power attenuation under the current db4 denoising settings. This provides a plausible physiological explanation for some classification losses, particularly for N2, but the present experiment does not establish causality.

These findings revise the earlier interpretation of wavelet denoising as a potentially beneficial preprocessing step based on three-subject experiments.

**Decision.**

Retain P1 as the provisional signal-processing configuration for the current 11-feature Random Forest pipeline. Do not include the tested P1 + P2 db4 combination in the selected pipeline.

Retain P3/P5 as flag-only quality-control indicators. Their integration does not constitute a classification improvement because the flags are not used as model inputs.

**Limitations and future work.**

- The conclusions apply to the current feature representation, classifier and wavelet settings.
- Alternative wavelet thresholds or feature representations could produce different results and would require new controlled experiments.
- The development folds have been used for multiple model comparisons; the final holdout must remain untouched until the pipeline is frozen.
- The paired subject-level analysis is descriptive; uncertainty estimates have not yet been calculated.

**Reproducibility.**

Runner: `scripts/internal/run_baseline_large.py`

Saved results:
- P1: `results/real__P1_20261029T161038916244Z/`
- P2 db4: `results/real__P2_20261030T112346818136Z/`
- P1 + P2 db4: `results/real__P1_P2_db4_20261101T171446625914Z/`
- Paired comparison: `results/P1_vs_P1_P2_subject_comparison.csv`

Commit: `66aa8ae`

### Integrated preprocessing and full-cohort quality-control analysis, Lili, 2026-10-31 / 2026-11-01

**Motivation.**

Following the large-scale preprocessing comparison, P1 was retained as the provisional signal-processing configuration. P3 and P5 were then integrated as quality-control (QC) indicators to identify potentially problematic EEG/EOG epochs without automatically removing data or modifying the extracted features.

The objective was to verify technical compatibility, quantify QC flags across the full development cohort, and investigate whether flagged epochs were associated with increased classification errors.

**Pipeline integration.**

The integrated configuration applies:

1. P3: detection of near-flat EEG/EOG epochs using fixed standard-deviation thresholds, with `action="flag"`.
2. P5: detection of suspected EEG clipping using recording-specific extrema and plateaus of at least three consecutive samples, with `action="flag"`.
3. P1: EEG 0.5–40 Hz zero-phase Butterworth band-pass filtering.
4. Baseline extraction of 11 features, followed by the existing Random Forest classifier.

P3 and P5 store detection masks and summaries in recording metadata. They do not modify the signal, exclude epochs, or provide additional features to the classifier.

**Technical integration validation.**

The integrated configuration was tested on recording `SC4001E0`, containing 2,650 epochs.

- EEG after P1 was identical with and without QC enabled.
- All 2,650 epochs were preserved.
- Labels and subject assignments remained identical.
- Feature matrices had shape `(2650, 11)` and were identical between P1-only and P1+QC configurations.
- All extracted features were finite.
- P3 and P5 detection metadata were present.
- P5 flagged two epochs in this recording.

This confirms that QC integration does not alter the baseline feature representation in the tested recording. It does not constitute a new full-cohort classifier evaluation.

**Full-cohort quality-control results.**

QC detection was performed on raw signals from 68 development subjects, corresponding to 133 recordings and 360,621 labelled 30-second epochs.

| QC indicator | Flagged epochs | Percentage |
|---|---:|---:|
| P3 — near-flat EEG/EOG | 748 | 0.207% |
| P5 — suspected clipping | 2,882 | 0.799% |
| Both P3 and P5 | 0 | 0.000% |
| Either P3 or P5 | 3,630 | 1.007% |

No epochs were excluded, and no signal reconstruction was performed. The flags represent heuristic indicators, not confirmed acquisition artifacts.

**Association with classification errors.**

The QC masks were aligned with the existing P1 out-of-fold predictions from five subject-wise GroupKFold checkpoints. Alignment checks covered all 360,621 epochs and 133 recordings.

| Category | Epochs | Errors | Error rate |
|---|---:|---:|---:|
| All epochs | 360,621 | 45,538 | 12.628% |
| P3 flagged | 748 | 64 | 8.556% |
| P5 flagged | 2,882 | 67 | 2.325% |
| Either flagged | 3,630 | 131 | 3.609% |
| Unflagged | 356,991 | 45,407 | 12.719% |

Flagged epochs had a lower aggregate error rate than unflagged epochs. However, 3,415 of the 3,630 flagged epochs (94.1%) were Wake, a stage with particularly low classification error in this evaluation.

**Stage-specific error analysis.**

| Stage | Flagged epochs | Flagged error rate | Unflagged error rate |
|---|---:|---:|---:|
| W | 3,415 | 0.56% | 2.19% |
| N1 | 48 | 75.00% | 86.25% |
| N2 | 123 | 37.40% | 18.72% |
| N3 | 7 | 57.14% | 33.23% |
| REM | 37 | 70.27% | 42.71% |

Flagged N2 and REM epochs showed higher error rates than their unflagged counterparts, whereas the aggregate flagged error rate was dominated by Wake epochs. The small numbers of flagged non-Wake epochs limit the strength of these comparisons.

These results establish an association, not a causal effect of signal anomalies on classification errors.

**Decision.**

Retain P1 as the provisional signal-processing configuration and integrate P3/P5 as non-destructive QC indicators.

The earlier P3 exclusion strategy is not used in the current integrated pipeline. Automatic exclusion is not justified by the present full-cohort QC and classification-error analysis.

**Limitations and next steps.**

- QC detection rules have not been validated against expert-annotated artifacts.
- The stage-specific comparison is descriptive and does not adjust for recording-level or subject-level clustering.
- P5 uses full-recording extrema and is therefore a retrospective QC method rather than an online detector.
- QC flags are not used as classifier features.
- Evaluate a combined P1 + P2 signal-processing configuration on the development cohort.
- Preserve the final holdout for evaluation of the selected pipeline.

**Reproducibility.**

Scripts:

- `src/sleepedf/track.py`
- `src/sleepedf/preprocessing/experiments.py`
- `scripts/internal/run_quality_control.py`
- `scripts/internal/analyze_qc_vs_errors.py`

Results:

- `results/qc_68_subjects/summary.json`
- `results/qc_68_subjects/recordings.csv`
- `results/qc_68_subjects/flagged_epochs.json`
- `results/qc_vs_errors_P1/summary.json`
- `results/qc_vs_errors_P1/overall.csv`
- `results/qc_vs_errors_P1/by_stage.csv`
- `results/qc_vs_errors_P1/by_recording.csv`
- P1 reference: `results/real__P1_20261029T161038916244Z/`

Commit: `66aa8ae`


### Large-scale preprocessing comparison (P0, P1, P2), Lili, 2026-10-29/30

**Motivation.**

Earlier preprocessing comparisons were conducted on three development subjects (SC400, SC401 and SC402). The limited cohort size made it difficult to assess whether the observed advantages of band-pass filtering and wavelet denoising generalised to a broader set of subjects.

The objective of this experiment was to reassess P0, P1 and P2 on 68 development subjects while keeping the dataset, feature extraction, classifier and evaluation partitions fixed.

**Dataset and experimental protocol.**

- Dataset: Sleep-EDF, 68 development subjects, 133 PSG/hypnogram pairs.
- Evaluated epochs: 360,621 labelled 30-second epochs.
- Preprocessing:
  - P0: no preprocessing.
  - P1: EEG 0.5–40 Hz zero-phase Butterworth band-pass filtering.
  - P2: EEG wavelet denoising using the current P2 configuration (db4 expected; configuration to be verified).
- Features: 11 supplied features, unchanged across experiments.
- Spectral estimation: Welch.
- Classifier: Random Forest, 200 trees, balanced class weights, seed 0.
- Feature selection: none.
- Cropping: none.
- Evaluation: five-fold subject-wise GroupKFold, with deterministic subject partitions shared across experiments.
- Final holdout subjects: excluded from development experiments.

Each subject's recordings were assigned to the same evaluation fold. The training and test epoch counts were identical across P0, P1 and P2.

| Fold | Test subjects | Training epochs | Test epochs |
|---|---:|---:|---:|
| 1 | 14 | 290,405 | 70,216 |
| 2 | 14 | 285,309 | 75,312 |
| 3 | 14 | 286,790 | 73,831 |
| 4 | 13 | 289,643 | 70,978 |
| 5 | 13 | 290,337 | 70,284 |

The saved checkpoint manifests were compared directly. All five subject-wise fold assignments were identical across P0, P1 and P2. This ensures that the preprocessing configurations were evaluated on the same held-out subjects, with identical training and test partitions.

**Classification results.**

| Metric | P0 — None | P1 — Band-pass | P2 — Wavelet |
|---|---:|---:|---:|
| Mean subject-wise Cohen's kappa | 0.726 | **0.728** | 0.687 |
| SD of subject-wise kappa | 0.118 | 0.120 | 0.129 |
| Subject-wise kappa range | 0.231–0.895 | 0.217–0.906 | 0.216–0.886 |
| Pooled accuracy | 0.873 | **0.874** | 0.856 |
| Pooled Cohen's kappa | 0.728 | **0.731** | 0.692 |
| Pooled macro-F1 | 0.651 | **0.655** | 0.624 |
| Pooled balanced accuracy | 0.628 | **0.634** | 0.605 |

**Stage-wise recall.**

Recall was calculated from the pooled confusion matrices, with true stages in rows and predicted stages in columns.

| Stage | P0 | P1 | P2 |
|---|---:|---:|---:|
| W | 97.97% | 97.83% | 97.00% |
| N1 | 13.08% | 13.78% | 11.02% |
| N2 | 80.93% | 81.24% | 76.60% |
| N3 | 66.67% | 66.75% | 65.75% |
| REM | 55.35% | 57.25% | 52.33% |

**Interpretation.**

P1 achieved the highest pooled Cohen's kappa, macro-F1 and balanced accuracy. However, the improvement relative to P0 was small: +0.003 pooled kappa, +0.004 macro-F1 and +0.006 balanced accuracy.

P2 performed worse than both P0 and P1 on all four pooled metrics. Relative to P0, pooled kappa decreased by 0.036 and macro-F1 decreased by 0.027. The most pronounced recall reductions occurred for N2 and REM.

N1 remained difficult for all three configurations, with recall below 14%. The strong class imbalance, particularly the dominance of Wake epochs, makes accuracy alone an insufficient performance measure.

The results do not establish that band-pass filtering is statistically superior to no preprocessing. Paired subject-level comparisons and uncertainty estimates are still needed.

**Revisiting the earlier preprocessing decision.**

The initial three-subject experiments suggested that wavelet denoising could improve classification relative to P0. This result did not generalise to the 68-subject development cohort under the current P2 settings.

The earlier physiological analysis also found substantial attenuation of selected spindle-like EEG oscillations under db4 wavelet denoising.

Taken together, these findings support retaining P1 as the provisional preprocessing choice while revisiting P2. The earlier mother-wavelet comparison identified coif3 as a possible alternative, but its small advantage over db4 on three subjects requires larger-cohort evaluation.

**Limitations.**

- The development cohort is not the final untouched holdout.
- The experiments share the same development subjects and should not be treated as independent test results.
- The P0/P1 difference is small relative to between-subject variability.
- The effect of wavelet family and thresholding has not yet been isolated on the 68-subject cohort.
- The conclusions apply to the current 11-feature Random Forest pipeline and may change with a different feature representation or classifier.

**Reproducibility.**

Runner:

`scripts/internal/run_baseline_large.py`

Command template:

```powershell
uv run --locked python -B scripts/internal/run_baseline_large.py --cache-dir "G:\My Drive\CM2013\data_cache\sleep_edf\physionet-sleep-data" --n-subjects 68 --preprocess <none|bandpass|wavelet>
```

Saved results:

- P0: `results/real__P0_20261029T140444314080Z/`
- P1: `results/real__P1_20261029T161038916244Z/`
- P2: `results/real__P2_20261030T112346818136Z/`

Each run includes saved evaluation results, provenance information, checkpoint manifests and fold prediction files.

**Decision.**

Retain P1 as the current preferred preprocessing configuration, with the qualification that its improvement over P0 is marginal. Do not select the current P2 configuration on classification performance alone. Re-evaluate coif3 and consider alternative denoising thresholds before making a final preprocessing recommendation.

Commit: `4ccdbbc`.


### P6 - Clock-based cropping and subject-wise evaluation - Lili - 2026-10-21

**Motivation.**

Exploratory analysis of the six Sleep-EDF recordings revealed a substantial class imbalance, with Wake accounting for 11,340 of 16,688 epochs (67.95%). P6 investigated whether restricting the training data to a fixed nighttime interval could reduce Wake dominance and improve sleep-stage classification.

**Method and experimental design.**

P6 applied the same 0.5–40 Hz EEG band-pass filtering as P1. Epoch timestamps were reconstructed from the PSG EDF measurement date and the annotation-derived epoch onsets. A fixed 20:30–11:00 window was used to select training epochs independently of their sleep-stage labels.

The experiment included SC400, SC401 and SC402, with two recordings per subject. The classification pipeline retained the same 11 features, Welch spectral estimation, 200-tree Random Forest, balanced class weights and seed 0.

Evaluation used three leave-one-subject-out (LOSO) folds. In each fold, P6 trained exclusively on nighttime epochs from the two training subjects, while predictions were generated for **all epochs of the held-out subject**. P1 used all training epochs. This ensured identical test sets for the two configurations.

**Cropping results.**

| Recording | Original epochs | Nighttime epochs | Outside window |
|---|---:|---:|---:|
| SC4001E0 | 2,650 | 1,740 | 910 |
| SC4002E0 | 2,829 | 1,739 | 1,090 |
| SC4011E0 | 2,802 | 1,740 | 1,062 |
| SC4012E0 | 2,848 | 1,740 | 1,108 |
| SC4021E0 | 2,804 | 1,740 | 1,064 |
| SC4022E0 | 2,755 | 1,739 | 1,016 |
| **Total** | **16,688** | **10,438** | **6,250** |

The clock window retained 62.55% of the original epochs. All 6,250 outside-window epochs were labelled Wake in this development cohort. This was established through post-hoc label analysis; labels were not used to determine the cropping mask.

**Full-night LOSO classification results.**

| Metric | P1 | P6 |
|---|---:|---:|
| Pooled accuracy | 0.8799 | 0.8731 |
| Pooled Cohen's kappa | 0.7516 | 0.7421 |
| Pooled macro-F1 | 0.6539 | 0.6520 |
| Pooled balanced accuracy | 0.6185 | 0.6251 |
| Mean subject-wise kappa | 0.743 | 0.735 |
| SD of subject-wise kappa | 0.114 | 0.102 |

P6 slightly improved balanced accuracy (+0.0066), but reduced pooled Cohen's kappa (−0.0095), accuracy (−0.0068) and macro-F1 (−0.0019). The differences were small relative to the observed subject-to-subject variability.

**Subject-wise Cohen's kappa.**

| Held-out subject | P1 | P6 |
|---|---:|---:|
| SC400 | 0.6152 | 0.6195 |
| SC401 | 0.8347 | 0.8156 |
| SC402 | 0.7798 | 0.7685 |

P6 slightly improved performance on SC400 but decreased performance on SC401 and SC402. The improvement on the most difficult subject did not translate into an overall improvement.

**Nighttime versus outside-window analysis.**

The held-out predictions were divided into nighttime and outside-window subsets to investigate where P6 affected classification performance.

| Nighttime metric (10,438 epochs) | P1 | P6 |
|---|---:|---:|
| Accuracy | 0.8160 | 0.8111 |
| Cohen's kappa | 0.7130 | 0.7080 |
| Macro-F1 | 0.6509 | 0.6526 |
| Balanced accuracy | 0.6154 | 0.6210 |

P6 slightly improved nighttime macro-F1 and balanced accuracy, but decreased accuracy and Cohen's kappa.

Outside the selected window, all 6,250 ground-truth epochs were Wake. P1 correctly classified 6,167 epochs (98.67%), compared with 6,104 (97.66%) for P6. Consequently, P6 made 63 additional Wake classification errors outside the nighttime window.

These results indicate that excluding daytime Wake epochs from training may reduce the model's ability to recognise Wake during those periods.

**Validation and leakage considerations.**

The timestamp alignment was validated on all six recordings. Epoch counts, label ordering and signal dimensions were preserved. P6 produced the same filtered EEG, EOG and EMG signals as P1 before training-epoch selection.

The cropping decision used EDF clock metadata and fixed time boundaries rather than sleep-stage annotations. Training and testing were separated by subject, and all held-out epochs remained in the evaluation. Both nights of each subject belonged to the same fold.

The 20:30–11:00 interval is a fixed clock window, not an individually verified lights-off interval. Its suitability may differ across recordings or datasets.

**Decision and limitations.**

P6 did not demonstrate a convincing overall improvement over P1. P1 is therefore retained as the preferred preprocessing and training configuration.

P6 is retained as a reproducible experimental alternative because it directly addresses training-set class imbalance and provides evidence about the trade-off between reducing Wake dominance and maintaining Wake recognition.

The evaluation involved only three development subjects. The window was investigated on these subjects and has not been independently validated on unseen recordings. The final holdout should remain untouched during method development.

**Future work — Random Wake Undersampling.**

A possible follow-up would be to retain all available sleep-stage epochs while randomly undersampling Wake epochs within each training fold. Unlike a fixed clock window, this could reduce Wake dominance without preferentially removing Wake from particular times of day.

However, random undersampling would need to be applied exclusively to the training folds, with the held-out subjects kept intact. The sampling ratio would need to be selected using development data, and variability across random seeds should be evaluated. This experiment has not been performed.

**Reproducibility.**

Scripts:

- `scripts/run_clock_cropping.py`
- `scripts/analyze_clock_cropping.py`
- `scripts/test_epoch_timestamps.py`
- `src/sleepedf/preprocessing/epoch_timestamps.py`
- `src/sleepedf/preprocessing/experiments.py`

Results:

- `results/clock_cropping/`

Commit: `f8bbda7`.

### Mother wavelet comparison and subject-level diagnostics - Lili - 2026-10-19

**Motivation.**

The previous spindle-preservation analysis indicated that the original P2 configuration (`db4`) substantially attenuated selected sigma-band oscillations. Four mother wavelets (`db4`, `sym4`, `coif1`, and `coif3`) were therefore investigated to determine whether changing the wavelet could improve physiological signal preservation and downstream sleep-stage classification.

**Methods and implementation validation.**

The classification experiment used three subjects (SC400, SC401 and SC402), two nights per subject, and 16,688 labelled 30-second epochs. Each wavelet was evaluated using the same 11 features, Welch spectral estimation, Random Forest classifier (seed 0), and three subject-wise LOSO folds.

A dedicated comparison track explicitly selected the mother wavelet because the original preprocessing dispatch did not propagate this parameter from the configuration.

Validation confirmed that:

- All four feature matrices had shape `(16688, 11)`.
- Labels and subject assignments remained identical across configurations.
- All extracted feature values were finite.
- The custom `db4` feature matrix exactly reproduced the original P2 feature matrix.
- The alternative wavelets produced different feature values, confirming that the intended preprocessing parameter was actually changed.

**Classification results.**

| Wavelet | Pooled accuracy | Pooled Cohen's kappa | Pooled macro-F1 | Pooled balanced accuracy |
|---|---:|---:|---:|---:|
| db4 | 0.877 | 0.743 | **0.648** | **0.613** |
| sym4 | 0.874 | 0.737 | 0.636 | 0.603 |
| coif1 | 0.872 | 0.734 | 0.635 | 0.604 |
| coif3 | **0.878** | **0.745** | 0.647 | **0.613** |

The results show no substantial improvement from replacing `db4`. Although `coif3` achieved the highest pooled Cohen's kappa, its advantage over `db4` was only 0.002, while its macro-F1 was marginally lower.

The earlier signal-preservation experiment found higher sigma-power retention with `coif1` than with `db4` (40.74% versus 27.63%). However, `coif1` did not improve downstream classification. This illustrates that preserving more sigma-band energy in a small set of spindle candidates does not necessarily improve the classification metrics.

**Subject-wise Cohen's kappa (primary metric).**

| Mother wavelet | Mean kappa | SD | Range |
|---|---:|---:|---|
| db4 | 0.736 | 0.102 | 0.620–0.811 |
| sym4 | 0.730 | 0.104 | 0.611–0.806 |
| coif1 | 0.727 | 0.090 | 0.625–0.798 |
| coif3 | 0.738 | 0.103 | 0.621–0.813 |

The highest mean subject-wise Cohen's kappa was obtained with coif3 (0.738), compared with 0.736 for db4. This difference (+0.002) was negligible relative to the between-subject variability (SD approximately 0.10). Therefore, the present three-subject development experiment does not provide sufficient evidence to replace db4 with coif3.

**Sleep-stage recall analysis.**

| Stage | db4 | sym4 | coif1 | coif3 |
|---|---:|---:|---:|---:|
| W | 97.2% | 97.1% | 97.0% | 97.2% |
| N1 | 20.6% | 20.0% | 18.8% | 20.3% |
| N2 | 89.8% | 89.8% | 88.9% | 90.1% |
| N3 | 35.6% | 31.9% | 33.0% | 34.3% |
| REM | 63.2% | 62.7% | 64.2% | 64.6% |

All four configurations recognized W and N2 considerably better than N1 and N3. Changing the mother wavelet did not resolve the poor minority-stage recall.

![Wavelet confusion matrices](results/wavelet_comparison/loso/wavelet_confusion_matrices.png)

**Subject-level diagnostic analysis.**

The `db4` LOSO confusion matrices revealed substantial inter-subject variability.

| Held-out subject | Cohen's kappa | Macro-F1 | Balanced accuracy |
|---|---:|---:|---:|
| SC400 | 0.620 | 0.492 | 0.496 |
| SC401 | 0.811 | 0.714 | 0.706 |
| SC402 | 0.777 | 0.703 | 0.677 |

SC400 was particularly challenging: its N1, N3 and REM recalls were 0.9%, 17.0% and 41.2%, respectively. SC401 and SC402 achieved substantially better results for several stages.

![db4 confusion matrices by subject](results/wavelet_comparison/loso/db4_confusions_by_subject.png)

**Ground-truth sleep-stage distribution.**

| Subject | W | N1 | N2 | N3 | REM |
|---|---:|---:|---:|---:|---:|
| SC400 | 70.9% | 2.1% | 11.4% | 9.4% | 6.2% |
| SC401 | 65.1% | 3.6% | 21.6% | 3.6% | 6.1% |
| SC402 | 68.0% | 5.0% | 17.0% | 3.8% | 6.2% |

Wakefulness accounted for approximately 68% of the pooled epochs. N1 represented only 3.6%, indicating strong class imbalance.

However, stage frequency alone does not explain all subject-level differences. SC400 had the highest proportion of N3 epochs but the lowest N3 recall. Additional investigations are required before attributing these errors to a particular cause.

![True sleep-stage distribution by subject](results/wavelet_comparison/loso/stage_distribution_by_subject.png)

**Decision and limitations.**

The tested mother wavelets produced similar overall classification performance. `db4` is retained as the reference P2 configuration, while `coif3` is identified as a candidate for re-evaluation with more development subjects.

This does not reverse the earlier preference for P1 band-pass filtering, which remains supported by the prior classification and spindle-preservation analyses.

The experiment used only three subjects and four wavelet configurations. Differences of a few thousandths in pooled metrics should not be interpreted as evidence of superiority. Repeated comparisons on the same development subjects can also introduce model-selection bias.

**Next steps.**

1. Verify how wake epochs are selected and whether wake cropping is applied in the current pipeline.
2. Investigate class imbalance and subject-specific classification errors.
3. Reassess `coif3` on a larger development cohort.
4. Preserve the final holdout for independent evaluation of the selected pipeline.

**Reproducibility.**

Scripts:

- `scripts/compare_wavelets.py`
- `scripts/compare_wavelets_loso.py`
- `scripts/plot_wavelet_confusions.py`
- `scripts/plot_db4_confusions_by_subject.py`
- `scripts/analyze_stage_distribution.py`

Results:

- `results/wavelet_comparison/loso/wavelet_loso_summary.csv`
- `results/wavelet_comparison/loso/stage_distribution_by_subject.csv`
- `results/wavelet_comparison/loso/` — diagnostic figures


### Physiological preservation of sleep spindles - Lili - 2026-10-16

**Motivation.**

Previous classification experiments showed that both P1 (0.5–40 Hz zero-phase EEG band-pass filtering) and P2 (db4 wavelet denoising with soft thresholding) improved sleep-stage classification relative to P0. However, similar classification scores do not guarantee equivalent preservation of physiologically relevant EEG events.

Sleep spindles are oscillatory events in the sigma frequency range, particularly relevant to stage N2. The objective was to determine whether P1 and P2 preserve the amplitude, spectral content and temporal detectability of spindle-like events observed in the original EEG.

**Dataset and experimental scope.**

The analysis was performed on recording SC400, using two 30-second N2 epochs (indices 1025 and 1637).

Eight spindle candidates were automatically detected in the unprocessed EEG:
- Epoch 1025: six candidates.
- Epoch 1637: two candidates.

These events were detected algorithmically and were not independently confirmed by expert annotations. They must therefore be described as spindle candidates rather than validated physiological spindles.

This was a targeted signal-preservation experiment, not a new sleep-stage classification evaluation.

**Methods.**

Three EEG signals were compared:
- Raw: unprocessed EEG.
- P1: 0.5–40 Hz zero-phase Butterworth band-pass filtering.
- P2: db4 wavelet denoising with automatic decomposition level (maximum 5), soft thresholding and an automatically estimated per-epoch VisuShrink threshold.

The evaluation included:

1. Sigma-band (11–16 Hz) power retention relative to Raw.
2. Hilbert-envelope amplitude retention relative to Raw.
3. Changes in sigma spectral specificity.
4. Independent spindle-candidate detection on Raw, P1 and P2.
5. One-to-one temporal matching using intersection-over-union (IoU).
6. Sensitivity analysis across IoU thresholds from 0.10 to 0.70.
7. Inspection of candidate timing near 30-second epoch boundaries.

**Signal-preservation results.**

| Metric | P1 | P2 |
|---|---|---|
| Sigma-band power retention | Approximately 100% | 27.63% (SD 17.98 percentage points) |
| Hilbert-envelope amplitude retention | Approximately 100% | 43.48% (SD 17.79 percentage points) |
| Mean sigma-power change relative to Raw | Approximately 0 dB | -6.45 dB (SD 3.00 dB) |
| Mean change in sigma spectral specificity | Approximately unchanged | -33.89% (SD 34.02 percentage points) |

P1 preserved the selected sigma-band oscillations with minimal measurable attenuation.

P2 substantially reduced both sigma-band power and oscillation-envelope amplitude. The effect varied between candidates, indicating that the denoising transformation did not preserve all detected events equally.

The reported SD values describe variability across the eight selected candidates, not variability across independent subjects.

**Independent spindle re-detection.**

Spindle detection was performed independently on each processed signal. Events were matched one-to-one against Raw candidates using temporal IoU ≥ 0.30.

| Metric | Raw | P1 | P2 |
|---|---:|---:|---:|
| Detected candidates | 8 | 8 | 9 |
| Matched Raw candidates | 8 | 8 | 5 |
| Raw candidates without a match | — | 0 | 3 |
| Unmatched processed candidates | — | 0 | 4 |
| Raw-candidate matching rate | — | 100% | 62.5% |

P1 reproduced all eight Raw candidates under the selected matching criterion.

P2 matched five of eight Raw candidates. It also produced four unmatched detections, indicating changes in candidate timing and/or detection behavior after preprocessing.

Unmatched processed detections should not automatically be classified as false positives because the Raw detector is not an expert-annotated reference.

**Sensitivity to the temporal matching threshold.**

| Minimum IoU | P1 matching rate | P2 matching rate |
|---|---:|---:|
| 0.10 | 100% | 62.5% |
| 0.20 | 100% | 62.5% |
| 0.30 | 100% | 62.5% |
| 0.40 | 100% | 50.0% |
| 0.50 | 100% | 37.5% |
| 0.60 | 100% | 25.0% |
| 0.70 | 100% | 12.5% |

P1 maintained complete matching throughout the tested IoU range.

P2 matching decreased as stricter temporal overlap was required, indicating reduced stability of event boundaries relative to the original signal.

**Epoch-boundary checks.**

All detected candidate intervals had valid durations and remained within the 30-second epoch boundaries.

Some candidates occurred close to the beginning or end of an epoch, including an event ending at 29.95 seconds. These events require additional investigation because filtering and Hilbert-envelope estimation on isolated epochs may introduce boundary effects.

The present analysis does not establish that the observed differences are caused by boundary artifacts.

**Interpretation and decision.**

The analysis provides additional physiological evidence in favor of P1.

Although P2 achieved competitive classification performance in previous development experiments, its current configuration substantially attenuated selected spindle-like oscillations and reduced their temporal re-detectability.

P1 is therefore retained as the preferred preprocessing candidate for subsequent development.

P2 is not considered physiologically equivalent to P1 under the tested settings. Its denoising thresholds should be reconsidered before further use if spindle preservation is an objective.

This is a provisional decision. The analysis involved only eight automatically detected candidates from two epochs in one recording, without expert spindle annotations or independent subject-level validation.

**Limitations and next steps.**

- Extend the analysis to more N2 epochs, recordings and subjects.
- Investigate events using continuous filtering or neighboring-epoch context.
- Evaluate alternative P2 thresholding strategies.
- Assess noise reduction as well as physiological signal preservation.
- Re-evaluate downstream classification performance with subject-wise splits after any preprocessing change.
- Keep the final holdout cohort untouched during method development.

**Reproducibility.**

Commit: `217763e`

Scripts:
- `scripts/visualize_preprocessing.py`
- `scripts/detect_spindle_candidates.py`
- `scripts/evaluate_spindle_preservation.py`
- `scripts/evaluate_spindle_redetection.py`
- `scripts/evaluate_spindle_matching_sensitivity.py`
- `scripts/check_spindle_epoch_boundaries.py`

Results:
- `results/preprocessing_visualization/`
- `results/spindle_candidates/`
- `results/spindle_evaluation/`
- `results/spindle_redetection/`

Quantitative outputs:
- `results/spindle_candidates/spindle_candidates.csv`
- `results/spindle_evaluation/preservation_metrics.csv`
- `results/spindle_evaluation/preservation_summary.csv`
- `results/spindle_redetection/redetection_events.csv`
- `results/spindle_redetection/redetection_summary.csv`
- `results/spindle_redetection/sensitivity/iou_sensitivity.csv`
- `results/spindle_redetection/sensitivity/matched_boundary_shifts.csv`

(new entry inserted to the top)
### Feature check - Lucas - 2026-10-15

## Check 1: Feature Names & Ordering

**Number of features:** 11

| Column | Feature Name |
|---:|---|
| 0 | `eeg_delta` |
| 1 | `eeg_theta` |
| 2 | `eeg_alpha` |
| 3 | `eeg_sigma` |
| 4 | `eeg_beta` |
| 5 | `eeg_hjorth_activity` |
| 6 | `eeg_hjorth_mobility` |
| 7 | `eeg_hjorth_complexity` |
| 8 | `eeg_spec_entropy` |
| 9 | `eog_movement` |
| 10 | `emg_rms` |

## Check 2: Row Alignment

| Dataset | Shape |
|---|---|
| Features (`X`) | (`8256, 11`) |
| Labels (`y`) | (`8256,`) |
| Subject Groups (`groups`) | (`8256,`) |

### Subject-Level Alignment

| Subject | Recording ID | Number of Labels | Number of Feature Rows | Status |
|---|---|---:|---:|---|
| SC400 | `SC4001E0` | 2,650 | 2,650 |  Matched |
| SC401 | `SC4011E0` | 2,802 | 2,802 |  Matched |
| SC402 | `SC4021E0` | 2,804 | 2,804 |  Matched |
| **Total** | — | **8,256** | **8,256** | **Matched** |

## Check 3: Data Integrity (NaNs / Infs)

| Validation | Result |
|---|---|
| Contains NaNs |  No |
| Contains Infs |  No |
| All values finite |  Yes |

### Feature Summary Statistics

| Feature | Mean | Std | Min | Median (50%) | Max |
|---|---:|---:|---:|---:|---:|
| `eeg_delta` | 3.541499e-10 | 3.062089e-10 | 8.961040e-12 | 2.732166e-10 | 2.488320e-09 |
| `eeg_theta` | 2.511438e-11 | 1.955244e-11 | 1.229510e-12 | 2.019621e-11 | 1.803406e-10 |
| `eeg_alpha` | 3.831991e-12 | 2.561465e-12 | 3.812442e-13 | 3.283522e-12 | 2.103810e-11 |
| `eeg_sigma` | 3.219647e-12 | 2.437007e-12 | 3.164061e-13 | 2.459242e-12 | 2.221975e-11 |
| `eeg_beta` | 4.662853e-12 | 5.336720e-12 | 2.245446e-13 | 2.277434e-12 | 4.619777e-11 |
| `eeg_hjorth_activity` | 5.668723e-10 | 4.697087e-10 | 1.955764e-11 | 4.379438e-10 | 3.841122e-09 |
| `eeg_hjorth_mobility` | 2.829099e-01 | 1.131066e-01 | 8.731642e-02 | 2.658017e-01 | 8.508576e-01 |
| `eeg_hjorth_complexity` | 5.236606e+00 | 1.652451e+00 | 2.007903e+00 | 4.906778e+00 | 1.466623e+01 |
| `eeg_spec_entropy` | 2.450701e+00 | 3.446285e-01 | 1.329981e+00 | 2.407419e+00 | 3.867844e+00 |
| `eog_movement` | 1.042046e-05 | 8.424379e-06 | 1.738589e-06 | 8.692221e-06 | 8.114621e-05 |
| `emg_rms` | 2.798696e-06 | 1.021178e-06 | 1.098497e-07 | 3.274786e-06 | 3.654510e-06 |


### Tested Model XGBoost - Xingkai - 2026-10-08

mean cohens_kappa 0.754 (sd 0.011, range 0.742-0.765 across 3 subjects)
accuracy: 0.869
cohens_kappa: 0.755
macro_f1: 0.726
balanced_accuracy: 0.776
Confusion matrix (rows=true, columns=predicted): ['W', 'N1', 'N2', 'N3', 'REM']
[[10242   622    87   328    61]
 [   87   305   109     2    93]
 [   71   126  2377   104   114]
 [   88     1    66   777     0]
 [    8   118   100     1   801]]
Saved results to `results/real__P2_xgboost_20261008T193616042677Z`



### Course-environment reproduction of P0-P5 - Lili - 2026-10-08

The preprocessing experiments were repeated in the `cm2013-team` Conda environment using Python 3.11.17.

All experiments used the same three subjects (SC400, SC401 and SC402), two nights per subject, 11 supplied features, a Random Forest classifier and three subject-wise leave-one-subject-out (LOSO) folds. No cropping was applied.

#### Performance comparison

| Metric                          |     P0 |        P1 |        P2 |     P3 |     P5 |
| ------------------------------- | -----: | --------: | --------: | -----: | -----: |
| Evaluated epochs                | 16,688 |    16,688 |    16,688 | 16,685 | 16,688 |
| Mean subject-wise Cohen's kappa |  0.720 | **0.743** |     0.736 |  0.721 |  0.720 |
| SD of subject-wise kappa        |  0.119 |     0.114 | **0.102** |  0.125 |  0.119 |
| Pooled accuracy                 |  0.868 | **0.880** |     0.877 |  0.869 |  0.868 |
| Pooled Cohen's kappa            |  0.729 | **0.752** |     0.743 |  0.731 |  0.729 |
| Pooled macro-F1                 |  0.622 | **0.654** |     0.648 |  0.621 |  0.622 |
| Pooled balanced accuracy        |  0.592 | **0.618** |     0.613 |  0.590 |  0.592 |

#### Interpretation and decisions

**P1 — Band-pass filtering**

P1 (0.5–40 Hz EEG band-pass filtering) achieved the highest mean subject-wise Cohen's kappa and the best pooled classification metrics in this reproduction.

P1 is retained as the current preferred preprocessing candidate.

**P2 — Wavelet denoising**

P2 (db4 wavelet denoising) also improved performance relative to P0. Although its mean kappa was slightly lower than P1, it achieved lower between-subject variability and better REM recall.

Both P1 and P2 are therefore retained as preprocessing candidates for further evaluation.

**P3 — Broken-segment handling**

P3 excluded three epochs with simultaneous near-flat EEG and EOG, leaving 16,685 epochs.

Its primary purpose remains data-quality control rather than classification improvement. Because P3 evaluates a slightly different set of epochs, its metrics should be interpreted with this difference in mind.

**P5 — Suspected clipping detection**

P5 flagged 57 of 16,688 epochs (0.342%) for suspected EEG clipping.

No signals or labels were modified, and no epochs were excluded. Classification metrics and the confusion matrix remained identical to P0.

P5 is retained as a quality-control safeguard, not as a denoising method. Flagged epochs are not necessarily confirmed instances of hardware saturation.

An additional exploratory investigation considered impulsive EEG disturbances and large baseline variations, using both EEG and EOG signals for morphological verification. Although several candidate events were identified, their interpretation remained ambiguous and no reliable criterion for automatic correction was established. Therefore, no further denoising transformation was added to P5, and the original signals were preserved.

#### Comparison with earlier experiments

The relative ranking of P1 and P2 differs from the experiments performed in the earlier environment.

In the earlier experiments, P2 achieved a slightly higher mean subject-wise Cohen's kappa than P1 (0.743 vs 0.737).

In the course-environment reproduction, P1 achieved a higher mean kappa than P2 (0.743 vs 0.736).

The historical results are preserved for transparency. These comparisons remain exploratory because only three subjects were evaluated.

#### Saved results and provenance

Each experiment generated a `report.json` containing the evaluation results and a `provenance.json` recording information needed for reproducibility.

| Experiment | Results directory                          |
| ---------- | ------------------------------------------ |
| P0         | `results/real__P0_20261008T115921097052Z/` |
| P1         | `results/real__P1_20261008T120846779566Z/` |
| P2         | `results/real__P2_20261008T121636`         |



### Course environment alignment - Xingkai - 2026-10-08

Reproduce from the team repository root:

```bash
uv sync --locked
uv run --locked python -B scripts/smoke_test.py
uv run --locked python -B -m unittest discover -s tests -v
uv run --locked python -B scripts/internal/run_baseline.py --subjects 0 1 2 --nights 1 2
```



### P5 EEG clipping detection and quality flagging - Lili - 2026-10-08

**Motivation.**

Exploratory EEG quality-control analysis identified unusually repeated amplitude extrema in several Sleep-EDF recordings, particularly SC4012E0 and SC4022E0. Visual inspection showed flattened EEG peaks, suggesting possible amplitude saturation or clipping. However, without confirmed acquisition limits, these events are classified as suspected rather than confirmed clipping.

**Detection method.**

P5 uses a deterministic, label-independent detector applied separately to each complete recording:

1. Compute the minimum and maximum EEG amplitude within the recording.
2. Identify sequences of at least three consecutive samples exactly equal to either extreme.
3. Flag any 30-second epoch containing such a sequence.
4. Preserve all original EEG, EOG and EMG signals, labels and epochs.

At 100 Hz, three samples correspond to 30 ms. The upper and lower extrema are checked separately to avoid combining opposite-amplitude samples into a single plateau.

The detector stores the flagged epoch indices and detection parameters in the recording metadata. A separate `clipping_qc.json` file provides the recording-level quality-control report.

**Quality-control results.**

| Recording | Flagged epochs | Total epochs | Flagged (%) |
| --------- | -------------: | -----------: | ----------: |
| SC4001E0  |              2 |        2,650 |       0.075 |
| SC4002E0  |              0 |        2,829 |       0.000 |
| SC4011E0  |              3 |        2,802 |       0.107 |
| SC4012E0  |             29 |        2,848 |       1.018 |
| SC4021E0  |              0 |        2,804 |       0.000 |
| SC4022E0  |             23 |        2,755 |       0.835 |
| **Total** |         **57** |   **16,688** |   **0.342** |

The longest observed extreme-value plateaus were 340 ms in SC4012E0 and 420 ms in SC4022E0. Most flagged epochs were concentrated in these two recordings.

**Controlled comparison with P0.**

Both experiments used the same six recordings, 11 supplied features, Random Forest classifier and three subject-wise LOSO folds.

| Metric                          |          P0 |          P5 |
| ------------------------------- | ----------: | ----------: |
| Mean subject-wise Cohen's kappa |       0.704 |       0.704 |
| SD of subject-wise kappa        |       0.087 |       0.087 |
| Subject-wise kappa range        | 0.627–0.799 | 0.627–0.799 |
| Accuracy                        |       0.849 |       0.849 |
| Pooled Cohen's kappa            |       0.710 |       0.710 |
| Macro-F1                        |       0.648 |       0.648 |
| Balanced accuracy               |       0.650 |       0.650 |

A direct comparison of the P0 and P5 prediction arrays confirmed that all 16,688 predictions were identical, with zero differences.

**Validation and leakage considerations.**

The independent P5 validation script confirmed that EEG, EOG, EMG, labels and epoch alignment were preserved. The detector does not use sleep-stage labels, statistics pooled across subjects, or classifier predictions.

Recording extrema are calculated independently for each complete night. This is a recording-local, label-free operation suitable for the retrospective full-recording analysis considered here. However, it uses the complete test recording's unlabelled signal distribution and is therefore not directly applicable to real-time epoch-by-epoch inference.

The detector was designed after exploratory inspection of the current three-subject development cohort. Its parameters and performance should not be presented as independently validated on unseen subjects. The rule must be frozen before final evaluation, and any use of full-recording test statistics must remain consistent with the declared evaluation protocol.

**Decision after evaluation.**

Retain P5 as a signal-quality monitoring safeguard, not as a performance-enhancing denoising method. Flagging suspected clipping preserves the original physiological signals and provides traceable warnings without introducing potentially misleading interpolation or reconstruction.

P5 does not improve classification performance because its flags are stored as metadata and are not used as classifier features. All epochs remain in the evaluation.

The current detector identifies repeated extrema within individual epochs and does not yet merge plateaus crossing epoch boundaries. It also cannot independently confirm hardware saturation. These limitations should be considered before extending the method to additional recordings.

**Reproducibility.**

Command:
`python scripts/internal/run_baseline.py --preprocess denoise_clipping`

Output directory:
`results/real__P5_20261008T100803267247Z/`

Artifacts:

- `report.json`
- `provenance.json`
- `clipping_qc.json`

Independent validation:
`python scripts/diagnostics/check_p5_flags.py`

P0/P5 prediction comparison:
16,688 identical predictions; 0 differences.

### P5 — Exploratory investigation of additional EEG noise

**Motivation.**

Following the suspected-clipping investigation, additional EEG signal-quality anomalies were explored to determine whether another objective preprocessing correction could be justified. The investigation focused on abrupt sample-to-sample EEG changes and large baseline variations within short windows.

**Exploratory analysis.**

Candidate events were identified using EEG amplitude changes and short-window baseline variations. The corresponding EEG and EOG signals were inspected together to assess event morphology and possible relationships between channels.

Diagnostic plots were generated at both broad and narrow time scales. Candidate events were also grouped into episodes to avoid interpreting consecutive detections as independent disturbances.

**Observations and limitations.**

Several candidate events were identified, but visual inspection did not provide sufficient evidence to classify them consistently as acquisition artifacts rather than physiological activity or mixed EEG/EOG events.

Large amplitude changes alone were not considered sufficient justification for automatic removal or correction. Likewise, baseline variations could not reliably be separated from physiological signal changes using the exploratory criteria.

**Decision.**

No additional denoising or artifact-correction method was introduced. The original EEG, EOG and EMG signals were preserved, and P5 remained limited to suspected-clipping detection and quality-control flagging.

This decision avoids introducing potentially unjustified signal modifications. The exploratory detectors and visualisations are retained as diagnostic evidence rather than as validated preprocessing methods.

**Diagnostic scripts and outputs.**

- `scripts/diagnostics/diagnose_p5_other_noise.py`
- `scripts/diagnostics/diagnose_p5_eeg_eog_events.py`
- `scripts/diagnostics/plot_p5_noise_examples.py`
- `scripts/diagnostics/plot_p5_event_morphology.py`
- `results/p5_diagnostics/`

### P3 Broken-segment handling - Lili - 2026-10-06

**Motivation.**  

The real-data QC identified a localized near-flat event in recording
`SC4012E0`. A continuous short-window analysis confirmed that EEG and EOG
were simultaneously near-flat for approximately 100 s, spanning the end of
epoch 2844 and epochs 2845–2847. Shorter low-variability periods were also
observed in individual channels in other recordings, so low variability in a
single channel was not considered sufficient evidence for exclusion.

**Decision.**  

P3 uses a conservative, label-independent detector based on the standard
deviation of the complete 30 s epoch. An epoch is classified as broken only
when both:

- EEG standard deviation < `4.820492569885e-06 V`
- EOG standard deviation < `7.200175602286e-06 V`

The thresholds were fixed from the QC analysis before evaluating P3 and are
not recomputed during LOSO evaluation. Epochs detected as broken are excluded,
with the same mask applied to EEG, EOG, EMG and labels. The detected indices
and QC decision are also stored in the recording metadata.

On the current six-recording development dataset, the detector excluded only
three epochs, all from `SC4012E0`: epochs 2845, 2846 and 2847. The dataset
therefore changed from 16,688 to 16,685 epochs (3/16,688 = 0.018%).

**Controlled comparison with P0.**

| Metric                          |          P0 |          P3 |
| ------------------------------- | ----------: | ----------: |
| Mean subject-wise Cohen's kappa |       0.704 |       0.694 |
| SD of subject-wise kappa        |       0.087 |       0.109 |
| Subject-wise kappa range        | 0.627–0.799 | 0.582–0.800 |
| Accuracy                        |       0.849 |       0.843 |
| Pooled Cohen's kappa            |       0.710 |       0.700 |
| Macro-F1                        |       0.648 |       0.644 |
| Balanced accuracy               |       0.650 |       0.647 |

P3 did not improve classification performance on the current three-subject
development cohort. Mean subject-wise kappa decreased by 0.010 and the other
summary metrics also decreased slightly. However, only three epochs (0.018%
of the dataset) were removed, so this experiment provides little evidence
about the effect of broken-segment handling when recordings contain more
substantial dropout.

**Decision after evaluation.**  
Retain P3 as a data-quality safeguard rather than as a performance-enhancing
preprocessing step. The exclusion criterion was motivated by signal QC rather
than classifier performance and targets epochs considered unreliable for
physiological feature extraction. Keeping the detector in the pipeline also
provides a predefined handling rule if similarly sustained multichannel
near-flat segments occur in additional recordings. The small decrease in
classification metrics on the current development cohort is therefore not
used as a reason to retain objectively broken epochs.



### P0 vs P1 vs P2 preprocessing comparison - Lili - 2026-10-06

Development subset: 3 subjects (SC400, SC401, SC402), 2 nights per subject, 6 recordings and 16,688 epochs. The dataset, 11 supplied features, Random Forest classifier and subject-wise LOSO evaluation were kept unchanged across all three experiments. Only the preprocessing step was changed.

- P0: no preprocessing.
- P1: EEG 0.5–40 Hz zero-phase Butterworth band-pass; EOG and EMG unchanged.
- P2: EEG wavelet denoising using db4, automatic decomposition level capped at 5, soft thresholding and an automatically estimated per-epoch VisuShrink threshold; EOG and EMG unchanged.


| Metric                     |          P0 |          P1 |          P2 |
| -------------------------- | ----------: | ----------: | ----------: |
| Mean subject Cohen's kappa |       0.704 |       0.737 |   **0.743** |
| SD subject Cohen's kappa   |       0.087 |       0.074 |   **0.065** |
| Subject kappa range        | 0.627–0.799 | 0.666–0.813 | 0.669–0.781 |
| Accuracy                   |       0.849 |       0.868 |   **0.872** |
| Pooled Cohen's kappa       |       0.710 |       0.742 |   **0.747** |
| Macro-F1                   |       0.648 |   **0.683** |       0.677 |
| Balanced accuracy          |       0.650 |   **0.680** |       0.666 |

Per-stage recall also increased for all five stages:

| Stage |    P0 |        P1 |        P2 |
| ----- | ----: | --------: | --------: |
| W     | 0.918 |     0.933 | **0.944** |
| N1    | 0.408 | **0.416** |     0.315 |
| N2    | 0.900 | **0.905** |     0.897 |
| N3    | 0.460 | **0.533** |     0.513 |
| REM   | 0.566 |     0.611 | **0.660** |

P0 VS P1
The largest recall improvements were observed for N3 and REM. N3→N2
confusions decreased from 320 to 273 epochs and REM→N2 confusions from
356 to 313 epochs.

P0 VS P2, P2 VS P1
P2 improved substantially over P0 in the primary metric (mean subject Cohen's kappa: 0.704 to 0.743) and also reduced between-subject variability (SD: 0.087 to 0.065). It also improved Wake, N3 and REM recall relative to P0. However, the comparison between P1 and P2 was less clear. P2 increased mean subject kappa by only 0.006 and pooled kappa by 0.005 relative to P1, while macro-F1 decreased from 0.683 to 0.677 and balanced accuracy decreased from 0.680 to 0.666.

The main stage-level trade-off was N1. Its recall decreased from 0.416 with P1 to 0.315 with P2. N2 recall also decreased slightly from 0.905 to 0.897, while REM recall improved from 0.611 to 0.660.

**Decision:** 
P1 : retain the 0.5–40 Hz EEG band-pass as the current preprocessing
candidate. It improved all primary and secondary metrics on the development
subset and reduced between-subject kappa variability. This decision remains
provisional until the selected final pipeline is evaluated on a larger
subject set.
P2 : Decision: P2 is considered beneficial relative to P0, but not clearly superior to P1. The small improvement in the primary metric is accompanied by less balanced stage-wise performance, particularly for N1. P1 is therefore retained as the current preprocessing candidate for subsequent development experiments. This decision remains provisional because the comparison is based on only three development subjects.



### Real EDF baseline - Xingkai - 2026-10-01

**Completed on real Sleep-EDF recordings, not synthetic data.** The supplied
baseline was unchanged: StandardScaler + RandomForestClassifier with 200 trees,
seed 0 and balanced class weights. Preprocessing was `none`, spectral estimation
was `welch`, all 11 supplied features were retained, and no wake cropping was
applied. Stages 3/4 were merged into N3 and Movement/Unknown dropped by the loader.
LOSO used three folds, each holding out all epochs of one subject. This small
subset is a baseline reference, not an untouched final test cohort.

Reproduce from the repository root:

```bash
.venv/bin/python -B scripts/internal/run_baseline.py --cache-dir sleep_edf_data --subjects 0 1 2 --nights 1
```

The runner evaluates every PSG/hypnogram pair under the cache directory. This run
used exactly SC4001E0, SC4011E0 and SC4021E0. Adding files changes the cohort.
Results and provenance for this run are saved in
`results/real_baseline_20261001T193926289176Z/`:
- `report.json`: metrics, confusion matrix, per-subject/fold results and aligned
  out-of-fold labels, predictions, groups and fold IDs.
- `provenance.json`: input EDF SHA-256 hashes, configuration, package versions,
  source hashes and Git state (HEAD `dde6e44419ce6f8254717e1c7d3d027620a8cff3`).

| Metric | Pooled result |
|---|---|
| Accuracy | 0.756 (unrounded: 0.7564195736) |
| Cohen's kappa | 0.579 |
| Macro-F1 | 0.618 |
| Balanced accuracy | 0.699 |

Harness summary: `mean cohens_kappa 0.618 (sd 0.202, range 0.386-0.760 across 3 subjects)`.

| Held-out subject | Recording | Epochs | Accuracy | Kappa | Macro-F1 |
|---|---|---|---|---|---|
| SC400 | SC4001E0 | 2650 | 0.902264 | 0.760222 | 0.677821 |
| SC401 | SC4011E0 | 2802 | 0.530335 | 0.386262 | 0.577265 |
| SC402 | SC4021E0 | 2804 | 0.844508 | 0.707555 | 0.684391 |

Confusion matrix: rows=true, columns=predicted.

| True / predicted | W | N1 | N2 | N3 | REM |
|---|---|---|---|---|---|
| W | 4312 | 255 | 111 | 1076 | 6 |
| N1 | 43 | 120 | 74 | 1 | 23 |
| N2 | 44 | 33 | 1193 | 28 | 59 |
| N3 | 61 | 0 | 74 | 284 | 1 |
| REM | 1 | 13 | 108 | 0 | 336 |

There were 8,256 epochs: W=5,760, N1=261, N2=1,357, N3=420, REM=458.
Wake accounts for about 69.8% of epochs, so accuracy alone is insufficient.
SC401 has the weakest kappa; the largest pooled confusion is Wake predicted as
N3 (1,076 epochs). No causal explanation or improvement is claimed yet.
These real-data metrics must not be interpreted as a gain/loss against the
synthetic smoke metrics, because the datasets differ.

Checks passed: all three EDF pairs loaded; 100 Hz / 3,000 samples per epoch;
finite feature matrix of shape (8256, 11); one prediction per epoch; three LOSO
folds; recomputed confusion matrix and kappa match the saved report; source hashes
match; JSON serialization, missing-input handling and overwrite protection tested.
Python package versions: NumPy 2.5.3, SciPy 1.18.1, scikit-learn 1.9.1, MNE 1.13.2.
The first execution reached the output step but could not save due to sandbox
permissions; the same configuration was rerun with write permission. No tuning
was performed. Runner and documentation prepared/executed with Codex assistance
at Xingkai's request. No commit or push was performed.



### Synthetic smoke-test evidence - Xingkai - 2026-09-30

PASS. These are synthetic-data results, not performance on real Sleep-EDF.

**Configuration**

- Data: `track.smoke(n_subjects=5, n_epochs=80, seed=0, difficulty="medium")`.
- 400 labelled 30-second epochs, 100 Hz, 11 supplied features per epoch.
- Preprocessing: `none`; spectral estimator: `welch`; feature selection: `none`.
- Classifier: `adapter.default_baseline(seed=0, n_estimators=200, imbalance="balanced")`.
- Pipeline: 200-tree random forest (balanced class weights) -> StandardScaler
- Validation: five LOSO folds; 320 training and 80 test epochs per fold.
- Environment: Python 3.13.3; NumPy 2.5.3; SciPy 1.18.1; scikit-learn 1.9.1; Matplotlib 3.11.2.

**Results**

| Pooled metric | Harness value |
|---|---|
| Accuracy | 0.753 |
| Cohen's kappa | 0.677 |
| Macro-F1 | 0.730 |
| Balanced accuracy | 0.747 |

Harness summary: `mean cohens_kappa 0.682 (sd 0.318, range 0.155-0.933 across 5 subjects)`.

| Held-out subject | Epochs | Accuracy | Kappa | Macro-F1 |
|---|---|---|---|---|
| S01 | 80 | 0.9125 | 0.867862 | 0.894755 |
| S02 | 80 | 0.3125 | 0.155470 | 0.354552 |
| S03 | 80 | 0.7125 | 0.615706 | 0.487004 |
| S04 | 80 | 0.9500 | 0.933040 | 0.951562 |
| S05 | 80 | 0.8750 | 0.837662 | 0.862940 |

Confusion matrix: rows are true labels, columns are predicted labels.

| True \ predicted | W | N1 | N2 | N3 | REM |
|---|---|---|---|---|---|
| W | 28 | 1 | 0 | 0 | 13 |
| N1 | 7 | 25 | 7 | 0 | 2 |
| N2 | 0 | 38 | 103 | 12 | 2 |
| N3 | 0 | 1 | 12 | 71 | 0 |
| REM | 1 | 1 | 2 | 0 | 74 |

Observed labels: W=42, N1=41, N2=155, N3=84, REM=78. The largest confusion is N2 predicted as N1 (38 epochs). S02 is much weaker than the other subjects, the pooled score alone hides this.

**Code**

```bash
import numpy as np
from adapter import default_baseline
from sleep_edf import SleepEDFTrack

track = SleepEDFTrack()
recs = track.smoke(n_subjects=5, n_epochs=80, seed=0, difficulty="medium")
X, y, groups = track.build_dataset(recs)
assert X.shape == (400, 11) and np.isfinite(X).all()
clf = default_baseline(seed=0, n_estimators=200, imbalance="balanced")
rep = track.evaluate(X, y, groups, clf=clf)
assert len(rep["y_pred"]) == len(y) == 400
assert rep["n_groups"] == len(rep["per_fold"]) == 5
assert np.asarray(rep["confusion"]).sum() == 400
assert all(np.isfinite(rep[k]) for k in (
    "accuracy", "cohens_kappa", "macro_f1", "balanced_accuracy"))
repeat = track.run_smoke()
assert np.array_equal(rep["y_true"], repeat["y_true"])
assert np.array_equal(rep["y_pred"], repeat["y_pred"])
print(rep["summary"])
for key in ("accuracy", "cohens_kappa", "macro_f1", "balanced_accuracy",
            "labels", "confusion", "per_group", "spread"):
    print(key, rep[key])
print("PASS: shape, finite values, prediction count, five folds, confusion total, repeatability")
```


## ⚠️ Before you fill in many rows — the garden of forking paths

The harness guarantees that **no single run** leaks a subject. It cannot guarantee anything
about the *sequence* of runs. Every row in the table above is scored on the **same**
group-aware folds, and those are the same folds that produce the number you will report. Try
twelve configurations against one held-out set and report the best, and the winner was chosen
partly because it happens to suit *these particular subjects*. Its margin over the runner-up is
optimistically biased, and nothing in the report will look wrong. This is a **selection effect**,
not a leak — which is exactly why the leakage guard cannot catch it, and why it has to be
handled by how you *plan* the work rather than by the code.

It bites hardest here because the cohorts are small: a dozen comparisons on five or six subjects
is a great deal of selection pressure on very little data.

Two defensible ways to handle it. **Say in the report which one you used** — Criterion 7 grades
the quality of the comparison, and this is part of that quality:

| approach | what you do | what it costs |
|---|---|---|
| **an explicit development set** | hold out a few groups *up front* as a DEV set; compare every design option on DEV only; run the chosen pipeline **once** on the untouched evaluation folds and report that | fewer groups serving each purpose — painful on these cohorts — and a noisier DEV estimate |
| **a comparison budget** | decide in advance how many configurations you will compare (a handful, not a sweep), write them into this file **before** you run them, and report the count | you may miss a better option, and you have to resist re-opening the budget once you have seen the numbers — which is the whole discipline |

Either way, two habits that cost nothing:

- **Record the count.** "We compared 6 configurations" belongs in the report. A team that
  compares six and says so is doing better science than one that compares twenty and shows a
  longer table.
- **Read a small margin as no margin.** If the difference between two options is smaller than
  the spread across your subjects/folds, it is not a result. Say "no measurable difference; we
  kept the simpler one" — that sentence earns marks, and claiming the 0.01 does not.

**Related, and equally invisible: *where* your preprocessing is fitted.** The notebook builds
features for every recording **before** `evaluate()` cuts the folds. That is safe for everything
the scaffold ships, because all of it is **stateless** — a fixed filter, or a threshold estimated
from one epoch's own samples. It stops being safe the moment you add a stage that **learns**:
CSP, PCA/ICA, a cohort-wide z-score, a learned artifact template. Fit one of those over all the
recordings and every held-out subject has already shaped the transform that built the training
features — and `assert_no_subject_leak` will still pass, because it checks group ids and cannot
see what a filter was learned from. A learned stage must be fitted **inside** the fold: as a step
in the classifier pipeline (cloned and refit per fold) or via `select_features()`. If you added
one, record here which of the two you used.



## Decision log — the choices behind the numbers

Rows above say *what happened*; this says *what you chose and why*, which is what §16.4 asks you
to make traceable and what the report's defence is built from. There is no single correct
pipeline here — the scaffold deliberately ships options, not answers. One line per decision;
add rows as the pipeline grows, and note the alternative you rejected.

| Pipeline module | Option chosen | Alternative(s) considered | Why this one (one sentence) | Iteration | Revised later? |
|---|---|---|---|---|---|
| 1. Data loading | *e.g.* 8 subjects, both nights | more subjects, one night each | subject-level split needs both nights inside one group | 1 | — |
| 2. Preprocessing — P1 band-pass filtering| EEG 0.5–40 Hz zero-phase Butterworth band-pass | No preprocessing; 50 Hz notch; wavelet denoising | P1 improved mean subject kappa from 0.704 to 0.737 and macro-F1 from 0.648 to 0.683 without increasing between-subject variability; no 50 Hz notch was justified by QC | 2b | No — current choice, subject to later revision |
| 2. Preprocessing — P2 wavelet denoising | Retained as an alternative preprocessing candidate alongside P1 | P2: EEG db4 wavelet denoising with automatic level (max 5), soft thresholding and automatic per-epoch threshold | P2 improved over P0 and achieved a slightly higher mean subject kappa than P1 (0.743 vs 0.737). However, the gain was small (+0.006), while macro-F1 decreased from 0.683 to 0.677, balanced accuracy from 0.680 to 0.666, and N1 recall from 0.416 to 0.315. P1 was therefore retained because its performance was more balanced across sleep stages. | 2c | Yes — retained alongside P1 after course-environment reproduction |
| 2. Preprocessing — P3 broken-segment handling | Retained as a data-quality safeguard: exclude complete epochs with simultaneous near-flat EEG and EOG | Flag detected epochs without exclusion; no broken-segment handling | QC identified a sustained simultaneous EEG/EOG near-flat event in SC4012E0; the fixed label-independent rule excluded only the three fully affected epochs (2845–2847). Although mean subject kappa decreased from 0.704 to 0.694 vs P0, the rule was retained because objectively broken epochs should not be treated as valid physiological signal and the same predefined rule can handle similar dropout in additional recordings. | 2d | Yes, revised in 2l–2m: flag-only QC replaced automatic exclusion in the integrated pipeline. |
| 2. Preprocessing — P5 clipping QC | Retained as a quality-control safeguard: flag suspected EEG clipping without signal modification or epoch exclusion | Exclude flagged epochs; interpolate saturated samples; apply generic denoising; ignore suspected clipping | QC found 57/16,688 epochs with repeated recording-specific EEG extrema. P5 preserved all original data and produced exactly the same 16,688 predictions as P0. Flagging was preferred because the lost signal cannot be reliably reconstructed and exclusion of entire 30-second epochs was not justified by the observed short plateaus. | 2e | No — retained for signal-quality documentation, not performance improvement |
| 2. Preprocessing — P5 additional EEG noise exploration | No additional automatic correction; preserve original signals | Correct abrupt EEG amplitude changes; remove suspected artifacts; correct baseline variations | Exploratory EEG/EOG morphology analysis identified ambiguous candidate events without a reliable criterion to distinguish artifacts from physiological activity. Additional corrections were therefore rejected to avoid unjustified signal modification. | 2e | No — exploratory diagnostics retained, but no new preprocessing transformation |
| 2. Preprocessing — spindle preservation review | Retain P1 as the preferred preprocessing candidate; reconsider P2 denoising thresholds | P2 wavelet denoising under the current settings | P1 preserved all eight Raw spindle candidates at IoU ≥ 0.30, whereas P2 matched only five and retained 27.63% of sigma-band power on average. This provides a physiological reason to favor P1 beyond classification metrics alone. | 2f | Yes — P2 remains an investigated alternative, but its physiological preservation is now a documented concern requiring revision before further use |
| 2. Preprocessing - P6 clock-based cropping | Retain P1 as the preferred configuration; document P6 as an alternative training-selection experiment | Fixed 20:30–11:00 training window versus full-night training | P6 slightly improved pooled balanced accuracy (0.6185→0.6251), but reduced pooled kappa (0.7516→0.7421) and outside-window Wake recall (98.67%→97.66%). The improvement was insufficient to replace P1. | 2h | No — P1 remains preferred; random Wake undersampling proposed but not tested |
| 2. Preprocessing, large-cohort revision | P1 provisionally retained; P2 db4 not selected | P0 none; P1 band-pass; P2 wavelet | On 68 subjects, P1 achieved pooled κ 0.731 versus 0.728 for P0, whereas P2 decreased to 0.692. This revises the earlier positive interpretation of P2 on three subjects; coif3 remains to be evaluated. | 2i–2k | Yes — earlier P2 assessment revised after larger-cohort evidence |
| 2. Preprocessing: integrated QC | P1 band-pass + P3/P5 flag-only QC | Automatic P3 exclusion; P5 correction or exclusion; no QC | Full-cohort QC identified 3,630 flagged epochs, but 94.1% were Wake and the association with classification errors depended strongly on sleep stage. Non-destructive QC preserves all data while retaining diagnostic metadata. | 2l–2m | Yes — supersedes the earlier P3 exclusion decision for the current integrated pipeline |
| 2. Preprocessing — combined P1+P2 | Retain P1; reject the tested P1+P2 db4 combination | Sequential band-pass filtering followed by db4 wavelet denoising | On 68 subjects, combined preprocessing decreased pooled κ from 0.731 to 0.702 relative to P1 and reduced subject-wise κ for 53/68 subjects. P1 remained better for all five sleep-stage recalls. | 2n | Yes — combined preprocessing was tested and rejected after large-scale downstream evaluation |
| 2. Preprocessing, Butterworth cutoff and order | Retain P1 (0.5–40 Hz, order 4) | P1b: 0.5–35 Hz order 4; P1c: 0.5–35 Hz order 5 | Both alternatives achieved pooled κ 0.730 and macro-F1 0.654, compared with 0.731 and 0.655 for P1. No meaningful improvement was demonstrated. | 2o–2p | No, P1 retained; continuous filtering to be tested in P1d |

| 2. Preprocessing — continuous versus epoch-wise filtering | Retain P1 epoch-wise EEG filtering | P1d continuous EEG filtering before segmentation | P1d achieved pooled κ 0.731 and mean subject κ 0.728 (SD 0.121), without meaningful improvement over P1; the existing epoch-wise method remains preferred. | 2q | No — P1 retained |
| 2. Signal quality — strict EEG clipping | Preserve all epochs and export EDF-boundary quality flags | Exclude clipped epochs; interpolate plateaus; rely only on the earlier P5 heuristic | A stricter detector identified 1,227 epochs containing sustained plateaus at EDF physical limits; signal reconstruction was not justified. | 2r | Yes — refined the interpretation of the earlier P5 flags |
| 2. Signal quality — EOG and EMG | Preserve original signals; no additional correction | Automatic exclusion based on extreme standard deviation; EOG/EMG denoising | EDF-limit audit found one EOG boundary sample and no EMG boundary samples across 133 recordings; visual variability alone did not establish artifacts. | 2s–2t | No — preprocessing investigation closed |


| 3. Feature extraction |  |  |  |  |  |
| 4. Feature selection | *e.g.* `select="none"` | ANOVA `SelectKBest`, tree importances | 14 features vs. ~1 800 epochs — pruning risked more than it saved | 1 | *e.g.* **yes, iter 4** — `select_k=20` was a no-op (harness said so); switched to `k=6` |
| 5. Classification, incl. `imbalance` | *e.g.* `imbalance="balanced"` | `"none"`, `"resample"`, `"threshold"` | *(if you kept the default, say you looked and why — a silent default earns nothing)* |  |  |
| 6. Inference |  |  |  |  |  |
| 7. Reporting |  |  |  |  |  |



## Revisions — the ones that went **backwards** (Criterion 9's actual evidence)

Adding iterations forward is a to-do list. What this section wants is the place a number
downstream sent you back **up** the pipeline. One row is enough; two is a good project.
The notebook's "Decision points on this track" section has a symptom → stage table to
diagnose from.

| # | The downstream result that triggered it | Which earlier decision it indicted | What you changed | What happened to the metric |
|---|---|---|---|---|
| 1 | *e.g.* worst-subject κ 0.14 vs. mean 0.61 | stage 2 — no per-recording normalisation | z-scored band powers within each recording | mean κ 0.61 → 0.59, **worst subject 0.14 → 0.38** — kept |
| 2 | P2 db4 attenuated selected spindle candidates and matched only 5/8 raw candidates, prompting a review of its preprocessing settings | Stage 2 — choice of mother wavelet for P2 | Revisited the db4 choice by testing sym4, coif1 and coif3 under identical LOSO conditions | coif3 increased pooled kappa from 0.743 to 0.745 but reduced macro-F1 from 0.648 to 0.647; db4 was retained as the P2 reference, and P1 remained preferred |
| 3 | Large-cohort P2 wavelet performance decreased to pooled κ 0.692, compared with 0.728 for P0 | Earlier three-subject assessment that P2 denoising was beneficial relative to P0 | Reassessed the same preprocessing approaches on 68 development subjects using five fixed subject-wise folds; retained P1 provisionally and planned coif3 reassessment | P2 pooled κ 0.743 on the earlier three-subject course-environment experiment versus 0.692 on 68 subjects; these are different cohorts, not a paired performance change |
| 4 | Full-cohort QC identified 748 P3 near-flat epochs and 2,882 P5 suspected-clipping epochs; stage-specific error analysis showed mixed associations and strong Wake dominance among flagged epochs | Earlier P3 strategy automatically excluded near-flat epochs | Revised the integrated P3 behavior from exclusion to flag-only QC, while preserving P5 as flag-only | No new classifier score was generated for the integrated configuration; the existing P1 predictions remain unchanged because QC flags are not used for feature extraction or classification |
| 5 | Combined P1+P2 reduced pooled κ from 0.731 to 0.702 relative to P1, with 53/68 subjects showing lower κ | Earlier hypothesis that band-pass filtering before wavelet denoising might improve the current feature representation | Implemented and evaluated sequential P1+P2 db4 preprocessing, then rejected it for the selected pipeline | Mean subject κ decreased from 0.728 to 0.696; mean paired Δκ = −0.0321 (SD 0.0553) |
| 6 | The earlier P5 heuristic flagged 2,882 epochs on the 68-subject cohort, but repeated recording extrema alone did not establish correspondence with EDF acquisition limits | Stage 2 — interpretation and specificity of the P5 suspected-clipping detector | Revisited the detection criterion using plateaus of at least 10 samples and independently verified EDF physical limits; produced 1,227 strict flags, all associated with EDF boundaries | No new classifier evaluation; this was a refinement of signal-quality evidence, not a performance improvement |


## Who did what

One line per person per iteration — the honest-disclosure requirement of §16.7, and the evidence
`INDIVIDUAL_ASSESSMENT.md` asks for. The seven modules do **not** have to map one-to-one onto
people: one person may own several modules, two people may share one, and ownership may rotate
between iterations. Record what actually happened.

| Iteration | Who | Modules / tasks owned | Reviewed by |
|---|---|---|---|
| 1 | Xingkai | Ran and verified the supplied baseline on smoke data |  |
| 1a | Xingkai | Ran and verified the supplied baseline on real Sleep-EDF data; inspected LOSO metrics, subject-wise spread and confusion matrix |  |
| 1b | Lili | Ran and verified the supplied baseline on real Sleep-EDF data; inspected LOSO metrics, subject-wise spread and confusion matrix | Xingkai |
| 2 | Lili | Signal-quality review; implemented and validated P1 EEG band-pass preprocessing, P2 EEG wavelet denoising and P3 broken-segment detection/exclusion; performed short-window and continuous-duration QC analysis of near-flat segments; ran controlled P0/P1, P0/P2 and P0/P3 LOSO comparisons; analysed subject-wise metrics, stage-wise performance and confusion matrices | Xingkai |
| 2e | Lili | Designed and implemented P5 suspected EEG clipping detection and recording-level quality flagging; analysed amplitude extrema and plateau durations across six recordings; validated preservation of all signals and labels; exported clipping QC results; performed LOSO evaluation and verified that all 16,688 P5 predictions were identical to P0; documented leakage considerations and limitations. Also investigated impulsive EEG disturbances and baseline variations, developed exploratory EEG/EOG event diagnostics, grouped candidate events into episodes, performed morphological verification, and documented the decision not to introduce additional automatic corrections. | |
| 2f | Lili | Designed and implemented the spindle-preservation evaluation of P1 and P2; performed automatic spindle-candidate detection, sigma-band power and Hilbert-envelope comparisons, independent re-detection, one-to-one IoU matching, matching-threshold sensitivity analysis and epoch-boundary checks; generated quantitative CSV outputs and diagnostic figures; documented physiological limitations and the resulting preprocessing recommendation. | |
| 2g | Lili | Designed and executed the four-mother-wavelet comparison; verified exact db4 baseline reproduction and feature/label alignment; performed three-fold LOSO Random Forest evaluation; analysed pooled and stage-specific confusion matrices, subject-level classification errors and ground-truth sleep-stage distributions; documented conclusions and follow-up investigations. | |
| 2h | Lili | Implemented and validated EDF-based epoch timestamp alignment and fixed clock-based cropping; performed subject-wise LOSO P1/P6 comparisons with identical held-out test sets; analysed nighttime and outside-window performance, subject-level results and confusion matrices; documented limitations and proposed random Wake undersampling as future work. | |
| 2i–2k | Lili | Executed and analysed large-scale P0/P1/P2 preprocessing comparisons on 68 development subjects; used reproducible five-fold subject-wise evaluation, saved fold checkpoints and provenance, compared pooled and subject-wise metrics, and revisited the earlier P2 decision | |
| 2l–2m | Lili | Integrated P3/P5 quality-control flags with P1 in the SleepEDFTrack pipeline; verified signal, label and feature preservation; performed full-cohort QC on 68 subjects and 133 recordings; aligned QC flags with P1 out-of-fold predictions; analysed overall and sleep-stage-specific classification errors; documented the decision to retain non-destructive QC | |
| 2n | Lili | Implemented and validated combined P1 band-pass and P2 db4 wavelet preprocessing; executed five-fold subject-wise evaluation on 68 development subjects; verified exact out-of-fold prediction alignment; analysed pooled metrics, stage-specific recall and paired subject-level Cohen's kappa differences; documented the negative result and revised the preprocessing decision | |
| 2o–2p | Lili | Implemented and evaluated EEG Butterworth cutoff-frequency and filter-order sensitivity experiments (P1b and P1c) on 68 development subjects; compared pooled metrics, subject-wise variability and sleep-stage recall against P0 and P1; documented the decision to retain P1 | |
| 2q | Lili | Implemented and evaluated continuous EEG filtering before epoch segmentation; verified preservation of EOG, EMG and labels; compared P1d against P1 using five-fold subject-wise evaluation on 68 development subjects | |
| 2r | Lili | Investigated EEG plateaus and clipping across 133 recordings; inspected EDF physical/digital limits; validated strict clipping candidates; quantified stage distribution and severity; generated epoch-level quality flags without modifying signals | |
| 2s | Lili | Audited original EOG and EMG channels across 133 recordings; examined native sampling rates, EDF boundaries and epoch variability; compared original 1 Hz EMG samples with resampled signals | |
| 2t | Lili | Performed final aligned EEG/EOG/EMG visual inspection; documented ambiguous multichannel variations and justified the decision not to introduce further automatic preprocessing | |



## Final numbers (fill in once, at the end)

| | Value | Under what split |
|---|---|---|
| Primary metric, development (mean + spread) |  |  |
| Secondary metrics (macro-F1 / balanced accuracy / per-class recall) |  |  |
| Held-out set — **scored once, never tuned against** |  |  |
| Supplied baseline, same harness |  |  |
| Yardstick from the dataset card (human ceiling / benchmark / chance) |  |  |
| **Configurations compared** before settling (a number) |  | on DEV folds / on the evaluation folds — say which |
| How option comparison was kept separate from final reporting |  | *e.g.* "separate DEV groups" / "budget of 6, fixed in advance" |

*Grading: `CAPSTONE_REPORT_RUBRIC.md` (team, 30 pts) and `INDIVIDUAL_ASSESSMENT.md`
(individual, 10 pts).*
