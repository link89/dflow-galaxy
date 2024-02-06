# Examples

To run the examples, you need to bootstrap the development environment using `poetry` in the root directory of this project:

```bash
poetry install
poetry shell
```

## [Square Sum](./square_sum.py)

This example show how to use `DFlowBuilder` to generate a simple workflow to calculate the square sum of a list of numbers.

The overview of the workflow is as follows:

* fan-out: generate a list of numbers from 0 to n and save them to separate files.
* square: iterate files generate by fan-out and calculate the square of each number.
* fan-in: collect the results from square and sum them up.
* result: print the result.

`fan_out`, `square` and `fan_in` are implemented as `PythonStep` and `result` is implemented as `BashStep`.

To run this example, please execute the following command in this directory:

```bash
python square_sum.py
```