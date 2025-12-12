import simpy
import networkx as nx

from simcore import Sim, PolicyEntry


def build_topology():
    G = nx.DiGraph()

    # GPUs: multiple QPs + RR quantum
    G.add_node("GPU0", type="gpu", num_qps=2, quantum_packets=1, tx_proc_delay=0.0, gpu_store_delay=0.0)
    G.add_node("GPU1", type="gpu", num_qps=2, quantum_packets=1, tx_proc_delay=0.0, gpu_store_delay=0.0)
    G.add_node("GPU2", type="gpu", num_qps=2, quantum_packets=1, tx_proc_delay=0.0, gpu_store_delay=0.0)
    G.add_node("GPU3", type="gpu", num_qps=2, quantum_packets=1, tx_proc_delay=0.0, gpu_store_delay=0.0)

    # Switches: store-and-forward
    G.add_node("SW1", type="switch", sw_proc_delay=0.0)
    G.add_node("SW2", type="switch", sw_proc_delay=0.0)

    # Directed links
    edges = [
        ("GPU0", "SW1"), ("SW1", "GPU1"),
        ("GPU1", "SW2"), ("SW2", "GPU2"),
        ("GPU1", "SW2"), ("SW2", "GPU3"),
    ]
    for u, v in edges:
        G.add_edge(u, v, link_rate_bps=100e9, prop_delay=0.0)

    return G


def main():
    env = simpy.Environment()
    topo = build_topology()

    sim = Sim(env, topo,
        packet_size_bytes=1024,
        header_size_bytes=0)

    MB = 1024 * 1024
    chunk_size = 64 * MB

    policy = [
        # chunk 0: GPU0 -> GPU1, line-rate
        # [chunkid, src, dst, QPid, rate, chunksize, path]
        PolicyEntry(0, "GPU0", "GPU1", 0, "Max", chunk_size, ["GPU0", "SW1", "GPU1"]),
        # fan-out after GPU1 fully receives chunk 0:
        PolicyEntry(0, "GPU1", "GPU2", 0, "Max",  chunk_size, ["GPU1", "SW2", "GPU2"]),
        PolicyEntry(0, "GPU1", "GPU3", 0, "Max",  chunk_size, ["GPU1", "SW2", "GPU3"]),
        PolicyEntry(1, "GPU0", "GPU1", 0, "Max", chunk_size, ["GPU0", "SW1", "GPU1"]),
    ]

    sim.load_policy(policy)
    sim.start()
    sim.run()

    print("=== Chunk ready times ===")
    for (chunk_id, node_id), t in sorted(sim.chunk_ready_time.items(), key=lambda x: x[1]):
        print(f"chunk={chunk_id} ready_at {node_id}: {t*1e3:.3f} ms")

    print("\n=== TX completion times ===")
    for tx_id, t in sorted(sim.tx_complete_time.items(), key=lambda x: (x[0][0], x[0][1], x[0][2])):
        print(f"tx={tx_id} complete: {t*1e3:.3f} ms")

    makespan = max(sim.tx_complete_time.values())
    print(f"\nMakespan = {makespan*1e3:.3f} ms")


if __name__ == "__main__":
    main()
