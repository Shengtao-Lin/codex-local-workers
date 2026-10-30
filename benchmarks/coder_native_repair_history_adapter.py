"""Correlate actual VALIDATE repair feedback without changing its contents."""

import coder_native_history_adapter as history


def install(worker, packet):
    history.install(worker, packet, repair_history=True)


if __name__ == "__main__":
    history.block.native.install = install
    raise SystemExit(history.block.native.main())
