"""Train the market value model and write evaluation artifacts.

Usage (from backend/):  python -m app.train

Model: scikit-learn Pipeline
    ColumnTransformer
        StandardScaler  -> goals, assists, minutes, age, age_sq, ga_per90
        OneHotEncoder   -> position
    TransformedTargetRegressor(LinearRegression, log1p / expm1)

Market values are heavily right-skewed, so the linear model is fit on
log(value); predictions and metrics are reported back in euros.
"""
import json
from datetime import datetime, timezone

import joblib
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import seaborn as sns  # noqa: E402
from matplotlib.ticker import FuncFormatter  # noqa: E402
from sklearn.compose import ColumnTransformer, TransformedTargetRegressor  # noqa: E402
from sklearn.linear_model import LinearRegression  # noqa: E402
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score  # noqa: E402
from sklearn.model_selection import GroupKFold, GroupShuffleSplit, cross_val_predict  # noqa: E402
from sklearn.pipeline import Pipeline  # noqa: E402
from sklearn.preprocessing import OneHotEncoder, StandardScaler  # noqa: E402

from . import config  # noqa: E402
from .features import (  # noqa: E402
    BASE_FEATURES, CATEGORICAL_FEATURES, MIN_MINUTES_FOR_TRAINING, NUMERIC_FEATURES, POSITIONS, TARGET,
    add_engineered_features,
)
from .predictor import LinearValueModel  # noqa: E402

# Wise-inspired palette (matches frontend/src/index.css)
LIME, INK, INK_DEEP, SAGE, NEGATIVE = "#9fe870", "#0e0f0c", "#163300", "#e8ebe6", "#d03238"
CV_FOLDS = 5


def build_pipeline() -> Pipeline:
    preprocess = ColumnTransformer([
        ("num", StandardScaler(), NUMERIC_FEATURES),
        ("cat", OneHotEncoder(categories=[POSITIONS], drop="first"), CATEGORICAL_FEATURES),
    ])
    model = TransformedTargetRegressor(regressor=LinearRegression(), func=np.log1p, inverse_func=np.expm1)
    return Pipeline([("preprocess", preprocess), ("model", model)])


def export_model_spec(pipeline: Pipeline) -> dict:
    """Flatten the fitted pipeline into plain numbers for sklearn-free serving."""
    preprocess = pipeline.named_steps["preprocess"]
    scaler = preprocess.named_transformers_["num"]
    encoder = preprocess.named_transformers_["cat"]
    regressor = pipeline.named_steps["model"].regressor_

    categories = list(encoder.categories_[0])
    dropped = encoder.drop_idx_[0] if encoder.drop_idx_ is not None else None
    kept = [c for i, c in enumerate(categories) if i != dropped]
    n_numeric = len(NUMERIC_FEATURES)
    return {
        "type": "log1p_linear_regression",
        "numeric_features": NUMERIC_FEATURES,
        "scaler_mean": scaler.mean_.tolist(),
        "scaler_scale": scaler.scale_.tolist(),
        "categorical_feature": CATEGORICAL_FEATURES[0],
        "categories": kept,
        "baseline_category": categories[dropped] if dropped is not None else None,
        "coef_numeric": regressor.coef_[:n_numeric].tolist(),
        "coef_categorical": regressor.coef_[n_numeric:].tolist(),
        "intercept": float(regressor.intercept_),
    }


def load_training_frame() -> tuple[pd.DataFrame, dict]:
    if not config.DATASET_PATH.exists():
        print("No dataset found - generating the mock dataset first.")
        from .fetch_data import build_mock_dataset
        build_mock_dataset()
    df = pd.read_csv(config.DATASET_PATH)
    meta = json.loads(config.DATASET_META_PATH.read_text()) if config.DATASET_META_PATH.exists() else {}
    df = add_engineered_features(df)
    df = df[(df["minutes"] >= MIN_MINUTES_FOR_TRAINING) & (df[TARGET] > 0)].reset_index(drop=True)
    return df, meta


def regression_metrics(y_true, y_pred) -> dict:
    return {
        "r2": float(r2_score(y_true, y_pred)),
        "r2_log": float(r2_score(np.log1p(y_true), np.log1p(y_pred))),
        "mae": float(mean_absolute_error(y_true, y_pred)),
        "rmse": float(np.sqrt(mean_squared_error(y_true, y_pred))),
    }


def euro_millions(x, _pos=None) -> str:
    return f"€{x / 1e6:.0f}M" if x >= 1e6 else f"€{x / 1e3:.0f}K"


def save_plots(preds: pd.DataFrame, coefficients: list[dict]) -> None:
    sns.set_theme(style="whitegrid", rc={"axes.edgecolor": SAGE, "grid.color": SAGE, "text.color": INK, "axes.labelcolor": "#454745", "xtick.color": "#454745", "ytick.color": "#454745"})

    # 1. Actual vs predicted (log-log)
    fig, ax = plt.subplots(figsize=(7, 6))
    sns.scatterplot(data=preds, x="actual", y="predicted", color=INK_DEEP, alpha=0.35, s=22, edgecolor="none", ax=ax)
    lo, hi = preds[["actual", "predicted"]].min().min() * 0.8, preds[["actual", "predicted"]].max().max() * 1.2
    ax.plot([lo, hi], [lo, hi], color=INK, linestyle="--", linewidth=1, label="Perfect prediction")
    ax.set(xscale="log", yscale="log", xlim=(lo, hi), ylim=(lo, hi),
           xlabel="Actual market value", ylabel="Predicted market value",
           title="Actual vs predicted (out-of-fold)")
    ax.xaxis.set_major_formatter(FuncFormatter(euro_millions))
    ax.yaxis.set_major_formatter(FuncFormatter(euro_millions))
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(config.PLOTS_DIR / "actual_vs_predicted.png", dpi=150)
    plt.close(fig)

    # 2. Residuals (log space, where the model is fit)
    resid = np.log(preds["actual"]) - np.log(preds["predicted"])
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.5))
    sns.scatterplot(x=preds["predicted"], y=resid, color=INK_DEEP, alpha=0.35, s=18, edgecolor="none", ax=ax1)
    ax1.axhline(0, color=INK, linestyle="--", linewidth=1)
    ax1.set(xscale="log", xlabel="Predicted market value", ylabel="log(actual) − log(predicted)",
            title="Residuals vs predicted")
    ax1.xaxis.set_major_formatter(FuncFormatter(euro_millions))
    sns.histplot(resid, bins=40, color=LIME, edgecolor=INK_DEEP, kde=True, ax=ax2)
    ax2.set(xlabel="log residual", title="Residual distribution")
    fig.tight_layout()
    fig.savefig(config.PLOTS_DIR / "residuals.png", dpi=150)
    plt.close(fig)

    # 3. Coefficients (% change in value per +1 std / vs Goalkeeper)
    coef_df = pd.DataFrame(coefficients).sort_values("effect_pct")
    fig, ax = plt.subplots(figsize=(7, 4.5))
    colors = [LIME if v >= 0 else NEGATIVE for v in coef_df["effect_pct"]]
    ax.barh(coef_df["feature"], coef_df["effect_pct"], color=colors, edgecolor=INK, linewidth=0.8)
    ax.axvline(0, color=INK, linewidth=1)
    ax.set(xlabel="% change in predicted value", title="Feature effects (per +1 std; positions vs Goalkeeper)")
    fig.tight_layout()
    fig.savefig(config.PLOTS_DIR / "coefficients.png", dpi=150)
    plt.close(fig)


def main() -> None:
    df, meta = load_training_frame()
    X, y, groups = df[NUMERIC_FEATURES + CATEGORICAL_FEATURES], df[TARGET], df["player_id"]
    print(f"Training on {len(df)} player-seasons / {groups.nunique()} players")

    # Hold-out split grouped by player so no player appears in both train and test.
    train_idx, test_idx = next(GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=42).split(X, y, groups))
    holdout = build_pipeline().fit(X.iloc[train_idx], y.iloc[train_idx])
    train_metrics = regression_metrics(y.iloc[train_idx], holdout.predict(X.iloc[train_idx]))
    test_metrics = regression_metrics(y.iloc[test_idx], holdout.predict(X.iloc[test_idx]))

    # Out-of-fold predictions for every row -> honest actual-vs-predicted chart.
    oof = cross_val_predict(build_pipeline(), X, y, groups=groups, cv=GroupKFold(n_splits=CV_FOLDS))
    cv_metrics = regression_metrics(y, oof)

    # Final model served by the API is fit on all data.
    final = build_pipeline().fit(X, y)
    regressor = final.named_steps["model"].regressor_
    names = [n.split("__", 1)[1] for n in final.named_steps["preprocess"].get_feature_names_out()]
    coefficients = [
        {"feature": name, "coef_log": float(c), "effect_pct": float((np.exp(c) - 1) * 100)}
        for name, c in zip(names, regressor.coef_)
    ]

    preds = df[["player_id", "name", "team", "season", "position", "age", "goals", "assists", "minutes"]].copy()
    preds["actual"] = y.round(0)
    preds["predicted"] = np.maximum(oof, 0).round(0)
    preds["split"] = "train"
    preds.loc[test_idx, "split"] = "test"
    preds.to_csv(config.PREDICTIONS_PATH, index=False)

    metrics = {
        "trained_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "model": "LinearRegression on log(market value)",
        "base_features": BASE_FEATURES,
        "model_features": NUMERIC_FEATURES + CATEGORICAL_FEATURES,
        "target": TARGET,
        "currency": "EUR",
        "data_source": meta.get("data_source", "unknown"),
        "label_source": meta.get("label_source", "unknown"),
        "seasons": meta.get("seasons", sorted(int(s) for s in df["season"].unique())),
        "n_rows": int(len(df)),
        "n_players": int(groups.nunique()),
        "n_train": int(len(train_idx)),
        "n_test": int(len(test_idx)),
        "train": train_metrics,
        "test": test_metrics,
        "cv": {"folds": CV_FOLDS, **cv_metrics},
        "intercept_log": float(regressor.intercept_),
        "coefficients": coefficients,
    }

    joblib.dump(final, config.MODEL_PATH)
    spec = export_model_spec(final)
    config.MODEL_SPEC_PATH.write_text(json.dumps(spec, indent=2))
    # The API serves from model.json, so it must reproduce the sklearn pipeline exactly.
    if not np.allclose(LinearValueModel(spec).predict(X), final.predict(X), rtol=1e-9):
        raise RuntimeError("model.json predictions diverge from the sklearn pipeline")
    config.METRICS_PATH.write_text(json.dumps(metrics, indent=2))
    save_plots(preds, coefficients)

    print(f"Test  R²={test_metrics['r2']:.3f}  R²(log)={test_metrics['r2_log']:.3f}  "
          f"MAE=€{test_metrics['mae'] / 1e6:.2f}M  RMSE=€{test_metrics['rmse'] / 1e6:.2f}M")
    print(f"CV    R²={cv_metrics['r2']:.3f}  R²(log)={cv_metrics['r2_log']:.3f}")
    print(f"Artifacts written to {config.ARTIFACTS_DIR}")


if __name__ == "__main__":
    main()
