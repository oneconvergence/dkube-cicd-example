# dkube-cicd-example

Example project showing how to use DKube CICD in your project. To use CICD in your project repository, create .dkube-ci.yml.

# Build project docker image using conda environment file
```
conda_env:                        
  path: conda_env.yaml
```
# Build project docker image using Dockerfile
```
Dockerfile: <path to Dockerfile>
```
# Register existing docker images with DKube
```
docker_envs: 
  - <registry>/<prefix>/<image>:TAG
  - <registry>/<prefix>/<image>@sha256:<digest>
```

# Build other docker images
```
images:
  path: images
  images:
    - name: my-image1
    - name: my-image2
      base_image: python:alpine
 ```
  
# Build kubeflow component and pipeline
```
components: # defaults to all components if list is empty
  path: kubeflow/components
  components:
    - name: my_add
    - name: my_divide
      base_image: python:alpine #Used when Dockerfile is missing
      
pipelines:
  path: kubeflow/pipelines
  pipelines:
    - name: workflow1.py
 ```
 # Add dkube jobs template or run jobs
```
jobs: # 
  path: jobs
  jobs:
    - name: train.yaml #jobs/train.yaml contains job configuration
      run: true # run the job. 
 ```
