# 开发笔记

记录 DPGEN/DPGEN2 重构过程中的设计思路。 

该文档不是完整的设计文档，只对一些关键设计决策进行记录。

## 概述

DFlow 基于 Argo Workflow 实现，属于确定性的声明式工作流。
不同于一般指令式的工作流，声明式工作流在设计时需要提前考虑好空间的划分，
否则当需要执行 all-reduce 操作时会产生困难。

## 设计

### 数据空间

DPGEN 工作流包含4个阶段的迭代: label, train, explore, select。 
这里需要注意到，label 产生的数据需要与历史数据合并做为 train 的输入，除此之外其它步骤都只依赖于上一步的输出。
虽然以迭代划分数据更符合直觉，以REST风格进行资源划分会更有利于数据访问。
规划如下：

```
{s3_prefix}/state.json  # 全局状态
{s3_prefix}/config/iter/{iter_id}/config.json  # 配置
{s3_prefix}/dataset/deepmd/iter/{iter_id}  # 训练数据集

# deepmd 任务数据
{s3_prefix}/train/deepmd/iter/{iter_id}/job/{job_id}/in
{s3_prefix}/train/deepmd/iter/{iter_id}/job/{job_id}/out
{s3_prefix}/train/deepmd/iter/{iter_id}/job/{job_id}/log

# cp2k 任务数据
{s3_prefix}/label/cp2k/iter/{iter_id}/job/{job_id}/in
{s3_prefix}/label/cp2k/iter/{iter_id}/job/{job_id}/out
{s3_prefix}/label/cp2k/iter/{iter_id}/job/{job_id}/log

# lammps 任务数据
{s3_prefix}/explore/lammps/iter/{iter_id}/job/{job_id}/in
{s3_prefix}/explore/lammps/iter/{iter_id}/job/{job_id}/out
{s3_prefix}/explore/lammps/iter/{iter_id}/job/{job_id}/log

# model_devi 任务数据
{s3_prefix}/select/model_devi/iter/{iter_id}/job/{job_id}/in
{s3_prefix}/select/model_devi/iter/{iter_id}/job/{job_id}/out
{s3_prefix}/select/model_devi/iter/{iter_id}/job/{job_id}/log
```
统一规范化的命令方式也将有利于后续添加对不同软件的支持。

其它由 DFlowBuilder 自动生成的文件内部文件，统一位于
```
{s3_prefix}/.dflow_builder
{s3_prefix}/.dflow_builder/python/pkg/{pkg_name}
{s3_prefix}/.dflow_builder/python/fn/{hash}.py
```

### 代码设计

#### 基本结构
声明式工作流的数据流是以副作用的形式体现的，即通过对输入数据的修改来实现数据的流动。
因此每一个 DFlow 的基本工作单元可以设计为一个只有单一输入且无输出的纯函数。

使用 dataclass 作为输入的数据结构以便于静态类型检查和重构。

另外，由于 Python 表达层次化数据结构的能力较弱，
因此入参采用扁平化的设计方式.

利用 Python 的 Annotated 类型以区分 input/output 和 param/artifact.

并且为了避免产生意料之外的更改，除 output_params 之外的所有参数都应该标注为 Final 类型.

命名上建议采用 `in_p_*`, `in_a_*`, `out_p_*`, `out_a_*` 的方式以示区分.

#### 约定管理
由于 DFlow 是基于约定的设计，因此需要采用一个中心化的方式对约定进行管理。

#### 跳过管理
在每个 all_reduce 阶段，输出一个标志位以指示下一个步骤是否需要执行，使用 when 条件来跳过步骤。
