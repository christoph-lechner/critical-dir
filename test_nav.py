import numpy as np
from nav import get_initial_course

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

def test_helpers(capsys):
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
    my_pos = [10, 53.5] # Hamburg, Germany
    get_initial_course(my_pos, np.add(my_pos,[0, 0.1]))

def test_nav_dirs(capsys):
    # on the equator: going East
    assert angle_comp(get_initial_course([0,0], [10,0]), 90.0)
    # on the equator: going West
    assert angle_comp(get_initial_course([0,0], [-10,0]), 270.0)
    # going North
    assert angle_comp(get_initial_course([0,0], [0,10]), 0.0)
    # going South
    assert angle_comp(get_initial_course([0,0], [0,-10]), 180.0)

    my_pos = [10, 53.5] # Hamburg, Germany

    assert angle_comp(get_initial_course(my_pos, np.add(my_pos,[0, 0.01])), 0.0)
    assert angle_comp(get_initial_course(my_pos, np.add(my_pos,[0,-0.01])), 180.0)
    # small positional variations (note that the larger the East/West movements, the larger the deviation from 90/270 deg -> https://en.wikipedia.org/wiki/Great-circle_navigation )
    assert angle_comp(get_initial_course(my_pos, np.add(my_pos,[ 0.01,0])), 90.0, max_dev=0.1)
    assert angle_comp(get_initial_course(my_pos, np.add(my_pos,[-0.01,0])), 270.0, max_dev=0.1)

    # worked example: LAX to JFK (remember that ref https://www.edwilliams.org/avform147.htm uses flipped sign conventions for long.)
    assert angle_comp(get_initial_course([-(118+24/60), 33+57/60], [-(73+47/60), 40+38/60]), 65.9, max_dev=0.1)

