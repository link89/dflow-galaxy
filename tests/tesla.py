from dflow_galaxy.workflow.tesla.domain import deepmd, model_devi
from dflow_galaxy.core.util import ensure_str
from dflow_galaxy.core.dispatcher import Resource


import unittest


class TestTesla(unittest.TestCase):
    def test_deepmd_train(self):
        res = Resource()
        deepmd_app = deepmd.DeepmdApp(resource=res)
        step = deepmd.RunDeepmdTrainingFn(
            config=deepmd.DeepmdConfig(),
            context=deepmd_app,
        )
        bash_script = step(deepmd.RunDeepmdTrainingArgs(
            slice_idx='{{item}}',
            init_dataset_dir='init-dataset',
            iter_dataset_dir='iter-dataset',
            work_dir='task_dir',
            persist_dir='output_dir',
        ))
        print(ensure_str(bash_script))


    def test_get_lammpstraj_frame_no(self):
        self.assertEqual(model_devi.get_lammpstrj_frame_no('100.lammpstraj'), 100)





if __name__ == '__main__':
    unittest.main()