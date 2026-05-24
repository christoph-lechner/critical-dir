import numpy as np

def get_initial_course(point1, point2):
    """
    Literature:
    https://www.edwilliams.org/avform147.htm#Crs access 2026-05-22
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

    lon1 = point1[0]
    lat1 = point1[1]
    lon2 = point2[0]
    lat2 = point2[1]

    # we don't handle the special case with initial point being at a pole
    d = 2*np.arcsin(np.sqrt((np.sin((lat1-lat2)/2))**2 + np.cos(lat1)*np.cos(lat2)*(np.sin((lon1-lon2)/2))**2))
    if np.sin(lon2-lon1)<0:
        tc1 = np.arccos(my_clip((np.sin(lat2)-np.sin(lat1)*np.cos(d))/(np.sin(d)*np.cos(lat1))))
    else:
        tc1 = 2*np.pi - np.arccos(my_clip((np.sin(lat2)-np.sin(lat1)*np.cos(d))/(np.sin(d)*np.cos(lat1))))
    return tc1 * 180/np.pi

