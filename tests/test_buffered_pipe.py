import server


def test_overall():
    sink_result = []

    def sink(*args):
        sink_result.append(args)

    bp = server.BufferedPipe(5, sink)
    for i in range(7):
        bp.append(bytes(i))
    assert sink_result == [(5, b'01234')]
    assert bp.payload == b'56'
