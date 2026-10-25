"""Smallest checks that fail if the scheduler logic breaks. Run: python test_cropclock.py"""
import numpy as np

from cropclock import FEEDER_KWH_PER_H, HOURS_PER_DAY, MAX_ON, SUN_HOURS, plan_day

rad = np.zeros(24)
rad[7:18] = [100, 300, 500, 700, 850, 900, 850, 700, 500, 300, 100]

# 8 feeders all wanting a full day: cap, 8 h limit, stressed first, sun first.
on = plan_day([1e9] * 8, rad, priority=list(range(8)))
per_hour = np.bincount([h for hrs in on for h in hrs], minlength=24)
assert per_hour.max() <= MAX_ON
assert all(len(hrs) == HOURS_PER_DAY for hrs in on)
assert set(on[7]) <= set(SUN_HOURS) and 12 in on[7]      # most stressed gets noon
assert any(h not in SUN_HOURS for h in on[0])             # least stressed spills to night

# A feeder that needs nothing gets no hours; a small need gets just enough.
on = plan_day([0, 1.5 * FEEDER_KWH_PER_H], rad, priority=[0, 1])
assert on[0] == [] and on[1] == [12, 11]
print("ok")
