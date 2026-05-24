from nav import get_initial_course

def test_nav():
    """
    Just a simple test: verifies that the function can run and doesn't raise exceptions
    """
    my_pos = [10, 53.5] # Hamburg, Germany
    get_initial_course(my_pos, [10.0, 53.6])

def test_nav_dirs():
    # TODO: understand sign conventions for returned course angle (or what is the role of point1/2, which one is the starting point and which one the destination point)
    print(get_initial_course([10.0, 53.5], [10.0, 53.6]))
    print(get_initial_course([10.0, 53.5], [10.0, 53.4]))
    print(get_initial_course([10.0, 53.5], [10.1, 53.5]))
    print(get_initial_course([10.0, 53.5], [9.9, 53.5]))

