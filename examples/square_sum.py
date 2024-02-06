import sys
import os
import glob
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))


from dataclasses import dataclass
from dflow_galaxy.core import dflow
from dflow_galaxy.core.util import ensure_dirname, ensure_dir


def main():

    @dataclass(frozen=True)
    class FanOutInput:
        num: dflow.InputParam[int]
        output_dir: dflow.OutputArtifact

    def fanout(input: FanOutInput):
        """
        Generate files with numbers from 0 to input.num and write to output_dir
        """
        for i in range(input.num):
            out_file = f'{input.output_dir}/file_{i}.txt'
            ensure_dirname(out_file)
            with open(out_file, 'w') as f:
                f.write(str(i))


    @dataclass(frozen=True)
    class SquareInput:
        input_dir : dflow.InputArtifact
        output_dir: dflow.OutputArtifact

    def square(input: SquareInput):
        """
        Read files from input_dir, square the number and write to output_dir
        """
        ensure_dir(input.output_dir)
        for file in glob.glob(f'{input.input_dir}/*'):
            with open(file, 'r') as f:
                num = int(f.read())
            out_file = f'{input.output_dir}/{os.path.basename(file)}'
            with open(out_file, 'w') as f:
                f.write(str(num*num))

    @dataclass(frozen=True)
    class SumInput:
        input_dir : dflow.InputArtifact

    def sum(input: SumInput):
        """
        Read files from input_dir, sum the numbers and print the total
        """
        import glob
        total = 0
        for file in glob.glob(f'{input.input_dir}/*'):
            with open(file, 'r') as f:
                total += int(f.read())
        print(f'Total: {total}')

    # build and run workflow
    dflow_builder = dflow.DFlowBuilder('square-sum', s3_prefix='s3/square-sum', debug=True)
    fanout_step = dflow_builder.make_python_step(fanout)(FanOutInput(num=10,
                                                                     output_dir='s3:///fanout'))
    square_step = dflow_builder.make_python_step(square)(SquareInput(input_dir=fanout_step.inputs.output_dir,
                                                                     output_dir='s3:///square'))
    sum_step = dflow_builder.make_python_step(sum)(SumInput(square_step.inputs.output_dir))

    dflow_builder.add_step(fanout_step)
    dflow_builder.add_step(square_step)
    dflow_builder.add_step(sum_step)

    dflow_builder.run()

main()

