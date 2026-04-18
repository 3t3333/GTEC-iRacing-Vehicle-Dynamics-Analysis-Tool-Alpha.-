import sys
import builtins
import opendav

class MockInput:
    def __init__(self, responses):
        self.responses = responses
        self.idx = 0
    def __call__(self, prompt):
        if self.idx < len(self.responses):
            resp = self.responses[self.idx]
            self.idx += 1
            return resp
        return 'q'

# 1 -> Single File
# 0 -> Select lap.ibt
# 9 -> Setup Prediction Engine (Wait, what is 9? Let's check opendav.py options)
builtins.input = MockInput(['1', '0', '7', 'q', 'q'])

try:
    opendav.main()
except SystemExit:
    pass
