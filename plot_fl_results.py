import pandas as pd
import matplotlib.pyplot as plt

# Load FL metrics
df = pd.read_csv("fl_training_metrics.csv")

print("\nLoaded metrics:")
print(df)

# -----------------------------
# Graph 1: Total Samples vs Round
# -----------------------------
plt.figure()

plt.plot(df["round"], df["total_samples"], marker="o")

plt.xlabel("Federated Round")
plt.ylabel("Total Training Samples")
plt.title("Federated Learning Participation")

plt.grid(True)

plt.savefig("fl_total_samples.png")



# -----------------------------
# Graph 2: Average Samples per Client
# -----------------------------
plt.figure()

plt.plot(df["round"], df["avg_samples"], marker="o")

plt.xlabel("Federated Round")
plt.ylabel("Average Samples per Client")
plt.title("Client Data Contribution")

plt.grid(True)

plt.savefig("fl_avg_samples.png")



# -----------------------------
# Graph 3: Aggregation Time
# -----------------------------
plt.figure()

plt.plot(df["round"], df["aggregation_time"], marker="o")

plt.xlabel("Federated Round")
plt.ylabel("Aggregation Time (seconds)")
plt.title("FL Aggregation Time")

plt.grid(True)

plt.savefig("fl_aggregation_time.png")



# -----------------------------
# Graph 4: Model Size
# -----------------------------
plt.figure()

plt.plot(df["round"], df["model_size_kb"], marker="o")

plt.xlabel("Federated Round")
plt.ylabel("Model Size (KB)")
plt.title("Global Model Size Over Time")

plt.grid(True)

plt.savefig("fl_model_size.png")



# -----------------------------
# Graph 5: Client Participation
# -----------------------------
plt.figure()

plt.plot(df["round"], df["clients"], marker="o")

plt.xlabel("Federated Round")
plt.ylabel("Participating Clients")
plt.title("Client Participation Per Round")

plt.grid(True)

plt.savefig("fl_clients.png")

# -----------------------------
# Graph 6: Client Contribution Distribution
# -----------------------------

plt.figure()

round_labels = df["round"]

plt.bar(round_labels, df["avg_samples"])

plt.xlabel("Federated Round")
plt.ylabel("Average Samples per Client")

plt.title("Client Contribution Distribution")

plt.grid(axis="y")

plt.savefig("fl_client_contribution.png")


# Show graphs
plt.show()