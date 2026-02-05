"""
Circuit Breaker Pattern for handling external service failures gracefully.
Prevents cascading failures and allows system recovery.
"""
import time
import logging
from enum import Enum
from typing import Callable, Any, Optional
from dataclasses import dataclass
from threading import Lock

class CircuitState(Enum):
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing - reject requests
    HALF_OPEN = "half_open"  # Testing if service recovered

@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker."""
    failure_threshold: int = 5      # Failures before opening circuit
    recovery_timeout: float = 30.0  # Seconds to wait before half-open
    success_threshold: int = 2      # Successes needed to close circuit
    timeout: float = 10.0           # Request timeout

class CircuitBreaker:
    """
    Circuit Breaker implementation.
    
    States:
    - CLOSED: Normal operation, requests pass through
    - OPEN: Too many failures, requests are rejected immediately
    - HALF_OPEN: Testing if service recovered, limited requests allowed
    """
    
    def __init__(self, name: str, config: CircuitBreakerConfig = None):
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = 0
        self.lock = Lock()
    
    def _should_allow_request(self) -> bool:
        """Determine if request should be allowed based on circuit state."""
        with self.lock:
            if self.state == CircuitState.CLOSED:
                return True
            
            if self.state == CircuitState.OPEN:
                # Check if recovery timeout has passed
                if time.time() - self.last_failure_time >= self.config.recovery_timeout:
                    self.state = CircuitState.HALF_OPEN
                    self.success_count = 0
                    logging.info(f"[CIRCUIT] {self.name}: OPEN -> HALF_OPEN (testing recovery)")
                    return True
                return False
            
            if self.state == CircuitState.HALF_OPEN:
                return True
            
            return False
    
    def record_success(self):
        """Record a successful request."""
        with self.lock:
            self.failure_count = 0
            
            if self.state == CircuitState.HALF_OPEN:
                self.success_count += 1
                if self.success_count >= self.config.success_threshold:
                    self.state = CircuitState.CLOSED
                    logging.info(f"[CIRCUIT] {self.name}: HALF_OPEN -> CLOSED (recovered)")
    
    def record_failure(self):
        """Record a failed request."""
        with self.lock:
            self.failure_count += 1
            self.last_failure_time = time.time()
            
            if self.state == CircuitState.HALF_OPEN:
                # Single failure in half-open means we're not recovered
                self.state = CircuitState.OPEN
                logging.warning(f"[CIRCUIT] {self.name}: HALF_OPEN -> OPEN (still failing)")
            
            elif self.state == CircuitState.CLOSED:
                if self.failure_count >= self.config.failure_threshold:
                    self.state = CircuitState.OPEN
                    logging.warning(f"[CIRCUIT] {self.name}: CLOSED -> OPEN (threshold reached)")
    
    def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute a function through the circuit breaker.
        
        Raises:
            CircuitOpenError: If circuit is open
            Original exception: If function fails
        """
        if not self._should_allow_request():
            raise CircuitOpenError(f"Circuit {self.name} is OPEN")
        
        try:
            result = func(*args, **kwargs)
            self.record_success()
            return result
        except Exception as e:
            self.record_failure()
            raise
    
    def get_state(self) -> dict:
        """Get current circuit breaker state."""
        return {
            'name': self.name,
            'state': self.state.value,
            'failure_count': self.failure_count,
            'success_count': self.success_count,
            'last_failure': self.last_failure_time
        }
    
    def reset(self):
        """Manually reset circuit breaker to closed state."""
        with self.lock:
            self.state = CircuitState.CLOSED
            self.failure_count = 0
            self.success_count = 0
            logging.info(f"[CIRCUIT] {self.name}: Manual reset to CLOSED")

class CircuitOpenError(Exception):
    """Raised when circuit breaker is open."""
    pass

# ============================================================
# PRE-CONFIGURED CIRCUIT BREAKERS
# ============================================================

# DuckDuckGo search circuit breaker
ddg_circuit = CircuitBreaker(
    name="duckduckgo",
    config=CircuitBreakerConfig(
        failure_threshold=5,
        recovery_timeout=60.0,  # Wait 1 minute before retry
        success_threshold=2
    )
)

# General HTTP requests circuit breaker
http_circuit = CircuitBreaker(
    name="http_requests",
    config=CircuitBreakerConfig(
        failure_threshold=10,
        recovery_timeout=30.0,
        success_threshold=3
    )
)

def get_all_circuit_states() -> list:
    """Get states of all circuit breakers."""
    return [
        ddg_circuit.get_state(),
        http_circuit.get_state()
    ]

def reset_all_circuits():
    """Reset all circuit breakers."""
    ddg_circuit.reset()
    http_circuit.reset()
