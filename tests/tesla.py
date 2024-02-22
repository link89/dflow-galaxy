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
            init_dataset='init-dataset',
            iter_index=0,
            work_dir='task_dir',
            persist_dir='output_dir',
        ))
        print(ensure_str(bash_script))




if __name__ == '__main__':
    unittest.main()