import sys
import ctypes

class Tee(object):
    def __init__(self, input_handle, output_handle):
        self.input = input_handle
        self.output = output_handle

    def readline(self):
        result = self.input.readline()
        self.output.write(result)

        return result


if __name__ == '__main__':
    if not sys.stdin.isatty():
        sys.stdin = Tee(input_handle=sys.stdin, output_handle=sys.stdout)

ctypes.windll.user32.MessageBoxW(0, "Your text", "Your title", 0)

# with open("test.txt", 'w') as f:
#     print('Foo1,', file=f, end='')
#     print('Foo2,', file=f, end='\n')
#     print('Foo3', file=f)

# input('Type something: ')
# input('Type something else: ')
