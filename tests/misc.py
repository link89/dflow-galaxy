import unittest

class TestMisc(unittest.TestCase):

    def test_callable_object_and_function(self):
        import inspect

        class C:
            def __call__(self, a: int, b: str) -> None:
                pass
        c1 = C()

        sig1 = inspect.signature(c1)

        def c2(a: int, b: str) -> None:
            pass

        sig2 = inspect.signature(c2)

        self.assertEqual(sig1, sig2)


if __name__ == '__main__':
    unittest.main()
