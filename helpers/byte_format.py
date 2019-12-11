# adapted from https://stackoverflow.com/questions/1094841/reusable-library-to-get-human-readable-version-of-file-size#1094933


# def sizeof_fmt(num, suffix='B'):
#     for unit in ['', 'Ki', 'Mi', 'Gi', 'Ti', 'Pi', 'Ei', 'Zi']:
#         if abs(num) < 1024.0:
#             return "%3.1f%s%s" % (num, unit, suffix)
#         num /= 1024.0
#     return "%.1f%s%s" % (num, 'Yi', suffix)


def format_bytes(num, binary=False):
    def _format_bytes(_num, factor, byte_suffix='', binary_indicator=''):
        mod = 0
        for unit in ['', 'K', 'M', 'G', 'T', 'P', 'E', 'Z']:
            if abs(_num) < factor:
                num_formatted = f'{_num:3.0f}' if mod == 0 else f'{_num:3.1f}'
                return f'{num_formatted}' \
                       f'{unit}' \
                       f'{"" if _num == num else binary_indicator}{byte_suffix}'
            mod = _num % factor
            _num /= factor
        return f'{_num:.1f}Y{binary_indicator}'

    if binary:
        return _format_bytes(num, 1024.0, 'B', 'i')
    else:
        return _format_bytes(num, 1000.0)


if __name__ == '__main__':
    for (i, num1, numb) in [(i, i * 1000, i * 1024) for i in range(0, 1000000, 1000)]:
        print(f'({i} * 1000) {num1}: {format_bytes(num1)}, {format_bytes(num1, True)}')
        print(f'({i} * 1024) {numb}: {format_bytes(numb)}, {format_bytes(numb, True)}')
