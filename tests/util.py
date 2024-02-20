import subprocess as sp
import unittest
import tempfile
import shlex
import os
from dflow_galaxy.core import util

class TestUtil(unittest.TestCase):

    def test_select_chunk(self):
        in_list = list(range(5))

        self.assertEqual(util.select_chunk(in_list, 1, 0), in_list)
        with self.assertRaises(AssertionError):
            util.select_chunk(in_list, 1, 1)

        self.assertEqual(util.select_chunk(in_list, 2, 0), [0, 1, 2])
        self.assertEqual(util.select_chunk(in_list, 2, 1), [3, 4])

        self.assertEqual(util.select_chunk(in_list, 5, 0), [0])
        self.assertEqual(util.select_chunk(in_list, 5, 4), [4])

        self.assertEqual(util.select_chunk(in_list, 6, 0), [0])
        self.assertEqual(util.select_chunk(in_list, 6, 5), [])


    def test_bash_iter_ls_slice(self):
        # use a temporary directory to avoid side effects
        with tempfile.TemporaryDirectory() as tempdir:
            script = '\n'.join([
                f'cd {tempdir}',
                f'mkdir -p {" ".join([str(i) for i in range(5)])}',
                util.bash_iter_ls_slice(search_pattern='*/', n=2, i=0, opt='-d',
                                        script='echo "$ITEM"'),
            ])
            result = sp.check_output(f'bash -c {shlex.quote(script)}', shell=True)
            self.assertEqual(result.decode('utf-8').strip(), '\n'.join(['0/', '1/']))


if __name__ == '__main__':
    unittest.main()
