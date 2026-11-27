from stream_merge import Record, reconcile


class Probe:
    def __init__(self):
        self.reads = 0
        self.comparisons = 0


class Key:
    def __init__(self, text, probe):
        self.text = text
        self.probe = probe

    def __hash__(self):
        return hash(self.text)

    def __eq__(self, other):
        self.probe.comparisons += 1
        return isinstance(other, Key) and self.text == other.text


class Row(Record):
    def __getattribute__(self, name):
        if name == "record_id":
            object.__getattribute__(self, "record_id").probe.reads += 1
        return super().__getattribute__(name)


def make(key, qty, source, probe):
    return Row(Key(key, probe), qty, source)


def check_budget(probe, total):
    assert probe.reads <= 5 * total, f"quadratic record-ID reads: {probe.reads}"
    assert probe.comparisons <= 5 * total, f"quadratic equality work: {probe.comparisons}"


def test_replacement_and_append_preserve_order_with_linear_probe_budget():
    probe = Probe()
    old = [make(f"k{i}", i, "old", probe) for i in range(120)]
    updates = [make(f"k{i}", 1000 + i, "new", probe) for i in range(60, 180)]
    before = list(old)
    result = reconcile(old, iter(updates))
    check_budget(probe, len(old) + len(updates))
    assert result[:60] == old[:60]
    assert result[60:120] == updates[:60]
    assert result[120:] == updates[60:]
    assert old == before
    assert type(result) is list


def test_duplicate_existing_and_repeated_updates_keep_first_position():
    probe = Probe()
    old = [make(f"id{i}", i, "old", probe) for i in range(130)]
    old.insert(6, make("id5", -1, "duplicate", probe))
    updates = [make(f"id{i % 75}", i, "update", probe) for i in range(100)]
    result = reconcile(old, updates)
    check_budget(probe, len(old) + len(updates))
    assert result[5] is updates[80]
    assert result[6] is old[6]
    assert len(result) == len(old)
