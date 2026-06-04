import numpy as np
from critical_dir.nav import get_initial_course,get_dist_radians

"""
Helper function and related testing
"""
def angle_comp(angle1, angle2, max_dev=1e-3):
    """
    Angles in degrees
    """
    delta = angle2-angle1
    delta = np.mod(delta, 360.0)
    if np.abs(delta)<=max_dev:
        return True
    if np.abs(delta-360.0)<=max_dev:
        return True
    return False

def test_helpers():
    assert angle_comp(10,10, max_dev=1)
    assert angle_comp(0,359.9, max_dev=1)
    assert angle_comp(12,10, max_dev=1)==False


"""
******************
*** MAIN TESTS ***
******************
"""
def test_nav():
    """
    Just a simple test: verifies that the function can run and doesn't raise exceptions
    """
    my_pos = [10, 53.55] # Hamburg, Germany
    get_initial_course(my_pos, np.add(my_pos,[0, 0.1]))

def test_nav_dirs(capsys):
    # on the equator: going East
    assert angle_comp(get_initial_course([0,0], [0,10]), 90.0)
    # on the equator: going West
    assert angle_comp(get_initial_course([0,0], [0,-10]), 270.0)
    # going North
    assert angle_comp(get_initial_course([0,0], [10,0]), 0.0)
    # going South
    assert angle_comp(get_initial_course([0,0], [-10,0]), 180.0)

    my_pos = [10, 53.55] # Hamburg, Germany

    assert angle_comp(get_initial_course(my_pos, np.add(my_pos,[ 0.01,0])), 0.0)
    assert angle_comp(get_initial_course(my_pos, np.add(my_pos,[-0.01,0])), 180.0)
    # small positional variations (note that the larger the East/West movements, the larger the deviation from 90/270 deg -> https://en.wikipedia.org/wiki/Great-circle_navigation )
    assert angle_comp(get_initial_course(my_pos, np.add(my_pos,[0, 0.01])), 90.0, max_dev=0.1)
    assert angle_comp(get_initial_course(my_pos, np.add(my_pos,[0,-0.01])), 270.0, max_dev=0.1)

    # Worked example:
    # LAX to JFK (remember that ref https://www.edwilliams.org/avform147.htm uses flipped sign conventions for long.)
    # 65.9 deg, great circle angle 0.623585 rad
    lax=[33+57/60, -(118+24/60)]
    jfk=[40+38/60, -(73+47/60)]
    assert angle_comp(get_initial_course(lax, jfk), 65.9, max_dev=0.1)
    assert np.abs(get_dist_radians(lax, jfk) - 0.623585)<2e-6


def test_nav_dist():
    dist_rad = get_dist_radians([0,0], [0,90])
    assert np.abs(dist_rad - np.pi/2)<1e-6
