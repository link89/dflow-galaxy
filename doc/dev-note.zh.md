# 开发笔记

记录 DPGEN/DPGEN2 重构过程中的设计思路。 

该文档不是完整的设计文档，只对一些关键设计决策进行记录。

## 分析

DFlow 基于 Argo Workflow 实现，属于声明式工作流。
DFlow 最核心的不足是无法表达 Artifact 集合的概念，因此无法直接实现 fan-in/fan-out 操作。
规避这一缺点的方法是对于需要 fan-in/fan-out 的步骤在文件输出/输入时使用公共前缀和相同的层次结构。

Argo Workflow 的另一个大问题是把 OutputArtifact 做为 Output 的一部分, 
但实际上 OutputArtifact 与 InputArtifact 本质上都属于副作用的范畴, 应该做为 Context 的一部分并用作函数的入参。


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
{s3_prefix}/.dflow
{s3_prefix}/.dflow/python/pkg/{pkg_name}
{s3_prefix}/.dflow/python/fn/{hash}.py
```

### 代码设计

#### 基本结构
Argo Workflow 包含 parameter 和 artifact 两种输入类型。
其中 parameter 即一般数据， 作用相当于纯函数的输入输出，
artifact 则用于表示文件副作用，相当于 ctx。

因此为与之对应，一个基本的设计单元应该具备如下形式
```python
def operator(in_params, ctx) -> out_params:
    ...
```
其中 ctx 包含所有的 input artifact 和 output artifact,
in_params 和 out_params 分别对应于 input parameter 和 output parameter.

上述3种数据类型均采用 dataclass 表达，且 in_params 和 out_params 均为 frozen=True。
使用元编程进行argo 配置生成可借助 Annotated 实现。

#### 约定管理
由于 DFlow 是基于约定的设计，因此需要采用一个中心化的方式对约定进行管理。

#### 跳过管理
在每个 all_reduce 阶段，输出一个标志位以指示下一个步骤是否需要执行，使用 when 条件来跳过步骤。
