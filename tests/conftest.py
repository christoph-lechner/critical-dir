from pathlib import Path

def pytest_ignore_collect(collection_path, config):
    """
    return value True results in resource being ignored.
    """

    testroot = Path(__file__).parent

    # per default, ignore these paths
    if collection_path.is_relative_to(testroot/'docker'):
        for arg in config.args:
            if 'docker' in Path(arg).parts:
                return False
        return True
    if collection_path.is_relative_to(testroot/'docker-ing'):
        for arg in config.args:
            if 'docker-ing' in Path(arg).parts:
                return False
        return True

    return False
