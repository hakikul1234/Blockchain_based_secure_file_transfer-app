import numpy as np
from sklearn.ensemble import RandomForestClassifier
import joblib

# Sample dataset (safe vs malicious simulation)

# Features: [size, entropy, extension]
X = np.array([
    [20000, 4.5, 1],
    [15000, 3.2, 4],
    [30000, 3.0, 2],
    [500000, 7.8, 1],
    [800000, 8.1, 0],
    [1000000, 8.5, 0]
])

# Labels: 0 = Safe, 1 = Malicious
y = np.array([0, 0, 0, 1, 1, 1])

model = RandomForestClassifier()
model.fit(X, y)

joblib.dump(model, "malware_model.pkl")


print("✅ Model trained and saved as malware_model.pkl")
