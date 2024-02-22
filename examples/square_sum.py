import sys
import os
import glob
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))


from dataclasses import dataclass
from dflow_galaxy.core import dflow, types, dispatcher
from dflow_galaxy.core.util import ensure_dirname, ensure_dir


def main():

    @dataclass(frozen=True)
    class FanOutArgs:
        num: types.InputParam[int]
        output_dir: types.OutputArtifact

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
        input_dir : types.InputArtifact
        output_dir: types.OutputArtifact

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
        input_dir : types.InputArtifact
        result_file: types.OutputArtifact

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
        result_file: types.InputArtifact

    def show(args: ShowArgs) -> str:
        return f"cat {args.result_file}"

    extra_kwargs = {}

    # run on HPC
    use_hpc = False
    if use_hpc:
        # HPC configuration
        hpc_config = dispatcher.HpcConfig(
            url='ssh://whxu@ai4ec-hpc',
            base_dir='/data/home/whxu/tmp/dflow-galaxy',
            slurm=dispatcher.HpcConfig.SlurmConfig(),
        )
        resource = dispatcher.Resource(
            queue='c52-small',
            sub_path='./square-sum',
            nodes=1,
            cpu_per_node=1,
        )
        executor = dispatcher.create_hpc_dispatcher(hpc_config, resource)
        extra_kwargs['default_executor'] = executor

    # build and run workflow
    dflow_builder = dflow.DFlowBuilder('square-sum', s3_prefix='s3/square-sum',
                                       debug=True, **extra_kwargs)

    fan_out_step = dflow_builder.make_python_step(fan_out)(FanOutArgs(num=10,
                                                                      output_dir='s3://./fanout'))
    square_step = dflow_builder.make_python_step(square)(SquareArgs(input_dir=fan_out_step.args.output_dir,
                                                                    output_dir='s3://./square'))
    fan_in_step = dflow_builder.make_python_step(fan_in)(FanInArgs(input_dir=square_step.args.output_dir,
                                                                   result_file='s3://./result.txt'))
    show_step = dflow_builder.make_bash_step(show)(ShowArgs(result_file=fan_in_step.args.result_file))

    dflow_builder.add_step(fan_out_step)
    dflow_builder.add_step(square_step)
    dflow_builder.add_step(fan_in_step)
    dflow_builder.add_step(show_step)

    dflow_builder.run()

main()
