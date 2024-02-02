from dataclasses import dataclass
import unittest

import dflow_galaxy.core.lib as dg_lib


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

        Foo_pkl = dg_lib.pickle_converts(Foo)
        r = eval(Foo_pkl)(1)
        self.assertIsInstance(r, Foo)
        self.assertEqual(r.x, 1)

        foo_pkl = dg_lib.pickle_converts(foo)
        r = eval(foo_pkl)(1)
        self.assertEqual(r, 1)

    def test_valid_python_step_input(self):
        @dataclass(frozen=True)
        class Foo:
            x: dg_lib.InputParam[int]
            y: dg_lib.InputArtifact
            z: dg_lib.OutputArtifact
        foo = Foo(1, '2', '3')
        list(dg_lib.iter_python_step_input(foo))

    def test_invalid_python_step_input(self):
        @dataclass(frozen=True)
        class Foo:
            x: dg_lib.InputParam[int]
            y: dg_lib.InputArtifact
            z: dg_lib.OutputArtifact
            e: int

        @dataclass(frozen=True)
        class Bar:
            x: dg_lib.InputParam[int]
            y: dg_lib.InputArtifact
            z: dg_lib.OutputArtifact
            e: dg_lib.OutputParam[int]

        with self.assertRaises(AssertionError):
            list(dg_lib.iter_python_step_input(Foo(1, '2', '3', 4)))

        with self.assertRaises(AssertionError):
            list(dg_lib.iter_python_step_input(Bar(1, '2', '3', 4)))

    def test_valid_python_step_output(self):
        @dataclass
        class Foo:
            x: dg_lib.OutputParam[int]
        foo = Foo(1)
        list(dg_lib.iter_python_step_output(foo))

    def test_invalid_python_step_output(self):
        @dataclass
        class Foo:
            x: dg_lib.OutputParam[int]
            y: int
        with self.assertRaises(AssertionError):
            list(dg_lib.iter_python_step_output(Foo(1, 2)))

    def test_convert_to_argo_script(self):
        @dataclass(frozen=True)
        class FooInput:
            x: dg_lib.InputParam[int]
            y: dg_lib.InputArtifact
            z: dg_lib.OutputArtifact
        @dataclass
        class FooOutput:
            x: dg_lib.OutputParam[int]

        def foo(input: FooInput) -> FooOutput:
            return FooOutput(input.x)

        ret = dg_lib.build_python_step(foo, base_path='/tmp/dflow-galaxy')
        print(ret.source)
        print(ret.script)



if __name__ == '__main__':
    unittest.main()
