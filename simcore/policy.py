from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Tuple, Union, Iterable, Set

import simpy

from .types import PolicyEntry, Packet, TxId


@dataclass(frozen=True)
class PolicySpec:
    packet_size_bytes: int = 1500
    header_size_bytes: int = 0


class PolicyEngine:
    """Policy-driven injection.

    Installs rules keyed by (chunk_id, src).
    When (src, chunk_id) becomes ready, fire all rules at that src immediately.
    """

    def __init__(self, env: simpy.Environment, sim: "Sim", spec: PolicySpec):
        self.env = env
        self.sim = sim
        self.spec = spec

        self.rules: Dict[Tuple[Union[int, str], str], List[PolicyEntry]] = {}
        self._fired: Set[Tuple[Union[int, str], str]] = set()  # (chunk_id, src)

    def install(self, entries: Iterable[PolicyEntry]) -> None:
        for e in entries:
            e.validate()
            key = (e.chunk_id, e.src)
            self.rules.setdefault(key, []).append(e)

    def infer_initial_sources(self) -> Dict[Union[int, str], List[str]]:
        by_chunk_src: Dict[Union[int, str], set[str]] = {}
        by_chunk_dst: Dict[Union[int, str], set[str]] = {}

        for (chunk_id, src), lst in self.rules.items():
            by_chunk_src.setdefault(chunk_id, set()).add(src)
            for e in lst:
                by_chunk_dst.setdefault(chunk_id, set()).add(e.dst)

        initial: Dict[Union[int, str], List[str]] = {}
        for chunk_id, srcs in by_chunk_src.items():
            dsts = by_chunk_dst.get(chunk_id, set())
            init = sorted(list(srcs - dsts))
            if not init:
                init = sorted(list(srcs))
            initial[chunk_id] = init
        return initial

    def bootstrap(self) -> None:
        initial = self.infer_initial_sources()
        for chunk_id, srcs in initial.items():
            for s in srcs:
                node = self.sim.nodes[s]
                if node.cfg.node_type != "gpu":
                    raise ValueError(f"Initial source {s} for chunk {chunk_id} must be a GPU")
                node.mark_initial_chunk(chunk_id)
                self.on_chunk_ready(s, chunk_id)

    def on_chunk_ready(self, node_id: str, chunk_id: Union[int, str]) -> None:
        key = (chunk_id, node_id)
        if key in self._fired:
            return
        self._fired.add(key)

        for e in self.rules.get(key, []):
            self._fire_entry(e)

    def _fire_entry(self, e: PolicyEntry) -> None:
        rate_bps, use_max_rate = e.normalized_rate()

        ps = int(self.spec.packet_size_bytes)
        total_packets = (e.chunk_size_bytes + ps - 1) // ps
        total_packets = max(1, total_packets)

        tx_id: TxId = (e.chunk_id, e.src, e.dst)
        self.sim.register_tx(tx_id)

        for i in range(total_packets):
            remaining = e.chunk_size_bytes - i * ps
            sz = ps if remaining >= ps else remaining
            if sz <= 0:
                sz = ps

            pkt = Packet(
                tx_id=tx_id,
                chunk_id=e.chunk_id,
                tx_src=e.src,
                tx_dst=e.dst,
                seq=i,
                total_packets=total_packets,
                size_bytes=sz,
                path=list(e.path),
                hop_idx=0,
                qpid=int(e.qpid),
                rate_bps=float(rate_bps),
                use_max_rate=bool(use_max_rate),
                created_time=self.env.now,
            )
            self.sim.send_from_src(pkt)
