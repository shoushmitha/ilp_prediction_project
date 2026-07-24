import pandas as pd
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import accuracy_score, classification_report
from xgboost import XGBClassifier
import joblib
import os

DATA_DIR = os.path.dirname(os.path.abspath(__file__))

# ── Load processed dataset ────────────────────────────────────────────────────
df = pd.read_csv(os.path.join(DATA_DIR, "processed_data.csv"))

# Support both 'winner' and 'target' column names
TARGET_COL = "target" if "target" in df.columns else "winner"

X = df.drop(TARGET_COL, axis=1)
y = df[TARGET_COL]

print(f"Dataset: {len(df)} matches | Features: {X.columns.tolist()}")

# ── Train / Test Split ────────────────────────────────────────────────────────
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

# ── Tuned XGBoost Model ───────────────────────────────────────────────────────
model = XGBClassifier(
    n_estimators=300,
    max_depth=6,
    learning_rate=0.05,
    subsample=0.8,
    colsample_bytree=0.8,
    min_child_weight=3,
    gamma=0.1,
    eval_metric="logloss",
    random_state=42,
    verbosity=0,
)

model.fit(X_train, y_train)

# ── Evaluation ────────────────────────────────────────────────────────────────
y_pred    = model.predict(X_test)
test_acc  = accuracy_score(y_test, y_pred)

# 5-fold cross-validation
cv_scores = cross_val_score(model, X, y, cv=5, scoring="accuracy")

print("\n=== MODEL PERFORMANCE ===")
print(f"Test  Accuracy : {test_acc * 100:.2f}%")
print(f"CV    Accuracy : {cv_scores.mean() * 100:.2f}% (+/- {cv_scores.std() * 100:.2f}%)")
print("\nClassification Report:")
print(classification_report(y_test, y_pred, target_names=["Team2 Wins", "Team1 Wins"]))

print("\nFeature Importances:")
for feat, imp in sorted(
    zip(X.columns, model.feature_importances_), key=lambda x: -x[1]
):
    bar = "#" * int(imp * 40)
    print(f"  {feat:<25} {imp:.4f}  {bar}")

# ── Save Model ────────────────────────────────────────────────────────────────
model_path = os.path.join(DATA_DIR, "xgb_model.pkl")
joblib.dump(model, model_path)
print(f"\nModel saved to: {model_path}")