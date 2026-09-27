from app.presentation.api.rate_limit import SlidingWindowRateLimiter


class FakeClock:
    def __init__(self, t: float = 0.0) -> None:
        self.t = t

    def __call__(self) -> float:
        return self.t


def test_allows_up_to_the_limit_then_blocks():
    clock = FakeClock()
    limiter = SlidingWindowRateLimiter(3, 60, clock=clock)
    results = [limiter.check("a")[0] for _ in range(4)]
    assert results == [True, True, True, False]


def test_remaining_counts_down():
    clock = FakeClock()
    limiter = SlidingWindowRateLimiter(3, 60, clock=clock)
    remainings = [limiter.check("a")[1] for _ in range(3)]
    assert remainings == [2, 1, 0]


def test_retry_after_reflects_oldest_hit_expiring():
    clock = FakeClock()
    limiter = SlidingWindowRateLimiter(1, 60, clock=clock)
    limiter.check("a")
    clock.t = 20
    allowed, _, retry_after = limiter.check("a")
    assert not allowed and retry_after == 40


def test_window_slides_and_recovers():
    clock = FakeClock()
    limiter = SlidingWindowRateLimiter(2, 10, clock=clock)
    limiter.check("a"); limiter.check("a")
    assert limiter.check("a")[0] is False
    clock.t = 11
    assert limiter.check("a")[0] is True


def test_keys_are_independent():
    clock = FakeClock()
    limiter = SlidingWindowRateLimiter(1, 60, clock=clock)
    assert limiter.check("a")[0] is True
    assert limiter.check("b")[0] is True
    assert limiter.check("a")[0] is False


def test_blocked_attempt_does_not_extend_the_window():
    """A caller retrying immediately after a 429 must not push its own limit further out."""
    clock = FakeClock()
    limiter = SlidingWindowRateLimiter(1, 60, clock=clock)
    limiter.check("a")
    clock.t = 30
    limiter.check("a")   # blocked, must not count as a new hit
    clock.t = 61
    assert limiter.check("a")[0] is True
