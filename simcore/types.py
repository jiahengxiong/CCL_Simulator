from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional, Tuple, Union

RateInput = Union[float, int, str]


@dataclass(frozen=True)
class PolicyEntry:
    """One policy rule:
      [chunk_id, src, dst, qpid, rate, chunk_size_bytes, path_nodes]
    """
    chunk_id: Union[int, str]
    src: str
    dst: str
    qpid: int
    rate: RateInput        # number (bps) or "Max"
    chunk_size_bytes: int
    path: List[str]
    time: float = 0.0  # earliest trigger time (seconds)

    def normalized_rate(self) -> tuple[float, bool]:
        if isinstance(self.rate, str):
            if self.rate.strip().lower() == "max":
                return 0.0, True
            raise ValueError(f"Invalid rate string: {self.rate!r}. Use number (bps) or 'Max'.")
        r = float(self.rate)
        if r <= 0:
            raise ValueError("rate must be > 0, or 'Max'")
        return r, False

    def validate(self) -> None:
        if not self.path or self.path[0] != self.src or self.path[-1] != self.dst:
            raise ValueError(f"Path must start at src and end at dst for entry chunk={self.chunk_id}: {self.path}")
        if self.chunk_size_bytes <= 0:
            raise ValueError("chunk_size_bytes must be > 0")
        if self.qpid < 0:
            raise ValueError("qpid must be >= 0")


TxId = Tuple[Union[int, str], str, str]  # (chunk_id, src, dst)


@dataclass(slots=True)
class Packet:
    # Transmission identity
    tx_id: TxId
    chunk_id: Union[int, str]
    tx_src: str
    tx_dst: str

    # Packet sequencing
    seq: int
    total_packets: int

    # Size
    size_bytes: int

    # Routing
    path: List[str]
    hop_idx: int  # index of current node in path

    # Scheduling
    qpid: int
    rate_bps: float
    use_max_rate: bool

    created_time: float = 0.0

    def next_hop(self) -> Optional[str]:
        if self.hop_idx + 1 >= len(self.path):
            return None
        return self.path[self.hop_idx + 1]

    def advance(self) -> None:
        self.hop_idx += 1

    @property
    def bits(self) -> int:
        return self.size_bytes * 8
