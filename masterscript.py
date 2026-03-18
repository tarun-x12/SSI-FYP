import subprocess
import time
import os
import psutil
import pandas as pd
import matplotlib.pyplot as plt

# -------------------------------------------------
# CONFIG
# -------------------------------------------------

OWNER_SCRIPT = "5_owner_node.py"
ANALYST_SCRIPT = "4_analyst_persistent.py"

IMPERSONATOR = "18_impersonator_attack.py"
SYBIL = "15_attack_sybil.py"
AUTH_ATTACK = "13_attack_authority.py"
CROSS_AUTH = "14_cross_authority.py"

ROUND_FILE = "fl_training_metrics.csv"

TOTAL_ROUNDS = 100
NORMAL_ROUNDS = 50
NUM_OWNERS = 3

process_times = {}
round_metrics = []

# -------------------------------------------------
# TERMINAL LAUNCHER
# -------------------------------------------------

def start_terminal(name, command):

    start = time.time()

    subprocess.Popen(
        f'start cmd /k python {command}',
        shell=True
    )

    process_times[name] = {"start": start, "end": None}

# -------------------------------------------------
# GET CURRENT ROUND
# -------------------------------------------------

def get_round():

    if not os.path.exists(ROUND_FILE):
        return 0

    try:
        df = pd.read_csv(ROUND_FILE)
        return len(df)
    except:
        return 0

# -------------------------------------------------
# WAIT FOR OWNERS READY
# -------------------------------------------------

def wait_for_owners():

    print("Waiting for owners to stabilize...")
    time.sleep(20)
    print("Owners ready")

# -------------------------------------------------
# MONITOR TRAINING
# -------------------------------------------------

def monitor_rounds():

    start_time = time.time()
    net_start = psutil.net_io_counters()

    last_round = 0

    while True:

        current_round = get_round()

        if current_round > last_round and current_round <= TOTAL_ROUNDS:

            last_round = current_round

            now = time.time()
            net_now = psutil.net_io_counters()

            exec_time = now - start_time

            bytes_sent = net_now.bytes_sent - net_start.bytes_sent
            bytes_recv = net_now.bytes_recv - net_start.bytes_recv

            comm_bits = (bytes_sent + bytes_recv) * 8

            latency = exec_time / current_round
            throughput = current_round / exec_time

            round_metrics.append({

                "Round": current_round,
                "Execution_Time": exec_time,
                "Communication_Bits": comm_bits,
                "Latency": latency,
                "Throughput": throughput

            })

            print(f"Round {current_round} logged")

            # Start attack phase
            if current_round == NORMAL_ROUNDS:

                print("----- ATTACK PHASE STARTED -----")

                start_terminal("impersonator", IMPERSONATOR)
                start_terminal("sybil", SYBIL)
                start_terminal("auth_attack", AUTH_ATTACK)
                start_terminal("cross_auth", CROSS_AUTH)

        if current_round >= TOTAL_ROUNDS:
            break

        time.sleep(2)

# -------------------------------------------------
# RUN EXPERIMENT
# -------------------------------------------------

def run_experiment():

    if os.path.exists(ROUND_FILE):
        os.remove(ROUND_FILE)

    print("Starting owners")

    start_terminal("owner1", f"{OWNER_SCRIPT} 1")
    start_terminal("owner2", f"{OWNER_SCRIPT} 2")
    start_terminal("owner3", f"{OWNER_SCRIPT} 3")

    wait_for_owners()

    print("Starting analyst")

    start_terminal("analyst", ANALYST_SCRIPT)

    monitor_rounds()

# -------------------------------------------------
# SAVE ROUND METRICS
# -------------------------------------------------

def save_round_metrics():

    df = pd.DataFrame(round_metrics)
    df.to_csv("round_metrics.csv", index=False)

# -------------------------------------------------
# FIG 7 – EFFICIENCY (3 LINE GRAPHS)
# -------------------------------------------------

def plot_efficiency():

    df = pd.read_csv("round_metrics.csv")

    rounds = df["Round"]
    comp = df["Execution_Time"]
    comm = df["Communication_Bits"] / 1e6
    msgs = rounds * NUM_OWNERS * 2

    # Computation Efficiency
    plt.figure(figsize=(8,5))
    plt.plot(rounds, comp)
    plt.xlabel("FL Rounds")
    plt.ylabel("Execution Time (s)")
    plt.title("Fig 7a – Computation Efficiency")
    plt.grid(True)
    plt.savefig("fig7a_computation_efficiency.png")
    plt.close()

    # Communication Efficiency
    plt.figure(figsize=(8,5))
    plt.plot(rounds, comm)
    plt.xlabel("FL Rounds")
    plt.ylabel("Communication (MB)")
    plt.title("Fig 7b – Communication Efficiency")
    plt.grid(True)
    plt.savefig("fig7b_communication_efficiency.png")
    plt.close()

    # Message Efficiency
    plt.figure(figsize=(8,5))
    plt.plot(rounds, msgs)
    plt.xlabel("FL Rounds")
    plt.ylabel("Messages")
    plt.title("Fig 7c – Message Efficiency")
    plt.grid(True)
    plt.savefig("fig7c_message_efficiency.png")
    plt.close()

# -------------------------------------------------
# FIG 8 – SCALABILITY (2 GRAPHS)
# -------------------------------------------------

def plot_scalability():

    df = pd.read_csv("round_metrics.csv")

    rounds = df["Round"]
    latency = df["Latency"]
    throughput = df["Throughput"]

    # Latency Graph
    plt.figure(figsize=(8,5))
    plt.plot(rounds, latency)
    plt.xlabel("FL Rounds")
    plt.ylabel("Latency (s)")
    plt.title("Fig 8a – Latency Scalability")
    plt.grid(True)
    plt.savefig("fig8a_latency_scalability.png")
    plt.close()

    # Throughput Graph
    plt.figure(figsize=(8,5))
    plt.plot(rounds, throughput)
    plt.xlabel("FL Rounds")
    plt.ylabel("Throughput (round/s)")
    plt.title("Fig 8b – Throughput Scalability")
    plt.grid(True)
    plt.savefig("fig8b_throughput_scalability.png")
    plt.close()

# -------------------------------------------------
# RUNTIME SUMMARY
# -------------------------------------------------

def print_runtime():

    print("\n===== SCRIPT RUNTIME SUMMARY =====")

    end = time.time()

    for name,data in process_times.items():

        runtime = end - data["start"]

        print(f"{name} ran for {runtime:.2f} seconds")

# -------------------------------------------------
# MAIN
# -------------------------------------------------

if __name__ == "__main__":

    run_experiment()

    save_round_metrics()

    plot_efficiency()

    plot_scalability()

    print_runtime()

    print("\nGenerated files:")
    print("round_metrics.csv")
    print("fig7a_computation_efficiency.png")
    print("fig7b_communication_efficiency.png")
    print("fig7c_message_efficiency.png")
    print("fig8a_latency_scalability.png")
    print("fig8b_throughput_scalability.png")