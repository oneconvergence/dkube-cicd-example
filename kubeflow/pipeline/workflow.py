# Copyright 2019 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Pipeline workflow definition."""
import kfp.dsl as dsl
from kfp import components
from kfp.components._yaml_utils import load_yaml
from kfp.components._yaml_utils import dump_yaml
from kubernetes import client as k8s_client
import json
import os
from dkube.sdk import *

setup_component = '''
name: create_dkube_resource
description: |
    creates dkube resources required for pipeline.
metadata:
  annotations: {platform: 'Dkube'}
  labels: {stage: 'create_dkube_resource', logger: 'dkubepl', wfid: '{{workflow.uid}}', runid: '{{pod.name}}'}
inputs:
  - {name: token,      type: String,   optional: false,
    description: 'Required. Dkube authentication token.'}
  - {name: user,      type: String,   optional: false,
    description: 'Required. Dkube Logged in User name.'}
  - {name: project_id,      type: String,   optional: false,
    description: 'Required. Dkube Project name.'}
implementation:
  container:
    image: docker.io/ocdr/dkube-examples-setup:cli-reg-2
    command: ['python3', 'regressionsetup.py']
    args: [
      --auth_token, {inputValue: token},
      --user, {inputValue: user},
      --project_id, {inputValue: project_id}
    ]
'''

# Get the project ID passed from JupyterLab creation
project_id = os.environ.get("DKUBE_PROJECT_ID", "")
print("project id")
# Check to see if this is blank, and if so use "clinical-reg"
if not project_id:
    print("inside project id")
    project_name = "clinical-reg"
    DKUBE_URL = "https://dkube-proxy.dkube:443"
    DKUBE_TOKEN = os.getenv("DKUBE_USER_ACCESS_TOKEN", "")
    print(DKUBE_TOKEN)
    api = DkubeApi(URL=DKUBE_URL,token=DKUBE_TOKEN)

    # If "clinical-reg" already exists, just get the project ID
    try:
        project = DkubeProject(project_name)
        res = api.create_project(project)
    except Exception as e:
        if e.reason.lower()=="conflict":
            print(f"Project \"{project_name}\" already exists")
            project_id = api.get_project_id(project_name)
            print(project_id)

def _component(stage, name):
    with open('kubeflow/components/{}/component.yaml'.format(stage), 'rb') as stream:
        cdict = load_yaml(stream)
        cdict['name'] = name
        cyaml = dump_yaml(cdict)
        return components.load_component_from_text(cyaml)
        
setup_op = components.load_component(text = setup_component)

@dsl.pipeline(
    name='dkube-regression-pl',
    description='sample regression pipeline with dkube components'
)

def d3pipeline(
    user,
    auth_token,
    tags,
    project_id=project_id,
    #Clinical preprocess
    clinical_preprocess_script="python clinical_reg/cli-pre-processing.py",
    clinical_preprocess_datasets=json.dumps(["clinical"]),
    clinical_preprocess_input_mounts=json.dumps(["/opt/dkube/input"]),
    clinical_preprocess_outputs=json.dumps(["clinical-preprocessed"]),
    clinical_preprocess_output_mounts=json.dumps(["/opt/dkube/output"]),
    
    #Image preprocess
    image_preprocess_script="python clinical_reg/img-pre-processing.py",
    image_preprocess_datasets=json.dumps(["images"]),
    image_preprocess_input_mounts=json.dumps(["/opt/dkube/input"]),
    image_preprocess_outputs=json.dumps(["images-preprocessed"]),
    image_preprocess_output_mounts=json.dumps(["/opt/dkube/output"]),
    
    #Clinical split
    clinical_split_script="python clinical_reg/split.py --datatype clinical",
    clinical_split_datasets=json.dumps(["clinical-preprocessed"]),
    clinical_split_input_mounts=json.dumps(["/opt/dkube/input"]),
    clinical_split_outputs=json.dumps(["clinical-train", "clinical-test", "clinical-val"]),
    clinical_split_output_mounts=json.dumps(["/opt/dkube/outputs/train", "/opt/dkube/outputs/test", "/opt/dkube/outputs/val"]),
    
    #Image split
    image_split_script="python clinical_reg/split.py --datatype image",
    image_split_datasets=json.dumps(["images-preprocessed"]),
    image_split_input_mounts=json.dumps(["/opt/dkube/input"]),
    image_split_outputs=json.dumps(["images-train", "images-test", "images-val"]),
    image_split_output_mounts=json.dumps(["/opt/dkube/outputs/train", "/opt/dkube/outputs/test", "/opt/dkube/outputs/val"])	,
    
    #RNA split
    rna_split_script="python clinical_reg/split.py --datatype rna",
    rna_split_datasets=json.dumps(["rna"]),
    rna_split_input_mounts=json.dumps(["/opt/dkube/input"]),
    rna_split_outputs=json.dumps(["rna-train", "rna-test", "rna-val"]),
    rna_split_output_mounts=json.dumps(["/opt/dkube/outputs/train", "/opt/dkube/outputs/test", "/opt/dkube/outputs/val"]),
    
    #Training
    job_group = 'default',
    #Framework. One of tensorflow, pytorch, sklearn
    framework = "tensorflow",
    #Framework version
    version = "2.3.0",
    #In notebook DKUBE_USER_ACCESS_TOKEN is automatically picked up from env variable
    #Or any other custom image name can be supplied.
    #For custom private images, please input username/password
    training_container=json.dumps({'image':'ocdr/dkube-datascience-tf-cpu:v2.3.0-17'}),
    #Name of the workspace in dkube. Update accordingly if different name is used while creating a workspace in dkube.
    training_program="regression",
    #Script to run inside the training container    
    training_script="python clinical_reg/train_nn.py --epochs 5",
    #Input datasets for training. Update accordingly if different name is used while creating dataset in dkube.    
    training_datasets=json.dumps(["clinical-train", "clinical-val", "images-train",
                                  "images-val", "rna-train", "rna-val"]),
    training_input_dataset_mounts=json.dumps(["/opt/dkube/inputs/train/clinical", "/opt/dkube/inputs/val/clinical",
                                      "/opt/dkube/inputs/train/images", "/opt/dkube/inputs/val/images",
                                      "/opt/dkube/inputs/train/rna", "/opt/dkube/inputs/val/rna"]),
    training_outputs=json.dumps(["regression-model"]),
    training_output_mounts=json.dumps(["/opt/dkube/output"]),
    #Request gpus as needed. Val 0 means no gpu, then training_container=docker.io/ocdr/dkube-datascience-tf-cpu:v1.12    
    training_gpus=0,
    #Any envs to be passed to the training program    
    training_envs=json.dumps([{"steps": 100}]),
    
    tuning=json.dumps({}),
    
    #Evaluation
    evaluation_script="python clinical_reg/evaluate.py",
    evaluation_datasets=json.dumps(["clinical-test", "images-test", "rna-test"]),
    evaluation_input_dataset_mounts=json.dumps(["/opt/dkube/inputs/test/clinical", "/opt/dkube/inputs/test/images",
                                      "/opt/dkube/inputs/test/rna"]),
    evaluation_models=json.dumps(["regression-model"]),
    evaluation_input_model_mounts=json.dumps(["/opt/dkube/inputs/model"]),
    
    #Serving
    #Device to be used for serving - dkube mnist example trained on gpu needs gpu for serving else set this param to 'cpu'
    deployment_name='regression-pl',
    serving_device='cpu',
    #Serving image
    serving_image=json.dumps({'image':'ocdr/tensorflowserver:2.3.0'}),
    #Transformer image
    transformer_image=json.dumps({'image':'ocdr/dkube-datascience-tf-cpu:v2.3.0-17'}),
    #Script to execute the transformer
    transformer_code="clinical_reg/transformer.py"):
    
    create_resource = setup_op(user = user, token = auth_token, project_id = project_id)
    
    create_resource.execution_options.caching_strategy.max_cache_staleness = "P0D"
    
    clinical_preprocess = _component('preprocess', 'clinical-preprocess')(container=training_container,
                                      tags=tags, program=training_program, run_script=clinical_preprocess_script,
                                      datasets=clinical_preprocess_datasets, outputs=clinical_preprocess_outputs,
                                      input_dataset_mounts=clinical_preprocess_input_mounts, output_mounts=clinical_preprocess_output_mounts).after(create_resource)
    image_preprocess  = _component('preprocess', 'images-preprocess')(container=training_container,
                                      tags=tags, program=training_program, run_script=image_preprocess_script,
                                      datasets=image_preprocess_datasets, outputs=image_preprocess_outputs,
                                      input_dataset_mounts=image_preprocess_input_mounts, output_mounts=image_preprocess_output_mounts).after(create_resource)
                                      
    clinical_split  = _component('preprocess', 'clinical-split')(container=training_container,
                                      tags=tags, program=training_program, run_script=clinical_split_script,
                                      datasets=clinical_split_datasets, outputs=clinical_split_outputs,
                                      input_dataset_mounts=clinical_split_input_mounts,
                                      output_mounts=clinical_split_output_mounts).after(clinical_preprocess)
                                      
    image_split  = _component('preprocess', 'images-split')(container=training_container,
                                      tags=tags, program=training_program, run_script=image_split_script,
                                      datasets=image_split_datasets, outputs=image_split_outputs,
                                      input_dataset_mounts=image_split_input_mounts,
                                      output_mounts=image_split_output_mounts).after(image_preprocess)
                                      
    rna_split  = _component('preprocess', 'rna-split')(container=training_container,
                                      tags=tags, program=training_program, run_script=rna_split_script,
                                      datasets=rna_split_datasets, outputs=rna_split_outputs,
                                      input_dataset_mounts=rna_split_input_mounts, output_mounts=rna_split_output_mounts).after(create_resource)
                                      
    train       = _component('training', 'regression-model-training')(container=training_container,
                                    tags=tags, program=training_program, run_script=training_script,
                                    datasets=training_datasets, outputs=training_outputs,
                                    input_dataset_mounts=training_input_dataset_mounts,
                                    output_mounts=training_output_mounts,
                                    ngpus=training_gpus,
                                    envs=training_envs,
                                    tuning=tuning, job_group=job_group,
                                    framework=framework, version=version).after(clinical_split).after(image_split).after(rna_split)
    serving     = _component('serving', 'model-serving')(model=train.outputs['artifact'], device=serving_device,
                                name=deployment_name,
                                serving_image=serving_image,
                                transformer_image=transformer_image,
                                transformer_project=training_program,
                                transformer_code=transformer_code).after(train)
    inference   = _component('viewer', 'model-inference')(servingurl=serving.outputs['servingurl'],
                                 servingexample='regression', viewtype='inference').after(serving)
