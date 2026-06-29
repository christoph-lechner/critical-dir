import os

def test_demo(capsys):
    # very first "test" -> check that we see the data file
    with capsys.disabled():
        os.system('ls -l /stor')
