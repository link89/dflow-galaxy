import unittest
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



if __name__ == '__main__':
    unittest.main()
