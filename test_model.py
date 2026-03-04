import torch
import numpy as np
from fl_utils import HybridDL

MODEL_PATH = "global_model_final.pth"

# Number of features your model expects
INPUT_DIM = 78   # change if your dataset has different features

# 1. Create model
model = HybridDL(INPUT_DIM)

# 2. Load weights
state_dict = torch.load(MODEL_PATH)

model.load_state_dict(state_dict, strict=False)

model.eval()

# 3. Manual sample input
sample = np.array([
    0.2, 0.1, 0.4, 0.6, 0.3, 0.5, 0.7, 0.2, 0.1, 0.9,
    0.3, 0.4, 0.2, 0.6, 0.7, 0.5, 0.8, 0.1, 0.2, 0.3,
    0.4, 0.6, 0.5, 0.7, 0.2, 0.9, 0.1, 0.3, 0.5, 0.8,
    0.6, 0.7, 0.4, 0.2, 0.3, 0.5, 0.9, 0.1, 0.6, 0.4,
    0.7, 0.2, 0.3, 0.5, 0.1, 0.3, 0.7, 0.4, 0.1, 0.3,
    0.2, 0.6, 0.7, 0.5, 0.8, 0.4, 0.3, 0.1, 0.9, 0.2,
    0.4, 0.6, 0.5, 0.7, 0.3, 0.8, 0.2, 0.4, 0.6, 0.1,
    0.7, 0.5, 0.3, 0.2, 0.8, 0.6, 0.4, 0.9
])

sample = sample.reshape(1, INPUT_DIM)

# 4. Convert to tensor
sample_tensor = torch.FloatTensor(sample)

# 5. Predict
with torch.no_grad():
    output = model(sample_tensor)

prob = output.item()

prediction = 1 if prob > 0.5 else 0

print("\nModel Output Probability:", prob)
print("Predicted Class:", prediction)

if prediction == 1:
    print("Result: ATTACK traffic")
else:
    print("Result: NORMAL traffic")