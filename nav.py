import numpy as np

def get_nav(point1, point2):
    """
    point1 is starting coordinates

    Literature:
    https://www.edwilliams.org/avform147.htm#Crs access 2026-05-22

    Sign conventions used in this source:
    "For the convenience of North Americans I will take North latitudes and West longitudes as positive and South and East negative. The longitude is the opposite of the usual mathematical convention. True course is defined as usual, as the angle between the course line and the local meridian measured clockwise."
    """
    def my_clip(x):
        eps = 1e-12
        if x>=-1.0 and x<=1.0:
            return x
        if x>1:
            if x<1+eps:
                return 1.0
        if x<-1:
            if x>(-1-eps):
                return -1.0
        raise ValueError(f'value outside of range [-1-eps; 1+eps] (eps={eps})')

    lon1 = -np.radians(point1[0]) # Sign convention: see note above
    lat1 =  np.radians(point1[1])
    lon2 = -np.radians(point2[0]) # Sign convention: see note above
    lat2 =  np.radians(point2[1])

    # we don't handle the special case with initial point being at a pole
    eps = 1e-12
    if np.cos(lat1)<eps:
        raise ValueError('not implemented: starting points at the pole')

    d = 2*np.arcsin(np.sqrt((np.sin((lat1-lat2)/2))**2 + np.cos(lat1)*np.cos(lat2)*(np.sin((lon1-lon2)/2))**2))
    if np.sin(lon2-lon1)<=0: # in reference the condition is "sin<0", changed it to "<=" so that N course returns 0 deg and not 360 deg.
        tc1 = np.arccos(my_clip((np.sin(lat2)-np.sin(lat1)*np.cos(d))/(np.sin(d)*np.cos(lat1))))
    else:
        tc1 = 2*np.pi - np.arccos(my_clip((np.sin(lat2)-np.sin(lat1)*np.cos(d))/(np.sin(d)*np.cos(lat1))))
    return (np.degrees(tc1), d)

def get_initial_course(point1, point2):
    course,dist = get_nav(point1,point2)
    return course

def get_dist_radians(point1, point2):
    course,dist = get_nav(point1,point2)
    return dist
