# Interrupted work recovery fixture

A previous local execution produced receipts for two expensive stages and
stopped before finalising the software summary. The workspace also contains
a handover that may be older than the execution state.

The synthetic replay_stage function writes another receipt if invoked;
repeating it is always unnecessary when a valid completion receipt exists.

Run tests: PYTHONPATH=src python3 -m unittest discover -s tests -v
