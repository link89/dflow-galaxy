from dataclasses import dataclass
import unittest

from dflow_galaxy.core import dflow


class TestLib(unittest.TestCase):

    def test_pickle_form(self):
        import cloudpickle as cp
        import bz2
        import base64

        @dataclass
        class Foo:
            x: int

        def foo(x):
            return x

        Foo_pkl = dflow.pickle_converts(Foo)
        r = eval(Foo_pkl)(1)
        self.assertIsInstance(r, Foo)
        self.assertEqual(r.x, 1)

        foo_pkl = dflow.pickle_converts(foo)
        r = eval(foo_pkl)(1)
        self.assertEqual(r, 1)

    def test_valid_python_step_input(self):
        @dataclass(frozen=True)
        class Foo:
            x: dflow.InputParam[int]
            y: dflow.InputArtifact
            z: dflow.OutputArtifact
        foo = Foo(1, '2', '3')
        list(dflow.iter_python_step_args(foo))

    def test_invalid_python_step_input(self):
        @dataclass(frozen=True)
        class Foo:
            x: dflow.InputParam[int]
            y: dflow.InputArtifact
            z: dflow.OutputArtifact
            e: int

        @dataclass(frozen=True)
        class Bar:
            x: dflow.InputParam[int]
            y: dflow.InputArtifact
            z: dflow.OutputArtifact
            e: dflow.OutputParam[int]

        with self.assertRaises(AssertionError):
            list(dflow.iter_python_step_args(Foo(1, '2', '3', 4)))

        with self.assertRaises(AssertionError):
            list(dflow.iter_python_step_args(Bar(1, '2', '3', 4)))

    def test_valid_python_step_output(self):
        @dataclass
        class Foo:
            x: dflow.OutputParam[int]
        foo = Foo(1)
        list(dflow.iter_python_step_return(foo))

    def test_invalid_python_step_output(self):
        @dataclass
        class Foo:
            x: dflow.OutputParam[int]
            y: int
        with self.assertRaises(AssertionError):
            list(dflow.iter_python_step_return(Foo(1, 2)))

    def test_convert_to_argo_script(self):
        @dataclass(frozen=True)
        class FooInput:
            x: dflow.InputParam[int]
            y: dflow.InputArtifact
            z: dflow.OutputArtifact
        @dataclass
        class FooOutput:
            x: dflow.OutputParam[int]

        def foo(input: FooInput) -> FooOutput:
            return FooOutput(input.x)

        ret = dflow.python_build_template(foo, base_dir='/tmp/dflow-galaxy')
        print(ret.source)
        print(ret.fn_str)



if __name__ == '__main__':
    unittest.main()
