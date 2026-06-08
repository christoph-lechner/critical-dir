"""
If there is no need to precisely diagnose if "no data at all" or just "insufficient amount of data", the user can just catch EInsufficientData.
"""
class EInsufficientData(Exception):
    """
    Exception is raised when there is insufficient data to perform requested data analysis.
    """
    def __init__(self,message:str):
        self.message = message
        super().__init__(self.message)

    def __str__(self):
        return f'insufficient data to perform operation, msg={self.message}'

class ENoData(EInsufficientData):
    """
    Exception is raised when there is no data to perform requested data analysis. Possible reasons could be incorrect time range or poor combination of filter settings.
    """
    def __init__(self,message:str):
        self.message = message
        super().__init__(self.message)

    def __str__(self):
        return f'no data to perform operation, msg={self.message}'
