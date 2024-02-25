# TESLA Workflow

## Usage

```bash
dgcli workflow tesla run tesla.yml --s3_prefix s3/tesla-demo --debug --max_iters 1
```

## Configuration Example

```yaml
executors:
  ikkem-hpc:
    hpc:
      url: "ssh://user@ip-or-host:port"
      base_dir: /public/home/whxu/tmp/dflow-galaxy
      key_file: /home/henry/.ssh/id_ed25519
      slurm: {}

    apps:
      python:
        resource:
          queue: small_s
        setup_script: |
          module load anaconda/2022.5
          source activate base
      deepmd:
        resource:
          queue: GPU_s
          nodes: 1
          cpu_per_node: 4
          gpu_per_node: 1
        setup_script: |
          module load anaconda/2022.5
          source activate /public/groups/ai4ec/libs/conda/deepmd/2.2.9/gpu
      lammps:
        resource:
          queue: small_s
          nodes: 1
          cpu_per_node: 4
          gpu_per_node: 0
        setup_script: |
          module load anaconda/2022.5
          source activate /public/groups/ai4ec/libs/conda/deepmd/2.2.9/gpu
      cp2k:
        resource:
          queue: small_s
          nodes: 1
          cpu_per_node: 32
          gpu_per_node: 0
        setup_script: |
          module load gcc/9.3 intel/2020.2
          module load cp2k/2022.1-intel-2020
          export CP2K_DATA_DIR=/public/software/cp2k-2022.1-intel/cp2k-2022.1/data
        cp2k_cmd: mpirun cp2k.psmp

  cheng-hpc:
    hpc:
      url: "ssh://user@ip-or-host:port"
      base_dir: /data/home/whxu/tmp/dflow-galaxy
      key_file: /home/henry/.ssh/id_ed25519
      slurm: {}

    apps:
      python:
        resource:
          queue: c51-small
        setup_script: |
          module load miniconda/3
          source activate py39

      deepmd:
        resource:
          queue: c52-large
          nodes: 1
          cpu_per_node: 4
          gpu_per_node: 0
        setup_script: |
          module load miniconda/3
          source activate /data/share/apps/deepmd/2.2.7-cpu
          export OMP_NUM_THREADS=1

orchestration:
  deepmd: ikkem-hpc
  lammps: ikkem-hpc
  model_devi: ikkem-hpc
  cp2k: ikkem-hpc

datasets:
  dpdata-h2o:
    url: ./water/train

  sys-h2o:
    url: ./water/explore
    includes: 'POSCAR*'

workflow:
  general:
    type_map: [H, O]
    mass_map: [1.008, 15.999]

  train:
    deepmd:
      input_template: !load_yaml deepmd_input.json
      init_dataset: [dpdata-h2o]

  explore:
    lammps:
      systems: [sys-h2o]
      nsteps: 1000
      product_vars:
        PRES: [1, 2]
      broadcast_vars:
        TEMP: [220, 330, 440]
      template_vars:
        POST_INIT: |
          neighbor 1.0 bin
          box      tilt large
        POST_READ_DATA:
          change_box all triclinic
      ensemble: nvt

  screen:
    model_devi:
      decent_range: [0.1, 0.5]

  label:
    cp2k:
      input_template: !load_text cp2k.inp
      limit: 1

  update:
    until_iter: 2
    patch:
      explore:
        lammps:
          nsteps: 2000

```