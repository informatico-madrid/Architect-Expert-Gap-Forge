class CircuitBreaker:
    def __init__(self, threshold: float = 0.2, batch_size: int = 10, consecutive_pass_threshold: int = 10):
        self.threshold = threshold
        self.batch_size = batch_size
        self.consecutive_pass_threshold = consecutive_pass_threshold
        self._results: list[bool] = []
        self._phase: str = "warmup"
        self._consecutive_passes: int = 0
        self._triggered: bool = False

    @property
    def phase(self) -> str:
        return self._phase

    @property
    def triggered(self) -> bool:
        return self._triggered

    def record_result(self, passed: bool) -> None:
        self._results.append(passed)
        if passed:
            self._consecutive_passes += 1
        else:
            self._consecutive_passes = 0
        self._transition_phase()

    def _transition_phase(self) -> None:
        n = len(self._results)
        if n < 5:
            self._phase = "warmup"
        elif n < 20:
            self._phase = "calibration"
        else:
            self._phase = "production"

    def should_switch(self) -> bool:
        if self._phase != "production":
            return False
        if len(self._results) < self.batch_size:
            return False
        # Check last batch_size results
        recent = self._results[-self.batch_size:]
        failures = sum(1 for r in recent if not r)
        failure_rate = failures / len(recent)
        if failure_rate >= self.threshold:
            self._triggered = True
            return True
        return False

    def try_reset(self) -> bool:
        if not self._triggered:
            return False
        if self._consecutive_passes >= self.consecutive_pass_threshold:
            self._triggered = False
            self._results.clear()
            self._consecutive_passes = 0
            self._phase = "warmup"
            return True
        return False

    def get_failure_rate(self) -> float:
        if not self._results:
            return 0.0
        return sum(1 for r in self._results if not r) / len(self._results)
