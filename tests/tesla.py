from dflow_galaxy.workflow.tesla.domain import deepmd
from dflow_galaxy.core.util import ensure_str


import unittest


class TestTesla(unittest.TestCase):
    def test_deepmd_train(self):
        step = deepmd.RunDeepmdTrainingFn(
            config=deepmd.DeepmdConfig(),
            concurrency=1,
            dp_cmd='dp',
        )
        bash_script = step(deepmd.RunDeepmdTrainingArgs(
            task_index=0,
            task_dir='task_dir',
            output_dir='output_dir',
        ))
        print(ensure_str(bash_script))




if __name__ == '__main__':
    unittest.main()