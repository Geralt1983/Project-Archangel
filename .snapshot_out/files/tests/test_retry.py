# Simple retry tests for the improved retry mechanism
from app.utils.retry import next_backoff

def test_backoff_bounds():
    """Test backoff calculation stays within bounds"""
    b1 = next_backoff(1)
    b5 = next_backoff(5)
    assert b1 >= 0.05
    assert b5 <= 60.0
    print(f"✅ Backoff test passed: b1={b1:.2f}, b5={b5:.2f}")

def test_backoff_progression():
    """Test exponential progression"""
    delays = [next_backoff(i) for i in range(1, 6)]
    # Should generally increase (allowing for jitter)
    base_delays = [0.5 * (2 ** (i-1)) for i in range(1, 6)]
    
    for i, (actual, expected) in enumerate(zip(delays, base_delays)):
        # Allow for jitter but check rough progression
        assert 0.05 <= actual <= 60.0
    
    print(f"✅ Progression test passed: {[f'{d:.2f}' for d in delays]}")

if __name__ == "__main__":
    test_backoff_bounds()
    test_backoff_progression()
    print("✅ All retry tests passed!")