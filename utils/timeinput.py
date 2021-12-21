class TimeInput(object):

    # TODO: Proper operator overload to compare times
    def __init__(self, time_inp: str):
        assert len(time_inp.split(":")) == 2, "time must be in format '23:59'"
        hr, minute = map(int, time_inp.split(":"))

