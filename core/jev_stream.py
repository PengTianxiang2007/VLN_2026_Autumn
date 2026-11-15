"""Prefix-invariant streaming prominence and causal node sampling."""
import math


def offline_streaming_prominence(values, window_size, max_delay):
    count = len(values)
    sigma = max(0.5, window_size / 6.0)
    past_radius = max(1, int(math.ceil(3 * sigma)))
    smoothed = [None] * count
    for index in range(count):
        total, weight = 0.0, 0.0
        end = min(count - 1, index + max_delay)
        for other in range(max(0, index - past_radius), end + 1):
            value = values[other]
            if value is None:
                continue
            distance = other - index
            current_weight = math.exp(
                -(distance * distance) / (2 * sigma * sigma)
            )
            total += value * current_weight
            weight += current_weight
        if weight > 0:
            smoothed[index] = total / weight
    positive = [None] * count
    baseline_window = 2 * window_size + 1
    for index in range(count):
        if smoothed[index] is None:
            continue
        samples = [
            value for value in smoothed[
                max(0, index - baseline_window + 1):index + 1
            ]
            if value is not None
        ]
        if samples:
            positive[index] = max(
                0.0, smoothed[index] - sum(samples) / len(samples)
            )
    out = [None] * count
    history = []
    for index, value in enumerate(positive):
        if value is None:
            continue
        history.append(value)
        history.sort()
        p95 = history[
            min(len(history) - 1, int(math.floor(0.95 * len(history))))
        ]
        out[index] = min(1.0, value / p95) if p95 > 0 else 0.0
    return out


def offline_nodes(series, window_size):
    high_threshold = 0.6
    low_threshold = 0.18
    plateau_threshold = 0.45
    min_distance = 3
    plateau_interval = 5
    plateau_minimum = 3
    warmup = max(7, window_size)
    peaks = []
    for index in range(warmup, len(series) - 2):
        value = series[index]
        if value is None or value < low_threshold:
            continue
        look = 1 if value >= high_threshold else 2
        neighbours = [
            series[other]
            for other in range(
                max(0, index - look),
                min(len(series), index + look + 1),
            )
            if other != index and series[other] is not None
        ]
        if any(value < other for other in neighbours):
            continue
        left = [
            item for item in series[
                max(0, index - min_distance):index + 1
            ]
            if item is not None
        ]
        right = [
            item for item in series[
                index:min(len(series), index + min_distance + 1)
            ]
            if item is not None
        ]
        if not left or not right:
            continue
        if min(value - min(left), value - min(right)) >= 0.03:
            peaks.append({'index': index, 'value': value, 'kind': 'peak'})
    regions = []
    current = []
    for index, value in enumerate(series):
        if value is not None and value >= plateau_threshold:
            current.append(index)
        elif current:
            regions.append(current)
            current = []
    if current:
        regions.append(current)
    plateau = []
    for region in regions:
        if len(region) < plateau_minimum:
            continue
        for offset in range(plateau_interval // 2, len(region), plateau_interval):
            index = region[offset]
            plateau.append({
                'index': index,
                'value': series[index],
                'kind': 'plateau',
            })
    candidates = sorted(
        peaks + plateau,
        key=lambda item: (-item['value'], item['index']),
    )
    nodes = []
    for candidate in candidates:
        if all(
            abs(node['index'] - candidate['index']) >= min_distance
            for node in nodes
        ):
            nodes.append(candidate)
    return sorted(nodes, key=lambda item: item['index'])


class OnlineProminence:
    """Freeze prominence at i+D and never revise an emitted node."""

    def __init__(self, window_size=11, max_delay=5):
        if window_size < 3 or window_size % 2 == 0:
            raise ValueError('Window must be an odd integer >= 3')
        if max_delay < 0 or max_delay > 5:
            raise ValueError('Maximum delay must be between 0 and 5')
        self.window_size = window_size
        self.max_delay = max_delay
        self.raw = []
        self.final = []
        self.smoothed = []
        self.positive = []
        self.out = []
        self.history = []
        self.next_freeze = 0
        self.stream_finished = False
        self.nodes = []
        self.plateau_start = None
        self.max_node_lag = 0

    def add_pending(self):
        self.raw.append(None)
        self.final.append(False)
        self.smoothed.append(None)
        self.positive.append(None)
        self.out.append(None)

    def resolve(self, index, value):
        if not 0 <= index < len(self.raw):
            raise IndexError(index)
        if self.final[index]:
            raise ValueError('JEV stream value resolved twice')
        self.raw[index] = value
        self.final[index] = True
        self._freeze_ready()

    def finish(self):
        if not all(self.final):
            raise ValueError('Cannot finish with unresolved JEV stream values')
        self.stream_finished = True
        self._freeze_ready()
        if self.next_freeze != len(self.raw):
            raise ValueError('Online prominence did not freeze every frame')
        return self.nodes

    def _freeze_ready(self):
        count = len(self.raw)
        while self.next_freeze < count:
            index = self.next_freeze
            needed_end = min(count - 1, index + self.max_delay)
            if not self.stream_finished and not all(
                self.final[position]
                for position in range(needed_end + 1)
            ):
                break
            sigma = max(0.5, self.window_size / 6.0)
            past_radius = max(1, int(math.ceil(3 * sigma)))
            total, weight = 0.0, 0.0
            for other in range(max(0, index - past_radius), needed_end + 1):
                value = self.raw[other]
                if value is None:
                    continue
                distance = other - index
                current_weight = math.exp(
                    -(distance * distance) / (2 * sigma * sigma)
                )
                total += value * current_weight
                weight += current_weight
            if weight <= 0:
                raise ValueError('No resolved values in prominence window')
            smoothed = total / weight
            self.smoothed[index] = smoothed
            baseline_window = 2 * self.window_size + 1
            samples = [
                value for value in self.smoothed[
                    max(0, index - baseline_window + 1):index + 1
                ]
                if value is not None
            ]
            positive = max(0.0, smoothed - sum(samples) / len(samples))
            self.positive[index] = positive
            self.history.append(positive)
            self.history.sort()
            p95 = self.history[
                min(
                    len(self.history) - 1,
                    int(math.floor(0.95 * len(self.history))),
                )
            ]
            value = min(1.0, positive / p95) if p95 > 0 else 0.0
            self.out[index] = value
            self._emit_available_candidates(index)
            self.next_freeze += 1

    def _raw_neighbours(self, index, look):
        result = []
        for other in range(
            max(0, index - look), min(len(self.raw), index + look + 1)
        ):
            if other != index:
                result.append((other, self.raw[other]))
        return result

    def _add_node(self, index, kind, available_at):
        if any(abs(node['index'] - index) < 3 for node in self.nodes):
            return
        self.nodes.append({
            'index': index,
            'value': self.out[index],
            'kind': kind,
            'available_at_stream_index': available_at,
            'lag_steps': available_at - index,
        })
        self.max_node_lag = max(self.max_node_lag, available_at - index)

    def _emit_available_candidates(self, available_at):
        index = available_at
        value = self.out[index]
        if value is None:
            return
        warmup = max(7, self.window_size)
        if index >= warmup and value >= 0.18:
            look = 1 if value >= 0.6 else 2
            neighbours = self._raw_neighbours(index, look)
            if neighbours and all(item is not None for _, item in neighbours):
                if all(value >= item for _, item in neighbours):
                    left = [
                        self.raw[other]
                        for other in range(max(0, index - 3), index + 1)
                        if self.raw[other] is not None
                    ]
                    right = [
                        self.raw[other]
                        for other in range(index, min(len(self.raw), index + 4))
                        if self.raw[other] is not None
                    ]
                    if (
                        left
                        and right
                        and min(value - min(left), value - min(right)) >= 0.03
                    ):
                        self._add_node(index, 'peak', available_at)
        if value >= 0.45:
            if self.plateau_start is None:
                self.plateau_start = index
            offset = index - self.plateau_start
            if offset >= 2 and (offset - 2) % 5 == 0:
                self._add_node(index, 'plateau', available_at)
        else:
            self.plateau_start = None
