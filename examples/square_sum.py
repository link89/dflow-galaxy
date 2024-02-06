import sys
import os
import glob
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))


from dataclasses import dataclass
from dflow_galaxy.core import dflow
from dflow_galaxy.core.util import ensure_dirname, ensure_dir


def main():

    @dataclass(frozen=True)
    class FanOutArgs:
        num: dflow.InputParam[int]
        output_dir: dflow.OutputArtifact

    def fan_out(args: FanOutArgs):
        """
        Generate files with numbers from 0 to input.num and write to output_dir
        """
        ensure_dir(args.output_dir)
        for i in range(args.num):
            out_file = f'{args.output_dir}/file_{i}.txt'
            with open(out_file, 'w') as f:
                f.write(str(i))


    @dataclass(frozen=True)
    class SquareArgs:
        input_dir : dflow.InputArtifact
        output_dir: dflow.OutputArtifact

    def square(args: SquareArgs):
        """
        Read files from input_dir, square the number and write to output_dir
        """
        ensure_dir(args.output_dir)
        for file in glob.glob(f'{args.input_dir}/*'):
            with open(file, 'r') as f:
                num = int(f.read())
            out_file = f'{args.output_dir}/{os.path.basename(file)}'
            with open(out_file, 'w') as f:
                f.write(str(num*num))

    @dataclass(frozen=True)
    class FanInArgs:
        input_dir : dflow.InputArtifact
        result_file: dflow.OutputArtifact

    def fan_in(args: FanInArgs):
        """
        Read files from input_dir, sum the numbers and print the total
        """
        total = 0
        for file in glob.glob(f'{args.input_dir}/*'):
            with open(file, 'r') as f:
                total += int(f.read())
        print(args.result_file)
        ensure_dirname(args.result_file)
        with open(args.result_file, 'w') as f:
            f.write(str(total))

    @dataclass(frozen=True)
    class ShowArgs:
        result_file: dflow.InputArtifact

    def show(args: ShowArgs) -> str:
        return f"cat {args.result_file}"


    # build and run workflow
    dflow_builder = dflow.DFlowBuilder('square-sum', s3_prefix='s3/square-sum', debug=True)

    fan_out_step = dflow_builder.make_python_step(fan_out)(FanOutArgs(num=10,
                                                                      output_dir='s3:///fanout'))
    square_step = dflow_builder.make_python_step(square)(SquareArgs(input_dir=fan_out_step.args.output_dir,
                                                                    output_dir='s3:///square'))
    fan_in_step = dflow_builder.make_python_step(fan_in)(FanInArgs(input_dir=square_step.args.output_dir,
                                                                   result_file='s3:///result.txt'))
    show_step = dflow_builder.make_bash_step(show)(ShowArgs(result_file=fan_in_step.args.result_file))

    dflow_builder.add_step(fan_out_step)
    dflow_builder.add_step(square_step)
    dflow_builder.add_step(fan_in_step)
    dflow_builder.add_step(show_step)

    dflow_builder.run()

main()
