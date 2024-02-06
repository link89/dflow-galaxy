# 开发备忘录

记录 DPGEN/DPGEN2 重构过程中的设计思路。 
该文档不是完整的设计文档，只对一些关键设计决策进行记录。

## DFlowBuilder 

DFlow 基于 Argo Workflow 实现，属于声明式工作流, 这个特性决定了它更适合使用 side-effect 进行数据传递，而不是基于输入/输出。
在进行工作流设计时务必需要考虑到这一点。

Argo 最核心的不足是无法表达 Artifact 集合的概念，因此无法直接实现 fan-in/fan-out 操作。
规避这一缺点的方法是对于需要 fan-in/fan-out 的步骤在文件输出/输入时使用公共前缀和相同的层次结构。

Argo Workflow 的另一个大问题是把 OutputArtifact 做为 Output 的一部分, 
但实际上 OutputArtifact 与 InputArtifact 本质上都属于side-effect, 应该做为 Context 的一部分并用作函数的入参。

把 OutputArtifact 做为入参可能会违反不少人的直觉，但实际上这才是正确的设计。不理解的人可以思考下文件操作的语义，
文件是一种side-effect, 因此任何函数都不可能return一个文件。
对一个文件进行操作都需要把文件指针做为入参。唯一的差别是该文件是可读(InputArtifact)，还是可写而已(OutputArtifact)。

DFlow 的 PythonOP 在设计时没有规避Argo的设计缺陷，导致了很多不必要的麻烦。在重新设计时要考虑到这一点。

有关于 Argo 无法支持 Artifact 集合的不足，目前正在与社区沟向 S3Artifact 添加一个 `includes` 字段，

> https://github.com/argoproj/argo-workflows/issues/12588#issuecomment-1927701403

该功能将能取代目前 Slice 中不必要的复杂设计.
在该功能就位之前，可以通过分组 prefix 来实现类似的功能。



为了解决上述问题，我将创建一个 DFlowBuilder 对 dflow 模块进行隔离，该模块将提供一种更符合直觉的方式来构建工作流。

DFlowBuilder 将是一个类型友好的 DFlow 封装，它将提供类型安全的 Python 和 bash 脚本构建工具。
该封装将只使用 dflow ScriptOpTemplate 以最小化对 dflow 的依赖。


### 代码设计
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

既然借助 Annotated, 那么区分 in_params 与 ctx 也就没有必要了，因此可以简化为
```python
def operator(args: Args) -> Result:
    ...
```
其中 Args = InputParams + InputArtifact + OutputArtifact, Result = OutputParams


## DPGEN 工作流重构


### 数据空间

工作流的数据传递必需由工作流开发者显示地进行空间规划，而不是依赖于工作流引擎的自动推断，核心原因在于 Argo Workflow 无法表达 Artifact 集合的概念。

DPGEN 工作流包含4个阶段的迭代: label, train, explore, select。 
这里需要注意到，label 产生的数据需要与历史数据合并做为 train 的输入，除此之外其它步骤都只依赖于上一步的输出。
虽然以迭代划分数据更符合直觉，但以REST风格进行资源划分会更有利于数据访问。
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


#### 约定管理
由于 DFlow 是基于约定的设计，因此需要采用一个中心化的方式对约定进行管理。

#### 跳过管理
在每个 all_reduce 阶段，输出一个标志位以指示下一个步骤是否需要执行，使用 when 条件来跳过步骤。
