"""Demo: circuit breaker trips on repeated failures, half-opens after timeout, recovers."""
import time
from framework.breaker import CircuitBreaker, CircuitOpen


def flaky_downstream(fail_times):
    """Return a fake downstream that fails the first `fail_times` calls, then succeeds."""
    calls = {"n": 0}
    def _call():
        calls["n"] += 1
        if calls["n"] <= fail_times:
            raise ConnectionError("downstream down")
        return "ok"
    return _call


def main():
    print("--- Case 1: closed, calls pass through ---")
    cb = CircuitBreaker(fail_threshold=3, reset_timeout=1.0)
    for i in range(3):
        try:
            print(f"  call {i+1}: {cb.call(flaky_downstream(0))}")
        except Exception as e:
            print(f"  call {i+1}: error {e}")
    print(f"  state: {cb.state}")

    print("\n--- Case 2: 3 failures -> circuit opens, calls fail fast ---")
    cb2 = CircuitBreaker(fail_threshold=3, reset_timeout=1.0)
    bad = flaky_downstream(99)
    for i in range(5):
        try:
            print(f"  call {i+1}: {cb2.call(bad)}")
        except CircuitOpen as e:
            print(f"  call {i+1}: CIRCUIT OPEN ({e.waited:.1f}s)")
        except Exception as e:
            print(f"  call {i+1}: error {e}")
    print(f"  state: {cb2.state}")

    print("\n--- Case 3: wait reset_timeout -> half-open probe -> success -> closed ---")
    time.sleep(1.1)
    try:
        print(f"  probe call: {cb2.call(flaky_downstream(0))}")
    except Exception as e:
        print(f"  probe call: error {e}")
    print(f"  state after probe: {cb2.state}")

    print("\n--- Case 4: half-open probe fails -> back to open ---")
    cb3 = CircuitBreaker(fail_threshold=2, reset_timeout=0.5)
    bad2 = flaky_downstream(99)
    for i in range(4):
        try:
            cb3.call(bad2)
        except CircuitOpen as e:
            print(f"  call {i+1}: open ({e.waited:.1f}s)")
        except Exception:
            print(f"  call {i+1}: downstream error")
    time.sleep(0.6)
    try:
        cb3.call(bad2)
    except CircuitOpen:
        print(f"  probe: open (blocked)")
    except Exception:
        print(f"  probe: downstream error -> back to open")
    print(f"  state: {cb3.state}")

    print("\n== all cases done ==")


if __name__ == "__main__":
    main()
